import copy
import json
import os.path
import unittest
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch, Mock

from metacore import storj
from metacore.database import files
from metacore.error_codes import *
from metacore.tests import *

__author__ = 'karatel'


class UploadFileCase(unittest.TestCase):
    """
    Test uploading files to the Node.
    """

    url = '/api/files/'

    def setUp(self):
        """
        Switch to test config.
        Remember initial records in the 'files' table.
        Remember initial files set in the Upload Dir.
        Remember initial blacklist content.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True
        self.files = set(tuple(_) for _ in files.select().execute())
        self.stored_files = set(os.listdir(self.app.config['UPLOAD_FOLDER']))

        self.file_data = b'some data'
        valid_hash = sha256(self.file_data).hexdigest()

        valid_signature = test_btctx_api.sign_unicode(test_owner_wif,
                                                      valid_hash)

        self.blocked_data = b'blocked_data'
        self.blocked_hash = sha256(self.blocked_data).hexdigest()
        with open(self.app.config['BLACKLIST_FILE'], 'r+') as fp:
            self.initial_blacklist = fp.read()
            fp.writelines((self.blocked_hash + '\n',))

        self.send_data = {
            'data_hash': valid_hash,
            'file_data': (BytesIO(self.file_data), 'test_file'),
            'file_role': '000'
        }

        self.headers = {
            'sender_address': test_owner_address,
            'signature': valid_signature
        }

        self.patcher = patch('metacore.processor.BTCTX_API', test_btctx_api)
        self.patcher.start()

    def tearDown(self):
        """
        Switch off some test configs.
        Remove new records form the 'files' table.
        Remove new files from Upload Dir.
        Return initial blacklist content.
        """
        self.patcher.stop()

        files.delete().where(
            files.c.hash not in (_[0] for _ in self.files)
        ).execute()

        added_files = set(
            os.listdir(self.app.config['UPLOAD_FOLDER'])
        ) - self.stored_files

        for filename in added_files:
            os.unlink(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))

        with open(self.app.config['BLACKLIST_FILE'], 'w') as fp:
            fp.write(self.initial_blacklist)

    def _get_saved_file_path(self):
        """
        Generate path for file which is expected to be saved.
        :return: file path
        :rtype: str
        """
        return os.path.join(self.app.config['UPLOAD_FOLDER'],
                            self.send_data['data_hash'])

    def _make_request(self, data, headers=None):
        """
        Make a common request for this Test Case. Get a response.
        :return: Response
        """
        if headers is None:
            headers = self.headers

        with self.app.test_client() as c:
            response = c.post(
                path=self.url,
                data=data,
                content_type='multipart/form-data',
                headers=headers
            )

        return response

    def test_success_upload(self):
        """
        Upload file with all valid data.
        """
        response = self._make_request(self.send_data)

        self.assertEqual(201, response.status_code,
                         "'Created' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'data_hash': self.send_data['data_hash'],
             'file_role': self.send_data['file_role']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        uploaded_file_record = files.select(
            files.c.hash == self.send_data['data_hash']
        ).execute().first()

        self.assertIsNotNone(uploaded_file_record,
                             "File record does not exist in the table.")

        self.assertEqual(self.headers['sender_address'],
                         uploaded_file_record.owner,
                         "Sender address has to be stored into 'owner' field.")

        self.assertSetEqual(
            self.files | {tuple(uploaded_file_record)},
            set(tuple(_) for _ in files.select().execute()),
            "Only new record has to be inserted in the database. "
            "No other changes."
        )

        try:
            with open(self._get_saved_file_path(), 'rb') as stored_file:
                self.assertEqual(
                    self.file_data, stored_file.read(),
                    "Stored file data does not match with uploaded one."
                )
        except FileNotFoundError:
            self.assertTrue(False, 'Uploaded file is not saved.')

    def test_invalid_hash(self):
        """
        Try to upload file with invalid SHA-256 hash.
        """
        self.send_data['data_hash'] = 'invalid hash'
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif,
            self.send_data['data_hash']
        )

        response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['INVALID_HASH']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_blocked_hash(self):
        """
        Try to upload file with blacklisted SHA-256 hash.
        """
        self.send_data.update({
            'file_data': (BytesIO(self.blocked_data), 'test_file'),
            'data_hash': self.blocked_hash
        })
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif,
            self.send_data['data_hash']
        )

        response = self._make_request(self.send_data)

        self.assertEqual(404, response.status_code,
                         "'Not Found' status code is expected.")

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_invalid_signature(self):
        """
        Try to upload file with invalid signature.
        """
        self.headers['signature'] = self.headers['signature'].swapcase()
        response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['INVALID_SIGNATURE']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_mismatched_hash(self):
        """
        Try to upload file with mismatched SHA-256 hash.
        """
        self.send_data['data_hash'] = sha256(self.file_data + b'_').hexdigest()
        self.headers['signature'] = test_btctx_api.sign_unicode(
            test_owner_wif, self.send_data['data_hash']
        )

        response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['MISMATCHED_HASH']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_huge_file(self):
        """
        Try to upload too big file.
        """
        mock_config = copy.deepcopy(self.app.config)
        mock_config['MAX_FILE_SIZE'] = len(self.file_data) - 1

        with patch('metacore.storj.app.config', mock_config):
            response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['HUGE_FILE']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_full_disk(self):
        """
        Try to upload file with no enough space on disk.
        """
        mock_config = copy.deepcopy(self.app.config)
        mock_config['NODE'] = Mock(capacity=1)

        with patch('metacore.storj.app.config', mock_config):
            response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['FULL_DISK']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")

    def test_reached_limit(self):
        """
        Try to upload file with bandwidth limit reached.
        """
        mock_config = copy.deepcopy(self.app.config)
        mock_config['NODE'].set_limits(incoming=1)

        with patch('metacore.storj.app.config', mock_config):
            response = self._make_request(self.send_data)

        self.assertEqual(400, response.status_code,
                         "Response has to be marked as 'Bad Request'.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            {'error_code': ERR_TRANSFER['LIMIT_REACHED']},
            json.loads(response.data.decode()),
            "Unexpected response data."
        )

        self.assertSetEqual(
            self.files,
            set(tuple(_) for _ in files.select().execute()),
            "Database has to be unchanged."
        )

        self.assertFalse(os.path.exists(self._get_saved_file_path()),
                         "File should not be saved.")


if __name__ == '__main__':
    unittest.main()
