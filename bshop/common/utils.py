import pytz
import copy
import time
import json
import decimal
import urllib.parse
from functools import wraps
from decimal import Decimal
from datetime import datetime
from django_redis import get_redis_connection

from common import exceptions


d0 = Decimal("0")


def utc_now():
    return datetime.utcnow().replace(tzinfo=pytz.UTC)


def floor_decimal(amount, digits=8):
    return amount.quantize(
        Decimal("1E-%d" % digits), context=decimal.Context(rounding=decimal.ROUND_FLOOR)
    )


def to_decimal(v, default="0", digits=8):
    if not isinstance(v, str):
        v = str(v)
    try:
        return floor_decimal(Decimal(v), digits=digits)
    except decimal.InvalidOperation:
        return Decimal(default)


def yuan2fen(d: Decimal) -> int:
    return int(d * 100)


def fen2yuan(d: int) -> Decimal:

    return to_decimal(d / 100)


def is_decimal(v):
    return isinstance(v, Decimal)


def urlencode(d):
    return urllib.parse.urlencode(d)


def timeit(method):
    @wraps(method)
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print(
            "timeit: %r (%r, %r) duration: %s sec"
            % (method.__name__, args, kw, te - ts)
        )
        return result

    return timed


def deepupdate(target, src):
    for k, v in src.items():
        if isinstance(v, list):
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                target[k].extend(v)
        elif isinstance(v, dict):
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                deepupdate(target[k], v)
        elif isinstance(v, set):
            if k not in target:
                target[k] = v.copy()
            else:
                target[k].update(v.copy())
        else:
            target[k] = copy.copy(v)


def ordered_dict_2_dict(input_ordered_dict):
    return json.loads(json.dumps(input_ordered_dict))


def get_cached_result(request, attr, queryset):
    if hasattr(request, attr):
        value = getattr(request, attr)
    else:
        value = queryset
        setattr(request, attr, queryset)
    return value


class AvoidResubmit:
    class ResubmittedError(exceptions.ErrorResultException):
        default_message = "resubmitted"

    def __init__(self, name, timeout=300):
        self.name = name
        self.prefix = "ar"
        self.con = get_redis_connection()
        self.timeout = timeout

    def gen_key(self, request_id, uid):
        return f"{self.prefix}:{self.name}:{uid}:{request_id}"

    def __call__(self, request_id, uid):
        key = self.gen_key(request_id, uid)
        if self.con.get(key):
            raise self.ResubmittedError

        self.con.setex(key, 1, self.timeout)
