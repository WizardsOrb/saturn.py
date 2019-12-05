from statistics import mean
import requests
import pandas as pd
from .utils import etheraddress

class RequestManager():
    payload = {'Origin': 'saturnpy'}
    def __init__(self, apiurl, provider, wallet, blockchain):
        self.apiurl = apiurl
        self.provider = provider
        self.wallet = wallet
        self.blockchain = blockchain

    def getTransaction(self, tx: str):
        url = f"{self.apiurl}transactions/{self.blockchain}/{tx}.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def getOrderByTx(self, tx: str):
        url = f"{self.apiurl}orders/by_tx/{self.blockchain}/{tx}.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def awaitOrderTx(self, tx):
        try:
            self.provider.eth.waitForTransactionReceipt(tx, timeout=120)
        except:
            errmessage = 'ERROR AWAITING ORDER RECEIPT'
            raise Exception(f"ERROR\n{errmessage}\n{tx}")
        finally:
            order = self.getOrderByTx(tx)
            return order

    def getTradeByTx(self, tx: str):
        url = f"{self.apiurl}trades/by_tx/{self.blockchain}/{tx}.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def awaitTradeTx(self, tx):
        try:
            self.provider.eth.waitForTransactionReceipt(tx, timeout=120)
        except:
            errmessage = 'ERROR AWAITING TRADE RECEIPT'
            raise Exception(f"ERROR\n{errmessage}\n{tx}")
        finally:
            trade = self.getTradeByTx(tx)
            return trade

    def getTokenInfo(self, address: str):
        url = f"{self.apiurl}tokens/show/{self.blockchain}/{address.lower()}.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def getExchangeContract(self, blockchain=None):
        if blockchain is None:
            blockchain = self.blockchain
        url = f"{self.apiurl}orders/contracts.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            data = data.json()
            result = data[blockchain.upper()]
            return result

    def ordersForAddress(self, address: str):
        url = f"{self.apiurl}orders/trader/{address.lower()}.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            data = data.json()
            sell_orders = pd.Series(data["sell_orders"])
            buy_orders = pd.Series(data["buy_orders"])

            return pd.concat([sell_orders, buy_orders], ignore_index=True)

    def orderbook(self, token: str):
        url = f"{self.apiurl}orders/{self.blockchain}/{token.lower()}/{str(etheraddress)}/all.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def ohlcv(self, token: str):
        url = f"{self.apiurl}tokens/ohlcv/{self.blockchain}/{token.lower()}/24h.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()

    def getRSI(self, token: str, periods: int = 14, ohlcvdata=None):
        if ohlcvdata is None:
            ohlcvdata = self.ohlcv(token.lower())
        data = ohlcvdata[-periods:]
        avg_open = []
        avg_close = []

        for x in data:
            avg_open.append(float(x["open"]))
            avg_close.append(float(x["close"]))

        avg_open = mean(avg_open)
        avg_close = mean(avg_close)

        rs = avg_close / avg_open
        rsi = 100 - ( 1 / (1 + rs) )

        out = {
            "RSI": rsi,
            "avgOpen": avg_open,
            "avgClose": avg_close,
            "periods": periods
        }
        return out

    def tradeHistory(self, token: str):
        url = f"{self.apiurl}trades/{self.blockchain}/{token.lower()}/{etheraddress.lower()}/all.json"
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception(f"ERROR GET URL: {url}")
        finally:
            return data.json()
