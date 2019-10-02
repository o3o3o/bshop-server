import logging
import requests
from django.conf import settings
from django.core.cache import caches

from wechatpy import WeChatClient as _Client

logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            print("Use the same instance")
        return cls._instances[cls]


class WechatClient(_Client, metaclass=Singleton):
    def __init__(self):
        super().__init__(
            settings.WECHAT_APP_ID, settings.WECHAT_APP_SECRET, session=caches["wechat"]
        )

    def get_open_id(self, js_code):
        # https://wechatpy.readthedocs.io/zh_CN/master/client/wxa.html#wechatpy.client.api.WeChatWxa.code_to_session
        res = self.code_to_session(js_code)
        d = res.json()
        logger.debug(f"wechat open id: {d}")
        if d.get("errcode", 0) != 0:
            logger.exception(f"wechat code2openid error, {d}")
            if d.get("errcode") == 40163:
                # code been used
                raise exceptions.CodeBeUsed
        elif "openid" in d:
            return d["openid"]
        else:
            raise Exception(f"wechat failed to get openid: {d}")
