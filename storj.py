import json
import os
import re
from datetime import datetime
from datetime import timedelta
from hashlib import sha256
from urllib.parse import unquote_to_bytes

from btctxstore import BtcTxStore
from file_encryptor import convergence
from flask import Flask, Response
from flask import abort, jsonify, request, send_from_directory, render_template
from sqlalchemy import and_

from database import audit, files
from error_codes import *
from processor import app, download
from processor import upload


BTCTX_API = BtcTxStore(dryrun=True)

hash_pattern = re.compile(r'^[a-f\d]{64}$')


class Checker:
    """
    Aggregator for common data and params checks.
    """

    def __init__(self, data_hash):
        self.data_hash = data_hash
        self.sender_address = request.environ['sender_address']

        self._checks = {
            'blacklist': self._check_blacklist,
            'file': self._get_file_from_hash,
            'hash': self._check_hash,
            'signature': self._check_signature
        }

    def check_all(self, *check_list):
        """
        Do all selected checks in selected order.
        :return: the first failed check result or None
            if all ones are successful
        :rtype: Response or NoneType
        """
        try:
            return next(filter(None, [self._checks[check_item]()
                                      for check_item in check_list]))
        except StopIteration:
            return None

    def _check_blacklist(self):
        """
        Check if data_hash is in Blacklist.
        :return: 'OK' HTTP Response with nothing or None if hash
            is not in list.
        :rtype: Response or NoneType
        """
        with open(app.config['BLACKLIST_FILE']) as fp:
            if self.data_hash in fp.readlines():
                return Response()

    def _check_hash(self):
        """
        Check if data_hash is a valid SHA-256 hash.
        :return: 'Bad Request' HTTP Response or None if hash is valid.
        :rtype: Response or NoneType
        """
        if not hash_pattern.match(self.data_hash):
            response = jsonify(error_code=ERR_AUDIT['INVALID_HASH'])
            response.status_code = 400
            return response

    def _check_signature(self):
        """
        Check if signature header match with data_hash parameter in request.
        :return: 'Bad Request' HTTP Response or None if signature is valid.
        :rtype: Response or NoneType
        """
        signature_is_valid = BTCTX_API.verify_signature_unicode(
            request.environ['sender_address'],
            request.environ['signature'],
            self.data_hash
        )
        if not signature_is_valid:
            response = jsonify(error_code=ERR_AUDIT['INVALID_SIGNATURE'])
            response.status_code = 400
            return response

    def _get_file_from_hash(self):
        """
        Check if file record with data_hash exists in the `files` table
            and allowed for getting and then store it as self.file.
        :return: 'Not Found' HTTP Response with nothing or None.
        :rtype: Response or RowProxy
        """
        self.file = files.select(
            files.c.hash == self.data_hash
        ).execute().first()

        if not self.file or (
                        self.file.role[1] != '0' and
                        self.file.owner != request.environ['sender_address']
        ):
            response = jsonify(error_code=ERR_AUDIT['NOT_FOUND'])
            response.status_code = 404
            return response


@app.route('/')
def index():
    """
    Index page.
    """
    return render_template('index.html')


@app.route('/api/audit/', methods=['POST'])
def audit_file():
    """
    Audit file.
    Generate challenge response by gotten challenge seed.
    """
    data_hash = request.form['data_hash']

    checker = Checker(data_hash)
    checks_result = checker.check_all('signature', 'hash', 'blacklist')
    if checks_result:
        return checks_result

    challenge_seed = request.form['challenge_seed']
    if not hash_pattern.match(challenge_seed):
        response = jsonify(error_code=ERR_AUDIT['INVALID_SEED'])
        response.status_code = 400
        return response

    file_check_result = checker.check_all('file')
    if file_check_result:
        return file_check_result

    file = checker.file
    sender_address = checker.sender_address
    is_owner = sender_address == file.owner

    current_attempts = audit.select(
        and_(
            audit.c.file_hash == data_hash,
            audit.c.is_owners == is_owner,
            audit.c.made_at >= datetime.now() - timedelta(hours=1)
        )
    ).count().scalar()

    limits_section = 'owner' if is_owner else 'other'
    if current_attempts >= app.config['AUDIT_RATE_LIMITS'][limits_section]:
        response = jsonify(error_code=ERR_AUDIT['LIMIT_REACHED'])
        response.status_code = 400
        return response

    audit.insert().values(file_hash=data_hash, is_owners=is_owner).execute()

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
              'rb') as f:
        file_data = f.read()
    challenge_response = sha256(file_data +
                                challenge_seed.encode()).hexdigest()

    response = jsonify(
        data_hash=data_hash,
        challenge_seed=challenge_seed,
        challenge_response=challenge_response
    )
    response.status_code = 201
    return response


@app.route('/api/files/<data_hash>', methods=['GET'])
def download_file(data_hash):
    """
    Download stored file from the Node.
    Check if data_hash is valid SHA-256 hash matched with existing file.
    :param data_hash: SHA-256 hash for needed file.
    """

    decryption_key = request.values.get('decryption_key')
    if decryption_key:
        decryption_key = unquote_to_bytes(decryption_key)

    result = download(
        data_hash,
        request.environ['sender_address'],
        request.environ['signature'],
        decryption_key
    )

    if isinstance(result, int):
        if result == ERR_BLACKLIST:
            abort(404)

        if result == ERR_TRANSFER['LOST_FILE']:
            with open(app.config['PEERS_FILE']) as peers_file:
                response = jsonify(peers=[_.strip() for _ in peers_file])
                response.status_code = 404
        else:
            response = jsonify(error_code=result)
            response.status_code = (404 if result == ERR_TRANSFER['NOT_FOUND']
                                    else 400)

        return response

    response = Response(
        result,
        200,
        {'X-Sendfile': request.values.get('file_alias', data_hash),
         'Content-Type': 'application/octet-stream'}
    )
    return response


@app.route('/api/files/', methods=['GET'])
def files_info():
    """
    Get files hash list.
    """
    with open(app.config['BLACKLIST_FILE']) as fp:
        blocked_hashes = tuple(fp.readlines())
    hash_list = [_['hash'] for _ in files.select().execute()
                 if _['hash'] not in blocked_hashes]
    return json.dumps(hash_list), 200, {'Content-Type': 'application/json'}


@app.route('/api/nodes/me/', methods=['GET'])
def status_info():
    """
    Get the Node status info.
    """
    return jsonify(app.config['NODE'].info)


@app.route('/api/files/', methods=['POST'])
def upload_file():
    """
    Upload file to the Node.
    """

    file_role = request.form['file_role']
    data_hash = request.form['data_hash']

    error_code = upload(
        request.files['file_data'].stream,
        data_hash,
        file_role,
        request.environ['sender_address'],
        request.environ['signature']
    )
    if error_code:
        if error_code == ERR_BLACKLIST:
            abort(404)

        response = jsonify(error_code=error_code)
        response.status_code = 400
        return response
    else:
        response = jsonify(data_hash=data_hash, file_role=file_role)
        response.status_code = 201
        return response


if __name__ == '__main__':
    app.run(host='0.0.0.0')
