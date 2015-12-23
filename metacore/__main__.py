import os.path
import sys

parentdir = os.path.dirname(os.path.dirname(__file__))

if not parentdir in sys.path:
    sys.path.insert(0, parentdir)

from metacore.storj import app as application


def main():
    application.run(host='0.0.0.0')

if __name__ == '__main__':
    main()

