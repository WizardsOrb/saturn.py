#!/usr/bin/env python3

import os, json, requests, math
from fractions import Fraction
from decimal import *
from web3 import Web3, HTTPProvider
from ethereum.utils import encode_int, decode_hex, encode_hex

absolutePath = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(absolutePath, "erc20.json")) as x:
    erc20 = json.load(x)

with open(os.path.join(absolutePath, "erc223.json")) as x:
    erc223 = json.load(x)

with open(os.path.join(absolutePath, "exchangeConfig.json")) as x:
    exchangeConfig = json.load(x)

class ExchangeInterface(object):
    etheraddress = "0x0000000000000000000000000000000000000000"
    etherDecimals = 18
    gaslimit = 400000
    
    def __init__(self, provider, wallet, query, blockchain, testmode = False):
        self.query = query
        self.testmode : bool = testmode
        self.provider : Web3 = provider
        self.wallet = wallet
        self.blockchain = blockchain.lower()
        self.networkId = self.getNetworkId(blockchain)
        self.exchangeContractAddress = self.provider.toChecksumAddress(exchangeConfig["address"][self.blockchain.upper()])

    def getNetworkId(self, blockchain : str = None):
        if blockchain == None:
            blockchain = self.blockchain
        blockchain = blockchain.lower()
        if blockchain == "etc":
            return 61
        if blockchain == "eth":
            return 1
        raise Exception("UNSUPPORTED BLOCKCHAIN:" + str(blockchain))

    def getGasPrice(self, blockchain = None):
        if blockchain == None:
            blockchain = self.blockchain.upper()
        else:
            blockchain = blockchain.upper()
        if blockchain == 'ETC':
            return self.provider.toWei('0.001', 'gwei')        
        if blockchain == 'ETH':
            r = requests.get('https://www.ethgasstationapi.com/api/standard')
            return self.provider.toWei(str(r.json()), 'gwei')    
        raise Exception("Unknown blockchain {}".format(blockchain))


    def isERC223(self, address : str):
        address = self.provider.toChecksumAddress(address)
        code = self.provider.eth.getCode(address)
        return bool(str(code.hex())[2:].find("be45fd62") > -1)

    def isERC20(self, address : str):
        address = self.provider.toChecksumAddress(address)
        code = self.provider.eth.getCode(address)
        return bool(str(code.hex())[2:].find("095ea7b3") > -1)
    
    def determineTokenType(self, address : str):
        address = self.provider.toChecksumAddress(address)
        is223 = self.isERC223(address)
        is20 = self.isERC20(address)
        if is223 == True:
            return "ERC223"
        if is20 == True:
            return "ERC20"
        raise Exception("Token {} on ${} is of unknown type".format(address, self.blockchain.upper()))
    
    def verifyOrderType(self, orderType : str):
        types = ["buy", "sell"]
        if orderType not in types:
            raise Exception("Unknown order type {}".format(orderType))

    def verifyOrderTradable(self, order):
        trader = self.wallet.address
        orderaddr = order["owner"].lower()
        if orderaddr == trader:
            raise Exception("Cannot trade against your own order!")
        
        if bool(order["active"]) == False:
            raise Exception("The order {} appears to no longer be active".format(order["transaction"]))
        
        return True

    def verifyAllowance(self, tokenInstance, parsedAmount : Fraction, address: str = None):
        if address == None:
            address = self.exchangeContractAddress

        trader = self.wallet.address
        trader = self.provider.toChecksumAddress(trader)
        address = self.provider.toChecksumAddress(address)
        allowance = tokenInstance.functions.allowance(trader, address).call()
        allowFraction = Fraction(Decimal(allowance))
        if allowFraction <= 0:
            raise Exception("Insufficient allowance for token {}. Please visit https://forum.saturn.network/t/saturnjs-insufficient-allowance-error/2966 to resolve".format(tokenInstance.address))
        return True

    def verifyEtherBalance(self, amount):
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(self.etherDecimals))
        trader = self.wallet.address
        unparsedBalance = self.provider.eth.getBalance(trader)
        balance = Fraction(str(unparsedBalance))
        if parsedAmount > balance:
            raise Exception("Insufficient ether balance. Requested amount: {}. Available amount: {}".format(amount, unparsedBalance))
        return True

    def verifyTokenBalance(self, tokenAddress : str, amount):
        trader = self.wallet.address
        contractAddr = self.provider.toChecksumAddress(tokenAddress)
        token = self.provider.eth.contract(address=contractAddr, abi=erc20)
        balance = Fraction(str(token.functions.balanceOf(trader).call()))
        decimals = token.functions.decimals().call()
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        if parsedAmount > balance:
            raise Exception("Insufficient balance for token {}. Requested amount: {}. Available amount: {}".format(contractAddr, amount, parsedAmount))
        return True

    def verifyCapacity(self, amount, order):
        if order["type"] == "BUY":
            raise Exception("verifyCapacity is only Allowed on Token balances")
        amount = str(amount)
        orderId = int(order["order_id"])
        orderContract = self.exchangeContractAddress
        contractAddr = ""
        if order["buytoken"]["address"] != self.etheraddress:
           contractAddr = order["buytoken"]["address"]
        if order["selltoken"]["address"] != self.etheraddress:
           contractAddr = order["selltoken"]["address"]           
        contractAddr = self.provider.toChecksumAddress(contractAddr)
        exchange = self.provider.eth.contract(address=orderContract, abi = exchangeConfig["abi"])
        token = self.provider.eth.contract(address=contractAddr, abi=erc20)
        decimals = token.functions.decimals().call()
        rawOrderBalance = int(exchange.functions.remainingAmount(orderId).call())
        parsedOrderBalance = rawOrderBalance / (10 ** int(decimals))
        if float(amount) > parsedOrderBalance:
            raise Exception("You attempted to trade more tokens ({}) than are available in the order ({}) for order_tx {}".format(amount, parsedOrderBalance, order["transaction"]))
        return parsedOrderBalance

    def toUint(self, num):
        return encode_hex(encode_int(num)).rjust(64, '0')

    def sendRawTx(self, unsignedTX):
        if self.testmode == True:
            print(unsignedTX)
            return '0x'

        try:
            signedTX = self.wallet.signTransaction(unsignedTX)
            self.provider.eth.sendRawTransaction(signedTX.rawTransaction)
            txhash = self.provider.toHex(self.provider.sha3(signedTX.rawTransaction))
            #print(txhash)
            return txhash
        except:
            raise Exception('ERROR SENDING RAW TRANSACTION')


    def createERC223OrderPayload(self, price : Fraction, buytoken : str):
        paddedToken = buytoken
        if buytoken == '0x0' or buytoken.lower() == self.etheraddress:
            paddedToken = str(self.etheraddress)
        return '0x' + str(self.toUint(int(price.numerator))) + str(self.toUint(price.denominator)) + paddedToken[2:]

