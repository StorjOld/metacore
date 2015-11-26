import json
import unittest
from hashlib import sha256

from metacore.database import files
from metacore.tests import *
from metacore import storj

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
        Remember initial blacklist content.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True

        self.blocked_data = b'blocked_data'
        self.blocked_hash = sha256(self.blocked_data).hexdigest()
        with open(self.app.config['BLACKLIST_FILE'], 'r+') as fp:
            self.initial_blacklist = fp.read()
            fp.writelines((self.blocked_hash + '\n',))

        self.files_id = files.insert().values(
            hash=sha256(b'_').hexdigest(), role='000', size=1,
            owner=test_owner_address
        ).execute().inserted_primary_key

        self.files_id.extend(
            files.insert().values(
                hash=sha256(b'__').hexdigest(), role='000', size=2,
                owner=test_owner_address
            ).execute().inserted_primary_key
        )

    def tearDown(self):
        """
        Remove initial records form the 'files' table.
        Return initial blacklist content.
        """
        files.delete().where(files.c.hash.in_(self.files_id)).execute()

        with open(self.app.config['BLACKLIST_FILE'], 'w') as fp:
            fp.write(self.initial_blacklist)

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

    def test_success_get_info_with_existing_files_and_hide_blocked(self):
        """
        Successful getting files info with existing files
        and hide blocked ones.
        """
        self.files_id.extend(
            files.insert().values(
                hash=self.blocked_hash, role='000',
                size=len(self.blocked_data), owner=test_owner_address
            ).execute().inserted_primary_key
        )

        with self.app.test_client() as c:
            response = c.get(path=self.url)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        data = json.loads(response.data.decode())

        self.assertIsInstance(data, list, "Has to be an array.")

        self.assertSetEqual(
            set(_['hash'] for _ in files.select(
                files.c.hash != self.blocked_hash
            ).execute()),
            set(data),
            "Has to contain all files hashes without blacklisted ones."
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
