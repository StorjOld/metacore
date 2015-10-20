import json
import os
import unittest
from hashlib import sha256

import storj
from database import files
from error_codes import *

__author__ = 'karatel'


class AuditFileCase(unittest.TestCase):
    """
    Test files audit.
    """

    url = '/api/audit/'

    def setUp(self):
        """
        Switch to test config.
        Create initial files set in the Upload Dir.
        Create initial records in the 'files' table.
        Remember challenge seed and response.
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
            hash=self.valid_hash, role='000', size=len(self.file_data)
        ).execute().inserted_primary_key

        self.challenge_seed = sha256(b'seed').hexdigest()
        self.challenge_response = sha256(
            self.file_data + self.challenge_seed.encode()
        ).hexdigest()

    def tearDown(self):
        """
        Remove initial files from Upload Dir.
        Remove initial records form the 'files' table.
        """
        os.unlink(self.file_saving_path)
        files.delete().where(files.c.id.in_(self.files_id)).execute()

    def make_request(self, data):
        """
        Make a common request for this Test Case. Get a response.
        :return: Response
        """
        with self.app.test_client() as c:
            response = c.post(
                path=self.url,
                data=data,
            )

        return response

    def test_success_audit(self):
        """
        Audit file with all valid data.
        """
        send_data = {
            'data_hash': self.valid_hash,
            'challenge_seed': self.challenge_seed
        }

        response = self.make_request(send_data)

        self.assertEqual(201, response.status_code,
                         "'Created' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {
                'data_hash': send_data['data_hash'],
                'challenge_seed': send_data['challenge_seed'],
                'challenge_response': self.challenge_response
            },
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

    def test_invalid_hash(self):
        """
        Try to audit file with invalid hash.
        """

        send_data = {
            'data_hash': 'invalid hash',
            'challenge_seed': self.challenge_seed
        }

        response = self.make_request(send_data)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_TRANSFER['INVALID_HASH']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")


if __name__ == '__main__':
    unittest.main()
