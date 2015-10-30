import json, unittest, os

from database import files

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
        files_size = (_['size'] for _ in files.select().execute())
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
            json.dump(self.info, file_config)

    def __increase_traffic(self, volume, incoming=True):
        direction = 'incoming' if incoming else 'outgoing'
        self.__current_bandwidth[direction] += abs(volume)
        self.__total_bandwidth[direction] += abs(volume)

        self._store()



from config import BASEDIR

class NodeTest(unittest.TestCase):

    def setUp(self):
        self.node = Node(os.path.join(BASEDIR, 'test_node.json'))


    def tearDown(self):
        del self.node

    def test_node_get_instance(self):
        """
        Checking out an Node instance creation
        """
        self.assertIsInstance(self.node, Node)



if __name__ == "__main__":
    unittest.main()