import sys
import json
import os.path
import unittest

from metacore.database import files
from metacore import node

if sys.version_info.major == 3:
    from unittest.mock import patch, MagicMock, mock_open
else:
    from mock import patch, MagicMock, mock_open


class NodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Setup fake database values by patching "files" in imported "database"
        module. Namely frame-up "files.selection().execute()" call results.
        """
        cls.saving_select = files.select
        files.select = MagicMock()
        files_size = []
        select_all_files = [{'size': item} for item in files_size]
        mock_execute = files.select.return_value
        mock_execute.execute.return_value = select_all_files
        cls.test_json_name = 'test_node_setup.json'

    @classmethod
    def tearDownClass(cls):
        files.select = cls.saving_select


    def setUp(self):
        self.node = node.Node(os.path.join(os.path.dirname(node.__file__),
                                           'test_node.json'))

        with open(self.node._Node__file_path, 'r') as main_json:
            init_node_data = json.load(main_json)
            main_json.seek(0)
            with open(
                os.path.join(
                    os.path.dirname(node.__file__), self.test_json_name),
                'w'
            ) as copy_json:
                copy_json.write(main_json.read())

        self.node._Node__file_path = os.path.join(
            os.path.dirname(node.__file__), self.test_json_name)
        self.data_from_test_nodeJSON = {
            '_Node__public_key': init_node_data['public_key'],
            '_Node__limits': init_node_data['bandwidth']['limits'],
            '_Node__current_bandwidth': init_node_data['bandwidth']['current'],
            '_Node__total_bandwidth': init_node_data['bandwidth']['total'],
            '_Node__capacity': init_node_data['storage']['capacity'],
            '_Node__file_path': self.node._Node__file_path
        }

    def tearDown(self):
        try:
            os.remove(os.path.join(os.path.dirname(
                node.__file__), self.test_json_name))
        except Exception:
            pass
        del self.node

    def test_node_get_instance(self):
        """
        Checking out an Node instance creation
        """
        self.assertIsInstance(self.node, node.Node,
                              "Crated object isn't instance of the Node")

        # fetch private data from Node instance
        data_from_instance = dict(
            filter(lambda item: item[0].startswith('_Node__'),
                   self.node.__dict__.items())
        )
        # verify the data in instance
        self.assertEqual(
            data_from_instance, self.data_from_test_nodeJSON,
            "Data in just created instance don't coincide with source file"
        )

    def test_node_add_incoming(self):
        """
        Test Node.add_incoming()
        """
        self.node._Node__increase_traffic = MagicMock()
        self.node.add_incoming(500)
        self.node._Node__increase_traffic.assert_called_once_with(500)

    def test_node_add_outgoing(self):
        """
        Test Node.add_outgoing()
        """
        self.node._Node__increase_traffic = MagicMock()
        self.node.add_outgoing(500)
        self.node._Node__increase_traffic.assert_called_once_with(500, False)

    def test_node_current(self):
        self.assertIs(self.node._Node__current_bandwidth, self.node.current)
        self.assertIsInstance(self.node._Node__current_bandwidth, dict)

    def test_node_capacity(self):
        """
        Test of correctness of working the capacity property
        """
        self.assertIs(self.node._Node__capacity, self.node.capacity)
        self.assertIsInstance(self.node.capacity, int)

    def test_node_limits(self):
        """
        Test of correctness of working the limits property
        """
        self.assertIs(self.node._Node__limits, self.node.limits)
        self.assertIsInstance(self.node.limits, dict)

    def test_node_total(self):
        """
        Test of correctness of working the node_total property
        """
        self.assertIs(self.node._Node__total_bandwidth, self.node.total)
        self.assertIsInstance(self.node.total, dict)

    def test_node_public_key(self):
        """
        Test of correctness of working the public_key property
        """
        self.assertIs(self.node._Node__public_key, self.node.public_key)

    def test_node_set_limits(self):
        """
        Test of setting up limits to node instance
        """
        self.node.set_limits(incoming=200, outgoing=300)
        self.assertEqual(
            (
                self.node._Node__limits['incoming'],
                self.node._Node__limits['outgoing'],
            ),
            (200, 300,)
        )

    def test_node_store(self):
        """
        Test of ability to rewrite node's json
        """
        mocked_open = mock_open()
        with patch('metacore.node.open', mocked_open, create=True):
            self.node._store()
        mocked_open.assert_called_once_with(self.node._Node__file_path, 'w')
        with open(self.node._Node__file_path, 'w') as file:
            file.write('corrupting the settings file for further repairing')
        self.node._store()
        with open(self.node._Node__file_path) as temp_file:
            with open(
                os.path.join(os.path.dirname(node.__file__), 'test_node.json')
            )as main_file:
                self.assertDictEqual(
                    json.load(temp_file),
                    json.load(main_file),
                    "problems with rewriting a json file of the Node "
                )

    @patch.object(files, 'select')
    def test_node_info(self, mock_select):
        """
        Test of compliance between info in instances json file and
        the data returned from node.info()
        """
        files_size = (50, 700, 200)
        select_all_files = [{'size': item} for item in files_size]
        mock_execute = mock_select.return_value
        mock_execute.execute.return_value = select_all_files

        with open(self.node._Node__file_path, 'r') as config_file:
            init_node_data = json.load(config_file)
            init_node_data['storage']['max_file_size'] = max(files_size)
            init_node_data['storage']['used'] = sum(files_size)

        self.assertDictEqual(init_node_data, self.node.info)

    def test_node_increase_traffic(self):
        """
        Test for Node.__increase_traffic()
        """
        info_before = self.node.info
        self.node._Node__increase_traffic(100)
        self.node._Node__increase_traffic(300, False)
        info_before['bandwidth'].update(
            total={'incoming': 100, 'outgoing': 300},
            current={'incoming': 100, 'outgoing': 300}
        )
        self.assertDictEqual(
            self.node.info,
            info_before,
            "Node.__increase_traffic() doesn't updating data of Node instance"
        )

if __name__ == "__main__":
    unittest.main()
