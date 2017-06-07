from grapheneexchange import GrapheneExchange


class Client(object):
    def __init__(self, witness_url, account, secret_key, watch_markets=None):
        if watch_markets is None:
            watch_markets = ["CNY_BTS", "BTS_CNY"]

        class Config:
            pass
        _bts_config = Config()
        _bts_config.witness_url = witness_url
        _bts_config.witness_user = ""
        _bts_config.witness_password = ""
        _bts_config.watch_markets = watch_markets
        _bts_config.market_separator = "_"
        _bts_config.account = account
        _bts_config.wif = secret_key
        self.exchange = GrapheneExchange(_bts_config, safe_mode=False)
