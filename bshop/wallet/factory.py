import factory
import factory.fuzzy
from datetime import timedelta

from common.utils import utc_now
from wallet.models import Fund, HoldFund
from user_center.factory import ShopUserFactory


class FundFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fund

    shop_user = factory.SubFactory(ShopUserFactory)
    cash = factory.fuzzy.FuzzyDecimal(0.1, 10000)


class HoldFundFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HoldFund

    fund = factory.SubFactory(FundFactory)
    amount = factory.fuzzy.FuzzyDecimal(0.01, 10000)
    expired_at = factory.fuzzy.FuzzyDateTime(
        utc_now() + timedelta(minutes=1), utc_now() + timedelta(minutes=3)
    )
