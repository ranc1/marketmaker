import websocket
import time

API_END_POINT = "wss://api.chbtc.com:9999/websocket"
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


class Client(object):
    def __init__(self, access_key=None):
        self.access_key = access_key
        ws = websocket.create_connection(API_END_POINT)

    def get_depth(self):
        ws = websocket.create_connection(API_END_POINT)
        request = "{'event': 'addChannel', 'channel': 'bts_cny_ticker'}"
        ws.send(request)
        result = ws.recv()
        return result

client = Client("")
value = 3500/1000
print(value)
while True:
    #print(client.get_depth())
    time.sleep(0.2)
