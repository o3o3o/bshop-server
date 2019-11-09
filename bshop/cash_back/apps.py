from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CashBackConfig(AppConfig):
    name = "cash_back"
    verbose_name = _("CashBack")
    verbose_name_plural = _("CashBack")
