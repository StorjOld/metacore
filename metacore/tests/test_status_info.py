from __future__ import (
    generators,
    division,
    absolute_import,
    with_statement,
    print_function,
    unicode_literals,
    nested_scopes
)
from __builtin__ import *
import json
import unittest
from metacore import storj

__author__ = 'karatel'


class GetStatusInfoCase(unittest.TestCase):
    """
    Test getting Node status info.
    """
    url = '/api/nodes/me/'

    def setUp(self):
        """
        Switch to test config.
        """
        self.app = storj.app
        self.app.config['TESTING'] = True

    def test_success_get_info(self):
        """
        Successful getting Node info.
        """
        with self.app.test_client() as c:
            response = c.get(path=self.url)

        self.assertEqual(200, response.status_code,
                         "'OK' status code is expected.")
        self.assertEqual('application/json', response.content_type,
                         "Has to be a JSON-response.")

        self.assertDictEqual(
            self.app.config['NODE'].info,
            json.loads(response.data.decode()),
            "Unexpected response data."
        )


if __name__ == '__main__':
    unittest.main()
