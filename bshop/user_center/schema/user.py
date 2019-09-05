import logging

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from graphene_file_upload.scalars import Upload

from django.conf import settings
from common.upload import Uploader
from common.schema import Result, DeviceType
from user_center.schema.credential import Credential
from user_center.models import ShopUser, PushToken

logger = logging.getLogger(__name__)


class BaseUserQL(object):
    id = graphene.String(required=True)
    avatar = graphene.String()
    nickname = graphene.String()
    last_name = graphene.String()
    first_name = graphene.String()

    def __init_subclass__(cls, *arg, **kw):
        super().__init_subclass__(*arg, **kw)

        def gen_resolve(key):
            return lambda self, info: getattr(self, key)

        for k in ("last_name", "first_name", "avatar"):
            setattr(cls, f"resolve_{k}", gen_resolve(k))

    def resolve_id(self, info):
        return self.uuid


class User(BaseUserQL, DjangoObjectType):
    class Meta:
        model = ShopUser
        only_fields = ("",)


class Me(BaseUserQL, DjangoObjectType):
    phone = graphene.String(required=True)

    class Meta:
        model = ShopUser
        only_fields = ("",)

    def resolve_phone(self, info):
        return self.phone


class UpdateUserInfoInput(graphene.InputObjectType):
    nickname = graphene.String(default_value=None)
    # avatar = Upload(default_value=None)


class UpdateUserInfo(graphene.Mutation):
    class Arguments:
        params = UpdateUserInfoInput(required=True, name="input")

    Output = Result

    @login_required
    def mutate(self, info, params):
        shop_user = info.context.user.shop_user
        for k, v in params.items():
            if k == "nickname":
                if ShopUser.objects.filter(_nickname=v).exists():
                    return Result(success=False, message="nickname_already_exists")

            setattr(shop_user, k, v)
        return Result(success=True, message="")
