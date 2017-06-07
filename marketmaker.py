import json
from btc38 import btc38exchange
from dex import dexexchange
import logging
from data import marketmakerexchange
from datetime import datetime
import traceback
import time
from apscheduler.schedulers.background import BackgroundScheduler
import multiprocessing
from notifications import emailsender
import operator

CNY_CURRENCY_CODE = marketmakerexchange.CNY
BTS_CURRENCY_CODE = marketmakerexchange.BTS
BIDS = marketmakerexchange.BIDS
ASKS = marketmakerexchange.ASKS
UPDATE_TIME = "updateTime"

# DEX has a lower profit threshold since it has no deposit limit.
BTC38_PROFIT_THRESHOLD = 0.023
DEX_PROFIT_THRESHOLD = 0.013
PROFIT_THRESHOLD = 0.02

MINIMUM_PURCHASE_VOLUME = 500
# Leave 100 shares in the listing as buffer
LISTING_VOLUME_BUFFER = 1000

ACCOUNT_CNY_RESERVE = 50
ACCOUNT_BTS_RESERVE = 100

# Assumed exchange update interval is under 1 seconds.
EXCHANGE_UPDATE_INTERVAL = 1
EXCHANGE_SYNC_TOLERANCE = 4
UPDATE_LAG_TOLERANCE = 10
# Order book information is valid for 4 seconds.
ORDER_BOOK_VALID_WINDOW = 4

# logger
log = logging.getLogger(__name__)


class TradeExchange(object):
    def __init__(self):
        with open("configurations/config.json") as client_config:
            config = json.load(client_config)

        for exchange_client in config:
            if exchange_client['client'] == dexexchange.EXCHANGE_NAME:
                self.dexExchange = dexexchange.DexExchange(exchange_client['WITNESS_URL'],
                                                           exchange_client['ACCOUNT'],
                                                           exchange_client['SECRET_KEY'])
            if exchange_client['client'] == btc38exchange.EXCHANGE_NAME:
                self.btc38Exchange = btc38exchange.BTC38Exchange(exchange_client['ACCESS_KEY'],
                                                                 exchange_client['SECRET_KEY'],
                                                                 exchange_client['ACCOUNT_ID'])


# Daemon to update order books. Each exchange requires one daemon. Daemon should not terminate in any cases.
def order_book_fetcher_daemon(exchange, order_book):
    while True:
        exchange_name = exchange.get_exchange_name()
        current_time = datetime.now()
        exchange_order_book = order_book[exchange_name]
        time_since_last_update = (current_time - exchange_order_book[UPDATE_TIME]).total_seconds()

        try:
            top_offers = exchange.get_top_offers()
            order_book_bid = exchange_order_book[BIDS]
            order_book_ask = exchange_order_book[ASKS]
            # Added this check to prevent exchanges not updating order book when orders change.
            if order_book_bid == top_offers[0] and order_book_ask == top_offers[1]:
                if time_since_last_update > EXCHANGE_UPDATE_INTERVAL:
                    exchange_order_book[UPDATE_TIME] = current_time
            else:
                exchange_order_book[BIDS] = top_offers[0]
                exchange_order_book[ASKS] = top_offers[1]
                exchange_order_book[UPDATE_TIME] = current_time

            order_book[exchange_name] = exchange_order_book
            time.sleep(1)
        except Exception as e:
            if time_since_last_update > UPDATE_LAG_TOLERANCE:
                log.warn("{}: Exchange: {} receives no update for {} seconds. (Last error: {})"
                          .format(current_time, exchange_name, time_since_last_update, e))


# Send notification email using the template.
def send_notification_email(message):
    with open("configurations/email_header.json") as email_header:
        header = json.load(email_header)
    with open("configurations/email_credential.json") as email_credential:
        credential = json.load(email_credential)

    email_sender = emailsender.EmailSender(credential["login"], credential["password"])
    email_process = multiprocessing.Process(target=email_sender.send_email_with_message,
                                            args=(message, header["subject"], header["from"], header["to"]))
    email_process.start()


