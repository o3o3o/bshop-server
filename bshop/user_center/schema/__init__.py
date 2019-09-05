import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required

from common import exceptions
from common.phone import parse_phone
from common.ratelimit import ratelimit
from user_center.models import ShopUser
from user_center.schema.auth import SignIn, SignUp, RequestVerificationCode, VerifyCode
from user_center.schema.credential import (
    CreateCredential,
    DeleteCredential,
    UpdateCredential,
)
from user_center.schema.user import Me, UpdateUserInfo


class Query(graphene.ObjectType):
    me = graphene.Field(Me)
    registered = graphene.Boolean(
        phone=graphene.String(required=True),
        description="check user's registered status by phone with country code prefix",
    )

    @login_required
    def resolve_me(self, info):
        return info.context.user.shop_user

    @ratelimit(key="ip", rate="10/m", block=True)
    @ratelimit(key="gql:phone", rate="5/m", block=True)
    def resolve_registered(self, info, phone):
        try:
            phone = parse_phone(phone, default_country=None)
        except exceptions.InvalidPhone as e:
            raise exceptions.GQLError(e.message)

        try:
            ShopUser.objects.get(user__username=phone)
            return True
        except ShopUser.DoesNotExist:
            return False


class Mutation(graphene.ObjectType):
    request_verification_code = RequestVerificationCode.Field()
    verify_code = VerifyCode.Field()
    sign_in = SignIn.Field()
    sign_up = SignUp.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    update_user_info = UpdateUserInfo.Field()
