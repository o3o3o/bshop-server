import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import models, transaction
from django.utils.functional import cached_property

from user_center.models import ShopUser
from common.utils import d0, utc_now, to_decimal
from common.base_models import (
    BaseModel,
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


class FundActionManager(models.Manager):
    pass


class FundAction(BaseModel, ModelWithExtraInfo):
    from_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_from", db_index=True, null=True
    )
    to_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_to", db_index=True, null=True
    )
    amount = DecimalField()
    note = models.CharField(max_length=128, null=True, blank=True)
    order_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    objects = FundActionManager()


@transaction.atomic
def do_transfer(
    from_user: ShopUser, to_user: ShopUser, amount: Decimal, note: str = None
):
    from_fund = from_user.get_user_fund()
    to_fund = to_user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    # First, we try to deduct from the HoldFund, if fail then deduct from Fund
    remain_amount = HoldFund.objects.decr_hold(from_fund, amount)

    if remain_amount > d0:
        Fund.objects.decr_cash(from_fund.id, remain_amount)

    if remain_amount < d0:
        raise AssertionError("Should not happen here")

    Fund.objects.incr_cash(to_fund.id, amount)

    action = FundAction.objects.create(
        from_fund=from_fund, to_fund=to_fund, amount=amount, note=note
    )
    return action


@transaction.atomic
def do_deposit(user: ShopUser, amount: Decimal, order_id: str, note: str = None):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")
    Fund.objects.incr_cash(fund.id, amount)

    action = FundAction.objects.create(
        to_fund=fund, amount=amount, order_id=order_id, note=note
    )
    return action


@transaction.atomic
def do_withdraw(user: ShopUser, amount: Decimal, order_id: str, note: str = None):
    fund = user.get_user_fund()

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    Fund.objects.decr_cash(fund.id, amount)

    action = FundAction.objects.create(
        from_fund=fund, amount=amount, order_id=order_id, note=note
    )
    return action


def do_cash_back(
    user: ShopUser, amount: Decimal, order_id: str = None, note: str = None
):
    # TODO more cash back stragety
    if amount <= to_decimal("1000"):
        return

    # FIXME:
    fund = user.get_user_fund()
    HoldFund.objects.incr_hold(fund, amount, expired_at=utc_now() + timedelta(years=1))
