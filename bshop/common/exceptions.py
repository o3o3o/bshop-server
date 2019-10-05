from requests.exceptions import RequestException

RETRY_EXCEPTIONS = (RequestException,)


class ErrorResultException(Exception):
    default_message = ""

    def __init__(self, message=None, data=None):
        self.message = message or self.default_message
        self.data = data
        super().__init__(message)


class NotSupportError(ErrorResultException):
    pass


class NoDataFound(ErrorResultException):
    pass


class ApiError(ErrorResultException):
    pass


class VerifyCodeError(ErrorResultException):
    pass


class InvalidURL(ErrorResultException):
    pass


class GQLError(ErrorResultException):
    pass


class InvalidPhone(ErrorResultException):
    default_message = "invalid_phone"


class TooLongQuery(ErrorResultException):
    default_message = "too_long_query"


class NeedVerifyPhone(ErrorResultException):
    default_message = "need_verify_phone"


class WrongVerifyCode(ErrorResultException):
    default_message = "wrong_verification_code"


class AlreadyBinded(GQLError):
    default_message = "alread_binded_need_unbind_bind"


class DoNotSupportBindType(GQLError):
    default_message = "do_not_support_bind_type"


class CodeBeUsed(GQLError):
    default_message = "code_been_used"


class WrongPassword(ErrorResultException):
    default_message = "wrong_password"


class NeedSetPaymentPassword(ErrorResultException):
    default_message = "need_set_payment_password"
