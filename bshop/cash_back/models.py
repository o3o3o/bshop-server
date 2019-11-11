import logging
from decimal import Decimal
from datetime import timedelta
from django.db.models import Q
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


from common.utils import utc_now, d0

from common.base_models import BaseModel, DecimalField, ModelWithExtraInfo

from user_center.models import ShopUser
from wallet.models import Fund, FundAction, FundTransfer, HoldFund

logger = logging.getLogger(__name__)


class DepositCashBackManager(models.Manager):
    @transaction.atomic
    def do_cash_back(self, user: "ShopUser", amount: "Decimal", **kw):

        if amount <= d0:
            raise ValueError("amount is not postive")

        r = self.filter(deposit_amount__gte=amount).order_by("amount").last()
        if not r:
            logger.info("No match deposit cash back")
            return

        fund = user.get_user_fund()
        transfer = FundTransfer.objects.create(
            to_fund=fund,
            amount=r.cash_back_amount,
            type="DEPOSIT_CASHBACK",
            extra_info=kw,
        )
        HoldFund.objects.incr_hold(
            fund,
            transfer.amount,
            expired_at=utc_now() + timedelta(days=r.cash_back_expired_day),
        )

        new_fund = Fund.objects.get(id=fund.id)
        FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)
        logger.info(f"Deposit cash back, {user} {amount}->{r.cash_back_amount}")

        return transfer


class DepositCashBack(BaseModel, ModelWithExtraInfo):
    """
      充值达到deposit_amount后，返现cash_back_amount,
      在cash_back_expired_day天后可以提现
    """

    deposit_amount = DecimalField(
        verbose_name=_("Deposit Amount"), help_text="充值门槛, 单位为元"
    )
    cash_back_amount = DecimalField(
        verbose_name=_("Deposit cash back amount"), help_text="返现多少元"
    )
    cash_back_expired_day = models.PositiveSmallIntegerField(
        verbose_name=_("cash back expired to withdraw"), help_text="返现后多少天可以提现"
    )
    is_active = models.BooleanField(default=False, verbose_name=_("Is active"))
    objects = DepositCashBackManager()

    class Meta:
        verbose_name = _("Deposit Cash Back")
        verbose_name_plural = _("Deposit Cash Back")


class PayCashBackManager(models.Manager):
    @transaction.atomic
    def do_cash_back(self, user: "ShopUser", paied_amount: "Decimal", **kw):

        if paied_amount <= d0:
            raise ValueError("paied_amount is not postive")

        total_paied_amount = user.get_total_paied_amount() + paied_amount

        now = utc_now()

        qs = self.filter(
            is_active=True,
            start_at__lt=now,
            end_at__gt=now,
            total_paied_amount__lte=total_paied_amount,
        )
        if not qs.exists():
            return

        # try to check if the user is hint the register PayCash
        r = qs.get(type="NEW_USER_TYPE")
        if r and utc_now() <= user.created_at + timedelta(days=r.days_of_new_user):
            type_ = "PAY_CASHBACK4NEW_USER"
        else:
            r = qs.get(type="OLD_USER_TYPE")
            type_ = "PAY_CASHBACK4NEW_USER"

        if not r:
            return

        fund = user.get_user_fund()

        transfer = FundTransfer.objects.create(
            to_fund=fund, amount=r.cash_back_amount, type=type_, extra_info=kw
        )

        HoldFund.objects.incr_hold(
            fund,
            transfer.amount,
            expired_at=utc_now() + timedelta(days=r.cash_back_expired_day),
        )

        new_fund = Fund.objects.get(id=fund.id)
        FundAction.objects.add_action(fund, transfer, balance=new_fund.amount_d)
        return transfer


class PayCashBack(BaseModel, ModelWithExtraInfo):
    """ 消费累计满amount, 返现amount, 在活动期间一个用户只能返现一次"""

    TYPE_CHOICES = [
        ("NEW_USER_TYPE", _("NEW_USER_TYPE")),
        ("OLD_USER_TYPE", _("OLD_USER_TYPE")),
    ]
    name = models.CharField(
        max_length=1024, null=True, blank=True, verbose_name=_("Pay Cash Back Name")
    )
    type = models.CharField(
        max_length=16, choices=TYPE_CHOICES, verbose_name=_("PayCashBack Type")
    )
    days_of_new_user = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Days of new users")
    )
    start_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Start Time"),
        help_text="活动开始时间, 只针对于老用户, 新用户不填",
    )
    end_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("End Time"),
        help_text="活动结束时间, 只针对于老用户, 新用户不填",
    )
    total_paied_amount = DecimalField(
        verbose_name=_("PayCashBack Amount"), help_text="活动期间累计消费门槛，单位为元"
    )
    cash_back_amount = DecimalField(
        verbose_name=_("PayCashBack Amount"), help_text="累积消费到达门槛后，一次性返现数量"
    )
    is_active = models.BooleanField(default=False, verbose_name=_("Is active"))
    objects = PayCashBackManager()

    class Meta:
        verbose_name = _("Pay Cash Back")
        verbose_name_plural = _("Pay Cash Back")

    def save(self, *args, **kwargs):
        if self.is_active:
            qs = self.objects.filter(is_active=True)
            if (
                qs.filter(type="OLD_USER_TYPE")
                .filter(
                    Q(start_at__range=(self.start_at, self.end_at))
                    | Q(end_at__range=(self.start_at, self.end_at))
                )
                .exists()
            ):
                raise ValueError(_("Duplicate active Pay Cash Back"))
            if self.type == "NEW_USER_TYPE":
                if self.days_of_new_user is None:
                    raise ValueError(_("Need days_of_new_user"))
            elif self.type == "OLD_USER_TYPE":
                if self.start_at is None or self.end_at is None:
                    raise ValueError(_("start_at and end_at cannot be empty"))

        return super().save(*args, **kwargs)


class PayCashBackRecord(BaseModel):
    pay_cash_back = models.ForeignKey(
        PayCashBack, models.SET_NULL, related_name="+", null=True, blank=True
    )
    shop_user = models.ForeignKey(ShopUser, models.CASCADE, related_name="+")

    class Meta:
        verbose_name = _("Pay Cash Back Record")
        verbose_name_plural = _("Pay Cash Back Record")
        unique_together = (("pay_cash_back", "shop_user"),)
