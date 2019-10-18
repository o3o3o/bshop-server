import logging
from decimal import Decimal
from common.utils import yuan2fen

from wechat_django.models import WeChatApp, WeChatUser

logger = logging.getLogger(__name__)


def get_wechat_app():
    return WeChatApp.objects.get_by_name("liuxiaoge")


def get_openid(auth_code):
    app = get_wechat_app()
    _, data = app.auth(auth_code)
    return data["openid"]


def create_order(
    body: str,
    amount: Decimal,
    out_trade_no: str,
    wechat_user: WeChatUser = None,
    openid: str = None,
    request=None,
    ext_info=None,
):
    if openid is None and wechat_user is None:
        raise ValueError("openid , wechat_user cannot be none at same time")

    app = get_wechat_app()
    order = app.pay.create_order(
        user=wechat_user,
        body=body,
        total_fee=yuan2fen(amount),  # Yuan to Fen
        out_trade_no=out_trade_no,
        openid=openid,
        ext_info=ext_info,
    )
    prepay = order.prepay(request)
    jsapi_params = order.jsapi_params(prepay["prepay_id"])
    return jsapi_params
