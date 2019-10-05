import logging

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from common import exceptions
from common.schema import LoginProvider, Result
from common.utils import urlencode, AvoidResubmit

from user_center.models import ShopUser
from wallet.models import do_transfer, FundAction
from wallet.order import wechat_create_order

logger = logging.getLogger(__name__)


class Ledger(DjangoObjectType):
    id = graphene.UUID()

    class Meta:
        model = FundAction
        only_fields = ("amount", "note")

    def resolve_id(self, info):
        return self.uuid


class CreateDepositOrderInput(graphene.InputObjectType):
    provider = graphene.Field(LoginProvider, required=True)
    code = graphene.String()
    amount = graphene.Decimal(required=True)
    # ip = graphene.String()


# https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_1&index=1
class CreateDepositOrder(graphene.Mutation):
    class Arguments:
        params = CreateDepositOrderInput(required=True, name="input")

    # wechat \ alipay...
    payment = graphene.JSONString()

    @login_required
    def mutate(self, info, params):
        if params.provider == LoginProvider.WECHAT.value:
            wechat_create_order(params.provider, params.code, params.amount)
        elif params.provider == LoginProvider.ALIPAY.value:
            pass

        return "{}"


class TransferInput(graphene.InputObjectType):
    to = graphene.UUID(required=True)
    amount = graphene.Decimal(required=True)
    note = graphene.String()
    payment_password = graphene.String(required=True)
    request_id = graphene.UUID(required=True)


class Transfer(graphene.Mutation):
    class Arguments:
        params = TransferInput(required=True, name="input")

    Output = Result

    @login_required
    def mutate(self, info, params):
        # 1. avoid resubmit
        shop_user = info.context.user.shop_user

        avoid_resubmit = AvoidResubmit("transferPay")
        try:
            avoid_resubmit(params.request_id, shop_user.id)
        except avoid_resubmit.ResubmittedError as e:
            raise exceptions.GQLError(e.message)

        # 2. check payment password
        try:
            if not shop_user.has_payment_password:
                raise exceptions.NeedSetPaymentPassword

            if not shop_user.check_payemnt_password(params.payment_password):
                raise exceptions.WrongPassword
        except exceptions.ErrorResultException as e:
            raise exceptions.GQLError(e.message)

        # TODO:
        # 3. do transfer
        to_user = ShopUser.objects.get(uuid=params.to)
        do_transfer(
            from_user=shop_user, to_user=to_user, amount=params.amount, note=params.note
        )

        return Result(success=True)


class Mutation(graphene.ObjectType):
    create_deposit_order = CreateDepositOrder.Field()
    transfer = Transfer.Field()


class VendorInfo(graphene.ObjectType):
    vendor_id = graphene.ID()
    vendor_name = graphene.String()
    schema = graphene.String()
    type = graphene.String()
    qr = graphene.String()


class Query(graphene.ObjectType):
    vendor_receive_pay_qr = graphene.Field(VendorInfo)

    @login_required
    def resolve_vendor_receive_pay_qr(self, info):
        shop_user = info.context.user.shop_user
        if not shop_user.is_vendor:
            raise exceptions.GQLError("not_vendor")

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
