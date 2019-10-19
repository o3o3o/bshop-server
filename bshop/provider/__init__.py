import os
import logging
import importlib
from decimal import Decimal
from os.path import dirname

from common import exceptions


logger = logging.getLogger(__name__)


class BaseProvider(object):
    field = None
    name = None

    def get_openid(self, auth_code):
        raise NotImplementedError

    def create_pay_order(self, code: str, amount: Decimal, to_user=None):
        raise NotImplementedError

    def order_info(self, order_id):
        raise NotImplementedError


def import_provider_clses():
    clses = {}
    from provider import BaseProvider

    cur_dir = dirname(__file__)
    files = os.listdir(cur_dir)

    for name in files:
        if name == "__init__.py":
            continue
        if name[-3:] != ".py":
            continue
        module_name = f"provider.{name[:-3]}"

        module = importlib.import_module(module_name)
        for attr in dir(module):
            obj = getattr(module, attr)
            try:
                if issubclass(obj, BaseProvider):
                    if obj.name is None:
                        continue
                    clses[obj.name] = obj
            except TypeError:
                pass

    return clses


_ProviderClsMap = None


def get_provider_cls(by_name=None):
    global _ProviderClsMap
    if _ProviderClsMap is None:
        _ProviderClsMap = import_provider_clses()

    if by_name:
        cls = _ProviderClsMap.get(by_name, None)
        if not cls:
            raise exceptions.DoNotSupportBindType
        return cls

    return _ProviderClsMap.values()
