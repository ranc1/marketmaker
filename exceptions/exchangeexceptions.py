class SubmitOrderFailureException(Exception):
    def __init__(self, message):
        super(SubmitOrderFailureException, self).__init__(message)


class UpdateOrderBookFailureException(Exception):
    def __init__(self, message):
        super(UpdateOrderBookFailureException, self).__init__(message)
