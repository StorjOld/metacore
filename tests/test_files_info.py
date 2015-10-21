import json
import unittest
from hashlib import sha256

from database import files
import storj

__author__ = 'karatel'


class GetFilesInfoCase(unittest.TestCase):
    """
    Test getting files info.
    """
    url = '/api/files/'

    def setUp(self):
        """
        Switch to test config.
        Create initial files set in the Upload Dir.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True

        self.files_id = files.insert().values(
            hash=sha256(b'_').hexdigest(), role='000', size=1, owner='a' * 26
        ).execute().inserted_primary_key

        self.files_id.extend(
            files.insert().values(
                hash=sha256(b'__').hexdigest(), role='000', size=2,
                owner='a' * 26
            ).execute().inserted_primary_key
        )

    def tearDown(self):
        """
        Remove initial records form the 'files' table.
        """
        files.delete().where(files.c.hash.in_(self.files_id)).execute()

    def test_success_get_info_with_existing_files(self):
        """
        Successful getting files info with existing files.
        """
        with self.app.test_client() as c:
            response = c.get(path=self.url)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        data = json.loads(response.data.decode())

        self.assertIsInstance(data, list, "Has to be an array.")

        self.assertSetEqual(
            set(_['hash'] for _ in files.select().execute()),
            set(data),
            "Has to contain all files hashes."
        )

    def test_success_get_info_with_no_files(self):
        """
        Successful getting files info with noo files.
        """
        files.delete().execute()

        with self.app.test_client() as c:
            response = c.get(path=self.url)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertListEqual([], json.loads(response.data.decode()))


if __name__ == '__main__':
    unittest.main()
