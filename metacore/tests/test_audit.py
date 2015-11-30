from __future__ import (
    generators,
    division,
    absolute_import,
    with_statement,
    print_function,
    unicode_literals,
    nested_scopes
)
import sys
import copy
import json
import os
import unittest
from hashlib import sha256

if sys.version_info.major == 3:
    from unittest.mock import patch
else:
    from mock import patch

from metacore import storj
from metacore.database import audit, files
from metacore.error_codes import *
from metacore.tests import *

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
        Remember initial blacklist content.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True

        self.file_data = b'existing file data'
        self.data_hash = sha256(self.file_data).hexdigest()
        valid_signature = test_btctx_api.sign_unicode(test_owner_wif,
                                                      self.data_hash)

        self.blocked_data = b'blocked_data'
        self.blocked_hash = sha256(self.blocked_data).hexdigest()
        with open(self.app.config['BLACKLIST_FILE'], 'r+') as fp:
            self.initial_blacklist = fp.read()
            fp.writelines((self.blocked_hash + '\n',))

        self.file_saving_path = os.path.join(
            self.app.config['UPLOAD_FOLDER'], self.data_hash
        )

        with open(self.file_saving_path, 'wb') as stored_file:
            stored_file.write(self.file_data)

        self.owner = test_owner_address

        self.files_id = files.insert().values(
            hash=self.data_hash, role='000', size=len(self.file_data),
            owner=self.owner
        ).execute().inserted_primary_key

        audit.delete().execute()

        self.challenge_seed = sha256(b'seed').hexdigest()
        self.challenge_response = sha256(
            self.file_data + self.challenge_seed.encode()
        ).hexdigest()

        self.send_data = {
            'data_hash': self.data_hash,
            'challenge_seed': self.challenge_seed
        }

        self.headers = {
            'sender_address': self.owner,
            'signature': valid_signature
        }

        self.other = test_other_address
        self.other_signature = test_btctx_api.sign_unicode(test_other_wfi,
                                                           self.data_hash)

        self.patcher = patch('metacore.processor.BTCTX_API', test_btctx_api)
        self.patcher.start()

    def tearDown(self):
        """
        Switch off some test configs.
        Remove initial files from Upload Dir.
        Remove initial records form the 'files' table.
        Return initial blacklist content.
        """
        self.patcher.stop()

        try:
            os.unlink(self.file_saving_path)
        except:
            pass

        files.delete().where(files.c.hash.in_(self.files_id)).execute()
        audit.delete().execute()

        with open(self.app.config['BLACKLIST_FILE'], 'w') as fp:
            fp.write(self.initial_blacklist)

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
            response = c.post(
                path=self.url,
                data=self.send_data,
                headers=headers
            )

        return response

    def test_success_audit_public_by_owner(self):
        """
        Audit public file by owner with all valid data.
        """

        response = self.make_request()

        self.assertEqual(201, response.status_code,
                         "'Created' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {
                'data_hash': self.send_data['data_hash'],
                'challenge_seed': self.send_data['challenge_seed'],
                'challenge_response': self.challenge_response
            },
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

    def test_success_audit_public_by_other(self):
        """
        Audit public file by other with all valid data.
        """
        response = self.make_request(False)

        self.assertEqual(201, response.status_code,
                         "'Created' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {
                'data_hash': self.send_data['data_hash'],
                'challenge_seed': self.send_data['challenge_seed'],
                'challenge_response': self.challenge_response
            },
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

    def test_success_audit_private_by_owner(self):
        """
        Audit private file by owner with all valid data.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='020').execute()

        response = self.make_request()

        self.assertEqual(201, response.status_code,
                         "'Created' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {
                'data_hash': self.send_data['data_hash'],
                'challenge_seed': self.send_data['challenge_seed'],
                'challenge_response': self.challenge_response
            },
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

    def test_blocked_hash(self):
        """
        Try to audit file with blacklisted SHA-256 hash.
        """
        self.send_data['data_hash'] = self.blocked_hash
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif, self.send_data['data_hash']
        )
        response = self.make_request()

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")

    def test_private_by_other(self):
        """
        Try to audit private file by other.
        """
        files.update().where(
            files.c.hash == self.data_hash
        ).values(role='020').execute()

        response = self.make_request(False)

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_hash(self):
        """
        Try to audit file with invalid hash.
        """

        self.send_data['data_hash'] = 'invalid hash'
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif, self.send_data['data_hash']
        )
        response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['INVALID_HASH']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_signature(self):
        """
        Try to audit file with invalid signature.
        """

        self.headers['signature'] = self.headers['signature'].swapcase()
        response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['INVALID_SIGNATURE']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_nonexistent_file(self):
        """
        Try to audit nonexistent file.
        """
        self.send_data['data_hash'] = sha256(self.file_data + b'_').hexdigest()
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif, self.send_data['data_hash']
        )

        response = self.make_request()

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['NOT_FOUND']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_invalid_seed(self):
        """
        Try to audit file with invalid challenge seed.
        """

        self.send_data['challenge_seed'] = 'invalid seed'
        response = self.make_request()

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['INVALID_SEED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_lost_file(self):
        """
        Try to download lost file.
        """
        os.unlink(self.file_saving_path)

        response = self.make_request()

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        with open(self.app.config['PEERS_FILE']) as fp:
            peers = [_.strip() for _ in fp]

        self.assertDictEqual({'peers': peers},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")

    def test_rate_limit_exceeded_by_owner(self):
        """
        Try to audit file with rate limit exceeded by owner.
        """
        mock_config = copy.deepcopy(self.app.config)
        mock_config['AUDIT_RATE_LIMITS']['owner'] = 2

        with patch('metacore.storj.app.config', mock_config):
            for i in range(self.app.config['AUDIT_RATE_LIMITS']['owner']):
                self.make_request()
            response = self.make_request()

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
        mock_config = copy.deepcopy(self.app.config)
        mock_config['AUDIT_RATE_LIMITS']['other'] = 2

        with patch('metacore.storj.app.config', mock_config):
            for i in range(self.app.config['AUDIT_RATE_LIMITS']['other']):
                self.make_request(False)
            response = self.make_request(False)

        self.assertEqual(400, response.status_code,
                         "'Bad Request' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON.")

        self.assertDictEqual({'error_code': ERR_AUDIT['LIMIT_REACHED']},
                             json.loads(response.data.decode()),
                             "Unexpected response data.")


if __name__ == '__main__':
    unittest.main()
