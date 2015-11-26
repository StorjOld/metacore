import json
import re
from urllib.parse import unquote_to_bytes

from flask import Response
from flask import abort, jsonify, request, render_template

from metacore.error_codes import *
from metacore.processor import app
from metacore.processor import audit_data, download, files_list, node_info, upload


hash_pattern = re.compile(r'^[a-f\d]{64}$')


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
    challenge_seed = request.form['challenge_seed']

    result = audit_data(
        data_hash,
        challenge_seed,
        request.headers.get('sender_address'),
        request.headers.get('signature')
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

    response = jsonify(
        data_hash=data_hash,
        challenge_seed=challenge_seed,
        challenge_response=result
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
        request.headers.get('sender_address'),
        request.headers.get('signature'),
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
    hash_list = files_list()
    return json.dumps(hash_list), 200, {'Content-Type': 'application/json'}


@app.route('/api/nodes/me/', methods=['GET'])
def status_info():
    """
    Get the Node status info.
    """
    return jsonify(node_info())


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
        request.headers.get('sender_address'),
        request.headers.get('signature')
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


def main():
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    main()
