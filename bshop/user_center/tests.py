from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from graphql_jwt.testcases import JSONWebTokenClient

# from user_center.models import ShopUser
from user_center.factory import ShopUserFactory


class MYJSONWebTokenClient(JSONWebTokenClient):
    def execute(self, query, variables=None, **extra):
        extra.update(self._credentials)
        context = self.post("/", **extra)

        if hasattr(self, "session_key"):
            context.COOKIES = {settings.SESSION_COOKIE_NAME: self.session_key}

        middleware = SessionMiddleware()
        middleware.process_request(context)
        context.session.save()
        self.session_key = context.session.session_key

        res = super(JSONWebTokenClient, self).execute(
            query, context=context, variables=variables
        )

        context.session.save()

        return res


class UserTests(TestCase):
    def setUp(self):
        self.shop_user = ShopUserFactory()
        self.shop_user2 = ShopUserFactory()

        self.user = self.shop_user.user
        self.user2 = self.shop_user2.user

        self.client = MYJSONWebTokenClient()

    def tearDown(self):
        self.shop_user.delete()
        self.shop_user2.delete()

        self.user.delete()
        self.user2.delete()

    @patch("user_center.auth.get_random_code")
    @override_settings(
        SMS_BACKEND="smsish.sms.backends.dummy.SMSBackend", RATELIMIT_ENABLE=False
    )
    def test_sign_up(self, mock_random_code):
        mock_random_code.return_value = "123456"
        phone = "+8613912345678"

        gql_signup = """
        mutation signin($username: String!) {
          signUp(username: $username) {
              token
              me{
                  id
                  username
                  phone
             }
          }
        }
        """
        variables_signup = {"username": phone}
        data = self.client.execute(gql_signup, variables_signup)
        self.assertIsNotNone(data.errors)
        # TODO: assert error msg

        gql_request_verify_code = """
        mutation rvc($phone: String!) {
          requestVerificationCode(phone: $phone) {
                success
                message
               }
        }
        """
        data = self.client.execute(gql_request_verify_code, {"phone": "+8612345678"})
        self.assertEquals(data.data["requestVerificationCode"]["success"], False)
        self.assertEquals(
            data.data["requestVerificationCode"]["message"], "invalid_phone"
        )

        self.verify_phone(phone)

        data = self.client.execute(gql_signup, variables_signup)
        self.assertIsNone(data.errors)
        self.assertEquals(data.data["signUp"]["me"]["username"], phone)
        self.assertIsNotNone(data.data["signUp"]["token"])
        self.assertEquals(data.data["signUp"]["me"]["phone"], phone)

        gql_bind_account = """
        mutation bc($provider: LoginProvider!, authCode: String!) {
          bindThirdAccount(provider: $provider, authCode: $authCode) {
                success
                message
               }
        }

        """
        variables_bind_account = {"provider": "WECHAT", "authCode": "test_auth_code"}
        with patch("user_center.provider.wechat_get_open_id") as mock_get_open_id:
            mock_get_open_id.return_value = "test_open_id"
            data = self.client.execute(gql_bind_account, variables_bind_account)
            self.assertIsNone(data.errors)
            self.assertEquals(data.data["bindThirdAccount"]["success"], True)

            mock_get_open_id.assert_called()

            user = get_user_model().objects.get(username=phone)
            self.assertEquals(user.shop_user.wechat_id, "test_open_id")

            user.delete()

    def verify_phone(self, phone):
        gql_request_verify_code = """
        mutation rvc($phone: String!) {
          requestVerificationCode(phone: $phone) {
                success
                message
               }
        }
        """
        data = self.client.execute(gql_request_verify_code, {"phone": phone})
        self.assertIsNone(data.errors)
        self.assertEquals(data.data["requestVerificationCode"]["success"], True)

        gql_verify_code = """
        mutation gvc($phone: String!, $code: String!) {
          verifyCode(phone: $phone, code: $code) {
                success
                message
               }
        }
        """

        variables = {"phone": phone, "code": "123456"}
        data = self.client.execute(gql_verify_code, variables)
        self.assertEquals(data.data["verifyCode"]["success"], False)
        self.assertEquals(data.data["verifyCode"]["message"], "wrong_verification_code")

        variables = {"phone": phone, "code": "123456"}
        data = self.client.execute(gql_verify_code, variables)
        self.assertIsNone(data.errors)
        self.assertEquals(data.data["verifyCode"]["success"], True)

    @patch("user_center.auth.get_random_code")
    @override_settings(
        SMS_BACKEND="smsish.sms.backends.dummy.SMSBackend", RATELIMIT_ENABLE=False
    )
    def test_sign_in(self, mock_random_code):
        phone = self.shop_user.phone
        mock_random_code.return_value = "123456"

        gql = """
mutation sigin($username: String!, $openid: String!, $provider: LoginProvider!) {
          signIn(username: $username, password: $password) {
              token
              refreshToken
          }
        }
        """

        # test sigin with phone, no sms code verified
        variables = {"username": phone}
        data = self.client.execute(gql, variables)
        self.assertIsNotNone(data.errors)

        self.verify_phone(phone)

        variables = {"username": phone}
        data = self.client.execute(gql, variables)
        self.assertIsNone(data.errors)
        self.assertIsNotNone(data.data["signIn"]["token"])

    def test_get_me(self):
        self.client.authenticate(self.user)
        gql = """
        query {
          me {
            id
            username
          }
        }"""

        data = self.client.execute(gql)
        self.assertEquals(data.errors, None)
        self.assertEquals(data.data["me"]["username"], "+8618612345678")
