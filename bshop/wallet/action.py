import logging
from decimal import Decimal
from datetime import timedelta
from django.db import transaction

from common import exceptions
from common.utils import d0, utc_now
from user_center.models import ShopUser

from wallet.models import Fund, FundAction, FundTransfer, HoldFund
from cash_back.models import PayCashBack, DepositCashBack

logger = logging.getLogger(__name__)


@transaction.atomic
def do_transfer(
    from_user: ShopUser,
    to_user: ShopUser,
    amount: Decimal,
    order_id: str = None,
    note: str = None,
    **kw,
):
    from_fund = from_user.get_user_fund()
    to_fund = to_user.get_user_fund()

    if from_fund.total < amount:
        raise exceptions.NotEnoughBalance

    # First, we try to deduct from the HoldFund, if fail then deduct from Fund
    remain_amount = HoldFund.objects.decr_hold(from_fund, amount)

    if remain_amount < d0:
        raise AssertionError("Should not happen here")
    elif remain_amount > d0:
        Fund.objects.decr_cash(from_fund.id, remain_amount)

    new_from_fund = Fund.objects.get(id=from_fund.id)
    new_to_fund = Fund.objects.incr_cash(to_fund.id, amount)

    transfer = FundTransfer.objects.create(
        from_fund=from_fund,
        to_fund=to_fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="TRANSFER",
        extra_info=kw,
    )

    FundAction.objects.add_action(from_fund, transfer, new_from_fund.amount_d)
    FundAction.objects.add_action(to_fund, transfer, balance=new_to_fund.amount_d)

    return transfer


@transaction.atomic
def do_pay(
    from_user: "ShopUser",
    to_user: "ShopUser",
    amount: "Decimal",
    order_id: str,
    note: str = None,
    **kw,
):
    fund = to_user.get_user_fund()

    new_fund = Fund.objects.incr_cash(fund.id, amount)

    transfer = FundTransfer.objects.create(
        to_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="PAY",
        from_shop_user=from_user,
        extra_info=kw,
    )

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    # cash back to payer
    cash_back_transfer = PayCashBack.objects.do_cash_back(
        from_user,
        paied_amount=amount,
        pay_transfer_id=transfer.id,
        pay_order_id=order_id,
    )

    return transfer, cash_back_transfer


@transaction.atomic
def do_deposit(user: ShopUser, amount: Decimal, order_id: str, note: str = None, **kw):
    fund = user.get_user_fund()

    new_fund = Fund.objects.incr_cash(fund.id, amount)

    transfer = FundTransfer.objects.create(
        to_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="DEPOSIT",
        extra_info=kw,
    )

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    cash_back_transfer = DepositCashBack.objects.do_cash_back(
        user, amount, order_id=order_id, deposit_transfer_id=transfer.id
    )
    return transfer, cash_back_transfer


@transaction.atomic
def do_withdraw(
    user: ShopUser, amount: Decimal, order_id: str = None, note: str = None, **kw
):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    new_fund = Fund.objects.decr_cash(fund.id, amount)

    transfer = FundTransfer.objects.create(
        from_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="WITHDRAW",
        extra_info=kw,
    )

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    return transfer
