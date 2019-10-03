from django.db import models
from user_center.models import ShopUser
from common.base_models import BaseModel, DecimalField, ModelWithExtraInfo

# Create your models here.
class Fund(BaseModel, ModelWithExtraInfo):
    shop_user = models.ForeignKey(
        ShopUser, models.CASCADE, related_name="user_funds", db_index=True
    )
    # CNY
    amount = DecimalField()


class FundTransfer(BaseModel, ModelWithExtraInfo):
    from_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_from", db_index=True, null=True
    )
    to_fund = models.ForeignKey(
        Fund, models.CASCADE, related_name="transfer_as_to", db_index=True, null=True
    )
    amount = DecimalField()
    # order_id = models.chapter
