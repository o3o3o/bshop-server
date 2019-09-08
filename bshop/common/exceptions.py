from requests.exceptions import RequestException
from ccxt.base.errors import RequestTimeout, ExchangeError

RETRY_EXCEPTIONS = (RequestException, RequestTimeout, ExchangeError)


class ErrorResultException(Exception):
    default_message = ""

    def __init__(self, message=None, data=None):
        self.message = message or self.default_message
        self.data = data
        super(Exception, self).__init__(message)


class NotSupportError(ErrorResultException):
    pass


class NoDataFound(ErrorResultException):
    pass


class ApiError(ErrorResultException):
    pass


class VerifyCodeError(ErrorResultException):
    pass


class InvalidPhone(ErrorResultException):
    default_message = "invalid_phone"


class InvalidURL(ErrorResultException):
    pass


class GQLError(ErrorResultException):
    pass


class TooLongQuery(ErrorResultException):
    default_message = "too_long_query"


class NeedVerifyPhone(ErrorResultException):
    default_message = "need_verify_phone"


class WrongVerifyCode(ErrorResultException):
    default_message = "wrong_verification_code"
