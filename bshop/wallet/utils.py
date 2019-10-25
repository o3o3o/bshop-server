from common.models import SystemQuota
from common.utils import to_decimal


def get_cash_back_threshold():
    return SystemQuota.objects.get_quota(
        "cashback.threshold", default=to_decimal("1000")
    )


def get_cash_back_expired_days():
    return SystemQuota.objects.get_quota(
        "cashback.expired.days", default=to_decimal("365")
    )
