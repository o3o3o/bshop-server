from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProviderConfig(AppConfig):
    name = "provider"
    verbose_name = _("Pay Provider")

    def ready(self):
        from .wechat import order_updated  # noqa
