import uuid
from unittest.mock import patch
from unittest import skip

from graphql_jwt.testcases import JSONWebTokenTestCase
from django_fakeredis import FakeRedis

from common.utils import ordered_dict_2_dict, urlencode, to_decimal
from user_center.factory import ShopUserFactory
from wallet.factory import FundFactory
from wallet.models import FundAction


class WalletTests(JSONWebTokenTestCase):
    def setUp(self):
        self.shop_user = ShopUserFactory()
        self.user = self.shop_user.user
        self.fund = FundFactory(shop_user=self.shop_user)

        self.shop_user2 = ShopUserFactory(is_vendor=True)
        self.user2 = self.shop_user2.user
        self.fund2 = FundFactory(shop_user=self.shop_user2)

    def tearDown(self):
        self.shop_user.delete()
        self.shop_user2.delete()
        self.fund.delete()

        self.user.delete()
        self.user2.delete()
        self.fund2.delete()

        FundAction.objects.all().delete()

    @skip("pending")
    def test_pre_create_order(self):
        self.client.authenticate(self.user)

        gql = """
        mutation _($input: CreateDepositOrderInput!){
          createDepositOrder(input: $input){
            payment
          }
        }"""
        variables = {"input": {"provider": "WECHAT", "code": "1234", "amount": "123.1"}}

        with patch("wallet.order.get_openid") as mock_get_openid:
            mock_get_openid.return_value = "fake_open_id"
            with patch("provider.wechat.create_order") as mock_create_order:
                mock_create_order.return_value = {}
                data = self.client.execute(gql, variables)

        self.assertIsNotNone(data.errors)
        self.assertDictEqual(data.data["createDepositOrder"]["payment"])

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
