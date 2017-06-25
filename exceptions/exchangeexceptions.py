# Failed to submit order.
class SubmitOrderFailureException(Exception):
    def __init__(self, message):
        super(SubmitOrderFailureException, self).__init__(message)


# Exception when failed to update order book for the exchange.s
class UpdateOrderBookFailureException(Exception):
    def __init__(self, message):
        super(UpdateOrderBookFailureException, self).__init__(message)


# Exception when failed to retrieve balance from exchange accounts.
class RetrieveBalanceFailureException(Exception):
    def __init__(self, message):
        super(RetrieveBalanceFailureException, self).__init__(message)
