import json
from uuid import uuid4
from django_fakeredis import FakeRedis

from django.test import TestCase, RequestFactory
from wechat_django.models import WeChatApp
from wechat_django.pay.models import WeChatPay, UnifiedOrder

from common.utils import to_decimal, json_dumps
from wallet.factory import FundFactory
from wallet.models import Fund, HoldFund, FundAction, FundTransfer
from user_center.models import ShopUser
from user_center.factory import ShopUserFactory


class ProviderTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        app = WeChatApp.objects.create(
            title="pay", name="pay", appid="appid", appsecret="secret"
        )
        WeChatPay.objects.create(
            app=app,
            mch_id="mch_id",
            api_key="api_key",
            mch_cert=b"mch_cert",
            mch_key=b"mch_key",
        )

    def setUp(self):
        self.shop_user = ShopUserFactory(wechat_id="openid")
        self.app = WeChatApp.objects.get_by_name("pay")
        self.fund = FundFactory(shop_user=self.shop_user)

        self.shop_user2 = ShopUserFactory(wechat_id="openid2")
        self.fund2 = FundFactory(shop_user=self.shop_user2)

        self.wechat_user = self.app.users.create(openid="openid")
        self.request = self.rf().get("/")

    def tearDown(self):
        ShopUser.objects.all().delete()
        WeChatApp.objects.all().delete()
        Fund.objects.all().delete()
        FundAction.objects.all().delete()
        FundTransfer.objects.all().delete()
        UnifiedOrder.objects.all().delete()

    @FakeRedis("provider.wechat.get_redis_connection")
    def test_order_update_transfer(self):
        # test deposit & transfer
        minimal = self.minimal_example
        minimal["ext_info"]["to_user_id"] = self.shop_user2.id
        order = self.app.pay.create_order(self.wechat_user, self.request, **minimal)
        result = self.success(self.app.pay, order)
        order.update(result)

        new_fund = Fund.objects.get(id=self.fund.id)
        new_fund2 = Fund.objects.get(id=self.fund2.id)

        self.assertEqual(self.fund.cash, new_fund.cash)
        self.assertEqual(self.fund2.cash + to_decimal("1.01"), new_fund2.cash)

        transfer = FundTransfer.objects.get(
            to_fund=self.fund, order_id=order.id, type="DEPOSIT"
        )
        self.assertEqual(transfer.note, f"deposit&buy")
        self.assertEqual(transfer.amount, to_decimal("1.01"))

        transfer = FundTransfer.objects.get(
            from_fund=self.fund, to_fund=self.fund2, order_id=order.id, type="TRANSFER"
        )
        self.assertEqual(transfer.note, f"deposit&buy")
        self.assertEqual(transfer.amount, to_decimal("1.01"))

    # TODO: test do cash back

    @FakeRedis("provider.wechat.get_redis_connection")
    def test_order_update_deposit(self):
        minimal = self.minimal_example

        order = self.app.pay.create_order(self.wechat_user, self.request, **minimal)
        result = self.success(self.app.pay, order)

        order.update(result)

        # test deposit
        new_fund = Fund.objects.get(id=self.fund.id)
        self.assertEqual(self.fund.cash + to_decimal("1.01"), new_fund.cash)
        transfer = FundTransfer.objects.get(to_fund=self.fund, order_id=order.id)
        self.assertEqual(transfer.type, "DEPOSIT")
        self.assertEqual(transfer.note, f"user:{self.shop_user.id} deposit")
        fund_action = FundAction.objects.get(fund=self.fund, transfer=transfer)
        self.assertDictEqual(
            fund_action.balance, json.loads(json_dumps(new_fund.amount_d))
        )

    def rf(self, **defaults):
        return RequestFactory(**defaults)

    @property
    def minimal_example(self):
        return {
            "body": "body",
            "out_trade_no": str(uuid4().hex),
            "total_fee": 101,
            "ext_info": {"provider": "WECHAT"},
            "openid": "openid",
        }

    def success(self, pay, order):
        """
        :type pay: wechat_django.pay.models.WeChatPay
                    :type order: wechat_django.pay.models.UnifiedOrder
        """
        return {
            "openid": "openid",
            "sub_mch_id": None,
            "cash_fee_type": "CNY",
            "settlement_total_fee": "101",
            "nonce_str": str(uuid4().hex),
            "return_code": "SUCCESS",
            "err_code_des": "SUCCESS",
            "time_end": "20190613190854",
            "mch_id": str(pay.mch_id),
            "trade_type": "JSAPI",
            "trade_state_desc": "ok",
            "trade_state": "SUCCESS",
            "sign": str(uuid4()),
            "cash_fee": "101",
            "is_subscribe": "Y",
            "return_msg": "OK",
            "fee_type": "CNY",
            "bank_type": "CMC",
            "attach": "sandbox_attach",
            "device_info": "sandbox",
            "out_trade_no": order.out_trade_no,
            "transaction_id": order.out_trade_no,
            "total_fee": "101",
            "appid": str(pay.appid),
            "result_code": "SUCCESS",
            "err_code": "SUCCESS",
        }
