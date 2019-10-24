import decimal
from django.db import models

from common.base_models import BaseModel, DecimalField


class SystemQuotaManager(models.Manager):
    def get_quota(self, name, default=0):
        try:
            sq = self.get(name=name)
            return sq.quota
        except SystemQuota.DoesNotExist:
            pass
        return decimal.Decimal(default)

    def set_quota(self, name, value):
        sq, __ = self.get_or_create(name=name)
        sq.quota = decimal.Decimal(value)
        sq.save()


class SystemQuota(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    quota = DecimalField()

    objects = SystemQuotaManager()

    class Meta:
        db_table = "system_quotas"

    def __str__(self):
        return self.name
