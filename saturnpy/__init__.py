#!/usr/bin/env python3

from eth_account import Account
from web3 import Web3, HTTPProvider, IPCProvider, WebsocketProvider
from saturnpy.request_manager import RequestManager
from saturnpy.exchange import ExchangeInterface
from saturnpy.mnemonic_utils import mnemonic_to_private_key

class Saturn(object):
    def __init__(self, settings):
        self.apiurl : str = settings["apiUrl"]
        self.testmode = False
        if "providerType" in settings:
            pT = settings["providerType"]
            if pT == "HTTPProvider":
                self.provider : Web3 = Web3(HTTPProvider(settings["providerUrl"]))
            elif pT == "IPCProvider":
                self.provider : Web3 = Web3(IPCProvider(settings["providerUrl"]))
            elif pT == "WebsocketProvider":
                self.provider : Web3 = Web3(WebsocketProvider(settings["providerUrl"]))
        else:
            self.provider : Web3 = Web3(HTTPProvider(settings["providerUrl"]))

        if "mnemonicKey" in settings:
            self.wallet : Account = Account.privateKeyToAccount(mnemonic_to_private_key(settings["mnemonicKey"]))
        if "privateKey" in settings:
            self.wallet : Account = Account.privateKeyToAccount(str(settings["privateKey"]))

        self.blockchain : str = str(settings["blockchain"]).lower()
        self.myaddress : str = self.wallet.address
        self.query = RequestManager(self.apiurl, self.provider, self.wallet, self.blockchain)

        if "testMode" in settings:
            if bool(settings["testMode"]) == True:
                print("TEST MODE ENABLED, TRANSACTION WONT BE BROADCASTED")
                self.testmode = True

        # The following flag values default to False, to allow the simplest and best trading experience for most users.
        # SBTKN False means TRADES ARE REQUESTED IN DECIMAL TOKEN UNITS. True means they are requested in integer subtoken units.
        # BNDL False means WE DO NOT ALLOW BUNDLE PRICING ON NEW ORDERS, ONLY INTEGER PRICES. True means we allow Fraction prices.
        # STRICT False means WE CREATE OR EXECUTE NEAREST VALID TRADE <= REQUESTED TRADE. True means invalid trades throw an error.
        # These flags can and should be ignored and left out of function calls unless the user wants to change them.
        self.SBTKN = False
        self.STRICT = False
        self.BNDL = False
        self.DEBUG = False

        if "SBTKN" in settings:
            self.SBTKN = settings["SBTKN"]
        if "STRICT" in settings:
            self.STRICT = settings["STRICT"]
        if "BNDL" in settings:
            self.BNDL = settings["BNDL"]

        if "DEBUG" in settings:
            self.DEBUG = settings["DEBUG"]

        self.exchange = ExchangeInterface(
            self.provider, self.wallet, self.query,
            self.blockchain, self.testmode,
            self.SBTKN, self.STRICT, self.BNDL,
            self.DEBUG
            )
        print("TRADING WALLET: " + self.myaddress)
