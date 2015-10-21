from btctxstore import BtcTxStore

__author__ = 'karatel'

test_btctx_api = BtcTxStore(testnet=True, dryrun=True)
test_owner_wif = test_btctx_api.create_key()
test_owner_address = test_btctx_api.get_address(test_owner_wif)
test_other_wfi = test_btctx_api.create_key()
test_other_address = test_btctx_api.get_address(test_other_wfi)