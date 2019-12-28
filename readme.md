<img src="https://forum.saturn.network/uploads/default/original/2X/e/e87ea6b5fb70b6044373d83cc89eb2d8a6c86449.png">

# Saturn.py
Version 0.0.2 by WizardsOrb and PseudoDeterminist, Oct 2019
This version includes the well-formed-trades version of Saturnpy. INVALID TRADES WILL NOT BE SENT to the exchange contract.

* https://github.com/WizardsOrb/saturn.py
* https://forum.saturn.network/t/saturn-py-source


### Optional Settings
The following flag values default to False, to allow the simplest and best trading experience for most users.
* `SBTKN` (default: `False`) means TRADES ARE REQUESTED IN DECIMAL TOKEN UNITS. True means they are requested in integer subtoken units.
* `BNDL` (default: `False`) means WE DO NOT ALLOW BUNDLE PRICING ON NEW ORDERS, ONLY INTEGER PRICES. True means we allow Fraction prices.
* `STRICT` (default: `False`) means WE CREATE OR EXECUTE NEAREST VALID TRADE <= REQUESTED TRADE. True means invalid trades throw an error.
* `DEBUG` (default: `False`) enables logs to console
* `TESTMODE` (default: `False`) enables testmode, forcedisable send transaction
* These flags can and should be ignored and left out of function calls unless the user wants to change them.

### Depencies
* python3+ https://www.python.org/downloads/
* web3
* eth_account
* ethereum
* pandas
* base58
* ecdsa

### Install
* `pip3 install -r requirements.txt`


### Note!!
* Newer versions of web3.py (> 5.0.0b5) will run into an error -> `TypeError: 'cytoolz.functoolz.curry' object is not subscriptable`
feel free to fix it.

### Sample Usage
> NOTE: The biggest difference to saturn.js is, that you have to create seperate instances if you want to use ETH and ETC!

~~~py
#!/usr/bin/env python3
from saturnpy import Saturn

# EDIT / LOAD etcprofile.json or create settings-obj in file.

settings = {
    "blockchain": "ETC",
    "apiUrl": "https://ticker.saturn.network/api/v2/",
    "providerUrl": "https://etc-rpc.binancechain.io",
    "mnemonicKey": "legal winner thank year wave sausage worth useful legal winner thank yellow",
    "testMode": True,
    "DEBUG": True
}

#you can also add privateKey to settings
settingsETH = {
    "blockchain": "ETH",
    "apiUrl": "https://ticker.saturn.network/api/v2/",
    "providerUrl": "http://localhost:8545",
    "privateKey": "0xKeyToShuttle",
    "testMode": False,
    "DEBUG": False
}

# Saturn instances
etc = Saturn(settings)
eth = Saturn(settingsETH)

orderbook_saturnetc = etc.query.orderbook("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
orderbook_saturneth = eth.query.orderbook("0xb9440022a095343b440d590fcd2d7a3794bd76c8")

print(orderbook_saturnetc, orderbook_saturneth)

myorders = etc.exchange.ordersForAddress(etc.myaddress)
print(myorders)

etc.exchange.newOrder("0xac55641cbb734bdf6510d1bbd62e240c2409040f", "buy", "5000", "0.0001")




#orderbook = saturn.query.orderbook("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
#print(orderbook)

#txhash = saturn.exchange.newOrder("0xac55641cbb734bdf6510d1bbd62e240c2409040f", "buy", "0.001", "0.00007")
#print(txhash)

#tradehash = saturn.exchange.newTrade("1", "0x682d3a524b93351a57b7f14ea3e9bddfe78309de8d5ee9af9eeb0ce1b24c255a")
#print(tradehash)

#Getting token infos
tokeninfo = saturn.query.getTokenInfo("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
ti = JsonToObject(tokeninfo)
pprint.pprint(tokeninfo)

tradehash = saturn.exchange.newTrade("1", ti["best_sell_order_tx"])
print(tradehash)

decodedlog = etc.exchange.decoder.allEvents(ti["best_sell_order_tx"])

print(decodedlog)

order = etc.query.getOrderByTx("0x0c5eaf9ec7c55117bfc69a065b896194de2d17f46cc69920cb7bd265f371847b")
veryfiy = etc.exchange.verifyCapacity("200.0", order)
#print(veryfiy)

gasPrice = etc.exchange.getGasPrice("etc")
print(gasPrice)

checkERC = etc.exchange.isERC223("0xac55641cbb734bdf6510d1bbd62e240c2409040f")
print(checkERC)
~~~

### Test Results

<img src="https://forum.saturn.network/uploads/default/optimized/2X/2/24806fbfa24b779175da856d12f595c5e9aa1a6a_2_690x168.png" alt="">
https://blockscout.com/etc/mainnet/tx/0x9b1af87133bc1b21373b5049bff56356e56f7ff92579c5473d6b82e500c0e498/token_transfers
https://blockscout.com/etc/mainnet/tx/0x489514c9eb3a7476e5ade01a41d64a38d7ed6140fca7f1c14fb53355ab6113e3/token_transfers

### Authors

* PseudoDetermist
* BigRalph
* OldCryptoGeek
* WizardsOrb
* Saturn.Network
