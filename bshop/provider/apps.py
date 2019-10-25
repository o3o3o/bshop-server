from django.apps import AppConfig


class ProviderConfig(AppConfig):
    name = "provider"

    def ready(self):
        from .wechat import order_updated  # noqa
