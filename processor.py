import os

from flask import Flask

from database import files


app = Flask(__name__)
app.config.from_object('config')


def upload(data: bytes, data_hash: str, role: str, sender: str):
    """
    Save data to file named as data_hash and add a coincident record  with a
    specific role in the database.

    :param data: binary file data
    :param data_hash: SHA-256 hash for data
    :param role: file role
    :param sender: file sender's Bitcoin address
    """
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
              'wb') as file_to_save:
        file_to_save.write(data)

    files.insert().values(
        hash=data_hash,
        role=role,
        size=len(data),
        owner=sender
    ).execute()
