import logging

from common.schema import LoginProvider
from common import exceptions

from provicer.wechat import WechatClient


logger = logging.getLogger(__name__)


# TODO: alipay
def alipay_get_open_id(auth_code):
    pass


PROVIDERS = {
    LoginProvider.WECHAT.value: {
        "field": "wechat_id",
        "get_open_id": WechatClient().get_open_id,
        "create_pay_order": WechatPayClient().,
    },
    LoginProvider.ALIPAY.value: {
        "field": "alipay_id",
        "get_open_id": alipay_get_open_id,
    },
}


def get_provider_field(provider):
    if provider not in PROVIDERS:
        raise exceptions.DoNotSupportBindType

    return PROVIDERS[provider]["field"]


def get_open_id(provider, auth_code):
    if provider not in PROVIDERS:
        raise exceptions.DoNotSupportBindType

    open_id = PROVIDERS[provider]["get_open_id"](auth_code)
    return open_id
