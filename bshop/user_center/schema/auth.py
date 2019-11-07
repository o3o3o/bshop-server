import logging
import graphene

# import graphql_jwt
from graphql_jwt.decorators import login_required

from functools import wraps

# from graphql_jwt.decorators import token_auth
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
        phone = kwargs.get("username", kwargs.get("phone"))
        if phone is None:
            raise ValueError("Cannot get phone number")
        try:
            has_verified_phone(request, phone)
        except exceptions.InvalidPhone as e:
            return Result(success=False, message=e.message)
        except exceptions.WrongVerifyCode as e:
            return Result(success=False, message=e.message)
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

    @ratelimit(key="ip", rate="10/m", block=True)
    @ratelimit(key="gql:phone", rate="5/m", block=True)
    def mutate(self, info, phone, code):
        request = info.context

        try:
            verify_code(request, phone, code)
        except exceptions.InvalidPhone as e:
            return Result(success=False, message=e.message)
        except exceptions.WrongVerifyCode as e:
            return Result(success=False, message=e.message)

        return Result(success=True)


class SignIn(graphene.Mutation):
    class Arguments:
        phone = graphene.String(description="phone number with counrtry code")
        auth_code = graphene.String()
        provider = graphene.Argument(LoginProvider)

    me = graphene.Field(Me)
    token = graphene.String()

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(me=info.context.user.shop_user)

    @classmethod
    def mutate(cls, root, info, **kwargs):

        request = info.context

        phone = kwargs.get("phone")
        auth_code = kwargs.get("auth_code")
        provider = kwargs.get("provider")

        if phone:
            try:
                has_verified_phone(request, phone)
            except exceptions.InvalidPhone as e:
                return Result(success=False, message=e.message)
            except exceptions.WrongVerifyCode as e:
                return Result(success=False, message=e.message)

            try:
                shop_user = ShopUser.objects.get(phone=phone)
            except ShopUser.DoesNotExist:
                return Result(success=False, message="not_exist_user_with_phone")

        elif auth_code and provider:
            try:
                shop_user = ShopUser.objects.get_user_by_auth_code(provider, auth_code)
            except ShopUser.DoesNotExist:
                return Result(success=False, message="not_exist_user_with_auth_code")

        request.user = shop_user.user
        token = get_token(shop_user.user)

        return cls(me=shop_user, token=token)


class SignUp(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)
        provider = graphene.Argument(LoginProvider)
        auth_code = graphene.String(description="signUp and bind account")

    me = graphene.Field(Me)
    token = graphene.String()
    refresh_token = graphene.String()

    @require_verified_phone
    def mutate(self, info, phone, provider=None, auth_code=None, **kw):
        try:
            phone = parse_phone(phone)
        except exceptions.InvalidPhone as e:
            raise exceptions.GQLError(e.message)

        try:
            shop_user = ShopUser.objects.get(phone=phone)
        except ShopUser.DoesNotExist:
            shop_user = ShopUser.objects.create_user(phone=phone)

        if provider and auth_code:
            try:
                shop_user.bind_third_account(provider, auth_code)
            except (
                exceptions.AlreadyBinded,
                exceptions.DoNotSupportBindType,
                exceptions.CodeBeUsed,
            ) as e:
                raise exceptions.GQLError(e.message)

        token = get_token(shop_user.user)
        refresh_token = create_refresh_token(shop_user.user)
        return SignUp(me=shop_user, token=token, refresh_token=refresh_token)


class BindThirdAccount(graphene.Mutation):
    class Arguments:
        # TODO: sign up with phone or wechat, alipay
        provider = graphene.Argument(LoginProvider)
        auth_code = graphene.String(required=True)

    Output = Result

    @login_required
    def mutate(self, info, provider, auth_code, **kw):
        shop_user = info.context.user.shop_user
        try:
            shop_user.bind_third_account(provider, auth_code)
        except (
            exceptions.AlreadyBinded,
            exceptions.DoNotSupportBindType,
            exceptions.CodeBeUsed,
        ) as e:
            raise exceptions.GQLError(e.message)

        return Result(success=True)


class SetPaymentPassword(graphene.Mutation):
    class Arguments:
        password = graphene.String(required=True)

    Output = Result

    @login_required
    def mutate(self, info, password, **kw):
        shop_user = info.context.user.shop_user
        if shop_user.has_payment_password:
            raise exceptions.GQLError("already_exist_payment_password")

        shop_user.set_payment_password(password)

        return Result(success=True)


class ChangePaymentPassword(graphene.Mutation):
    class Arguments:
        old_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    Output = Result

    @login_required
    def mutate(self, info, old_password, new_password, **kw):
        shop_user = info.context.user.shop_user
        if shop_user.has_payment_password:
            if not shop_user.check_payemnt_password(old_password):
                raise exceptions.GQLError("wrong_old_password")

        shop_user.set_payment_password(new_password)
        return Result(success=True)
