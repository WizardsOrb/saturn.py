#!/usr/bin/env python3

# EDIT / LOAD etcprofile.json or create settings-obj in file.

#you can also add privateKey to settings
settings = {
    "blockchain": "ETC",
    "apiUrl": "https://ticker.saturn.network/api/v2/",
    "providerUrl": "https://etc-rpc.binancechain.io",
    "mnemonicKey": "legal winner thank year wave sausage worth useful legal winner thank yellow",
    "testMode": True
}

from saturnpy import Saturn
saturn = Saturn(settings)

orderbook = saturn.query.orderbook("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
print(orderbook)