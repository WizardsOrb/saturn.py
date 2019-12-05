#!/usr/bin/env python3

# PseudoDeterminist, [06.09.2019]

from decimal import Decimal, getcontext
from fractions import Fraction
from eth_utils import decode_hex, event_abi_to_log_topic
from web3._utils.abi import filter_by_type
from web3._utils.events import get_event_data
from ethereum.utils import encode_int, encode_hex


getcontext().prec = 100  # Set Decimal Precision good enough for eth Uint256

# constants
expEtherDecimals = 1000000000000000000 # 10 ** 18
exp_ether_decimals = 1000000000000000000 # 10 ** 18
etheraddress = "0x0000000000000000000000000000000000000000"
gaslimit = 400000

# Get rid of leading and trailing zeroes in internal representation of d
# decimal.py does not have, but can use, this function

def trunc(d):
    da = d.adjusted()
    return Decimal(d).scaleb(-da).normalize().scaleb(da)

# No more computing powers of 10, this is d * 10 ** e, with internal leading and trailing 0's removed

def shiftedBy(d, e):
    return trunc(Decimal(d).scaleb(e)) # scaleb() can leave extra padded 0's

# decimal.py really needs this! return regular fixed notation string. str(d) is mixed.

def toFixed(d):
    td = trunc(Decimal(d))

    if (td == 0):
        return "0"

    dtuple   = td.as_tuple()
    dsign    = dtuple[0]
    ddigits  = dtuple[1]
    dlength  = len(ddigits)
    dexpt    = dtuple[2]
    dindex   = 0
    point   = "."

    if (dsign):
        dstr = "-"
    else:
        dstr = ""

    if (dexpt <= -dlength):
        dstr  += "0."
        point  = ""

    while (dexpt < -dlength):
        dstr  += "0"
        dexpt += 1

    while (dlength > -dexpt):
        if (dlength > 0):
            dstr += str(ddigits[dindex])
        else:
            dstr += "0"

        dindex  += 1
        dlength -= 1

    if (dlength > 1):
        dstr += point

    while (dlength > 0):
        dstr    += str(ddigits[dindex])
        dindex  += 1
        dlength -= 1

    return dstr

# Increment decimal by i shifted 1 past last significant place

def mentDecimal(d, i=0):
    d = trunc(Decimal(d))

    da = d.adjusted()
    dshifted = shiftedBy(d, -da)
    ishifted = shiftedBy(i, -len(dshifted.as_tuple()[1]))

    return shiftedBy(dshifted + ishifted, da)

# convert ERC token units to subunits and back, with error checking

def toSbtkn(tknAmt, expDecimals, STRICT = True):
    return intVerify(Fraction(tknAmt) * expDecimals, STRICT = STRICT)

def toTkn(sbtknAmt, expDecimals, STRICT = True):
    sbtknAmt = intVerify(sbtknAmt, STRICT)
    return Fraction(sbtknAmt) / expDecimals

def intVerify (amount, STRICT = True):
    amount = Fraction(amount)
    if STRICT:
        assert amount == int(amount), f'amount {amount} must be integer value'
    return int(amount)

def toUint(num):
    return encode_hex(encode_int(num)).rjust(64, '0')

class AbiDecoder(object):
    def __init__(self, provider, abi):
        self.provider = provider
        self.abi = abi

    def __decode_event(self, log, abi):
        if isinstance(log["topics"][0], str):
            log["topics"][0] = decode_hex(log["topics"][0])
        elif isinstance(log["topics"][0], int):
            log["topics"][0] = decode_hex(hex(log["topics"][0]))
        event_id = log["topics"][0]
        events = filter_by_type("event", abi)
        topic_to_event_abi = {event_abi_to_log_topic(event_abi): event_abi for event_abi in events}
        event_abi = topic_to_event_abi[event_id]
        return get_event_data(event_abi, log)

    def allEvents(self,txhash : str, customAbi = None):
        useAbi = self.abi
        if customAbi != None:
            useAbi = customAbi

        receipt = self.provider.eth.getTransactionReceipt(txhash)
        foundEvents = []
        errors = []
        for eventlog in receipt.logs:
            try:
                decoded = self.__decode_event(eventlog, useAbi)
                foundEvents.append(decoded)
            except Exception as e:
                errors.append(e)
                #pass
        return foundEvents

    def getIntegerPrice(self, txhash):
        decoded_event_data = self.allEvents(txhash)
        price = {}
        for event in decoded_event_data:
            _args = event["args"]
            if "priceMul" in _args:
                price["mul"] = _args["priceMul"]
                price["id"] = _args["id"]

            if "priceMul" in _args:
                price["div"] = _args["priceDiv"]
        return price
