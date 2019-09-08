import time
import random
import logging
import graphene
import graphql_jwt

from functools import wraps
from django.contrib.auth import get_user_model
from graphql_jwt.decorators import token_auth
from graphql_jwt.exceptions import JSONWebTokenError
from graphql_jwt.shortcuts import get_token, create_refresh_token

from common import exceptions
from common.phone import parse_phone
from common.ratelimit import ratelimit
from common.schema import Result
from user_center.schema.user import Me
from user_center.models import ShopUser
from user_center.auth import verified_phone, verify_code
from sms_service import send_verify_code

logger = logging.getLogger(__name__)

SMS_EXPIRATION = 5 * 60
MAX_RETRY_VERIFY = 5


def get_random_code():
    return "".join(["%s" % random.randint(0, 9) for num in range(0, 6)])


def require_verify_phone(fn):
    @wraps(fn)
    def wrapper(root, info, *args, **kwargs):
        request = info.context
        phone = kwargs.get("username", None)
        verified_phone(request, phone)
        return fn(root, info, *args, **kwargs)

    return wrapper


class RequestVerificationCode(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)

    Output = Result

    @ratelimit(key="ip", rate="10/m", block=True)
    @ratelimit(key="gql:phone", rate="5/m", block=True)
    def mutate(self, info, phone):
        request = info.context
        try:
            request_verify_code(request, phone)
        except exceptions.InvalidPhone as e:
            return Result(success=False, message=e.message)
        except exceptions.VerifyCodeError as e:
            return Result(success=False, message=e.message)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result(success=False, message="system_error")

        return Result(success=True)


class VerifyCode(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)
        code = graphene.String(required=True)

    Output = Result

    def mutate(self, info, phone, code):
        request = info.context

        verify_code(request, phone, code)

        try:
            verified_phone(request, phone, code)
        except exceptions.InvalidPhone as e:
            return Result(success=False, message=e.message)
        except exceptions.WrongVerifyCode as e:
            return Result(success=False, message=e.message)

        return Result(success=True)


class SignIn(graphql_jwt.JSONWebTokenMutation):
    class Arguments:
        phone = graphene.String(required=True)
        code = graphene.String(required=True)

    me = graphene.Field(Me)
    token = graphene.String()

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(me=info.context.user.shop_user)

    @classmethod
    @token_auth
    def mutate(cls, root, info, **kwargs):

        request = info.context
        phone = kwargs.get("phone")
        verify_code(request, phone, code)

        # copy phone to username for token_auth
        kwargs["username"] = phone
        return cls.resolve(root, info, **kwargs)


class SignUp(graphene.Mutation):
    # TODO: sign up with phone or wechat, alipay
    class Arguments:
        phone = graphene.String(required=True)
        # wechat, alipay
        bind_type = graphene.String(required=True)

    me = graphene.Field(Me)
    token = graphene.String()
    refresh_token = graphene.String()

    # @require_verify_phone
    def mutate(self, info, phone):
        try:
            phone = parse_phone(phone)
        except exceptions.InvalidPhone as e:
            raise exceptions.GQLError(e.message)

        try:
            ShopUser.objects.get(phone=phone)
            raise exceptions.GQLError("user_already_exists")
        except ShopUser.DoesNotExist:
            shop_user = ShopUser.objects.create_user(phone=phone)
            token = get_token(shop_user.user)
            refresh_token = create_refresh_token(shop_user.user)
            return SignUp(me=shop_user, token=token, refresh_token=refresh_token)
