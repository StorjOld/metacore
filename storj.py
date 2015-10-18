import json

from flask import Flask, jsonify

from database import files

app = Flask(__name__)
app.config.from_object('config')


@app.route('/api/files/', methods=['GET'])
def files_info():
    hash_list = tuple(_['hash'] for _ in files.select().execute())
    return json.dumps(hash_list), 200, {'Content-Type': 'application/json'}


@app.route('/api/nodes/me/', methods=['GET'])
def status_info():
    return jsonify(app.config['NODE'].info)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
