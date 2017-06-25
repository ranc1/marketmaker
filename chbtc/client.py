import struct
import urllib.request
import urllib.parse
import json
import time
import logging
import hashlib

DATA_URL = "http://api.chbtc.com/data/v1/"
TRADE_URL = "http://trade.chbtc.com/api/"

ENCODING = 'utf-8'

API_PATH_DICT = {
    # Data API
    'ticker': DATA_URL + 'ticker?',
    'depth': DATA_URL + 'depth?',
    'kline': DATA_URL + 'kline?',
    'trades': DATA_URL + 'trades?',

    # Trade API
    'order': TRADE_URL + 'order?',
    'cancelOrder': TRADE_URL + 'cancelOrder?',
    'getAccountInfo': TRADE_URL + 'getAccountInfo?'
}

log = logging.getLogger(__name__)


def fill(value, length, fill_byte):
    if len(value) >= length:
        return value
    else:
        fill_size = length - len(value)
    return value + chr(fill_byte) * fill_size


def do_xor(s, value):
    slist = list(s)
    for index in range(len(slist)):
        slist[index] = chr(slist[index] ^ value)
    return "".join(slist)


def hmac_sign(input_value, input_key):
    keyb = struct.pack("%ds" % len(input_key), input_key.encode(ENCODING))
    value = struct.pack("%ds" % len(input_value), input_value.encode(ENCODING))
    k_ipad = do_xor(keyb, 0x36)
    k_opad = do_xor(keyb, 0x5c)
    k_ipad = fill(k_ipad, 64, 54)
    k_opad = fill(k_opad, 64, 92)
    m = hashlib.md5()
    m.update(k_ipad.encode(ENCODING))
    m.update(value)
    dg = m.digest()

    m = hashlib.md5()
    m.update(k_opad.encode(ENCODING))
    sub_str = dg[0:16]
    m.update(sub_str)
    dg = m.hexdigest()
    return dg


def digest(input_value):
    value = struct.pack("%ds" % len(input_value), input_value.encode(ENCODING))
    h = hashlib.md5()
    h.update(value)
    dg = h.hexdigest()
    return dg


class Client(object):
    def __init__(self, access_key=None, private_key=None):
        if access_key and private_key:
            self.access_key = access_key
            self.private_key = private_key
        else:
            log.warning("Please provide correct credentials.")

    def __request(self, api_name, param=None, sign_needed=False):

        headers = {'User-Agent': 'Mozilla/4.0'}
        url = API_PATH_DICT[api_name]

        if not param:
            param = {}
        if sign_needed:
            param['method'] = API_PATH_DICT[api_name]
            param['accesskey'] = self.access_key
            sha_secret = digest(self.private_key)
            sign_parameters = '&'.join(['%s=%s' % (key, value) for (key, value) in param.items()])
            signature = hmac_sign(sign_parameters, sha_secret)
            param['sign'] = signature
            param['reqTime'] = int(time.time() * 1000)

        parameters = '&'.join(['%s=%s' % (key, value) for (key, value) in param.items()])
        url += parameters
        log.info(url)

        request = urllib.request.Request(url=url, headers=headers)

        response = urllib.request.urlopen(request, timeout=5)
        result = response.readlines()
        response.close()
        return result

    def get_account_info(self):
        result = self.__request('getAccountInfo', sign_needed=True)
        log.info(result)
        return json.loads(result[0].decode(ENCODING))

    def get_depth(self, currency='bts_cny', size=None, merge=None):
        param = {'currency': currency}
        if size:
            param['size'] = size
        if merge:
            param['merge'] = merge
        result = self.__request('depth', param)

        return json.loads(result[0].decode(ENCODING))


client = Client('21d1a9a0-145b-4b2a-9129-1d9cbe21950a', 'fad13186-376e-453a-a4f3-f1a4bf481b8a')
logging.basicConfig(level=logging.INFO)

while True:
    account = client.get_account_info()
    log.info(account)
    time.sleep(0.2)
