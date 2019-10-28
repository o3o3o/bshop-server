import json
import uuid
from unittest.mock import patch
from django.test import RequestFactory

# from unittest import skip

from graphql_jwt.testcases import JSONWebTokenTestCase
from django_fakeredis import FakeRedis

from wechat_django.pay.models import WeChatPay  # , UnifiedOrder
from wechat_django.models import WeChatApp

from common import exceptions
from common.utils import (
    ordered_dict_2_dict,
    urlencode,
    to_decimal,
    decimal2str,
    utc_now,
    d0,
)
from provider.wechat import WeChatProvider
from user_center.models import ShopUser
from user_center.factory import ShopUserFactory
from wallet.factory import FundFactory, HoldFundFactory

from wallet.models import Fund, HoldFund, FundAction
from wallet.action import do_deposit, do_transfer, do_withdraw


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
        self.hold_fund = HoldFundFactory(fund=self.fund)

        self.shop_user2 = ShopUserFactory(is_vendor=True)
        self.user2 = self.shop_user2.user
        self.fund2 = FundFactory(shop_user=self.shop_user2)
        self.hold_fund2 = HoldFundFactory(fund=self.fund2)

        self.miniprogram = WeChatApp.objects.get_by_name("miniprogram")
        self.request = RequestFactory()

    def tearDown(self):
        self.shop_user.delete()
        self.shop_user2.delete()
        self.fund.delete()

        self.user.delete()
        self.user2.delete()
        self.fund2.delete()

        ShopUser.objects.all().delete()
        Fund.objects.all().delete()
        HoldFund.objects.all().delete()
        FundAction.objects.all().delete()

    def test_pre_create_order(self):
        self.client.authenticate(self.user)

        gql = """
        mutation _($input: CreatePayOrderInput!){
          createPayOrder(input: $input){
            payment
          }
        }"""
        variables = {
            "input": {
                "provider": "WECHAT",
                "code": "1234",
                "amount": "12.31",
                "requestId": uuid.uuid4().hex,
            }
        }

        mocked_result = {
            "appId": "wx74389d88c9f437dc",
            "timeStamp": "1571289315",
            "nonceStr": "LiKeWq8TGVd3rQlmAY17EMhpagOw4obx",
            "signType": "MD5",
            "package": "prepay_id=wx17131459805524ca5ee4012e1090096300",
            "paySign": "05AFA977E030B5776C82CB8146C03CA9",
        }
        mocked_openid = "fake_open_id"
        with patch.object(WeChatProvider, "get_openid") as mock_get_openid:
            mock_get_openid.return_value = mocked_openid
            with patch.object(WeChatProvider, "create_order") as mock_create_order:
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

    def test_fund_api(self):
        self.client.authenticate(self.user)
        gql = """
        query {
          fund{
            total
            cash
            hold
            currency
          }
        }"""
        data = self.client.execute(gql)
        self.assertIsNone(data.errors)
        expected = {
            "total": decimal2str(self.fund.cash + self.hold_fund.amount),
            "cash": decimal2str(self.fund.cash),
            "hold": decimal2str(self.fund.hold),
            "currency": "CNY",
        }
        self.assertDictEqual(ordered_dict_2_dict(data.data["fund"]), expected)

        new_add_cash = to_decimal("1.2")
        transfer = do_deposit(
            self.shop_user, new_add_cash, order_id="1", note="test deposit"
        )
        old_cash = self.fund.cash

        self.fund.refresh_from_db()
        self.assertEquals(old_cash + new_add_cash, self.fund.cash)

        data = self.client.execute(gql)
        self.assertIsNone(data.errors)
        expected = {
            "total": decimal2str(self.fund.cash + self.hold_fund.amount),
            "cash": decimal2str(self.fund.cash),
            "hold": decimal2str(self.fund.hold),
            "currency": "CNY",
        }
        self.assertDictEqual(ordered_dict_2_dict(data.data["fund"]), expected)

        gql = """
        query _($before: String) {
          ledgerList(before: $before){
            edges{
              node{
                id
                type
                amount
                note
                status
                orderId
                createdAt
              }
            }
             pageInfo{
                startCursor
                endCursor
                hasNextPage
                hasPreviousPage
             }
          }
        }"""
        variables = {"before": None}
        data = self.client.execute(gql, variables)
        self.assertIsNone(data.errors)
        expected = {
            "id": str(transfer.uuid),
            "type": "DEPOSIT",
            "amount": decimal2str(new_add_cash),
            "note": "test deposit",
            "status": "SUCCESS",
            "orderId": "1",
            "createdAt": transfer.created_at.isoformat(),
        }
        self.assertDictEqual(
            ordered_dict_2_dict(data.data["ledgerList"]["edges"][0]["node"]), expected
        )
        page_info = data.data["ledgerList"]["pageInfo"]
        self.assertIsNotNone(page_info["startCursor"])
        self.assertIsNotNone(page_info["endCursor"])
        self.assertIsNotNone(page_info["hasNextPage"])
        self.assertIsNotNone(page_info["hasPreviousPage"])

    def test_unhold(self):
        hold_fund = HoldFundFactory(expired_at=utc_now())
        fund = hold_fund.fund

        old_amount = fund.amount_d

        HoldFund.objects.expired_unhold()

        fund.refresh_from_db()

        self.assertEquals(fund.total, old_amount["total"])
        self.assertEquals(fund.cash, old_amount["cash"] + old_amount["hold"])
        self.assertEquals(fund.hold, d0)

    def test_transfer(self):
        old_amount = self.fund.amount_d
        old_amount2 = self.fund2.amount_d
        delta = to_decimal("2.3")

        transfer = do_transfer(
            self.shop_user, self.shop_user2, delta, note="test transfer"
        )

        self.fund.refresh_from_db()
        self.fund2.refresh_from_db()

        self.assertEquals(self.fund.total, old_amount["total"] - delta)
        self.assertEquals(self.fund.hold, old_amount["hold"] - delta)
        self.assertEquals(self.fund.cash, old_amount["cash"])

        self.assertEquals(self.fund2.total, old_amount2["total"] + delta)
        self.assertEquals(self.fund2.cash, old_amount2["cash"] + delta)
        self.assertEquals(self.fund2.hold, old_amount2["hold"])

        self.assertEquals(transfer.note, "test transfer")

        # test insufficient cash
        old_amount = self.fund.amount_d
        old_amount2 = self.fund2.amount_d

        delta = self.fund.total + to_decimal("0.1")
        with self.assertRaises(exceptions.NotEnoughBalance):
            do_transfer(self.shop_user, self.shop_user2, delta, note="test transfer2")

        self.fund.refresh_from_db()
        self.fund2.refresh_from_db()

        self.assertEquals(self.fund.amount_d, old_amount)
        self.assertEquals(self.fund2.amount_d, old_amount2)

    @FakeRedis("common.utils.get_redis_connection")
    def test_transfer_api(self):
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

        self.shop_user.set_payment_password("654321")

        # test wrong paymentpassword
        variables["input"]["paymentPassword"] = "123456"
        variables["input"]["requestId"] = uuid.uuid4().hex
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)
        self.assertEquals("wrong_password", data.errors[0].message)

        # test true paymentpassword
        variables["input"]["paymentPassword"] = "654321"
        variables["input"]["requestId"] = uuid.uuid4().hex

        old_amount = self.fund.amount_d
        old_amount2 = self.fund2.amount_d

        data = self.client.execute(gql, variables)
        self.assertIsNone(data.errors)

        self.fund2.refresh_from_db()
        self.fund.refresh_from_db()

        self.assertEquals(self.fund.total, old_amount["total"] - to_decimal("0.1"))
        self.assertEquals(self.fund2.cash, old_amount2["cash"] + to_decimal("0.1"))

    def test_withdraw(self):

        user_old_cash = self.fund.cash

        d = to_decimal("1.12")
        transfer = do_withdraw(
            self.shop_user, d, order_id="test_order_id", note="test_withdraw"
        )
        self.assertEqual(transfer.amount, d)
        self.assertEqual(transfer.order_id, "test_order_id")
        self.assertEqual(transfer.note, "test_withdraw")

        self.fund.refresh_from_db()
        self.assertEqual(self.fund.cash, user_old_cash - d)

        # test insufficient cash
        delta = self.fund.cash + to_decimal("0.1")
        with self.assertRaises(exceptions.NotEnoughBalance):
            do_withdraw(
                self.shop_user, delta, order_id="test_order_id2", note="test_withdraw"
            )

        user_old_cash = self.fund.cash

        self.fund.refresh_from_db()

        self.assertEquals(self.fund.cash, user_old_cash)

    @FakeRedis("common.utils.get_redis_connection")
    def test_withdraw_api(self):
        self.client.authenticate(self.user)
        gql = """
        mutation _($input: WithdrawInput!){
          withdraw(input: $input){
            success
          }
        }"""
        test_request_uuid = uuid.uuid4().hex
        variables = {
            "input": {
                "amount": decimal2str(to_decimal("0.1") + self.fund.cash),
                "requestId": test_request_uuid,
                "provider": "WECHAT",
            }
        }
        # test balance not enough
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)
        self.assertEquals("not_enough_balance", data.errors[0].message)

        # test resbumitted
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)
        self.assertEquals("resubmitted", data.errors[0].message)

        variables["input"]["amount"] = "0.1"
        variables["input"]["requestId"] = uuid.uuid4().hex

        old_fund_cash = self.fund.cash

        # test fail and revert
        def withdraw_fail(*args, **kw):
            raise exceptions.WithdrawError("fail")

        with patch.object(WeChatProvider, "withdraw") as mock_withdraw:
            mock_withdraw.side_effect = withdraw_fail

            data = self.client.execute(gql, variables)
            self.assertIsNotNone(data.errors)
            self.assertEqual("fail", data.errors[0].message)
            self.fund.refresh_from_db()
            self.assertEqual(old_fund_cash, self.fund.cash)

        # test withdraw success
        variables["input"]["requestId"] = uuid.uuid4().hex
        mocked_result = {
            "mch_appid": "wx478898d89cf437dc",
            "mchid": "1231736602",
            "nonce_str": "pslL019BgHIzSDqfv8FUy6EC32OtZauK",
            "partner_trade_no": "1231736602201910260304298054",
            "payment_no": "10100101184011910260023619583860",
            "payment_time": "2019-10-26 11:04:32",
            "result_code": "SUCCESS",
            "return_code": "SUCCESS",
            "return_msg": None,
        }
        with patch.object(WeChatProvider, "withdraw") as mock_withdraw:
            mock_withdraw.return_value = mocked_result

            data = self.client.execute(gql, variables)
            self.assertIsNone(data.errors)

        self.fund.refresh_from_db()
        self.assertEqual(old_fund_cash - to_decimal("0.1"), self.fund.cash)

        self.assertTrue(data.data["withdraw"]["success"])

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
