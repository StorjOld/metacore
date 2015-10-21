import copy
import json
import os.path
import unittest
from hashlib import sha256
from unittest.mock import patch
from urllib.parse import quote_from_bytes

from file_encryptor import convergence

import storj
from database import files
from error_codes import *
from tests import *

__author__ = 'karatel'


class ServeFileCase(unittest.TestCase):
    """
    Test serving files.
    """

    base_url = '/api/files/'

    def setUp(self):
        """
        Switch to test config.
        Create initial files set in the Upload Dir.
        Create initial records in the 'files' table.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True

        self.file_data = b'existing file data'

        temp_hash = sha256(self.file_data).hexdigest()

        file_path = os.path.join(
            self.app.config['UPLOAD_FOLDER'], temp_hash
        )

        with open(file_path, 'wb') as fp:
            fp.write(self.file_data)

        self.key = convergence.encrypt_file_inline(file_path, None)

        with open(file_path, 'rb') as fp:
            self.encrypted_data = fp.read()

        self.data_hash = sha256(self.encrypted_data).hexdigest()
        valid_signature = test_btctx_api.sign_unicode(test_owner_wif,
                                                      self.data_hash)
        self.file_saving_path = os.path.join(self.app.config['UPLOAD_FOLDER'],
                                             self.data_hash)
        os.rename(file_path, self.file_saving_path)

        self.files_id = files.insert().values(
            hash=self.data_hash, role='001', size=len(self.encrypted_data),
            owner=test_owner_address
        ).execute().inserted_primary_key

        self.headers = {
            'sender_address': test_owner_address,
            'signature': valid_signature
        }

        self.query_string = {
            'decryption_key': quote_from_bytes(self.key),
            'file_alias': 'file.txt'
        }

        self.patcher = patch('storj.BTCTX_API', test_btctx_api)
        self.patcher.start()

    def tearDown(self):
        """
        Switch off some test configs.
        Remove initial files from Upload Dir.
        Remove initial records form the 'files' table.
        """
        self.patcher.stop()

        os.unlink(self.file_saving_path)
        files.delete().where(files.c.hash.in_(self.files_id)).execute()

    def make_request(self, is_owner=True):
        """
        Make a common request for this Test Case. Get a response.
        :return: Response
        """

        headers = self.headers if is_owner else {
            'sender_address': test_other_address,
            'signature': test_btctx_api.sign_unicode(test_other_wfi,
                                                     self.data_hash)
        }

        with self.app.test_client() as c:
            response = c.get(
                path=self.base_url + self.data_hash,
                query_string=self.query_string,
                environ_base=headers
            )

        return response

    def test_success_getting_by_owner(self):
        """
        Download public served file by owner with all valid params.
        """

        response = self.make_request()

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")
        self.assertEqual(self.query_string['file_alias'],
                         response.headers['X-Sendfile'],
                         "File has to have selected named.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_success_getting_by_owner_without_alias(self):
        """
        Download public served file by owner without file alias.
        """
        self.query_string.pop('file_alias')

        response = self.make_request()

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")
        self.assertEqual(self.data_hash,
                         response.headers['X-Sendfile'],
                         "File has to have selected named.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_success_getting_public_by_other(self):
        """
        Download public served file by other with all valid params.
        """

        response = self.make_request(False)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")
        self.assertEqual(self.query_string['file_alias'],
                         response.headers['X-Sendfile'],
                         "File has to have selected named.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_success_getting_private_by_owner(self):
        """
        Download private served file by owner with all valid params.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='021').execute()

        response = self.make_request()

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")
        self.assertEqual(self.query_string['file_alias'],
                         response.headers['X-Sendfile'],
                         "File has to have selected named.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_private_by_other(self):
        """
        Try to download private served file by other.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='021').execute()

        response = self.make_request(False)

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_non_served_by_owner(self):
        """
        Try to download public non-served file by owner.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='000').execute()

        response = self.make_request()

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_non_served_by_other(self):
        """
        Try to download public non-served file by other.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='000').execute()

        response = self.make_request(False)

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_hash(self):
        """
        Try to download public served file with invalid hash.
        """
        self.data_hash = 'invalid hash'
        self.headers['signature'] = test_btctx_api.sign_unicode(test_owner_wif,
                                                                self.data_hash)
        response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['INVALID_HASH']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_signature(self):
        """
        Try to download served file with invalid signature.
        """
        self.headers['signature'] = self.headers['signature'].swapcase()
        response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['INVALID_SIGNATURE']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_nonexistent_file(self):
        """
        Try to download nonexistent file.
        """
        self.data_hash = sha256(self.file_data + b'_').hexdigest()
        self.headers['signature'] = test_btctx_api.sign_unicode(test_owner_wif,
                                                                self.data_hash)

        response = self.make_request()

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_bandwidth_limit(self):
        """
        Try to download public served file with bandwidth limit reached.
        """

        mock_config = copy.deepcopy(self.app.config)
        mock_config['NODE'].set_limits(outgoing=1)

        with patch('storj.app.config', mock_config):
            response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['LIMIT_REACHED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")


if __name__ == '__main__':
    unittest.main()
