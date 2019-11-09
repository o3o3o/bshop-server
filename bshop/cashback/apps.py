from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CashbackConfig(AppConfig):
    name = "cashback"
    verbose_name = _("CashBack")
    verbose_name_plural = _("CashBack")
