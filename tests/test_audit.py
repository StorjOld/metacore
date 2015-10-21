import copy
import json
import os
import unittest
from hashlib import sha256
from unittest.mock import patch

import storj
from database import audit, files
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

        self.owner = 'a' * 26

        self.files_id = files.insert().values(
            hash=self.valid_hash, role='000', size=len(self.file_data),
            owner=self.owner
        ).execute().inserted_primary_key

        audit.delete().execute()

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
        files.delete().where(files.c.hash.in_(self.files_id)).execute()
        audit.delete().execute()

    def make_request(self, data, headers=None):
        """
        Make a common request for this Test Case. Get a response.
        :return: Response
        """
        with self.app.test_client() as c:
            response = c.post(
                path=self.url,
                data=data,
                environ_base=headers
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

        headers = {
            'sender_address': self.owner,
            'signature': ''
        }

        response = self.make_request(send_data, headers)

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

        headers = {
            'sender_address': self.owner,
            'signature': ''
        }

        response = self.make_request(send_data, headers)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['INVALID_HASH']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_seed(self):
        """
        Try to audit file with invalid challenge seed.
        """

        send_data = {
            'data_hash': self.valid_hash,
            'challenge_seed': 'invalid seed'
        }

        response = self.make_request(send_data)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['INVALID_SEED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_rate_limit_exceeded_by_owner(self):
        """
        Try to audit file with rate limit exceeded by owner.
        """

        send_data = {
            'data_hash': self.valid_hash,
            'challenge_seed': self.challenge_seed
        }

        headers = {
            'sender_address': self.owner,
            'signature': ''
        }

        mock_config = copy.deepcopy(self.app.config)
        mock_config['AUDIT_RATE_LIMITS']['owner'] = 2

        with patch('storj.app.config', mock_config):
            for i in range(self.app.config['AUDIT_RATE_LIMITS']['owner']):
                self.make_request(send_data, headers)
            response = self.make_request(send_data, headers)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['LIMIT_REACHED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_rate_limit_exceeded_by_other(self):
        """
        Try to audit file with rate limit exceeded by other user.
        """

        send_data = {
            'data_hash': self.valid_hash,
            'challenge_seed': self.challenge_seed
        }

        headers = {
            'sender_address': self.owner + '_',
            'signature': ''
        }

        mock_config = copy.deepcopy(self.app.config)
        mock_config['AUDIT_RATE_LIMITS']['other'] = 2

        with patch('storj.app.config', mock_config):
            for i in range(self.app.config['AUDIT_RATE_LIMITS']['other']):
                self.make_request(send_data, headers)
            response = self.make_request(send_data, headers)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['LIMIT_REACHED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")


if __name__ == '__main__':
    unittest.main()