# TRADING FUNCTIONS

    def newERC223Trade(self, tokenAddress : str, amount, order, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        token = self.provider.eth.contract(address=tokenAddress, abi=erc223)
        decimals = token.functions.decimals().call()
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        payload = "0x" + self.toUint(int(order["order_id"]))
        exContract = self.provider.toChecksumAddress(order["contract"])
        
        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce
            
        unsignedTX = token.functions.transfer(
            exContract,
            int(parsedAmount),
            payload
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce  
        })
        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def newERC20Trade(self, tokenAddress : str, amount, order, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        exContract = self.provider.toChecksumAddress(order["contract"])
        token = self.provider.eth.contract(address=tokenAddress, abi=erc20)
        exchange = self.provider.eth.contract(address=exContract, abi = exchangeConfig["abi"])
        decimals = token.functions.decimals().call()
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        self.verifyAllowance(token, parsedAmount, exContract)

        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = exchange.functions.buyOrderWithERC20Token(
            int(order["order_id"]),
            tokenAddress,
            int(parsedAmount)
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce  
        })
        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def newEtherTrade(self, amount, order, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(order["selltoken"]["address"])
        exContract = self.provider.toChecksumAddress(order["contract"])
        token = self.provider.eth.contract(address=tokenAddress, abi=erc20)
        exchange = self.provider.eth.contract(address=exContract, abi = exchangeConfig["abi"])
        decimals = token.functions.decimals().call()
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        requiredEtherAmount = exchange.functions.getBuyTokenAmount(
            int(parsedAmount),
            int(order["order_id"])
        ).call()

        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = exchange.functions.buyOrderWithEth(
            int(order["order_id"])
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce,
            'value': int(requiredEtherAmount)
        })
        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def newTrade(self, amount, orderTx, customNonce = None):
        order = self.query.awaitOrderTx(orderTx)        
        self.verifyOrderTradable(order)
        orderType = order["type"].lower()
        if orderType == "sell":
            self.verifyCapacity(amount, order)
            self.verifyEtherBalance(amount * float(order["price"]))
            return self.newEtherTrade(amount, order, customNonce)
        elif orderType == "buy":
            tokenAddress = self.provider.toChecksumAddress(order["buytoken"]["address"])
            tokenType = self.determineTokenType(tokenAddress)
            self.verifyTokenBalance(tokenAddress, amount)
            if tokenType == "ERC223":
                return self.newERC223Trade(tokenAddress, amount, order, customNonce)
            else:
                return self.newERC20Trade(tokenAddress, amount, order, customNonce)
        else:
            raise Exception("Unknown order type for order_tx {} on ${this.blockchain}".format(orderTx, self.blockchain))
        #print(order)

    def cancelOrder(self, orderId : int, contract : str = None, customNonce = None):
        if contract == None:
            contract = self.exchangeContractAddress

        contractAddr = self.provider.toChecksumAddress(contract)
        exchange = self.provider.eth.contract(address=contractAddr, abi = exchangeConfig["abi"])

        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = exchange.functions.cancelOrder(orderId).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce
        })
        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def cancelOrderByTxHash(self, txhash : str):
        order = self.query.getOrderByTx(txhash.lower())
        orderid = int(order["order_id"])
        cancel_hash = self.cancelOrder(orderid)
        #print("CANCELING ORDERID {} (ORDERHASH: {}), CANCEL HASH: {}".format(orderid, txhash, cancel_hash))
        wait = self.provider.eth.waitForTransactionReceipt(cancel_hash, timeout=120)
        return wait


    def newOrder(self, tokenAddress: str, orderType: str, amount, price, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        self.verifyOrderType(orderType.lower())
        tokenType = self.determineTokenType(tokenAddress)
        orderContract = self.exchangeContractAddress
        if orderType == 'buy':
            self.verifyEtherBalance(amount * price)
            return self.newBuyOrder(tokenAddress, amount, price, orderContract, customNonce)
        elif orderType == 'sell':
            self.verifyTokenBalance(tokenAddress, amount)
            if tokenType == 'ERC223':
                return self.newERC223sellOrder(tokenAddress, amount, price, orderContract, customNonce)
            elif tokenType == 'ERC20':
                return self.newERC20sellOrder(tokenAddress, amount, price, orderContract, customNonce)
            else:
                raise Exception('UNKNOWN TOKEN STANDARD')
        else:
            raise Exception('UNKNOWN ORDERTYPE {}', orderType)

    def newBuyOrder(self, tokenAddress : str, amount, price : int, orderContract : str, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        exContract = self.provider.toChecksumAddress(self.exchangeContractAddress)
        token = self.provider.eth.contract(address=tokenAddress, abi=erc20)
        exchange = self.provider.eth.contract(address=exContract, abi = exchangeConfig["abi"])
        decimals = token.functions.decimals().call()
        parsedPrice = Fraction(price)._mul(Fraction(10).__pow__(self.etherDecimals))._div(
            Fraction(10).__pow__(decimals)
        )
        parsedAmount = Fraction(amount * price)._mul(Fraction(10).__pow__(self.etherDecimals))
        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = exchange.functions.sellEther(
            tokenAddress,
            parsedPrice.numerator,
            parsedPrice.denominator
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce,
            'value': int(parsedAmount)
        })

        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def newERC223sellOrder(self, tokenAddress : str, amount, price, orderContract : str, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        orderContract = self.provider.toChecksumAddress(orderContract)
        token = self.provider.eth.contract(address=tokenAddress, abi=erc223)
        decimals = token.functions.decimals().call()
        
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        parsedPrice = Fraction(price)._mul(Fraction(10).__pow__(self.etherDecimals))._div(
            Fraction(10).__pow__(decimals)
        )
        parsedPrice = Fraction(1)._div(parsedPrice)
        payload = self.createERC223OrderPayload(parsedPrice, self.etheraddress)
        #print('PARSED AMOUNT', int(parsedAmount))
        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = token.functions.transfer(
            orderContract,
            int(parsedAmount),
            payload
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsignedTX)
        return txhash

    def newERC20sellOrder(self, tokenAddress : str, amount, price : int, orderContract : str, customNonce = None):
        tokenAddress = self.provider.toChecksumAddress(tokenAddress)
        orderContract = self.provider.toChecksumAddress(orderContract)        
        exchange = self.provider.eth.contract(address=orderContract, abi = exchangeConfig["abi"])
        token = self.provider.eth.contract(address=tokenAddress, abi=erc20)
        decimals = token.functions.decimals().call()
        parsedAmount = Fraction(amount)._mul(Fraction(10).__pow__(decimals))
        parsedPrice = Fraction(price)._mul(Fraction(10).__pow__(self.etherDecimals))._div(
            Fraction(10).__pow__(decimals)
        )
        parsedPrice = Fraction(1)._div(parsedPrice)
        self.verifyAllowance(token, parsedAmount, orderContract)

        if customNonce == None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = customNonce

        unsignedTX = exchange.functions.sellERC20Token(
            tokenAddress,
            self.etheraddress,
            int(parsedAmount),
            int(parsedPrice.numerator),
            int(parsedPrice.denominator)
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': self.gaslimit,
            'nonce': nonce
        })
        txhash = self.sendRawTx(unsignedTX)
        return txhash