class MarketMaker(object):
    def __init__(self):
        self.exchange = TradeExchange()
        btc38_exchange_name = self.exchange.btc38Exchange.get_exchange_name()
        dex_exchange_name = self.exchange.dexExchange.get_exchange_name()
        self.account_balance = {btc38_exchange_name: {CNY_CURRENCY_CODE: 0, BTS_CURRENCY_CODE: 0},
                                dex_exchange_name: {CNY_CURRENCY_CODE: 0, BTS_CURRENCY_CODE: 0}}
        current_time = datetime.now()
        manager = multiprocessing.Manager()
        self.order_book = manager.dict({btc38_exchange_name: {BIDS: [0, 0], ASKS: [0, 0], UPDATE_TIME: current_time},
                                        dex_exchange_name: {BIDS: [0, 0], ASKS: [0, 0], UPDATE_TIME: current_time}})
        self.exchanges = [self.exchange.btc38Exchange, self.exchange.dexExchange]
        self.exchanges_name_dict = {btc38_exchange_name: self.exchange.btc38Exchange,
                                    dex_exchange_name: self.exchange.dexExchange}

        self.last_transaction_time = {btc38_exchange_name: current_time, dex_exchange_name: current_time}

        # Check balance only when transactions were made.
        self.need_balance_check = True

    def run(self):
        scheduler = BackgroundScheduler()
        # Update account balance every 5 minutes in case external transfer happened.
        scheduler.add_job(self.__request_account_balance_checking, 'interval', minutes=5)
        scheduler.start()

        order_book_fetchers = []
        for exchange in self.exchanges:
            p = multiprocessing.Process(target=order_book_fetcher_daemon, args=(exchange, self.order_book))
            p.daemon = True
            order_book_fetchers.append(p)
            p.start()
            log.info("Started updating order book process for exchange: {}, pid: {}"
                     .format(exchange.get_exchange_name(), p.pid))

        while all(map(multiprocessing.Process.is_alive, order_book_fetchers)):
            try:
                self.__speculate()
                time.sleep(0.5)
            except Exception as e:
                traceback.print_exc()
                log.error("Unexpected exception caught in main execution. (Error: {})".format(e))

        log.fatal("Order book daemon terminated! Exit the market maker.")
        send_notification_email("Market Maker terminated!")

    def __speculate(self):
        if self.need_balance_check:
            try:
                self.__update_account_balance()
            except Exception as e:
                log.error("Failed to update account balance.(Error: {})".format(e))
                return

        for buyer_name, buyer_exchange in self.exchanges_name_dict.items():
            if self.__is_order_book_valid(buyer_name):
                profitable_exchange_name = self.__find_profitable_exchange(buyer_exchange)
                if profitable_exchange_name:
                    seller_exchange = self.exchanges_name_dict[profitable_exchange_name]

                    purchase_price = self.order_book[buyer_name][ASKS][0]
                    sell_price = self.order_book[profitable_exchange_name][BIDS][0]

                    purchase_volume = self.__calculate_purchase_volume(buyer_exchange, seller_exchange)
                    sell_volume = self.__calculate_sell_volume(buyer_exchange, purchase_volume)

                    order_placed = self.__place_arbitrage_orders(buyer_exchange, purchase_price, purchase_volume,
                                                                 seller_exchange, sell_price, sell_volume)

                    if order_placed:
                        send_notification_email("Arbitrage: purchase from {} at {}, volume: {}\n"
                                                "Arbitrage: sell to {} at {}, volume: {}"
                                                .format(buyer_name, purchase_price, purchase_volume,
                                                        profitable_exchange_name, sell_price, sell_volume))

    """
        Find the highest bidder in the order book. If the profit is higher than the threshold,
        return profitable exchange name.
    """
    def __find_profitable_exchange(self, buyer_exchange):
        buyer_name = buyer_exchange.get_exchange_name()
        target_order_book = {exchange_name: order_book[BIDS][0] for exchange_name, order_book in self.order_book.items()
                             if self.__is_order_book_valid(exchange_name) and exchange_name != buyer_name
                             and self.__order_books_in_sync(buyer_name, exchange_name)}

        if len(target_order_book) == 0:
            return None

        best_offer = max(target_order_book.items(), key=operator.itemgetter(1))
        purchase_price = self.order_book[buyer_name][ASKS][0]
        profit = (best_offer[1] - purchase_price) / purchase_price
        if profit - buyer_exchange.get_profit_deduction() > PROFIT_THRESHOLD:
            log.info("Found profitable exchange {}! Profit: {}%."
                     .format(buyer_name, round(profit, 3) * 100))
            return best_offer[0]

    def __order_books_in_sync(self, base_exchange_name, target_exchange_name):
        base_ex_update_time = self.order_book[base_exchange_name][UPDATE_TIME]
        compare_ex_update_time = self.order_book[target_exchange_name][UPDATE_TIME]
        if abs((base_ex_update_time - compare_ex_update_time).total_seconds()) > EXCHANGE_SYNC_TOLERANCE:
            return False
        else:
            return True

    def __is_order_book_valid(self, exchange_name):
        current_time = datetime.now()
        last_update_time = self.order_book[exchange_name][UPDATE_TIME]
        updated_after_transactions = last_update_time > self.last_transaction_time[exchange_name]
        order_book_valid = (current_time - last_update_time).total_seconds() < ORDER_BOOK_VALID_WINDOW
        return updated_after_transactions and order_book_valid

    def __request_account_balance_checking(self):
        self.need_balance_check = True

    def __update_account_balance(self):
        for exchange in self.exchanges:
            exchange_name = exchange.get_exchange_name()
            balance = exchange.get_maker_account_balance()
            self.account_balance[exchange_name][CNY_CURRENCY_CODE] = balance[CNY_CURRENCY_CODE]
            self.account_balance[exchange_name][BTS_CURRENCY_CODE] = balance[BTS_CURRENCY_CODE]

        log.info("Account balance updated. New account balance: {}".format(self.account_balance))
        self.need_balance_check = False

    # Price = BTS price in terms of CNY. Volume = number of BTS shares.
    def __calculate_purchase_volume(self, buyer_exchange, seller_exchange):
        buyer_exchange_name = buyer_exchange.get_exchange_name()
        seller_exchange_name = seller_exchange.get_exchange_name()

        buyer_vol = self.order_book[buyer_exchange_name][ASKS][1]
        seller_vol = self.order_book[seller_exchange_name][BIDS][1]

        volume_available = min(buyer_vol, seller_vol)

        if volume_available < MINIMUM_PURCHASE_VOLUME + LISTING_VOLUME_BUFFER:
            return 0

        buyer_price = self.order_book[buyer_exchange_name][ASKS][0]

        usable_cny = self.account_balance[buyer_exchange_name][CNY_CURRENCY_CODE] - ACCOUNT_CNY_RESERVE
        usable_bts = self.account_balance[seller_exchange_name][BTS_CURRENCY_CODE] - ACCOUNT_BTS_RESERVE

        if usable_cny <= 0:
            log.info("Insufficient fund on buyer account: {}".format(buyer_exchange_name))
            return 0
        elif usable_bts <= 0:
            log.info("Insufficient fund on seller account: {}".format(seller_exchange_name))
            return 0
        else:
            return min(round(usable_cny / buyer_price, 5), usable_bts, volume_available - LISTING_VOLUME_BUFFER)

    @staticmethod
    def __calculate_sell_volume(buyer_exchange, purchase_volume):
        buyer_name = buyer_exchange.get_exchange_name()
        # Withdrawal fee from btc38 is 1%, therefore, sell_vol = purchase_vol * 0.99 - 1
        if buyer_name == btc38exchange.EXCHANGE_NAME:
            return purchase_volume * 0.99 - 1
        else:
            return purchase_volume - 1

    def __open_order_exists(self):
        for exchange in self.exchanges:
            orders = exchange.list_my_orders()
            if orders:
                log.info("{} order still open: {}".format(exchange.get_exchange_name(), orders))
                return True
        return False

    """
        Place arbitrage order, return True if both orders have been placed, false otherwise.
        After placing arbitrage order, send out email notification.
        Price = BTS price in terms of CNY. Volume = number of BTS shares.
    """
    def __place_arbitrage_orders(self, buyer_exchange, purchase_price, purchase_volume,
                                 seller_exchange, sell_price, sell_volume):
        if sell_volume < MINIMUM_PURCHASE_VOLUME:
            log.info("Under minimum arbitrage volume: {}".format(sell_volume))
            return False

        buyer_exchange_name = buyer_exchange.get_exchange_name()
        seller_exchange_name = seller_exchange.get_exchange_name()

        # If this method is called, successful or not, we need to recheck the account balance.
        self.need_balance_check = True
        # Update last transaction date no matter the transaction succeeded or not.
        current_time = datetime.now()

        try:
            buyer_exchange.submit_arbitrage_order(1, purchase_price, purchase_volume)
            self.last_transaction_time[buyer_exchange_name] = current_time
            log.info("Arbitrage: purchase from {} at {}, volume: {}"
                     .format(buyer_exchange_name, purchase_price, purchase_volume))
        except Exception as e:
            log.error("Unable to place order at exchange: {}. Error: {}"
                      .format(buyer_exchange_name, e))
            return False
        seller_exchange.submit_arbitrage_order(2, sell_price, sell_volume)
        self.last_transaction_time[seller_exchange_name] = current_time
        log.info("Arbitrage: sell to {} at {}, volume: {}".format(seller_exchange_name, sell_price, sell_volume))

        return True