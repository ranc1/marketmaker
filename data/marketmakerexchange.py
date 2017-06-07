import abc

BIDS = 'bids'
ASKS = 'asks'
MARKET = "BTS_CNY"
CNY = "CNY"
BTS = "BTS"
FAKE_ORDER_AMOUNT = 10


class MarketMakerExchange(object):
    # order_type 1 for biding, 2 for asking.
    @abc.abstractclassmethod
    def submit_arbitrage_order(self, order_type, price, volume):
        raise NotImplementedError('Not implemented in abc')

    @abc.abstractclassmethod
    def get_top_offers(self):
        raise NotImplementedError('Not implemented in abc')

    @abc.abstractclassmethod
    def get_exchange_name(self):
        raise NotImplementedError('Not implemented in abc')

    @abc.abstractclassmethod
    def get_maker_account_balance(self):
        raise NotImplementedError('Not implemented in abc')

    @abc.abstractclassmethod
    def list_my_orders(self):
        raise NotImplementedError('Not implemented in abc')

    @abc.abstractclassmethod
    def get_profit_deduction(self):
        raise NotImplementedError('Not implemented in abc')
