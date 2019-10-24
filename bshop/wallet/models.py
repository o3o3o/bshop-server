import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import models, transaction
from django.utils.functional import cached_property
from django.contrib.postgres.fields import JSONField

from user_center.models import ShopUser
from common.utils import d0, utc_now
from wallet.utils import get_cash_back_threshold, get_cash_back_expired_days
from common.base_models import (
    BaseModel,
    MYJSONField,
    DecimalField,
    ModelWithExtraInfo,
    RefreshFromDbInvalidatesCachedPropertiesMixin,
)

logger = logging.getLogger(__name__)


class FundManager(models.Manager):
    def incr_cash(self, fund_id, amount):
        cnt = self.filter(id=fund_id).update(cash=models.F("cash") + amount)
        logger.info("fund %s incr cash %s, cnt=%s", fund_id, amount, cnt)
        return self.get(id=fund_id)

    def decr_cash(self, fund_id, amount):
        cnt = self.filter(id=fund_id, cash__gte=amount).update(
            cash=models.F("cash") - amount
        )
        if cnt == 0:
            logger.error(
                "fund %s decr cash %s, cnt=%s, InsufficientCash", fund_id, amount, cnt
            )
            raise self.model.InsufficientCash()

        logger.info("fund %s decr cash %s, cnt=%s", fund_id, amount, cnt)
        return self.get(id=fund_id)


class Fund(
    RefreshFromDbInvalidatesCachedPropertiesMixin, BaseModel, ModelWithExtraInfo
):
    shop_user = models.ForeignKey(
        ShopUser, models.CASCADE, related_name="user_funds", db_index=True
    )
    # CNY
    currency = models.CharField(max_length=8, default="CNY")
    cash = DecimalField()

    objects = FundManager()

    def __str__(self):
        return f"fund:{self.id} {self.shop_user.phone}"

    class InsufficientCash(Exception):
        pass

    @cached_property
    def total(self):
        return self.cash + self.hold

    @cached_property
    def hold(self):
        return HoldFund.objects.total_amount(self)

    @property
    def amount_d(self):
        return {"total": self.total, "hold": self.hold, "cash": self.cash}


class HoldFundManager(models.Manager):
    def incr_hold(self, fund: Fund, amount: Decimal, expired_at: datetime):
        return self.create(fund=fund, amount=amount, expired_at=expired_at)

    def decr_hold(self, fund: Fund, amount: Decimal):
        with transaction.atomic():
            hold_funds = (
                self.select_for_update().filter(fund=fund).order_by("-expired_at")
            )

            for cbf in hold_funds:
                if cbf.amount >= amount:
                    cbf.amount -= amount
                    logger.info(f"holdfund {cbf.id} decr hold {amount}")
                    amount = d0
                else:
                    # deduct the amount and try next
                    logger.info(f"holdfund {cbf.id} decr hold {cbf.amount}")
                    cbf.amount = d0
                    amount -= cbf.amount

                if cbf.amount == d0:
                    cbf.delete()
                else:
                    cbf.save(update_fields=["amount"])

                if amount == d0:
                    return d0

            return amount

    def total_amount(self, fund: Fund):
        return (
            self.filter(fund=fund).aggregate(total=models.Sum("amount"))["total"] or d0
        )

    def expired_unhold(self):
        with transaction.atomic():
            hold_funds = self.select_for_update().filter(expired_at__lte=utc_now())
            for cbf in hold_funds:
                cbf.unhold()


class HoldFund(BaseModel, ModelWithExtraInfo):
    """ Hold cash for cash back """

    fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="hold_funds", db_index=True
    )

    amount = DecimalField()
    expired_at = models.DateTimeField()
    order_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    objects = HoldFundManager()

    def unhold(self):
        self.delete()
        Fund.objects.incr_cash(self.fund_id, self.amount)
        logger.info(f"Unhold for fund {self.fund_id} amount: {self.amount}")


class FundTransferManager(models.Manager):
    pass


class FundTransfer(BaseModel, ModelWithExtraInfo):
    TYPE_CHOICES = [(x, x) for x in ["WITHDRAW", "DEPOSIT", "CASHBACK", "TRANSFER"]]
    STATUS_CHOICES = [(x, x) for x in ["ADMIN_REQUIRED", "ADMIN_DENIED", "SUCCESS"]]

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="SUCCESS", db_index=True
    )

    # how to support deduct from holdfund?
    from_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_from", db_index=True, null=True
    )
    to_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_to", db_index=True, null=True
    )
    amount = DecimalField()
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, null=True, blank=True)
    note = models.CharField(max_length=128, null=True, blank=True)
    order_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    objects = FundTransferManager()


class FundActionManager(models.Manager):
    # FIXME: how to use fund action to store the history of fund changing
    def add_action(self, fund, transfer, balance=None, **kw):
        action, _ = self.update_or_create(
            fund=fund,
            transfer=transfer,
            defaults={"extra_info": kw if kw else None, "balance": balance},
        )
        # TODO: send signal
        return action


class FundAction(BaseModel, ModelWithExtraInfo):

    fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="fund_actions", db_index=True, null=True
    )
    transfer = models.ForeignKey(FundTransfer, models.CASCADE, null=True)
    balance = MYJSONField()

    objects = FundActionManager()


@transaction.atomic
def do_transfer(
    from_user: ShopUser, to_user: ShopUser, amount: Decimal, note: str = None
):
    from_fund = from_user.get_user_fund()
    to_fund = to_user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    transfer = FundTransfer.objects.create(
        from_fund=from_fund, to_fund=to_fund, amount=amount, note=note
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
def do_deposit(user: ShopUser, amount: Decimal, order_id: str, note: str = None):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    transfer = FundTransfer.objects.create(
        to_fund=fund, amount=amount, order_id=order_id, note=note
    )

    new_fund = Fund.objects.incr_cash(fund.id, amount)

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    return transfer


@transaction.atomic
def do_withdraw(user: ShopUser, amount: Decimal, order_id: str, note: str = None):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    transfer = FundTransfer.objects.create(
        from_fund=fund, amount=amount, order_id=order_id, note=note
    )

    new_fund = Fund.objects.decr_cash(fund.id, amount)

    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)

    return transfer


@transaction.atomic
def do_cash_back(
    user: ShopUser, amount: Decimal, order_id: str = None, note: str = None
):
    # TODO more cash back stragety
    cash_back_threshold = get_cash_back_threshold()
    if amount <= cash_back_threshold:
        return

    cash_back_expired_days = get_cash_back_expired_days()

    fund = user.get_user_fund()

    note = f"cash_back: {amount}"
    transfer = FundAction.objects.create(
        to_fund=fund, amount=amount, order_id=order_id, note=note
    )

    HoldFund.objects.incr_hold(
        fund, amount, expired_at=utc_now() + timedelta(days=cash_back_expired_days)
    )

    new_fund = Fund.objects.get(id=fund.id)
    FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)
    return transfer
