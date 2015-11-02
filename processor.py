import os
import re
from hashlib import sha256

from btctxstore import BtcTxStore
from file_encryptor import convergence
from flask import Flask

from database import files
from error_codes import *

app = Flask(__name__)
app.config.from_object('config')

BTCTX_API = BtcTxStore(dryrun=True)

hash_pattern = re.compile(r'^[a-f\d]{64}$')


class Checker:
    """
    Aggregator for common data and params checks.
    """

    def __init__(self, data_hash: str, sender_address: str, signature: str):
        self.data_hash = data_hash
        self.sender_address = sender_address
        self.signature = signature

        self._checks = {
            'blacklist': self._check_blacklist,
            'file': self._get_file_from_hash,
            'hash': self._check_hash,
            'signature': self._check_signature
        }

    def check_all(self, *check_list):
        """
        Do all selected checks in selected order.
        :param check_list: names of needed checks
        :return: error code of the first failed check result or None
            if all ones are successful
        """
        try:
            return next(filter(None, [self._checks[check_item]()
                                      for check_item in check_list]))
        except StopIteration:
            return None

    def _check_blacklist(self):
        """
        Check if data_hash is in Blacklist.
        :return: 'Blacklist' error code or None if hash is not in list.
        """
        with open(app.config['BLACKLIST_FILE']) as fp:
            if self.data_hash in fp.readlines():
                return ERR_BLACKLIST

    def _check_hash(self):
        """
        Check if data_hash is a valid SHA-256 hash.
        :return: 'Invalid Hash' error code or None if hash is valid.
        """
        if not hash_pattern.match(self.data_hash):
            return ERR_AUDIT['INVALID_HASH']

    def _check_signature(self):
        """
        Check if signature header match with data_hash parameter in request.
        :return: 'Invalid Signature' error code or None if signature is valid.
        """
        signature_is_valid = BTCTX_API.verify_signature_unicode(
            self.sender_address,
            self.signature,
            self.data_hash
        )
        if not signature_is_valid:
            return ERR_AUDIT['INVALID_SIGNATURE']

    def _get_file_from_hash(self):
        """
        Check if file record with data_hash exists in the `files` table
            and allowed for getting and then store it as self.file.
        :return: 'Not Found' error code or None if the record exists.
        :rtype: Response or RowProxy
        """
        self.file = files.select(
            files.c.hash == self.data_hash
        ).execute().first()

        if not self.file or (
                        self.file.role[1] != '0' and
                        self.file.owner != self.sender_address
        ):
            return ERR_AUDIT['NOT_FOUND']


def download(data_hash: str, sender: str, signature: str,
             decryption_key: bytes = None):
    """
    Check if data_hash is valid SHA-256 hash matched with existing file.
    Download stored file from the Node.
    :param data_hash: SHA-256 hash for needed file
    :param sender: file sender's BitCoin address
    :param signature: data signature
    :param decryption_key: key for decrypt stored file
    :return: file data generator
    """
    node = app.config['NODE']

    checker = Checker(data_hash, sender, signature)
    checks_result = checker.check_all('signature', 'hash', 'blacklist', 'file')
    if checks_result:
        return checks_result

    file = checker.file
    if node.limits['outgoing'] is not None and (
                file.size > node.limits['outgoing'] - node.current['outgoing']
    ):
        return ERR_TRANSFER['LIMIT_REACHED']

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], data_hash)
    if not os.path.exists(file_path):
        return ERR_TRANSFER['LOST_FILE']

    if decryption_key:
        if file.role[2] == '1':
            return convergence.decrypt_generator(file_path, decryption_key)
        else:
            return ERR_TRANSFER['NOT_FOUND']

    return open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash), 'rb')


def files_list() -> list:
    """
    Get list of files hashes stored on the Node.
    :return: list of hashes
    """
    with open(app.config['BLACKLIST_FILE']) as fp:
        blocked_hashes = tuple(fp.readlines())
    hash_list = [_['hash'] for _ in files.select().execute()
                 if _['hash'] not in blocked_hashes]
    return hash_list


def upload(file, data_hash: str, role: str, sender: str,
           signature: str):
    """
    Check if data_hash is valid SHA-256 hash matched with uploading file.
    Check file size.
    Save uploaded file to the Upload Dir and insert a record in the 'files'
    table.

    :param file: file-like object with binary data
    :param data_hash: SHA-256 hash for data
    :param role: file role
    :param sender: file sender's BitCoin address
    :param signature: data signature
    """
    node = app.config['NODE']
    checker = Checker(data_hash, sender, signature)
    checks_result = checker.check_all('signature', 'hash', 'blacklist')
    if checks_result:
        return checks_result

    file_data = file.read()
    file_size = len(file_data)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    if file_size > app.config['MAX_FILE_SIZE']:
        return ERR_TRANSFER['HUGE_FILE']

    if file_size > node.capacity:
        return ERR_TRANSFER['FULL_DISK']

    if node.limits['incoming'] is not None and (
                file_size > node.limits['incoming'] - node.current['incoming']
    ):
        return ERR_TRANSFER['LIMIT_REACHED']

    if data_hash != sha256(file_data).hexdigest():
        return ERR_TRANSFER['MISMATCHED_HASH']

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
              'wb') as file_to_save:
        file_to_save.write(file_data)

    files.insert().values(
        hash=data_hash,
        role=role,
        size=len(file_data),
        owner=sender
    ).execute()
