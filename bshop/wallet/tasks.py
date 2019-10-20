import logging
from bshop.celery import app
from wechat_django.pay.models import UnifiedOrder, UnifiedOrderResult

from common.utils import utc_now

logger = logging.getLogger(__name__)


class NoSuccess(Exception):
    pass


@app.task(autoretry_for=(NoSuccess,), max_retries=10, retry_backoff=2)
def sync_wechat_order(order_id):
    order = UnifiedOrder.objects.get(id=order_id)

    if (
        order.trade_state() == UnifiedOrderResult.State.SUCCESS
        or order.time_expire < utc_now()
    ):
        logger.info(f"Skip sync order {order}")
        return

    res = order.sync()
    print(res)
    if order.trade_state() != UnifiedOrderResult.State.SUCCESS:
        print("retry...")
        raise NoSuccess
    else:
        logger.info(f"Sync {order} successfully!")
