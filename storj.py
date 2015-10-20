import os
import re
from hashlib import sha256

from flask import Flask, jsonify, request, send_from_directory

from database import files
from error_codes import *

app = Flask(__name__)
app.config.from_object('config')

hash_pattern = re.compile(r'^[a-f\d]{64}$')


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

    if not hash_pattern.match(request.form['data_hash']):
        response = jsonify(error_code=ERR_INVALID_HASH)
        response.status_code = 400
        return response

    file_data = request.files['file_data'].stream.read()
    file_size = len(file_data)

    if file_size > app.config['MAX_FILE_SIZE']:
        response = jsonify(error_code=ERR_HUGE_FILE)
        response.status_code = 400
        return response

    if file_size > node.capacity:
        response = jsonify(error_code=ERR_FULL_DISK)
        response.status_code = 400
        return response

    if node.limits['incoming'] is not None and (
                file_size > node.limits['incoming'] - node.current['incoming']
    ):
        response = jsonify(error_code=ERR_LIMIT_REACHED)
        response.status_code = 400
        return response

    data_hash = sha256(file_data).hexdigest()

    if data_hash != request.form['data_hash']:
        response = jsonify(error_code=ERR_MISMATCHED_HASH)
        response.status_code = 400
        return response

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
              'wb') as file_to_save:
        file_to_save.write(file_data)

    files.insert().values(
        hash=data_hash,
        role=request.form['file_role'],
        size=len(file_data)
    ).execute()

    response = jsonify(data_hash=data_hash,
                       file_role=request.form['file_role'])
    response.status_code = 201

    return response


@app.route('/api/files/<data_hash>', methods=['GET'])
def download_file(data_hash):
    """
    Download stored file from the Node.
    Check if data_hash is valid SHA-256 hash matched with existing file.
    """
    node = app.config['NODE']

    if not hash_pattern.match(data_hash):
        response = jsonify(error_code=ERR_INVALID_HASH)
        response.status_code = 400
        return response

    file = files.select(files.c.hash == data_hash).execute().first()

    if not file:
        response = jsonify(error_code=ERR_NOT_FOUND)
        response.status_code = 400
        return response

    if node.limits['outgoing'] is not None and (
                file.size > node.limits['outgoing'] - node.current['outgoing']
    ):
        response = jsonify(error_code=ERR_LIMIT_REACHED)
        response.status_code = 400
        return response

    return send_from_directory(app.config['UPLOAD_FOLDER'], data_hash)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
