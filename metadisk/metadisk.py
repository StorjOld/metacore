#! /usr/bin/env python3

import argparse
import os.path
import sys
from hashlib import sha256
from urllib.parse import urljoin


import requests
from btctxstore import BtcTxStore

__author__ = 'eugene.viktorov'

url_base = 'http://dev.storj.anvil8.com/api/files/'

parser = argparse.ArgumentParser()

parser.add_argument('action', choices=['download', 'upload'])

if sys.argv[1] == 'download':
    parser.add_argument('file_hash', type=str, help="file hash")
    parser.add_argument('--decryption_key', type=str, help="decryption key")
    parser.add_argument('--rename_file', type=str, help="rename file")
elif sys.argv[1] == 'upload':
    parser.add_argument('file', type=argparse.FileType('rb'), help="path to file")
    parser.add_argument('-r', '--file_role', type=str, default='001',
                    help="set file role")



args = parser.parse_args()

btctx_api = BtcTxStore()
sender_key = btctx_api.create_key()
sender_address = btctx_api.get_address(sender_key)

if args.action == 'download':
    signature = btctx_api.sign_unicode(sender_key, args.file_hash)
    params={}
    if args.decryption_key:
        params['decryption_key'] = args.decryption_key
    if args.rename_file:
        params['file_alias'] = args.rename_file
    r = requests.get(
        urljoin(url_base, args.file_hash),
        params=params,
        headers={
            'sender_address': sender_address,
            'signature': signature,
        }
    )
    if r.status_code == 200:
        file_name = os.path.join(os.path.dirname(__file__),
                                 r.headers['X-Sendfile'])
        with open(file_name, 'wb') as fp:
            fp.write(r.content)
    else:
        print(r.status_code)
        print(r.text)


elif args.action == 'upload':
    files = {'file_data': args.file}
    data_hash = sha256(args.file.read()).hexdigest()
    args.file.seek(0)
    signature = btctx_api.sign_unicode(sender_key, data_hash)

    r = requests.post(
        url_base,
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


