import time
import random
import logging

from django.conf import settings
from django.contrib.auth.models import User

from common import exceptions
from common.phone import parse_phone
from sms_service import send_verify_code

logger = logging.getLogger(__name__)


def has_verified_phone(request, phone):
    if not phone and hasattr(request, "user"):
        # NOTE: Assume phone is the same as username.
        phone = request.user.username

    vp = request.session.get("verified_phone", None)
    if (
        not vp
        or type(vp) != dict
        or time.time() > vp["expired_at"]
        or vp["phone"] != phone
    ):
        raise exceptions.NeedVerifyPhone


SMS_EXPIRATION = 5 * 60
MAX_RETRY_VERIFY = 5


def get_random_code():
    if settings.DEBUG:
        return "123456"
    return "".join(["%s" % random.randint(0, 9) for num in range(0, 6)])


def request_verify_code(request, phone):
    code = get_random_code()

    phone = parse_phone(phone)

    send_verify_code(request, phone, code)
    request.session["verify_code"] = {
        "phone": phone,
        "code": code,
        "retry": 0,
        "expired_at": time.time() + SMS_EXPIRATION,
    }


def verify_code(request, phone, code):
    session = request.session
    vc = session.get("verify_code", None)

    phone = parse_phone(phone)

    if not vc or phone != vc.get("phone", None):
        raise exceptions.WrongVerifyCode

    retry = vc.get("retry", 0)
    vc["retry"] = retry + 1

    if retry > MAX_RETRY_VERIFY:
        raise exceptions.WrongVerifyCode("too_much_retry")

    if (
        vc.get("code", None) != code
        or not vc.get("expired_at", None)
        or vc.get("used", False)
        or time.time() > vc.get("expired_at", 0)
    ):
        raise exceptions.WrongVerifyCode

    vc["used"] = True
    session["verified_phone"] = {
        "phone": phone,
        "expired_at": time.time() + SMS_EXPIRATION,
    }


class ShopUserAuthBackend:
    def authenticate(self, request, username=None, **kw):
        # has_verified_phone(request, phone=username)

        try:
            user = User.objects.get(username=username)
            if hasattr(user, "shop_user"):
                return user
        except User.DoesNotExist:
            pass

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get_by_natural_key(user_id)
        except User.DoesNotExist:
            return None
