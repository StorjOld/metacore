import os.path

from node import Node

__author__ = 'karatel'


BASEDIR = os.path.dirname(__file__)

DEBUG = True
SECRET_KEY = b'\xfa\xe4I\xc7dt\xe5\x1bV\xf1\xfc\xc2\xc4\xe0\t\xe2\xedu\xe1' \
             b'\xe7\xf4\x8c\\\xe6'

UPLOAD_FOLDER = os.path.join(BASEDIR, 'storage')

NODE = Node(os.path.join(BASEDIR, 'test_node.json'))