import logging
from bshop.celery import app
from wechat_django.pay.models import UnifiedOrder, UnifiedOrderResult

from common.utils import utc_now

logger = logging.getLogger(__name__)


@app.task
def sync_wechat_order(order_id):
    order = UnifiedOrder.objects.get(id=order_id)

    if order.state == UnifiedOrderResult.State.SUCCESS or order.time_expire < utc_now():
        logger.info(f"Skip sync order {order}")
        return

    res = order.sync()
    print(res)
    if order.state != UnifiedOrderResult.State.SUCCESS:
        sync_wechat_order.apply_async(args=[order_id], countdown=1, expires=10)
    else:
        logger.info(f"Sync {order} successfully!")
