from data import marketmakerexchange
from btc38 import client
import logging

EXCHANGE_NAME = "btc38"
BTC38_PROFIT_DEDUCTION = 0.014
log = logging.getLogger(__name__)


class BTC38Exchange(marketmakerexchange.MarketMakerExchange):
    def get_profit_deduction(self):
        return BTC38_PROFIT_DEDUCTION

    def list_my_orders(self):
        return self.client.get_order_list(marketmakerexchange.BTS)

    def __init__(self, access_key=None, secret_key=None, account_id=None):
        self.client = client.Client(access_key, secret_key, account_id)

    def get_maker_account_balance(self):
        balance = self.client.get_my_balance()
        return {marketmakerexchange.CNY: float(balance["cny_balance"]),
                marketmakerexchange.BTS: float(balance["bts_balance"])}

    def get_exchange_name(self):
        return EXCHANGE_NAME

    def get_top_offers(self):
        orders = self.client.get_depth()
        bids = orders[marketmakerexchange.BIDS]
        asks = orders[marketmakerexchange.ASKS]
        return [self.__get_true_orders(bids),
                self.__get_true_orders(asks)]

    def submit_arbitrage_order(self, order_type, price, volume):
        self.client.submit_order(order_type, 'cny', price, volume, 'bts')

    @staticmethod
    def __get_true_orders(orders):
        vol = 0
        for order in orders:
            vol += order[1]
            if vol > marketmakerexchange.FAKE_ORDER_AMOUNT:
                return [order[0], vol]
        return orders[0]
