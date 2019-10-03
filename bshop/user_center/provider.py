import logging

from common.schema import LoginProvider
from common import exceptions

from provider import wechat
from provider import alipay


logger = logging.getLogger(__name__)


# TODO: alipay
def alipay_get_openid(auth_code):
    pass


PROVIDERS = {
    LoginProvider.WECHAT.value: {
        "field": "wechat_id",
        "get_openid": wechat.get_openid,
        "create_pay_order": wechat.create_order,
    },
    LoginProvider.ALIPAY.value: {
        "field": "alipay_id",
        "get_openid": alipay.get_openid,
        "get_openid": alipay.create_order,
    },
}


def get_provider_field(provider):
    if provider not in PROVIDERS:
        raise exceptions.DoNotSupportBindType

    return PROVIDERS[provider]["field"]


def get_openid(provider, auth_code):
    if provider not in PROVIDERS:
        raise exceptions.DoNotSupportBindType

    open_id = PROVIDERS[provider]["get_openid"](auth_code)
    return open_id
