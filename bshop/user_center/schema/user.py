import logging

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

# from django.conf import settings
from common.schema import Result
from user_center.models import ShopUser

logger = logging.getLogger(__name__)


class BaseUserQL(object):
    id = graphene.String(required=True)
    avatar = graphene.String()
    nickname = graphene.String()
    last_name = graphene.String()
    first_name = graphene.String()
    has_payment_password = graphene.Boolean(default_value=False)
    is_vendor = graphene.Boolean(default_value=False)

    def __init_subclass__(cls, *arg, **kw):
        super().__init_subclass__(*arg, **kw)

        def gen_resolve(key):
            return lambda self, info: getattr(self, key)

        for k in ("last_name", "first_name", "avatar", "has_payment_password"):
            setattr(cls, f"resolve_{k}", gen_resolve(k))

    def resolve_id(self, info):
        return self.uuid


class User(BaseUserQL, DjangoObjectType):
    class Meta:
        model = ShopUser
        only_fields = ("",)


class Me(BaseUserQL, DjangoObjectType):
    phone = graphene.String(required=True)
    is_vendor = graphene.Boolean()

    class Meta:
        model = ShopUser
        only_fields = ("is_vendor", "phone")


class UpdateUserInfoInput(graphene.InputObjectType):
    nickname = graphene.String(default_value=None)
    avatar_url = graphene.String(default_value=None)
    # avatar = Upload(default_value=None)


class UpdateUserInfo(graphene.Mutation):
    class Arguments:
        params = UpdateUserInfoInput(required=True, name="input")

    Output = Result

    @login_required
    def mutate(self, info, params):
        shop_user = info.context.user.shop_user
        for k, v in params.items():
            setattr(shop_user, k, v)
            shop_user.save(update_fields=[k])
        return Result(success=True, message="")
