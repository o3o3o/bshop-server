import uuid
from django.db import models
from django.utils.functional import cached_property
from django.contrib.postgres.fields import JSONField

from common.utils import d0


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


class RefreshFromDbInvalidatesCachedPropertiesMixin:
    def refresh_from_db(self, *args, **kwargs):
        self.invalidate_cached_properties()
        return super().refresh_from_db(*args, **kwargs)

    def invalidate_cached_properties(self):
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, cached_property):
                self.__dict__.pop(key, None)
