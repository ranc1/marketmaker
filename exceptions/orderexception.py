class SubmitOrderFailureException(Exception):
    def __init__(self, message):
        super(SubmitOrderFailureException, self).__init__(message)
