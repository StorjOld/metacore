from __future__ import (
    generators,
    division,
    absolute_import,
    with_statement,
    print_function,
    unicode_literals,
    nested_scopes
)
import os.path

from metacore.node import Node

__author__ = 'karatel'


BASEDIR = os.path.dirname(__file__)

DEBUG = True
SECRET_KEY = b'\xfa\xe4I\xc7dt\xe5\x1bV\xf1\xfc\xc2\xc4\xe0\t\xe2\xedu\xe1' \
             b'\xe7\xf4\x8c\\\xe6'

MAX_FILE_SIZE = 128 * 1024 * 1024
UPLOAD_FOLDER = os.path.join(BASEDIR, 'storage')

NODE = Node(os.path.join(BASEDIR, 'test_node.json'))
AUDIT_RATE_LIMITS = {
    'owner': 100,
    'other': 50
}
BLACKLIST_FILE = os.path.join(BASEDIR, 'Blacklist.txt')
PEERS_FILE = os.path.join(BASEDIR, 'peers.txt')
