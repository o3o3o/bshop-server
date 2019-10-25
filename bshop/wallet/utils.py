from common.models import SystemQuota
from common.utils import to_decimal


class CashBackSettings(object):
    CASHBACK_THRESHOLD = "cashback.threshold"
    CASHBACK_EXPIRED_DAYS = "cashback.expired.days"

    @property
    def threshold(self):
        return SystemQuota.objects.get_quota(
            self.CASHBACK_THRESHOLD, default=to_decimal("1000")
        )

    @threshold.setter
    def threshold(self, value):
        return SystemQuota.objects.set_quota(self.CASHBACK_THRESHOLD, to_decimal(value))

    @property
    def expired_days(self) -> int:
        r = SystemQuota.objects.get_quota(
            self.CASHBACK_EXPIRED_DAYS, default=to_decimal("365")
        )
        if r:
            return int(r)
        else:
            return 0

    @expired_days.setter
    def expired_days(self, value):
        return SystemQuota.objects.set_quota(
            self.CASHBACK_EXPIRED_DAYS, to_decimal(value)
        )
