import logging

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from user_center.models import ShopUser
from wallet.order import wechat_create_order

logger = logging.getLogger(__name__)


class Ledger(DjangoObjectType):
    pass


class CreatePayOrderInput(graphene.InputObjectType):
    provider = graphene.Field(LoginProvider, required=True)
    code = graphene.String()
    amount = graphene.Decimal(required=True)
    ip = graphene.String()


# https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_1&index=1
class CreatePayOrder(graphene.Mutation):
    class Arguments:
        params = CreatePayOrderInput(required=True, name="input")

    # wechat \ alipay...
    payment = graphene.Generic()

    @login_required
    def mutate(self, info, params):
        if params.provider == LoginProvider.WECHAT.value:
            wechat_create_order(params.provider, params.code, params.amount)
        elif params.provider == LoginProvider.ALIPAY.value:
            pass
