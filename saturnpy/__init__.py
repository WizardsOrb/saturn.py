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
        if 'providerType' in settings:
            pT = settings["providerType"]
            if pT == 'HTTPProvider':
                self.provider : Web3 = Web3(HTTPProvider(settings["providerUrl"]))
            elif pT == 'IPCProvider':
                self.provider : Web3 = Web3(IPCProvider(settings["providerUrl"]))
            elif pT == 'WebsocketProvider':
                self.provider : Web3 = Web3(WebsocketProvider(settings["providerUrl"]))
        else:
            self.provider : Web3 = Web3(HTTPProvider(settings["providerUrl"]))

        if 'mnemonicKey' in settings:
            self.wallet : Account = Account.privateKeyToAccount(mnemonic_to_private_key(settings["mnemonicKey"]))
        if 'privateKey' in settings:
            self.wallet : Account = Account.privateKeyToAccount(str(settings["privateKey"]))
       
        self.blockchain : str = str(settings["blockchain"]).lower()
        self.myaddress : str = self.wallet.address
        self.query = RequestManager(self.apiurl, self.provider, self.wallet, self.blockchain)

        if 'testMode' in settings:
            if bool(settings["testMode"]) == True:
                print("TEST MODE ENABLED, TRANSACTION WONT BE BROADCASTED")
                self.testmode = True

        self.exchange = ExchangeInterface(self.provider, self.wallet, self.query, self.blockchain, self.testmode)
        print("TRADING WALLET: " + self.myaddress)
