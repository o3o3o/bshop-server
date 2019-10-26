import logging
from decimal import Decimal
from datetime import timedelta
from django.db import transaction

from common import exceptions
from common.utils import d0, utc_now
from user_center.models import ShopUser

from wallet.utils import CashBackSettings
from wallet.models import Fund, FundAction, FundTransfer, HoldFund

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

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    if from_fund.total < amount:
        raise exceptions.NotEnoughBalance

    transfer = FundTransfer.objects.create(
        from_fund=from_fund,
        to_fund=to_fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="TRANSFER",
        extra_info=kw,
    )

    # First, we try to deduct from the HoldFund, if fail then deduct from Fund
    remain_amount = HoldFund.objects.decr_hold(from_fund, amount)

    if remain_amount > d0:
        Fund.objects.decr_cash(from_fund.id, remain_amount)

    if remain_amount < d0:
        raise AssertionError("Should not happen here")

    new_fund = Fund.objects.get(id=from_fund.id)
    FundAction.objects.add_action(from_fund, transfer, new_fund.amount_d)

    new_fund = Fund.objects.incr_cash(to_fund.id, amount)
    FundAction.objects.add_action(to_fund, transfer, balance=new_fund.amount_d)

    return transfer


@transaction.atomic
def do_deposit(user: ShopUser, amount: Decimal, order_id: str, note: str = None, **kw):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    transfer = FundTransfer.objects.create(
        to_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="DEPOSIT",
        extra_info=kw,
    )

    new_fund = Fund.objects.incr_cash(fund.id, amount)

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    return transfer


@transaction.atomic
def do_withdraw(
    user: ShopUser, amount: Decimal, order_id: str = None, note: str = None, **kw
):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    if fund.cash < amount:
        raise exceptions.NotEnoughBalance

    transfer = FundTransfer.objects.create(
        from_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="WITHDRAW",
        extra_info=kw,
    )

    new_fund = Fund.objects.decr_cash(fund.id, amount)

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    return transfer


@transaction.atomic
def do_cash_back(
    user: ShopUser, amount: Decimal, order_id: str = None, note: str = None, **kw
):
    # TODO more cash back stragety
    csetting = CashBackSettings()

    if amount <= csetting.threshold:
        return

    fund = user.get_user_fund()

    note = f"cash_back: {amount}"
    transfer = FundTransfer.objects.create(
        to_fund=fund,
        amount=amount,
        order_id=order_id,
        note=note,
        type="CASHBACK",
        extra_info=kw,
    )

    HoldFund.objects.incr_hold(
        fund, amount, expired_at=utc_now() + timedelta(days=csetting.expired_days)
    )

    new_fund = Fund.objects.get(id=fund.id)
    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)
    return transfer
