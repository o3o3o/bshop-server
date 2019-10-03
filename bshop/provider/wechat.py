import logging

from wechat_django.models import WeChatApp

logger = logging.getLogger(__name__)


def get_wechat_app():
    return WeChatApp.objects.get_by_name("liuxiaoge")


def get_openid(auth_code):
    app = get_wechat_app()
    _, data = app.auth(auth_code)
    return data["openid"]


def create_order(
    body, total_fee, out_trade_no, wechat_user=None, openid=None, request=None
):
    if openid is None and wechat_user is None:
        raise ValueError("openid , wechat_user cannot be none at same time")

    app = get_wechat_app()
    order = app.pay.create_order(
        user=wechat_user,
        body=body,
        total_fee=1,
        out_trade_no=out_trade_no,
        openid=openid,
    )
    prepay = order.prepay(request)
    jsapi_params = order.jsapi_params(prepay["prepay_id"])
    return jsapi_params
