import requests
from django.conf import settings

# from redis import Redis
# from wechatpy import WeChatClient
# from wechatpy.session.redisstorage import RedisStorage

from common.schema import LoginProvider

# redis_client = Redis.from_url("redis://%s:6379/0" % settings.REDIS_HOST)
#
# session_interface = RedisStorage(redis_client, prefix="wechatpy")
#
# wechat_client = WeChatClient(
#    settings.WECHAT_APP_ID, settings.WECHAT_APP_SECRET, session=session_interface
# )


def wechat_get_open_id(auth_code):
    # TODO: https://wechatpy.readthedocs.io/zh_CN/master/client/wxa.html#wechatpy.client.api.WeChatWxa.code_to_session
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": auth_code,
        "grant_type": "authorization_code",
    }
    res = requests.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params=req_params,
        timeout=3,
        verify=False,
    )
    d = res.json()
    if d["errcode"] != 0:
        logger.error(f"wechat code2openid error, {d}")

    return res["openid"]


def alipay_get_open_id(auth_code):
    pass


PROVIDERS = {
    LoginProvider.WECHAT.value: {
        "field": "wechat_id",
        "get_open_id": wechat_get_open_id,
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