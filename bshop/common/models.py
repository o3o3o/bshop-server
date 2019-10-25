from decimal import Decimal
from django.db import models

from common.utils import to_decimal
from common.base_models import BaseModel, DecimalField


class SystemQuotaManager(models.Manager):
    def get_quota(self, name: str, default=0) -> Decimal:
        try:
            sq = self.get(name=name)
            return sq.quota
        except SystemQuota.DoesNotExist:
            pass
        return to_decimal(default)

    def set_quota(self, name: str, value: Decimal):
        sq, __ = self.get_or_create(name=name)
        sq.quota = value
        sq.save()


class SystemQuota(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    quota = DecimalField()

    objects = SystemQuotaManager()

    class Meta:
        db_table = "system_quotas"

    def __str__(self):
        return self.name


# TODO: user quota?
