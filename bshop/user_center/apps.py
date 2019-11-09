from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UserCenterConfig(AppConfig):
    name = "user_center"
    verbose_name = _("User center")
    verbose_name_plural = _("User center")
