import logging

import graphene
from graphql.error import GraphQLError
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from common.schema import LoginProvider
from common.utils import urlencode

# from user_center.models import ShopUser
from wallet.order import wechat_create_order

logger = logging.getLogger(__name__)


# class Ledger(DjangoObjectType):
#    pass


class CreatePayOrderInput(graphene.InputObjectType):
    provider = graphene.Field(LoginProvider, required=True)
    code = graphene.String()
    amount = graphene.Decimal(required=True)
    # ip = graphene.String()


# https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_1&index=1
class CreatePayOrder(graphene.Mutation):
    class Arguments:
        params = CreatePayOrderInput(required=True, name="input")

    # wechat \ alipay...
    payment = graphene.JSONString()

    @login_required
    def mutate(self, info, params):
        if params.provider == LoginProvider.WECHAT.value:
            wechat_create_order(params.provider, params.code, params.amount)
        elif params.provider == LoginProvider.ALIPAY.value:
            pass

        return "{}"


class VendorInfo(graphene.ObjectType):
    vendor_id = graphene.ID()
    vendor_name = graphene.String()
    schema = graphene.String()
    type = graphene.String()
    qr = graphene.String()


class Mutation(graphene.ObjectType):
    create_pay_order = CreatePayOrder.Field()


class Query(graphene.ObjectType):
    vendor_receive_pay_qr = graphene.Field(VendorInfo)

    @login_required
    def resolve_vendor_receive_pay_qr(self, info):
        shop_user = info.context.user.shop_user
        if not shop_user.is_vendor:
            raise GraphQLError("not_vendor")

        qr = "bshop://pay/?" + urlencode(
            {"vendorId": shop_user.uuid, "vendorName": shop_user.vendor_name}
        )
        return VendorInfo(
            vendor_id=shop_user.uuid,
            vendor_name=shop_user.vendor_name,
            schema="bshop",
            type="pay",
            qr=qr,
        )
