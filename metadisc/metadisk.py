import argparse
from hashlib import sha256

import requests
from btctxstore import BtcTxStore

__author__ = 'eugene.viktorov'


parser = argparse.ArgumentParser()
parser.add_argument('file', type=argparse.FileType('rb'), help="path to file")
parser.add_argument('-r', '--file_role', type=str, default='001',
                    help="set file role")

args = parser.parse_args()

btctx_api = BtcTxStore()
sender_key = btctx_api.create_key()
sender_address = btctx_api.get_address(sender_key)

files = {'file_data': args.file}
data_hash = sha256(args.file.read()).hexdigest()
args.file.seek(0)

signature = btctx_api.sign_unicode(sender_key,
                                         data_hash)

url = 'http://0.0.0.0:5000/api/files/'

r = requests.post(
    url,
    data={
        'data_hash': data_hash,
        'file_role': args.file_role,
    },
    files=files,
    headers={
        'sender_address': sender_address,
        'signature': signature,
    }
)

print(r.status_code)
print(r.text)


