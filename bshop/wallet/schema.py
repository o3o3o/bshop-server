import logging

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from django.db.models import Q
from django.db import transaction
from django.conf import settings

from common import exceptions
from common.schema import LoginProvider, Result, OrderState
from common.utils import urlencode, AvoidResubmit, d0
from gql import type as gtype

from user_center.models import ShopUser
from wallet.models import FundAction, Fund
from wallet.action import do_transfer, do_withdraw
from provider import get_provider_cls

logger = logging.getLogger(__name__)


class Ledger(DjangoObjectType):
    id = graphene.UUID()
    out = graphene.Boolean()

    class Meta:
        model = FundAction
        only_fields = ("amount", "note")
        order_by = "id"  # FIXME:

    def resolve_id(self, info):
        return self.uuid

    def resolve_out(self, info):
        if info.fund == self.from_fund:
            return False
        elif info.fund == self.to_fund:
            return False
        else:
            raise ValueError


class WithdrawInput(graphene.InputObjectType):
    amount = gtype.Decimal(required=True)
    request_id = graphene.UUID(required=True)
    provider = graphene.Field(LoginProvider, required=True)


class Withdraw(graphene.Mutation):
    class Arguments:
        params = WithdrawInput(required=True, name="input")

    Output = Result

    @login_required
    def mutate(self, info, params):

        shop_user = info.context.user.shop_user

        avoid_resubmit = AvoidResubmit("withdraw")
        try:
            avoid_resubmit(params.request_id, shop_user.id)
        except avoid_resubmit.ResubmittedError as e:
            raise exceptions.GQLError(e.message)

        try:
            cls = get_provider_cls(params.provider)
            obj = cls()
            openid = obj.get_openid(shop_user=shop_user)
        except exceptions.DoNotSupportBindType:
            raise exceptions.GQLError(f"Does not support {params.provider}")

        note = settings.LOGO_NAME + "-提现"

        with transaction.atomic():
            try:
                transfer = do_withdraw(shop_user, params.amount, note="提现到零钱")
            except exceptions.NotEnoughBalance as e:
                raise exceptions.GQLError(e.message)

            try:
                res = obj.withdraw(openid, params.amount, note)
            except exceptions.WithdrawError as e:
                # FIXME: revert do_withdraw?
                # 提现进行中，可能会有一定延时，需要人工处理
                # 提现排队中....
                logger.exception(str(e))
                raise exceptions.GQLError(e.message)

            transfer.extra_info = dict(res)
            transfer.order_id = res["payment_no"]
            transfer.save()

            return Result(success=True)


class CreatePayOrderInput(graphene.InputObjectType):
    provider = graphene.Field(LoginProvider, required=True)
    code = graphene.String()
    amount = gtype.Decimal(required=True)
    to = graphene.UUID()
    request_id = graphene.UUID(required=True)


# https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_1&index=1
class CreatePayOrder(graphene.Mutation):
    """ deposit """

    class Arguments:
        params = CreatePayOrderInput(required=True, name="input")

    # wechat \ alipay...
    payment = graphene.JSONString()

    @login_required
    def mutate(self, info, params):

        shop_user = info.context.user.shop_user

        avoid_resubmit = AvoidResubmit("createPayOrder")
        try:
            avoid_resubmit(params.request_id, shop_user.id)
        except avoid_resubmit.ResubmittedError as e:
            raise exceptions.GQLError(e.message)

        to_user = None
        if params.to:
            to_user = ShopUser.objects.get(uuid=params.to)
        try:
            cls = get_provider_cls(params.provider)
            res = cls().create_pay_order(params.code, params.amount, to_user=to_user)
        except exceptions.DoNotSupportBindType:
            raise exceptions.GQLError(f"Does not support {params.provider}")

        return CreatePayOrder(payment=res)


class TransferInput(graphene.InputObjectType):
    to = graphene.UUID(required=True)
    amount = gtype.Decimal(required=True)
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
        try:
            do_transfer(
                from_user=shop_user,
                to_user=to_user,
                amount=params.amount,
                note=params.note,
            )
        except exceptions.NotEnoughBalance as e:
            raise exceptions.GQLError(e.message)

        return Result(success=True)


class Mutation(graphene.ObjectType):
    create_pay_order = CreatePayOrder.Field()
    transfer = Transfer.Field()
    withdraw = Withdraw.Field()


class OrderInfo(graphene.ObjectType):
    id = graphene.ID()
    state = graphene.Field(OrderState)
    amount = gtype.Decimal()


class VendorInfo(graphene.ObjectType):
    vendor_id = graphene.ID()
    vendor_name = graphene.String()
    schema = graphene.String()
    type = graphene.String()
    qr = graphene.String()


class FundQL(DjangoObjectType):
    total = gtype.Decimal(default_value=d0)
    cash = gtype.Decimal(default_value=d0)
    hold = gtype.Decimal(default_value=d0)

    class Meta:
        model = Fund
        only_fields = ("cash", "currency")
        name = "Fund"

    def resolve_total(self, info):
        return self.total

    def resolve_hold(self, info):
        return self.hold


class Query(graphene.ObjectType):
    fund = graphene.Field(FundQL)
    ledger_list = graphene.List(Ledger)
    vendor_receive_pay_qr = graphene.Field(VendorInfo)
    order_info = graphene.Field(
        OrderInfo, provider=graphene.Argument(LoginProvider), order_id=graphene.String()
    )
    # test_order_info = graphene.Field(OrderInfo, order_id=graphene.String())

    @login_required
    def resolve_fund(self, info):
        shop_user = info.context.user.shop_user
        try:
            return Fund.objects.get(shop_user=shop_user)
        except Fund.DoesNotExist:
            return FundQL(currency="CNY")

    @login_required
    def resolve_ledger_list(self, info):
        shop_user = info.context.user.shop_user
        fund = Fund.objects.get(shop_user=shop_user)
        setattr(info, "fund", fund)

        return FundAction.objects.filter(Q(from_fund=fund) | Q(to_fund=fund))

    # def resolve_test_order_info(self, info, order_id, **kw):
    #    from wechat_django.pay.models import UnifiedOrder
    #    from wechat_django.pay import signals
    #    from wechat_django.pay.signals import order_updated

    #    order = UnifiedOrder.objects.get(id=order_id)
    #    order.result.update({"attach": "attach"}, signal=True, verify=False)
    #    signals.order_updated.send(
    #        sender=order.pay.staticname,
    #        result=order.result,
    #        order=order,
    #        state=order.trade_state,
    #        attach="attach",
    #    )
    #    return None

    @login_required
    def resolve_order_info(self, info, provider, order_id, **kw):
        shop_user = info.context.user.shop_user

        cls = get_provider_cls(provider)
        obj = cls()

        openid = obj.get_openid(shop_user=shop_user)
        res = obj.order_info(order_id, openid)
        if res:
            return OrderInfo(**res)
        else:
            return None

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
