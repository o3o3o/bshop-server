import uuid
from django.db import models
from common.utils import d0
from django.contrib.postgres.fields import JSONField


class DecimalField(models.DecimalField):
    def __init__(self, **kw):
        kw.setdefault("max_digits", 65)
        kw.setdefault("decimal_places", 4)
        kw.setdefault("default", d0)
        super(DecimalField, self).__init__(**kw)


class BaseModel(models.Model):
    """
    Basic Model cover uuid and timestamp
    """

    uuid = models.UUIDField(max_length=36, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class ModelWithExtraInfo(models.Model):
    extra_info = JSONField(null=True, blank=True)

    class Meta:
        abstract = True
