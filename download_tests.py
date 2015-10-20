import copy
import json
import os.path
import unittest
from hashlib import sha256
from unittest.mock import patch

import storj
from database import files
from error_codes import *

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
        self.valid_hash = sha256(self.file_data).hexdigest()
        self.file_saving_path = os.path.join(
            self.app.config['UPLOAD_FOLDER'], self.valid_hash
        )

        with open(self.file_saving_path, 'wb') as stored_file:
            stored_file.write(self.file_data)

        self.files_id = files.insert().values(
            hash=self.valid_hash, role='000', size=len(self.file_data),
            owner='a' * 26
        ).execute().inserted_primary_key

    def tearDown(self):
        """
        Remove initial files from Upload Dir.
        Remove initial records form the 'files' table.
        """
        os.unlink(self.file_saving_path)
        files.delete().where(files.c.hash.in_(self.files_id)).execute()

    def make_request(self, data_hash):
        """
        Make a common request for this Test Case. Get a response.
        :return: Response
        """
        with self.app.test_client() as c:
            response = c.get(path=self.base_url + data_hash)

        return response

    def test_success_download(self):
        """
        Download file with all valid params.
        """

        response = self.make_request(self.valid_hash)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/octet-stream', response.content_type,
                         "Has to be an octet-stream.")

        self.assertEqual(response.data, self.file_data,
                         "Stored file content is expected.")

    def test_invalid_hash(self):
        """
        Try to download file with invalid hash.
        """

        response = self.make_request('invalid hash')

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['INVALID_HASH']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_nonexistent_file(self):
        """
        Try to download nonexistent file.
        """

        response = self.make_request(sha256(self.file_data + b'_').hexdigest())

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
            response = self.make_request(self.valid_hash)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['LIMIT_REACHED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")


if __name__ == '__main__':
    unittest.main()
