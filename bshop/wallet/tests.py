from graphql_jwt.testcases import JSONWebTokenTestCase

from common.utils import ordered_dict_2_dict, urlencode
from user_center.factory import ShopUserFactory


class WalletTests(JSONWebTokenTestCase):
    def setUp(self):
        self.shop_user = ShopUserFactory()
        self.user = self.shop_user.user

        self.shop_user2 = ShopUserFactory(is_vendor=True)
        self.user2 = self.shop_user2.user

    def tearDown(self):
        self.shop_user.delete()
        self.shop_user2.delete()

        self.user.delete()
        self.user2.delete()

    def test_pre_create_order(self):
        self.client.authenticate(self.user)
        pass

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
