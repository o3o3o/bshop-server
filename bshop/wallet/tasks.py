import logging
from bshop.celery import app
from wechat_django.pay.models import UnifiedOrder, UnifiedOrderResult

from common.utils import utc_now
from wallet.models import HoldFund

logger = logging.getLogger(__name__)


class NoSuccess(Exception):
    pass


# https://celery.readthedocs.io/en/latest/userguide/tasks.html?highlight=retry_backof#Task.retry_backoff
@app.task(autoretry_for=(NoSuccess,), max_retries=3, default_retry_delay=1)
def sync_wechat_order(order_id):
    order = UnifiedOrder.objects.get(id=order_id)

    if (
        order.trade_state() == UnifiedOrderResult.State.SUCCESS
        or order.time_expire < utc_now()
    ):
        logger.info(f"wechat_order skip sync {order}")
        return

    res = order.sync()
    logger.debug(res)
    if order.trade_state() != UnifiedOrderResult.State.SUCCESS:
        raise NoSuccess
    else:
        logger.info(f"wechat_order sync {order} successfully!")


@app.task
def test_order(order_id):
    order = UnifiedOrder.objects.get(id=order_id)
    order.result.update({"attach": "attach"}, signal=True, verify=False)


@app.task
def check_expired_holdfund():
    # TODO: check aciton with celery  ETA?
    HoldFund.objects.expired_unhold()
