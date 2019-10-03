import uuid
from user_center.provider import get_open_id
from provider import wechat


def wechat_create_order(provider, code, amount):
    openid = get_openid(provider, code)
    res = wechat.create_order(
        openid=openid, total_fee=amount, body="刘小哥-会员充值", out_trade_no=uuid.uuid4().hex
    )
    return res["prepay_id"]


def alipay_create_order(code, amount):
    pass
