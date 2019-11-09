from django.db import models
from django.utils.translation import gettext_lazy as _
from common.base_models import BaseModel, DecimalField, ModelWithExtraInfo


class DepositCashBack(BaseModel, ModelWithExtraInfo):
    amount = DecimalField(verbose_name=_("Deposit Amount"), help_text="充值门槛")
    return_amount = DecimalField(
        verbose_name=_("Deposit cash back amount"), help_text="返现数量"
    )


class PayCashBack(BaseModel, ModelWithExtraInfo):
    start_at = models.DateTimeField(verbose_name=_("Start Time"))
    end_at = models.DateTimeField(verbose_name=_("End Time"))
    amount = DecimalField(verbose_name=_("PayCashBack Amount"))
