import logging
import graphene
import graphql_jwt

from functools import wraps
from graphql_jwt.decorators import token_auth
from graphql_jwt.shortcuts import get_token, create_refresh_token

from common import exceptions
from common.phone import parse_phone
from common.ratelimit import ratelimit
from common.schema import Result, LoginProvider
from user_center.schema.user import Me
from user_center.models import ShopUser
from user_center.auth import has_verified_phone, verify_code, request_verify_code

logger = logging.getLogger(__name__)


def require_verified_phone(fn):
    @wraps(fn)
    def wrapper(root, info, *args, **kwargs):
        request = info.context
        phone = kwargs.get("phone", None)
        has_verified_phone(request, phone)
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
            has_verified_phone(request, phone, code)
        except exceptions.InvalidPhone as e:
            return Result(success=False, message=e.message)
        except exceptions.WrongVerifyCode as e:
            return Result(success=False, message=e.message)

        return Result(success=True)


class SignIn(graphql_jwt.JSONWebTokenMutation):
    class Arguments:
        phone = graphene.String(required=False)
        openid = graphene.String(required=False)

    me = graphene.Field(Me)
    token = graphene.String()

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(me=info.context.user.shop_user)

    @classmethod
    @require_verified_phone
    @token_auth
    def mutate(cls, root, info, **kwargs):

        # request = info.context
        phone = kwargs.get("phone")
        # openid = kwargs.get("openid")

        # TODO: login with openid
        # copy phone to username for token_auth
        kwargs["username"] = phone
        return cls.resolve(root, info, **kwargs)


class BindOpenId(graphene.Mutation):
    class Arguments:
        # TODO: sign up with phone or wechat, alipay
        bind_type = graphene.Field(LoginProvider, required=True)
        openid = graphene.String(required=True)

    Output = Result

    @require_verified_phone
    def mutate(self, info, bind_type, openid, **kw):
        shop_user = info.request.user.shop_user
        try:
            shop_user.bind_openid(bind_type, openid)
        except (exceptions.AlreadyBinded, exceptions.DoNotSupportBindType) as e:
            raise exceptions.GQLError(e.message)

        # TODO: recheck openid with thirdparty server

        return Result(success=True)


class SignUp(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)

    me = graphene.Field(Me)
    token = graphene.String()
    refresh_token = graphene.String()

    @require_verified_phone
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
