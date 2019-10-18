import json
import uuid
from unittest.mock import patch
from django.test import RequestFactory

# from unittest import skip

from graphql_jwt.testcases import JSONWebTokenTestCase
from django_fakeredis import FakeRedis

from wechat_django.pay.models import UnifiedOrder, WeChatPay
from wechat_django.models import WeChatApp

from common.utils import ordered_dict_2_dict, urlencode, to_decimal
from user_center.factory import ShopUserFactory
from wallet.factory import FundFactory
from wallet.models import FundAction


class WalletTests(JSONWebTokenTestCase):
    @classmethod
    def setUpTestData(cls):
        miniprogram = WeChatApp.objects.create(
            title="miniprogram",
            name="miniprogram",
            appid="miniprogram",
            appsecret="secret",
            type=WeChatApp.Type.MINIPROGRAM,
        )
        WeChatPay.objects.create(
            app=miniprogram,
            mch_id="mch_id",
            api_key="api_key",
            mch_cert=b"mch_cert",
            mch_key=b"mch_key",
        )

    def setUp(self):
        self.shop_user = ShopUserFactory()
        self.user = self.shop_user.user
        self.fund = FundFactory(shop_user=self.shop_user)

        self.shop_user2 = ShopUserFactory(is_vendor=True)
        self.user2 = self.shop_user2.user
        self.fund2 = FundFactory(shop_user=self.shop_user2)

        self.miniprogram = WeChatApp.objects.get_by_name("miniprogram")
        self.request = RequestFactory()

    def tearDown(self):
        self.shop_user.delete()
        self.shop_user2.delete()
        self.fund.delete()

        self.user.delete()
        self.user2.delete()
        self.fund2.delete()

        FundAction.objects.all().delete()

    def test_pre_create_order(self):
        self.client.authenticate(self.user)

        gql = """
        mutation _($input: CreatePayOrderInput!){
          createPayOrder(input: $input){
            payment
          }
        }"""
        variables = {"input": {"provider": "WECHAT", "code": "1234", "amount": "12.31"}}

        mocked_result = {
            "appId": "wx74389d88c9f437dc",
            "timeStamp": "1571289315",
            "nonceStr": "LiKeWq8TGVd3rQlmAY17EMhpagOw4obx",
            "signType": "MD5",
            "package": "prepay_id=wx17131459805524ca5ee4012e1090096300",
            "paySign": "05AFA977E030B5776C82CB8146C03CA9",
        }
        mocked_openid = "fake_open_id"
        with patch("wallet.order.get_openid") as mock_get_openid:
            mock_get_openid.return_value = mocked_openid
            with patch("provider.wechat.create_order") as mock_create_order:
                mock_create_order.return_value = mocked_result
                data = self.client.execute(gql, variables)

        self.assertIsNone(data.errors)
        expected = json.dumps(mocked_result)
        self.assertEqual(data.data["createPayOrder"]["payment"], expected)
        # TODO: mock order
        # order = UnifiedOrder.objects.get(openid=mocked_openid)
        # self.assertEquals(order.total_fee, 1231)
        # self.assertNotIn("to_user_id", order.ext_info)

        # TODO: test transfer

        # test order is success...

    def test_get_qr_code_info(self):
        self.client.authenticate(self.user)

        gql = """
        query {
          vendorReceivePayQr {
            vendorId
            vendorName
            schema
            type
            qr
          }
        }"""

        data = self.client.execute(gql)
        self.assertIsNotNone(data.errors)
        self.assertEquals("not_vendor", data.errors[0].message)

        data = self.client.execute(gql)

        self.client.logout()

        self.client.authenticate(self.user2)
        data = self.client.execute(gql)
        self.assertIsNone(data.errors)
        expected = {
            "vendorId": str(self.shop_user2.uuid),
            "vendorName": self.shop_user2.vendor_name,
            "schema": "bshop",
            "type": "pay",
            "qr": "bshop://pay/?"
            + urlencode(
                {
                    "vendorId": str(self.shop_user2.uuid),
                    "vendorName": self.shop_user2.vendor_name,
                }
            ),
        }
        self.assertDictEqual(
            ordered_dict_2_dict(data.data["vendorReceivePayQr"]), expected
        )

    @FakeRedis("common.utils.get_redis_connection")
    def test_transfer(self):
        self.client.authenticate(self.user)
        gql = """
        mutation _($input: TransferInput!){
          transfer(input: $input){
            success
          }
        }"""
        test_request_uuid = uuid.uuid4().hex
        variables = {
            "input": {
                "to": str(self.shop_user2.uuid),
                "amount": "0.1",
                "note": "test transfer",
                "requestId": test_request_uuid,
                "paymentPassword": "123456",
            }
        }
        # test with not set payment password
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)
        self.assertEquals("need_set_payment_password", data.errors[0].message)

        # test resbumitted
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)
        self.assertEquals("resubmitted", data.errors[0].message)

        # test true paymentpassword
        self.shop_user.set_payment_password("654321")
        variables["input"]["paymentPassword"] = "654321"
        variables["input"]["requestId"] = uuid.uuid4().hex

        data = self.client.execute(gql, variables)
        self.assertIsNone(data.errors)

        old_cash = self.fund.cash
        old_cash2 = self.fund2.cash

        self.fund2.refresh_from_db()
        self.fund.refresh_from_db()

        self.assertEquals(self.fund.cash, old_cash - to_decimal("0.1"))
        self.assertEquals(self.fund2.cash, old_cash2 + to_decimal("0.1"))
