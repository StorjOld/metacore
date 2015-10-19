import os

from flask import Flask, jsonify, request

from database import files

app = Flask(__name__)
app.config.from_object('config')


@app.route('/api/files/', methods=['POST'])
def upload_file():
    """
    Upload file to the Node.
    """
    file_data = request.files['file_data'].stream.read()

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with open(
            os.path.join(app.config['UPLOAD_FOLDER'],
                         request.form['data_hash']),
            'wb'
    ) as file_to_save:
        file_to_save.write(file_data)

    files.insert().values(
        hash=request.form['data_hash'],
        role=request.form['file_role'],
        size=len(file_data)
    ).execute()

    response = jsonify(data_hash=request.form['data_hash'],
                       file_role=request.form['file_role'])
    response.status_code = 201

    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0')
