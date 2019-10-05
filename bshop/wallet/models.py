import logging
from decimal import Decimal
from django.db import models, transaction

from user_center.models import ShopUser
from common.utils import d0
from common.base_models import BaseModel, DecimalField, ModelWithExtraInfo

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
        logging.info("fund %s decr cash %s, cnt=%s", fund_id, amount, cnt)
        return self.get(id=fund_id)


# Create your models here.
class Fund(BaseModel, ModelWithExtraInfo):
    shop_user = models.ForeignKey(
        ShopUser, models.CASCADE, related_name="user_funds", db_index=True
    )
    # CNY
    currency = models.CharField(max_length=8, default="CNY")
    cash = DecimalField()

    objects = FundManager()

    class InsufficientCash(Exception):
        pass


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
    # order_id = models.chapter

    objects = FundActionManager()


@transaction.atomic
def do_transfer(from_user, to_user, amount: Decimal, note: str = None):
    from_fund = from_user.user_funds.get(currency="CNY")
    to_fund = to_user.user_funds.get(currency="CNY")

    if amount <= d0:
        raise ValueError("Invalid minus amount")

    Fund.objects.decr_cash(from_fund.id, amount)
    Fund.objects.incr_cash(to_fund.id, amount)

    action = FundAction.objects.create(
        from_fund=from_fund, to_fund=to_fund, amount=amount, note=note
    )
    return action
