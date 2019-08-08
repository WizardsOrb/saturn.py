import requests, json
import pandas as pd
from statistics import mean 

class RequestManager():
    etheraddress = "0x0000000000000000000000000000000000000000"
    payload = {'Origin': 'saturnpy'}
    def __init__(self, apiurl, provider, wallet, blockchain):
        self.apiurl = apiurl
        self.provider = provider
        self.wallet = wallet
        self.blockchain = blockchain

    def getTransaction(self, tx : str):
        url = "{}transactions/{}/{}.json".format(str(self.apiurl), str(self.blockchain),str(tx))
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()

    def getOrderByTx(self, tx : str):
        url = "{}orders/by_tx/{}/{}.json".format(str(self.apiurl), str(self.blockchain),str(tx))
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()
    
    def awaitOrderTx(self, tx):
        try:
            self.provider.eth.waitForTransactionReceipt(tx, timeout=120)
        except:
            errmessage = 'ERROR AWAITING ORDER RECEIPT'
            raise Exception('ERROR\n{}\n{}'.format(errmessage, tx))
        finally:
            order = self.getOrderByTx(tx)
            return order

    def getTradeByTx(self, tx : str):
        url = "{}trades/by_tx/{}/{}.json".format(str(self.apiurl), str(self.blockchain),str(tx))
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()

    def awaitTradeTx(self, tx):
        try:
            self.provider.eth.waitForTransactionReceipt(tx, timeout=120)
        except:
            errmessage = 'ERROR AWAITING TRADE RECEIPT'
            raise Exception('ERROR\n{}\n{}'.format(errmessage, tx))
        finally:
            trade = self.getTradeByTx(tx)
            return trade

    def getTokenInfo(self, address : str):
        url = "{}tokens/show/{}/{}.json".format(str(self.apiurl), str(self.blockchain),str(address).lower())
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()

    def getExchangeContract(self, blockchain = None):
        if blockchain == None:
            blockchain = self.blockchain
        url = "{}orders/contracts.json".format(str(self.apiurl))
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            data = data.json()
            result = data[blockchain.upper()]
            return result

    def ordersForAddress(self, address : str):
        url = "{}orders/trader/{}.json".format(str(self.apiurl), str(address).lower())
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            data = data.json()
            sell_orders = pd.Series(data["sell_orders"])
            buy_orders = pd.Series(data["buy_orders"])

            return pd.concat([sell_orders, buy_orders], ignore_index=True)

    def orderbook(self, token : str):
        url = "{}orders/{}/{}/{}/all.json".format(str(self.apiurl), str(self.blockchain),str(token).lower(), str(self.etheraddress))
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()

    def ohlcv(self, token : str):
        url = "{}tokens/ohlcv/{}/{}/24h.json".format(str(self.apiurl), str(self.blockchain),str(token).lower())
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()

    def getRSI(self, token : str, periods : int = 14, ohlcvdata = None):
        if ohlcvdata == None:
            ohlcvdata = self.ohlcv(token.lower())
        data = ohlcvdata[-periods:]
        avgOpen = []
        avgClose = []

        for x in data:
            avgOpen.append(float(x["open"]))
            avgClose.append(float(x["close"]))

        avgOpen = mean(avgOpen)
        avgClose = mean(avgClose)

        RS = avgClose / avgOpen
        RSI = 100 - ( 1 / (1 + RS) )

        out = {
            "RSI": RSI,
            "avgOpen": avgOpen,
            "avgClose": avgClose,
            "periods": periods
        }
        return out

    def tradeHistory(self, token : str):
        url = "{}trades/{}/{}/{}/all.json".format(str(self.apiurl), str(self.blockchain),str(token).lower(),str(self.etheraddress).lower())
        try:
            data = requests.get(url, params=self.payload)
        except:
            raise Exception('ERROR GET URL: {}'.format(url))
        finally:
            return data.json()
