import urllib.request
import urllib.error
import urllib.parse
import urllib
import json
import time
import hashlib
from retry import retry
import logging
import socket
from exceptions import orderexception

BASE_URL = 'http://api.btc38.com/v1/'
SUBMIT_ORDER_SUCCESS_STRING = "succ"
ENCODING = 'utf-8'
log = logging.getLogger(__name__)

API_PATH_DICT = {
    # GET
    # market code required in url as {market}.json
    'tickers': 'ticker.php?',
    # 'tickers' : 'ticker.php?c=%s&mk_type=%s',

    'depth': 'depth.php?',
    # 'depth': 'depth.php?c=%s&mk_type=%s',

    # order id required in url query string as '?id={id}'
    'myorders': 'getOrderList.php',

    # market required in url query string as '?market={market}'
    'trades': 'trades.php?',
    # 'trades': 'trades.php?c=%s&mk_type=%s&tid=%s',

    # POST
    'balance': 'getMyBalance.php',
    'submitorder': 'submitOrder.php',
    'cancelorder': 'cancelOrder.php',

    # market required in url query string as '?market={market}'
    'mytrades': 'getMyTradeList.php',
}


def get_api_path(name):
    path_pattern = API_PATH_DICT[name]
    return BASE_URL + path_pattern


class Client(object):
    def __init__(self, access_key=None, secret_key=None, account_id=None):
        if access_key and secret_key:
            self.access_key = access_key
            self.secret_key = secret_key
            self.mdt = "%s_%s_%s" % (access_key, account_id, secret_key)
        else:
            log.warning("please provide correct keys")

    def __request(self, name, data=None, c=None, mk_type=None, tid=None):
        headers = {'User-Agent': 'Mozilla/4.0'}
        url = get_api_path(name)

        if c:
            query = "c=%s&mk_type=%s" % (c, mk_type)
            if tid:
                query += "&tid=%s" % tid
            url += query

        if data:
            data = urllib.parse.urlencode(data)
            data = data.encode(ENCODING)
            req = urllib.request.Request(url=url, data=data, headers=headers)
        else:
            req = urllib.request.Request(url=url, data=None, headers=headers)

        resp = self.__urlopen_with_retry(req)
        result = resp.readlines()
        resp.close()
        return result

    def get_tickers(self, c='bts', mk_type='cny'):
        result = self.__request('tickers', c=c, mk_type=mk_type)
        return json.loads(result[0].decode(ENCODING))

    """ Sample:
        {'bids': [[0.4402, 1623.38488], [0.4401, 10366.271967], [0.44, 8204.550502], [0.4392, 2624], ..,],
        'asks': [[0.4444, 4127.835417], [0.4457, 7358.901461], [0.4458, 10000], [0.4459, 9170.8], ...]}
    """
    def get_depth(self, c='bts', mk_type='cny'):
        result = self.__request('depth', c=c, mk_type=mk_type)
        # Might get [b'fail#3']
        try:
            return json.loads(result[0].decode(ENCODING))
        except IndexError as e:
            log.error("Index error, result: {}".format(result))
            raise e

    def get_my_balance(self):
        timestamp, md5 = self.__get_md5()
        params = {'key': self.access_key, 'time': timestamp, 'md5': md5}
        result = self.__request("balance", params)
        return json.loads(result[0].decode(ENCODING))

    """ Submit order. Max precision for cny is 5 digits, for btc is 8. Max precision for amount is 6.
        type: 1 for buy, and 2 for sell
    """
    def submit_order(self, order_type, mk_type, price, amount, coinname):
        timestamp, md5 = self.__get_md5()
        params = {'key': self.access_key,
                  'time': timestamp,
                  'md5': md5,
                  'type': order_type,
                  'mk_type': mk_type,
                  'price': price,
                  'amount': amount,
                  'coinname': coinname}

        result = self.__request("submitorder", params)
        if SUBMIT_ORDER_SUCCESS_STRING not in result[0].decode(ENCODING):
            log.error(result)
            raise orderexception.SubmitOrderFailureException("Failed to place order in BTC38 exchange.")
        return result

    def cancel_order(self, mk_type, order_id):
        timestamp, md5 = self.__get_md5()
        params = {'key': self.access_key, 'time': timestamp, 'md5': md5, 'mk_type': mk_type, 'order_id': order_id}
        return self.__request("cancelorder", params)

    def get_order_list(self, coinname=None):
        timestamp, md5 = self.__get_md5()
        params = {'key': self.access_key, 'time': timestamp, 'md5': md5, 'coinname': coinname}
        result = self.__request("myorders", params)
        if result == [b'no_order']:
            return []
        return json.loads(result[0].decode(ENCODING))

    def get_my_trade_list(self, mk_type='cny', coinname='bts', page=1):
        timestamp, md5 = self.__get_md5()
        params = {'key': self.access_key,
                  'time': timestamp,
                  'md5': md5,
                  'mk_type': mk_type,
                  'coinname': coinname,
                  'page': page}

        result = self.__request("mytrades", params)
        return json.loads(result[0].decode(ENCODING))

    def __get_md5(self):
        stamp = int(time.time())
        mdt = "%s_%s" % (self.mdt, stamp)
        md5 = hashlib.md5()
        md5.update(mdt.encode(ENCODING))
        return stamp, md5.hexdigest()

    @retry((urllib.error.URLError, socket.timeout), tries=1, delay=1, backoff=1.1)
    def __urlopen_with_retry(self, request):
        return urllib.request.urlopen(request, timeout=2)
