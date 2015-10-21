from btctxstore import BtcTxStore

__author__ = 'karatel'

btctx_api = BtcTxStore(testnet=True, dryrun=True)
btctx_wif = btctx_api.create_key()
btctx_address = btctx_api.get_address(btctx_wif)