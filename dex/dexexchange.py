from data import marketmakerexchange
from dex import client
import logging

log = logging.getLogger(__name__)
EXCHANGE_NAME = "dex"
DEX_PROFIT_DEDUCTION = 0.004


class DexExchange(marketmakerexchange.MarketMakerExchange):
    def get_profit_deduction(self):
        return DEX_PROFIT_DEDUCTION

    def list_my_orders(self):
        return self.client.exchange.returnOpenOrders(marketmakerexchange.MARKET)[marketmakerexchange.MARKET]

    def __init__(self, witness_url, account, secret_key):
        self.client = client.Client(witness_url, account, secret_key)

    def get_maker_account_balance(self):
        balance = self.client.exchange.returnBalances()
        return {marketmakerexchange.CNY: float(balance["CNY"]),
                marketmakerexchange.BTS: float(balance["BTS"])}

    def get_exchange_name(self):
        return EXCHANGE_NAME

    def get_top_offers(self):
        orders = self.client.exchange.returnOrderBook(currencyPair=marketmakerexchange.MARKET)
        bids = orders[marketmakerexchange.MARKET][marketmakerexchange.BIDS]
        asks = orders[marketmakerexchange.MARKET][marketmakerexchange.ASKS]
        return [self.__get_true_orders(bids),
                self.__get_true_orders(asks)]

    def submit_arbitrage_order(self, order_type, price, volume):
        if order_type == 1:
            self.client.exchange.buy("BTS_CNY", price, volume)
        elif order_type == 2:
            self.client.exchange.sell("BTS_CNY", price, volume)
        else:
            log.error("Unrecognized order type: {}".format(order_type))

    @staticmethod
    def __get_true_orders(orders):
        vol = 0
        for order in orders:
            vol += order[1]
            if vol > marketmakerexchange.FAKE_ORDER_AMOUNT:
                return [order[0], vol]
        return orders[0][:2]
