import json
import os
import re
from datetime import datetime
from datetime import timedelta
from hashlib import sha256

from btctxstore import BtcTxStore
from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import and_

from database import audit, files
from error_codes import *

app = Flask(__name__)
app.config.from_object('config')

BTCTX_API = BtcTxStore(dryrun=True)

hash_pattern = re.compile(r'^[a-f\d]{64}$')


@app.route('/api/audit/', methods=['POST'])
def audit_file():
    """
    Audit file.
    Generate challenge response by gotten challenge seed.
    """
    data_hash = request.form['data_hash']

    sender_address = request.environ['sender_address']
    signature_is_valid = BTCTX_API.verify_signature_unicode(
        sender_address,
        request.environ['signature'],
        request.form['data_hash']
    )
    if not signature_is_valid:
        response = jsonify(error_code=ERR_AUDIT['INVALID_SIGNATURE'])
        response.status_code = 400
        return response

    if not hash_pattern.match(data_hash):
        response = jsonify(error_code=ERR_AUDIT['INVALID_HASH'])
        response.status_code = 400
        return response

    challenge_seed = request.form['challenge_seed']

    if not hash_pattern.match(challenge_seed):
        response = jsonify(error_code=ERR_AUDIT['INVALID_SEED'])
        response.status_code = 400
        return response

    sender = request.environ['sender_address']

    file = files.select(files.c.hash == data_hash).execute().first()

    if not file or file.role[1] != '0' and file.owner != sender_address:
        response = jsonify(error_code=ERR_AUDIT['INVALID_HASH'])
        response.status_code = 400
        return response

    is_owner = sender == file.owner

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

    with open(
            os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
            'rb'
    ) as f:
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
    """
    node = app.config['NODE']

    sender_address = request.environ['sender_address']
    signature_is_valid = BTCTX_API.verify_signature_unicode(
        sender_address,
        request.environ['signature'],
        data_hash
    )
    if not signature_is_valid:
        response = jsonify(error_code=ERR_TRANSFER['INVALID_SIGNATURE'])
        response.status_code = 400
        return response

    if not hash_pattern.match(data_hash):
        response = jsonify(error_code=ERR_TRANSFER['INVALID_HASH'])
        response.status_code = 400
        return response

    file = files.select(files.c.hash == data_hash).execute().first()

    if not file or file.role[1] != '0' and file.owner != sender_address:
        response = jsonify(error_code=ERR_TRANSFER['NOT_FOUND'])
        response.status_code = 400
        return response

    if node.limits['outgoing'] is not None and (
                file.size > node.limits['outgoing'] - node.current['outgoing']
    ):
        response = jsonify(error_code=ERR_TRANSFER['LIMIT_REACHED'])
        response.status_code = 400
        return response

    return send_from_directory(app.config['UPLOAD_FOLDER'], data_hash)


@app.route('/api/files/', methods=['GET'])
def files_info():
    """
    Get files hash list.
    """
    hash_list = [_['hash'] for _ in files.select().execute()]
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
    Check if data_hash is valid SHA-256 hash matched with uploading file.
    Check file size.
    Save uploaded file to the Upload Dir and insert a record in the 'files'
    table.
    """
    node = app.config['NODE']

    sender_address = request.environ['sender_address']
    signature_is_valid = BTCTX_API.verify_signature_unicode(
        sender_address,
        request.environ['signature'],
        request.form['data_hash']
    )
    if not signature_is_valid:
        response = jsonify(error_code=ERR_TRANSFER['INVALID_SIGNATURE'])
        response.status_code = 400
        return response

    if not hash_pattern.match(request.form['data_hash']):
        response = jsonify(error_code=ERR_TRANSFER['INVALID_HASH'])
        response.status_code = 400
        return response

    file_data = request.files['file_data'].stream.read()
    file_size = len(file_data)

    if file_size > app.config['MAX_FILE_SIZE']:
        response = jsonify(error_code=ERR_TRANSFER['HUGE_FILE'])
        response.status_code = 400
        return response

    if file_size > node.capacity:
        response = jsonify(error_code=ERR_TRANSFER['FULL_DISK'])
        response.status_code = 400
        return response

    if node.limits['incoming'] is not None and (
                file_size > node.limits['incoming'] - node.current['incoming']
    ):
        response = jsonify(error_code=ERR_TRANSFER['LIMIT_REACHED'])
        response.status_code = 400
        return response

    data_hash = sha256(file_data).hexdigest()

    if data_hash != request.form['data_hash']:
        response = jsonify(error_code=ERR_TRANSFER['MISMATCHED_HASH'])
        response.status_code = 400
        return response

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
              'wb') as file_to_save:
        file_to_save.write(file_data)

    files.insert().values(
        hash=data_hash,
        role=request.form['file_role'],
        size=len(file_data),
        owner=sender_address
    ).execute()

    response = jsonify(data_hash=data_hash,
                       file_role=request.form['file_role'])
    response.status_code = 201

    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0')
