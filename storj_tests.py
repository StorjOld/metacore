import json
import os.path
import unittest
from hashlib import sha256
from io import BytesIO

import storj
from database import files

__author__ = 'karatel'


class UploadFileCase(unittest.TestCase):
    """
    Test uploading files to the Node.
    """

    def setUp(self):
        """
        Switch to test config.
        Remember initial records in the 'files' table.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True
        self.files = set(tuple(_) for _ in files.select().execute())
        self.stored_files = set(os.listdir(self.app.config['UPLOAD_FOLDER']))

    def tearDown(self):
        """
        Remove records form the 'files' table.
        """
        files.delete().where(
            files.c.id not in (_[0] for _ in self.files)
        ).execute()

        added_files = set(
            os.listdir(self.app.config['UPLOAD_FOLDER'])
        ) - self.stored_files

        for filename in added_files:
            os.unlink(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))

    def test_success_upload(self):
        file_data = b'some data'
        send_data = {
            'data_hash': sha256(file_data).hexdigest(),
            'file_data': (BytesIO(file_data), 'test_file'),
            'file_role': '000'
        }

        with self.app.test_client() as c:
            response = c.post(
                path='/api/files/',
                data=send_data,
                content_type='multipart/form-data'
            )

        self.assertEqual(201, response.status_code)
        self.assertEqual('application/json', response.content_type)

        self.assertDictEqual(
            {'data_hash': send_data['data_hash'],
             'file_role': send_data['file_role']},
            json.loads(response.data.decode())
        )

        uploaded_file_record = files.select(
            files.c.hash == send_data['data_hash']
        ).execute().first()

        self.assertIsNotNone(uploaded_file_record,
                             "File record does not exist in the table.")

        self.assertSetEqual(
            self.files | {tuple(uploaded_file_record)},
            set(tuple(_) for _ in files.select().execute())
        )

        try:
            with open(
                    os.path.join(self.app.config['UPLOAD_FOLDER'],
                                 send_data['data_hash']),
                    'rb'
            ) as stored_file:
                self.assertEqual(file_data, stored_file.read())
        except FileNotFoundError:
            self.assertTrue(False, 'Uploaded file is not saved.')


if __name__ == '__main__':
    unittest.main()
