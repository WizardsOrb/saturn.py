#!/usr/bin/env python3

# EDIT / LOAD etcprofile.json or create settings-obj in file.
#you can also add privateKey to settings
import pprint
from saturnpy import Saturn

SETTINGS = {
    "blockchain": "ETC",
    "apiUrl": "https://ticker.saturn.network/api/v2/",
    "providerUrl": "https://www.ethercluster.com/etc",
    "mnemonicKey": "legal winner thank year wave sausage worth useful legal winner thank yellow",
    "testMode": True,
    "DEBUG": False
}
# LOAD SATURN INSTANCE
SATURN = Saturn(SETTINGS)

#Getting token infos
TOKENINFO = SATURN.query.getTokenInfo("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
pprint.pprint(TOKENINFO)


DECODEDLOG = SATURN.exchange.decoder.allEvents(TOKENINFO["best_sell_order_tx"])
PR = SATURN.exchange.decoder.getIntegerPrice(TOKENINFO["best_sell_order_tx"])

ORDER = SATURN.query.getOrderByTx(TOKENINFO["best_sell_order_tx"])
VERYFIY = SATURN.exchange.verifyCapacity("200.0", ORDER)

GASPRICE = SATURN.exchange.getGasPrice("etc")
print(GASPRICE)

CHECKERC = SATURN.exchange.isERC223("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
print(CHECKERC)

TRADEHASH = SATURN.exchange.newTrade("1", TOKENINFO["best_sell_order_tx"])
print(TRADEHASH)
