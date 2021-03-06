import os
import re
import binascii
from datetime import datetime
from datetime import timedelta
from hashlib import sha256

from btctxstore import BtcTxStore
from file_encryptor import convergence
from flask import Flask
from sqlalchemy import and_

from metacore.database import audit, files
from metacore.error_codes import *
from metacore import config

app = Flask(__name__)
app.config.from_object(config)

BTCTX_API = BtcTxStore(testnet=True, dryrun=True)

hash_pattern = re.compile(r'^[a-f\d]{64}$')


class Checker:
    """
    Aggregator for common data and params checks.
    """

    def __init__(self, data_hash, sender_address, signature):
        self.data_hash = data_hash
        self.sender_address = sender_address
        self.signature = signature

        self._checks = {
            'blacklist': self._check_blacklist,
            'file': self._get_file_from_hash,
            'hash': self._check_hash,
            'signature': self._check_signature,
            'double_uploading': self._check_file_existence
        }

    def check_all(self, *check_list):
        """
        Do all selected checks in selected order.
        :param check_list: names of needed checks
        :return: error code of the first failed check result or None
            if all ones are successful
        """
        try:
            return next(iter(filter(None, [self._checks[check_item]()
                                      for check_item in check_list
                                      ])))
        except StopIteration:
            return None

    def _check_blacklist(self):
        """
        Check if data_hash is in Blacklist.
        :return: 'Blacklist' error code or None if hash is not in list.
        """
        with open(app.config['BLACKLIST_FILE']) as fp:
            if self.data_hash in (_.strip() for _ in fp.readlines()):
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

    def _check_file_existence(self):
        """
        Check if file with data_hash is already downloaded on the Node.
        Prevent repeated downloading the same data.

        :return:

        """
        self.file = files.select(
            files.c.hash == self.data_hash
        ).execute().first()

        if self.file:
            return ERR_TRANSFER['REPEATED_UPLOAD']


def audit_data(data_hash, seed, sender, signature):
    """
    Generate challenge response by gotten challenge seed.
    :param data_hash: SHA-256 hash of the file
    :param seed: challenge seed
    :param sender: sender's BitCoin address
    :param signature: data signature
    :return: challenge response generated from the file data and seed
    """
    checker = Checker(data_hash, sender, signature)
    checks_result = checker.check_all('signature', 'hash', 'blacklist')
    if checks_result:
        return checks_result

    if not hash_pattern.match(seed):
        return ERR_AUDIT['INVALID_SEED']

    file_check_result = checker.check_all('file')
    if file_check_result:
        return file_check_result

    file = checker.file
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
        return ERR_AUDIT['LIMIT_REACHED']

    audit.insert().values(file_hash=data_hash, is_owners=is_owner).execute()

    try:
        with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash),
                  'rb') as f:
            file_data = f.read()
        return sha256(file_data + seed.encode()).hexdigest()
    except:
        return ERR_TRANSFER['LOST_FILE']


def download(data_hash, sender, signature, decryption_key):
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
    if not (signature and sender):
        checks_result_unauthenticated = checker.check_all('hash', 'blacklist',
                                                          'file')
        if checks_result_unauthenticated:
            return checks_result_unauthenticated
        if checker.file.role not in ('001', '101'):
            return ERR_TRANSFER['INVALID_SIGNATURE']
    else:
        checks_result_authenticated = checker.check_all('hash', 'blacklist',
                                                        'file', 'signature')
        if checks_result_authenticated:
            return checks_result_authenticated

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
            try:
                decryption_key = binascii.unhexlify(decryption_key)
                # test on decryption_key validness
                test_decrypt_data_generator = convergence.decrypt_generator(
                        file_path, decryption_key)
                next(test_decrypt_data_generator)
                decrypt_data_generator = convergence.decrypt_generator(
                        file_path, decryption_key)
                return decrypt_data_generator
            except (binascii.Error, ValueError):
                return ERR_TRANSFER['INVALID_DECRYPTION_KEY']
        else:
            return ERR_TRANSFER['NOT_FOUND']

    with open(os.path.join(app.config['UPLOAD_FOLDER'], data_hash), 'rb') as f:
        returned_data = f.read()

    return returned_data


def files_list():
    """
    Get list of files hashes stored on the Node.
    :return: list of hashes
    """
    with open(app.config['BLACKLIST_FILE']) as fp:
        blocked_hashes = [_.strip() for _ in fp.readlines()]
    hash_list = [_['hash'] for _ in files.select().execute()
                 if _['hash'] not in blocked_hashes]
    return hash_list


def node_info():
    """
    Get the Node info.
    :return: Node info dict
    """
    return app.config['NODE'].info


def upload(file, data_hash, role, sender, signature):
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

    checks_result = checker.check_all('double_uploading')
    if checks_result:
        return {'file_role': checker.file.role}

    checks_result = checker.check_all('signature', 'hash', 'blacklist')
    if checks_result:
        return checks_result

    file_data = file.read()
    file_size = len(file_data)

    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

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
