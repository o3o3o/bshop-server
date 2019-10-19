import logging
from provider import BaseProvider
from common.schema import LoginProvider


logger = logging.getLogger(__name__)


class WeChatProvider(BaseProvider):
    field = "alipay_id"
    name = LoginProvider.ALIPAY.value
