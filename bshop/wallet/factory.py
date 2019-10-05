import factory
import factory.fuzzy
from wallet.models import Fund
from user_center.factory import ShopUserFactory


class FundFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fund

    shop_user = factory.SubFactory(ShopUserFactory)
    cash = factory.fuzzy.FuzzyDecimal(0.1, 10000)
