import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.dispatch import receiver
from django_redis import get_redis_connection

from wechat_django.pay import signals
from wechat_django.pay.models.orderresult import UnifiedOrderResult

from common.utils import to_decimal
from provider import wechat
from user_center.models import ShopUser
from user_center.provider import get_openid
from wallet.models import FundAction, do_deposit, do_transfer

logger = logging.getLogger(__name__)


def wechat_create_order(
    provider: str, code: str, amount: Decimal, to_user: ShopUser = None
):
    openid = get_openid(provider, code)

    ext_info = {"provider": provider}
    if to_user:
        body = f"柳小哥-{to_user.vendor_name}"
        ext_info["to_user_id"] = to_user.id
    else:
        body = "柳小哥-会员充值"

    res = wechat.create_order(
        openid=openid,
        amount=amount,
        body=body,
        out_trade_no=uuid.uuid4().hex,
        ext_info=ext_info,
    )

    logger.info("wechat_create_order: %s", res)
    # {'appId': 'wx478898d89cf437dc', 'timeStamp': '1571289315', 'nonceStr': 'LiKeWqT8GdV3QrlAmY17EMhpagOw4obx', 'signType': 'MD5', 'package': 'prepay_id=wx17131459805542ca5ee402e11090069300', 'paySign': '05AFA977E030B5776C82CB8146C03CA9'}
    return res


def alipay_create_order(code, amount):
    pass


def test_wechat_order(request):
    openid = "oxpoR5XoVo_CicymWNHLZoq7c8BI"
    body = "柳小哥-会员充值"
    amount = 0.01
    res = wechat.create_order(
        openid=openid,
        total_fee=amount,
        body=body,
        out_trade_no=uuid.uuid4().hex,
        request=request,
    )
    return res


@receiver(signals.order_updated)
def order_updated(result, order, state, attach, **kwargs):
    # TODO: how to unify wechat, alipay?
    if state != UnifiedOrderResult.State.SUCCESS:
        logger.info(f"{order} deposit signal, skip for no-success state")
        return

    if FundAction.objects.get(order_id=order.id).exist():
        logger.info(f"{order} deposit signal, skip for duplicate trigger")
        return

    con = get_redis_connection()
    lock_name = f"order:{order.id}_update_signal"

    provider = order.ext_info["provider"]
    user = ShopUser.objects.get_user_by_openid(provider, order.openid)

    amount = to_decimal(order.total_fee / 100)

    # Ensure cocurrent callback in 10 seconds
    with con.lock(lock_name, timeout=10):
        if order.ext_info and order.ext_info.get("to_user_id"):
            # transfer
            to_user_id = order.ext_info["to_user_id"]
            to_user = ShopUser.objects.get(id=to_user_id)
            note = "deposit&buy"

            with transaction.atomic():
                do_deposit(
                    user,
                    to_decimal(order.total_fee / 100),
                    order_id=order.id,
                    note=note,
                )
                do_transfer(user, to_user, amount, note=note)
        else:
            # deposit
            note = f"user:{user.id} deposit"
            # TODO: check order_id lock?
            do_deposit(user, amount, order_id=order.id, note=note)

    logger.info(f"{order} deposit success: {note}")
