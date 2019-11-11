#!/usr/bin/env python3

# exchange.py Version 0.0.2 by WizardsOrb and PseudoDeterminist, Oct 2019

# This is the well-formed-trades version of Saturnpy. INVALID TRADES WILL NOT BE SENT to the exchange contract.

from fractions import Fraction
import pprint
import os
import json
import requests

from web3 import Web3
from .utils import toSbtkn, intVerify, exp_ether_decimals, etheraddress, gaslimit, AbiDecoder, toUint

ABSOLUTEPATH = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(ABSOLUTEPATH, "erc20.json")) as x:
    ERC20 = json.load(x)

with open(os.path.join(ABSOLUTEPATH, "erc223.json")) as x:
    ERC223 = json.load(x)

with open(os.path.join(ABSOLUTEPATH, "exchangeConfig.json")) as x:
    EXCHANGECONFIG = json.load(x)

class ExchangeInterface(object):
    def __init__(self, provider, wallet, query, blockchain, TESTMODE, SBTKN, STRICT, BNDL, DEBUG):
        self.query = query
        self.TESTMODE: bool = TESTMODE
        self.provider: Web3 = provider
        self.wallet = wallet
        self.blockchain = blockchain.lower()
        self.networkId = self.getNetworkId(blockchain)
        self.exchange_contract_address = self.provider.toChecksumAddress(EXCHANGECONFIG["address"][self.blockchain.upper()])
        self.decoder = AbiDecoder(self.provider, EXCHANGECONFIG["abi"])
        self.SBTKN, self.STRICT, self.BNDL, self.DEBUG = SBTKN, STRICT, BNDL, DEBUG

    def getNetworkId(self, blockchain = None):
        if blockchain is None:
            blockchain = self.blockchain
        blockchain = blockchain.lower()
        if blockchain == "etc":
            return 61
        if blockchain == "eth":
            return 1
        raise Exception(f'UNSUPPORTED BLOCKCHAIN: {blockchain}')

    def log(self, logstring):
        if not self.DEBUG:
            return
        pprint.pprint(f"DEBUG: {logstring}")

    def getGasPrice(self, blockchain=None):
        if blockchain is None:
            blockchain = self.blockchain.upper()
        else:
            blockchain = blockchain.upper()

        if blockchain == 'ETC':
            return self.provider.toWei('0.001', 'gwei')
        if blockchain == 'ETH':
            req = requests.get('https://www.ethgasstationapi.com/api/standard')
            return self.provider.toWei(str(req.json()), 'gwei')
        raise Exception(f'Unknown blockchain {blockchain}')

    def isERC223(self, address):
        address = self.provider.toChecksumAddress(address)
        code = self.provider.eth.getCode(address)
        return bool(str(code.hex())[2:].find("be45fd62") > -1)

    def isERC20(self, address):
        address = self.provider.toChecksumAddress(address)
        code = self.provider.eth.getCode(address)
        return bool(str(code.hex())[2:].find("095ea7b3") > -1)

    def determineTokenType(self, address):
        address = self.provider.toChecksumAddress(address)
        is223 = self.isERC223(address)
        is20 = self.isERC20(address)
        if is223 == True:
            return "ERC223"
        if is20 == True:
            return "ERC20"
        raise Exception(f'Token {address} on ${self.blockchain.upper()} is of unknown type')

    def verifyOrderType(self, order_type):
        types = ["buy", "sell"]
        if order_type not in types:
            raise Exception(f'Unknown order type {order_type}')

    def verifyOrderTradable(self, order):
        trader = self.wallet.address
        orderaddr = order["owner"].lower()
        if orderaddr == trader:
            raise Exception('Cannot trade against your own order!')

        if bool(order["active"]) == False:
            raise Exception(f'The order {str(order["transaction"])} appears to no longer be active')

        return True

    def verifyAllowance(self, token_address, amount, address):
        token_address = self.provider.toChecksumAddress(token_address)
        address = self.provider.toChecksumAddress(address)
        trader = self.provider.toChecksumAddress(self.wallet.address)
        token = self.provider.eth.contract(address=token_address, abi=ERC20)

        if address is None:
            address = self.exchange_contract_address

        allowance = token.functions.allowance(trader, address).call()

        if allowance < amount:
            raise Exception(f'Insufficient allowance for token {token_address}. Please visit https://forum.saturn.network/t/saturnjs-insufficient-allowance-error/2966 to resolve')

        return True

    def verifyEtherBalance(self, amount):
        trader = self.wallet.address
        balance = int(self.provider.eth.getBalance(trader))

        if amount > balance:
            raise Exception(f'Insufficient wei balance. Requested amount: {amount}. Available amount: {balance}')
        return True

    def verifyTokenBalance(self, token_address, amount):
        trader = self.wallet.address
        contract_addr = self.provider.toChecksumAddress(token_address)
        token = self.provider.eth.contract(address=contract_addr, abi=ERC20)

        balance = int(token.functions.balanceOf(trader).call())
        if amount > balance:
            raise Exception(f'Insufficient balance for token {contract_addr}. Requested amount: {amount}. Available amount: {balance}')
        return True

    def verifyCapacity(self, amount, order):
        order_id = int(order["order_id"])
        order_contract = self.exchange_contract_address
        token_addr = ""
        if order["buytoken"]["address"] != etheraddress:
            token_addr = order["buytoken"]["address"]
        if order["selltoken"]["address"] != etheraddress:
            token_addr = order["selltoken"]["address"]
        token_addr = self.provider.toChecksumAddress(token_addr)
        token = self.provider.eth.contract(address=token_addr, abi=ERC20)
        exchange = self.provider.eth.contract(address=order_contract, abi=EXCHANGECONFIG["abi"])

        if not self.SBTKN:
            exp_decimals = 10 ** int(token.functions.decimals().call())
            amount = toSbtkn(amount, exp_decimals, self.STRICT)

        amount = intVerify(amount)

        price_obj = self.decoder.getIntegerPrice(order["transaction"])
        price_mul = int(price_obj["mul"])
        price_div = int(price_obj["div"])

        order_balance = int(exchange.functions.remainingAmount(order_id).call())

        if order["type"] == "BUY":
            nearest_trade = min(amount - amount * price_mul % price_div, order_balance * price_div // price_mul)
        elif order["type"] == "SELL":
            nearest_trade = min(amount - amount * price_div % price_mul, order_balance)
        else:
            raise Exception(f'Unknown order type for order_tx {order["transaction"]} on ${self.blockchain}')

        if self.STRICT:
            if amount != nearest_trade:
                raise Exception(f'Order cannot trade amount {amount}. nearest possible trade: {nearest_trade}')

        self.log(f"nearestTrade = {nearest_trade}")
        self.log(f"amount = {amount}")

        return nearest_trade

    def sendRawTx(self, unsigned_tx):
        if self.TESTMODE == True:
            self.log(unsigned_tx)
            return '0x'

        try:
            signed_tx = self.wallet.signTransaction(unsigned_tx)
            self.provider.eth.sendRawTransaction(signed_tx.rawTransaction)
            txhash = self.provider.toHex(self.provider.sha3(signed_tx.rawTransaction))
            return txhash
        except:
            raise Exception('ERROR SENDING RAW TRANSACTION')

    def createERC223OrderPayload(self, price_mul, price_div, buytoken):
        padded_token = buytoken
        if buytoken == '0x0' or buytoken.lower() == etheraddress:
            padded_token = str(etheraddress)
        if (not isinstance(price_mul, int)) or (not isinstance(price_div, int)):
            raise Exception(f'priceMul and priceDiv must be of type int')
        return '0x' + str(toUint(price_mul)) + str(toUint(price_div)) + padded_token[2:]

# TRADING FUNCTIONS

    def newERC223Trade(self, token_address, amount, order, custom_nonce=None):
        self.verifyOrderTradable(order)

        amount = self.verifyCapacity(amount, order)

        self.log(f"newERC223Trade, amount = {amount}")

        token_address = self.provider.toChecksumAddress(token_address)
        self.verifyTokenBalance(token_address, amount)

        token = self.provider.eth.contract(address=token_address, abi=ERC223)

        payload = "0x" + toUint(int(order["order_id"]))
        ex_contract = self.provider.toChecksumAddress(order["contract"])

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        unsigned_tx = token.functions.transfer(
            ex_contract,
            amount,
            payload
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def newERC20Trade(self, token_address, amount, order, custom_nonce=None):
        self.verifyOrderTradable(order)
        amount = self.verifyCapacity(amount, order)

        token_address = self.provider.toChecksumAddress(token_address)
        self.verifyTokenBalance(token_address, amount)

        ex_contract = self.provider.toChecksumAddress(order["contract"])
        exchange = self.provider.eth.contract(address=ex_contract, abi=EXCHANGECONFIG["abi"])
        self.verifyAllowance(token_address, amount, ex_contract)

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        unsigned_tx = exchange.functions.buyOrderWithERC20Token(
            int(order["order_id"]),
            token_address,
            amount
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def newEtherTrade(self, amount, order, custom_nonce=None):
        self.verifyOrderTradable(order)

        amount = self.verifyCapacity(amount, order)
        self.log(f"newEtherTrade, amount = {amount}")

        ex_contract = self.provider.toChecksumAddress(order["contract"])
        exchange = self.provider.eth.contract(address=ex_contract, abi=EXCHANGECONFIG["abi"])
        required_ether_amount = exchange.functions.getBuyTokenAmount(
            amount, int(order["order_id"])
        ).call()

        self.log(f"newEtherTrade, requiredEtherAmount = {required_ether_amount}")

        self.verifyEtherBalance(required_ether_amount)

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        unsigned_tx = exchange.functions.buyOrderWithEth(
            int(order["order_id"])
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce,
            'value': required_ether_amount
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def newTrade(self, amount, orderTx, custom_nonce=None):
        order = self.query.awaitOrderTx(orderTx)
        order_type = order["type"].lower()
        if order_type == "sell":
            return self.newEtherTrade(amount, order, custom_nonce)
        elif order_type == "buy":
            token_address = self.provider.toChecksumAddress(order["buytoken"]["address"])
            token_type = self.determineTokenType(token_address)
            if token_type == "ERC223":
                return self.newERC223Trade(token_address, amount, order, custom_nonce)
            else:
                return self.newERC20Trade(token_address, amount, order, custom_nonce)
        else:
            raise Exception(f'Unknown order type for order_tx {orderTx} on ${self.blockchain}')

    def cancelOrder(self, order_id: int, contract: str=None, custom_nonce=None) -> str:
        if contract is None:
            contract = self.exchange_contract_address

        contract_addr = self.provider.toChecksumAddress(contract)
        exchange = self.provider.eth.contract(address=contract_addr, abi=EXCHANGECONFIG["abi"])

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        unsigned_tx = exchange.functions.cancelOrder(order_id).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def cancelOrderByTxHash(self, txhash : str):
        order = self.query.getOrderByTx(txhash.lower())
        order_id = int(order["order_id"])
        cancel_hash = self.cancelOrder(order_id)
        self.log(f'CANCELING ORDERID {order_id} (ORDERHASH: {txhash}), CANCEL HASH: {cancel_hash}')
        wait = self.provider.eth.waitForTransactionReceipt(cancel_hash, timeout=120)
        return wait

    def newOrder(self, token_address, order_type, amount, price, custom_nonce=None):
        token_address = self.provider.toChecksumAddress(token_address)

        self.verifyOrderType(order_type.lower())
        token_type = self.determineTokenType(token_address)
        order_contract = self.exchange_contract_address

        if order_type == 'buy':
            return self.newBuyOrder(token_address, amount, price, order_contract, custom_nonce)
        elif order_type == 'sell':
            if token_type == 'ERC223':
                return self.newERC223sellOrder(
                    token_address, amount,
                    price, order_contract,
                    custom_nonce
                )
            elif token_type == 'ERC20':
                return self.newERC20sellOrder(
                    token_address, amount,
                    price, order_contract,
                    custom_nonce
                )
            else:
                raise Exception('UNKNOWN TOKEN STANDARD')
        else:
            raise Exception(f'UNKNOWN ORDERTYPE {order_type}')

    def newBuyOrder(self, token_address, amount, price, order_contract, custom_nonce):
        amount = Fraction(amount)
        price = Fraction(price)

        token_address = self.provider.toChecksumAddress(token_address)
        ex_contract = self.provider.toChecksumAddress(order_contract)
        exchange = self.provider.eth.contract(address=ex_contract, abi=EXCHANGECONFIG["abi"])

        if not self.SBTKN:
            token = self.provider.eth.contract(address=token_address, abi=ERC20)
            exp_decimals = 10 ** int(token.functions.decimals().call())
            amount = amount * exp_decimals
            price = price * exp_ether_decimals / exp_decimals

        amount = intVerify(amount, self.STRICT)
        wei_amount = intVerify(amount * price, self.STRICT)

        if not self.BNDL:
            if price.denominator != 1:
                raise Exception(f'Price is a Fraction. Bundle Pricing is not allowed.')

        self.verifyEtherBalance(wei_amount)

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        unsigned_tx = exchange.functions.sellEther(
            token_address,
            price.numerator,
            price.denominator
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce,
            'value': int(wei_amount)
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def newERC223sellOrder(self, token_address, amount, price, order_contract, custom_nonce=None):
        amount = Fraction(amount)
        price = Fraction(price)

        token_address = self.provider.toChecksumAddress(token_address)
        order_contract = self.provider.toChecksumAddress(order_contract)
        token = self.provider.eth.contract(address=token_address, abi=ERC223)

        if not self.SBTKN:
            exp_decimals = 10 ** int(token.functions.decimals().call())
            amount = toSbtkn(amount, exp_decimals, self.STRICT)
            price = price * exp_ether_decimals / exp_decimals

        amount = intVerify(amount, self.STRICT)
        intVerify(amount * price, self.STRICT)

        if not self.BNDL:
            if price.denominator != 1:
                raise Exception(f'Price is a Fraction. Bundle Pricing is not allowed.')

        self.verifyTokenBalance(token_address, amount)

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        payload = self.createERC223OrderPayload(price.denominator, price.numerator, etheraddress)

        unsigned_tx = token.functions.transfer(
            order_contract,
            amount,
            payload
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash

    def newERC20sellOrder(self, token_address, amount, price, order_contract, custom_nonce=None):
        amount = Fraction(amount)
        price = Fraction(price)

        token_address = self.provider.toChecksumAddress(token_address)
        order_contract = self.provider.toChecksumAddress(order_contract)
        token = self.provider.eth.contract(address=token_address, abi=ERC20)

        if not self.SBTKN:
            exp_decimals = 10 ** int(token.functions.decimals().call())
            amount = toSbtkn(amount, exp_decimals, self.STRICT)
            price = price * exp_ether_decimals / exp_decimals

        amount = intVerify(amount, self.STRICT)
        intVerify(amount * price, self.STRICT)

        if not self.BNDL:
            if price.denominator != 1:
                raise Exception(f'Price is a Fraction. Bundle Pricing is not allowed.')

        self.verifyTokenBalance(token_address, amount)

        if custom_nonce is None:
            nonce = self.provider.eth.getTransactionCount(self.wallet.address)
        else:
            nonce = custom_nonce

        self.verifyAllowance(token_address, amount, order_contract)

        exchange = self.provider.eth.contract(address=order_contract, abi=EXCHANGECONFIG["abi"])

        unsigned_tx = exchange.functions.sellERC20Token(
            token_address,
            etheraddress,
            amount,
            price.denominator,
            price.numerator
        ).buildTransaction({
            'chainId': self.networkId,
            'gasPrice': self.getGasPrice(),
            'gas': gaslimit,
            'nonce': nonce
        })

        txhash = self.sendRawTx(unsigned_tx)
        return txhash
