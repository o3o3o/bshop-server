import time
import logging
from django.conf import settings
from common import exceptions
from sms_service.tasks import async_send_single_msg

logger = logging.getLogger(__name__)

PREFIX = "【" + settings.LOGO_NAME + "】"

SESSION_CODE_TIMEOUT = getattr(settings, "SESSION_CODE_TIMEOUT", 60)


class InvalidSessionCode(Exception):
    pass


def validate_session_code(request, session_name, max_retries=3):
    current_time = time.time()
    retry_time = 0
    send_at = 0

    if session_name in request.session:
        if type(request.session[session_name]) == dict:
            retry_time = int(request.session[session_name].get("retry_time", "0"))
            send_at = request.session[session_name].get("send_at", current_time)

        if current_time - send_at < SESSION_CODE_TIMEOUT and retry_time > max_retries:
            return False
        if current_time - send_at >= SESSION_CODE_TIMEOUT:
            retry_time = 0

    request.session[session_name] = {
        "send_at": time.time(),
        "retry_time": retry_time + 1,
    }

    return True


def send_verify_code(request, phone, code):
    try:
        validate_session_code(request, "verify_code_last_send")
    except InvalidSessionCode:
        logger.warn(
            "send_code_log: send_verify_code send verify code still in 1 minutes"
        )
        raise exceptions.VerifyCodeError("request_too_frequent")

    message = PREFIX + f"您的验证码是{code}"
    if settings.SMS_BACKEND == settings.SMS_BACKEND_TWILIO:
        async_send_single_msg.delay(phone, message)
    else:
        async_send_single_msg.apply(args=[phone, message])
