import copy
import json
import os.path
import unittest
from hashlib import sha256
from unittest.mock import patch

import storj
from database import files
from error_codes import *
from tests import *

__author__ = 'karatel'


class DownloadFileCase(unittest.TestCase):
    """
    Test downloading files to the Node.
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
        self.data_hash = sha256(self.file_data).hexdigest()
        valid_signature = test_btctx_api.sign_unicode(test_owner_wif,
                                                      self.data_hash)

        self.file_saving_path = os.path.join(
            self.app.config['UPLOAD_FOLDER'], self.data_hash
        )

        with open(self.file_saving_path, 'wb') as stored_file:
            stored_file.write(self.file_data)

        self.files_id = files.insert().values(
            hash=self.data_hash, role='000', size=len(self.file_data),
            owner=test_owner_address
        ).execute().inserted_primary_key

        self.headers = {
            'sender_address': test_owner_address,
            'signature': valid_signature
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
                environ_base=headers
            )

        return response

    def test_success_download_public_by_owner(self):
        """
        Download public file by owner with all valid params.
        """

        response = self.make_request()

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_success_download_public_by_other(self):
        """
        Download public file by other with all valid params.
        """

        response = self.make_request(False)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_success_download_private_by_owner(self):
        """
        Download private file by owner with all valid params.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='020').execute()

        response = self.make_request()

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_private_by_other(self):
        """
        Try to download private file by other.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='020').execute()

        response = self.make_request(False)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_hash(self):
        """
        Try to download file with invalid hash.
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
        Try to download file with invalid signature.
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

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_bandwidth_limit(self):
        """
        Try to download file with bandwidth limit reached.
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
