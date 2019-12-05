#!/usr/bin/env python3

# EDIT / LOAD etcprofile.json or create settings-obj in file.
#you can also add privateKey to settings
import pprint
from saturnpy import Saturn

SETTINGS = {
    "blockchain": "ETC",
    "apiUrl": "https://ticker.saturn.network/api/v2/",
    "providerUrl": "https://etc-rpc.binancechain.io",
    "mnemonicKey": "legal winner thank year wave sausage worth useful legal winner thank yellow",
    "testMode": True,
    "DEBUG": False
}
# LOAD SATURN INSTANCE
SATURN = Saturn(SETTINGS)

#Getting token infos
TOKENINFO = SATURN.query.getTokenInfo("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
pprint.pprint(TOKENINFO)

TRADEHASH = SATURN.exchange.newTrade("1", TOKENINFO["best_sell_order_tx"])
print(TRADEHASH)

DECODEDLOG = SATURN.exchange.decoder.allEvents(TOKENINFO["best_sell_order_tx"])

print(DECODEDLOG)

ORDER = SATURN.query.getOrderByTx("0x0c5eaf9ec7c55117bfc69a065b896194de2d17f46cc69920cb7bd265f371847b")
VERYFIY = SATURN.exchange.verifyCapacity("200.0", ORDER)
print(VERYFIY)

GASPRICE = SATURN.exchange.getGasPrice("etc")
print(GASPRICE)

CHECKERC = SATURN.exchange.isERC223("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
print(CHECKERC)
