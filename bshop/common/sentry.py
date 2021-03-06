import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from common.exceptions import GQLError

IGNORE_STRS = (
    "Signature has expired\n",
    "Invalid refresh token\n",
    "You do not have permission to perform this action\n",
    "wrong_verification_code\n",
)


def ignore_exceptions(event, hint):
    from jwt.exceptions import ExpiredSignatureError
    from graphql_jwt.exceptions import JSONWebTokenError

    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, (GQLError, JSONWebTokenError, ExpiredSignatureError)):
            return None

    # ignore auth failed for sentry
    if "log_record" in hint:
        msg = hint["log_record"].msg

        for ignore_str in IGNORE_STRS:
            if msg.endswith(ignore_str):
                return None

    return event


def sentry_init(dsn, env):
    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        attach_stacktrace=True,
        # debug=True,
        before_send=ignore_exceptions,
        environment=env,
    )
