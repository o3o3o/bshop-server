import uuid
import logging
from decimal import Decimal

from django.db import transaction
from django.dispatch import receiver
from django_redis import get_redis_connection

from wechat_django.pay import signals
from wechat_django.pay.models.orderresult import UnifiedOrderResult, UnifiedOrder
from wechat_django.models import WeChatApp, WeChatUser

from common.utils import yuan2fen, to_decimal, fen2yuan
from common.schema import LoginProvider
from provider import BaseProvider
from user_center.models import ShopUser
from wallet.tasks import sync_wechat_order
from wallet.models import FundAction, do_deposit, do_transfer


logger = logging.getLogger(__name__)


class WeChatProvider(BaseProvider):
    field = "wechat_id"
    name = LoginProvider.WECHAT.value

    def __init__(self):
        self.app = None

    def get_wechat_app(self):
        if self.app:
            return self.app

        self.app = WeChatApp.objects.get_by_name("liuxiaoge")
        return self.app

    def get_openid(self, auth_code: str = None, shop_user: ShopUser = None):
        app = self.get_wechat_app()
        if auth_code:
            _, data = app.auth(auth_code)
            return data["openid"]
        elif shop_user:
            return shop_user.wechat_id

    def create_order(
        self,
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

        app = self.get_wechat_app()
        order = app.pay.create_order(
            user=wechat_user,
            body=body,
            total_fee=yuan2fen(amount),
            out_trade_no=out_trade_no,
            openid=openid,
            ext_info=ext_info,
        )
        sync_wechat_order.apply_async(args=[order.id], countdown=3, expires=7200)

        prepay = order.prepay(request)
        jsapi_params = order.jsapi_params(prepay["prepay_id"])
        jsapi_params["order_id"] = out_trade_no
        return jsapi_params

    def create_pay_order(self, code: str, amount: Decimal, to_user: ShopUser = None):
        openid = self.get_openid(code)

        ext_info = {"provider": self.name}
        if to_user:
            body = f"柳小哥-{to_user.vendor_name}"
            ext_info["to_user_id"] = to_user.id
        else:
            body = "柳小哥-会员充值"

        res = self.create_order(
            openid=openid,
            amount=amount,
            body=body,
            out_trade_no=uuid.uuid4().hex,
            ext_info=ext_info,
        )

        logger.info("wechat_create_order: %s", res)
        # {'appId': 'wx478898d89cf437dc', 'timeStamp': '1571289315', 'nonceStr': 'LiKeWqT8GdV3QrlAmY17EMhpagOw4obx', 'signType': 'MD5', 'package': 'prepay_id=wx17131459805542ca5ee402e11090069300', 'paySign': '05AFA977E030B5776C82CB8146C03CA9'}
        # TODO: sync order state async
        return res

    def order_info(self, order_id, openid):
        app = self.get_wechat_app()
        try:
            # TODO: get by open_id
            order = UnifiedOrder.objects.get(
                pay=app.pay, out_trade_no=order_id, openid=openid
            )
        except UnifiedOrder.DoesNotExist:
            return None

        return {
            "id": order_id,
            "state": order.trade_state(),
            "amount": fen2yuan(order.total_fee) if order.total_fee else None,
        }


@receiver(signals.order_updated)
def order_updated(result, order, state, attach, **kwargs):
    # TODO: how to unify wechat, alipay?
    if state != UnifiedOrderResult.State.SUCCESS:
        logger.info(f"{order} deposit signal, skip for no-success state")
        return

    if FundAction.objects.filter(order_id=order.id).exists():
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
