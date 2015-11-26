import json
import os.path
import unittest

from unittest.mock import patch, MagicMock, mock_open

from metacore.database import files

__author__ = 'karatel'


class Node(object):
    """
    Node.
    """

    def __init__(self, file_path):
        with open(file_path, 'r') as config_file:
            config_data = json.load(config_file)

        self.__public_key = config_data['public_key']
        self.__limits = config_data['bandwidth']['limits']
        self.__current_bandwidth = config_data['bandwidth']['current']
        self.__total_bandwidth = config_data['bandwidth']['total']
        self.__capacity = config_data['storage']['capacity']

        self.__file_path = file_path

    def add_incoming(self, volume):
        """
        Increase incoming bandwidth values.
        :param volume: added value in bytes
        :type volume: int
        :return: None
        :rtype: NoneType
        """
        self.__increase_traffic(volume)

    def add_outgoing(self, volume):
        """
        Increase outgoing bandwidth values.
        :param volume: added value in bytes
        :type volume: int
        :return: None
        :rtype: NoneType
        """
        self.__increase_traffic(volume, False)

    @property
    def info(self):
        """
        Aggregate common status info for Node (public key, bandwidth, storage).
        :return: Node status info
        :rtype: dict
        """
        files_size = [_['size'] for _ in files.select().execute()]
        info = {
            'public_key': self.public_key,
            'bandwidth': {
                'current': self.__current_bandwidth,
                'limits': self.__limits,
                'total': self.__total_bandwidth
            },
            'storage': {
                'capacity': self.__capacity,
                'max_file_size': max(files_size, default=0),
                'used': sum(files_size)
            }
        }
        return info

    @property
    def capacity(self):
        """
        Get current capacity.
        :return: current Node capacity in bytes
        :rtype: int
        """
        return self.__capacity

    @property
    def current(self):
        """
        Get current bandwidth.
        :return: current incoming and outgoing bandwidth
        :rtype: dict
        """
        return self.__current_bandwidth

    @property
    def limits(self):
        """
        Get limit values.
        :return: incoming and outgoing limits
        :rtype: dict
        """
        return self.__limits

    @property
    def total(self):
        """
        Get total bandwidth.
        :return: total incoming and outgoing bandwidth
        :rtype: dict
        """
        return self.__total_bandwidth

    @property
    def public_key(self):
        """
        Get Node's Public Key.
        :return: Public Key
        :rtype: str
        """
        return self.__public_key

    def set_limits(self, incoming=None, outgoing=None):
        """
        Update the Node limits.
        :param incoming: new incoming limit
        :type incoming: int
        :param outgoing: new outgoing limit
        :type outgoing: int
        :return: None
        :rtype: NoneType
        """
        self.__limits.update({'incoming': incoming, 'outgoing': outgoing})

    def _store(self):
        """
        Save the Node data to its config file.
        :return: None
        :rtype: NoneType
        """

        with open(self.__file_path, 'w') as file_config:
            json.dump(self.info, file_config, indent='\t')

    def __increase_traffic(self, volume, incoming=True):
        direction = 'incoming' if incoming else 'outgoing'
        self.__current_bandwidth[direction] += abs(volume)
        self.__total_bandwidth[direction] += abs(volume)

        self._store()


class NodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Setup fake database values by patching "files" in imported "database"
        module. Namely frame-up "files.selection().execute()" call results.
        """
        files.select = MagicMock()
        files_size = []
        select_all_files = [{'size': item} for item in files_size]
        mock_execute = files.select.return_value
        mock_execute.execute.return_value = select_all_files

    def setUp(self):
        self.node = Node(os.path.join(os.path.dirname(__file__),
                                      'test_node.json'))

        with open(self.node._Node__file_path, 'r') as main_json:
            init_node_data = json.load(main_json)
            main_json.seek(0)
            with open('test_node_setup.json', 'w') as copy_json:
                copy_json.write(main_json.read())

        self.node._Node__file_path = os.path.join(os.path.dirname(__file__),
                                                  'test_node_setup.json')
        self.data_from_test_nodeJSON = {
            '_Node__public_key': init_node_data['public_key'],
            '_Node__limits': init_node_data['bandwidth']['limits'],
            '_Node__current_bandwidth': init_node_data['bandwidth']['current'],
            '_Node__total_bandwidth': init_node_data['bandwidth']['total'],
            '_Node__capacity': init_node_data['storage']['capacity'],
            '_Node__file_path': self.node._Node__file_path
        }

    def tearDown(self):
        del self.node
        if 'test_node_setup.json' in os.listdir():
            os.remove('test_node_setup.json')

    def test_node_get_instance(self):
        """
        Checking out an Node instance creation
        """
        self.assertIsInstance(self.node, Node,
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
        self.assertIsInstance(self.node.public_key, str)

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
        self.assertDictEqual(
            json.load(open(self.node._Node__file_path)),
            json.load(open(
                os.path.join(os.path.dirname(__file__), 'test_node.json')
            )),
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
