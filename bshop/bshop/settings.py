"""
Django settings for bshop project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import sys
import environ

env = environ.Env()

## reading .env file
environ.Env.read_env()

RUN_IN_DOCKER = env.bool("RUN_IN_DOCKER", default=False)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SENTRY_DSN = env("SENTRY_DSN", default=False)
if SENTRY_DSN:
    from common.sentry import sentry_init

    sentry_init(SENTRY_DSN, env("ENVIRONMENT", default="dev"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="#5!23i=@=21j(7uytn&z07e$z--h@@m8ws*(ioyjz8_rgtfv3#"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "django_nose",
    "graphene_django",
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    "wechat_django",
    "wechat_django.pay",
    "ratelimit",
    "smsish",
    "common",
    "user_center",
    "wallet",
    "sms_service",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "bshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "bshop.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
if RUN_IN_DOCKER:
    DB_HOST = env("DB_HOST", default="db")
else:
    DB_HOST = "localhost"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="bshopdb"),
        "USER": env("DB_USER", default="bshop"),
        "PASSWORD": env("DB_PASS", default="password"),
        "HOST": DB_HOST,
        "PORT": "5432",
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(name)s [%(levelname)s] %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": sys.stdout,
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "factory": {"level": "ERROR"},
        "faker": {"level": "ERROR"},
        # "wechat.api": {"level": "DEBUG", "handlers": ["console"]},
        # "wechat.handler": {"level": "DEBUG", "handlers": ["console"]},
        # "wechat.oauth": {"level": "WARNING", "handlers": ["console"]},
    },
}

# Avoid to be guessed the admin url by pentester
SUB_ADMIN_URL = env("SUB_ADMIN_URL", default="")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
STATIC_URL = "/static/"
if RUN_IN_DOCKER:
    REDIS_HOST = os.environ["REDIS_HOST"] if "REDIS_HOST" in os.environ else "redis"
    STATIC_ROOT = "/data/static"
else:
    REDIS_HOST = "localhost"
    STATIC_ROOT = os.path.join(BASE_DIR, "static")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    "ratelimit": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/2",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    "wechat": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/3",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
}
# The name of the cache (from the CACHES dict) to use for django-ratelimit
RATELIMIT_USE_CACHE = "ratelimit"

# CELERY STUFF
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:6379/4"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:6379/4"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Graphql Settings

SHOW_GRAPHQL_DOC = env.bool("SHOW_GRAPHQL_DOC", default=False)

if env.bool("HIDE_GQL_SCHEMA", default=True):
    ProdGQLMiddleware = ["gql.middleware.HideIntrospectMiddleware"]
else:
    ProdGQLMiddleware = []

if env.bool("DEBUG_GQL", default=False):
    DebugGQLMiddleware = ["graphene_django.debug.DjangoDebugMiddleware"]
else:
    DebugGQLMiddleware = []

GRAPHENE = {
    "SCHEMA": "gql.schema.schema",
    "MIDDLEWARE": ["graphql_jwt.middleware.JSONWebTokenMiddleware"]
    + ProdGQLMiddleware
    + DebugGQLMiddleware,
}

GRAPHQL_JWT = {
    # "JWT_VERIFY_EXPIRATION": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_REFRESH_EXPIRED_HANDLER": lambda orig_iat, context: False,
    "JWT_AUTH_TOKEN_WITH_PASSWORD": False,
}

AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    # "user_center.auth.ShopUserAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Test settings
TEST_RUNNER = "django_nose.NoseTestSuiteRunner"

if not env.bool("DISABLE_COVERAGE", default=False):
    NOSE_ARGS = [
        "--with-coverage",
        "--cover-package=gql,wallet,user_center",
        "--cover-min-percentage=60",
    ]

# SMS settings
SMS_BACKEND_CONSOLE = "smsish.sms.backends.console.SMSBackend"
SMS_BACKEND_DUMMY = "smsish.sms.backends.dummy.SMSBackend"
SMS_BACKEND_TWILIO = "smsish.sms.backends.twilio.SMSBackend"
SMS_BACKEND_YUNPIAN = "smsish.sms.backends.yunpian.SMSBackend"

TEST_SMS_ALL = env.bool("TEST_SMS_ALL", default=False)
ENABLE_SMS = env.bool("ENABLE_SMS", default=False)

if ENABLE_SMS:
    SMS_BACKEND = SMS_BACKEND_YUNPIAN
else:
    SMS_BACKEND = SMS_BACKEND_CONSOLE

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_MAGIC_FROM_NUMBER = "+15005550006"  # This number passes all validation.
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default=TWILIO_MAGIC_FROM_NUMBER)


YUNPIAN_API_KEY = env("YUNPIAN_API_KEY", default="")


# Wechat settings

# WECHAT_APP_ID = env("WECHAT_APP_ID", default="")
# WECHAT_APP_SECRET = env("WECHAT_APP_SECRET", default="")

WECHAT_SITE_HOST = env("WECHAT_SITE_HOST", default=None)
WECHAT_PATCHADMINSITE = False
# WECHAT_SESSIONSTORAGE = CACHES["wechat"]["BACKEND"]

# Debug Request
DEBUG_REQUEST = env.bool("DEBUG_REQUEST", default=False)
if DEBUG_REQUEST:
    import requests  # noqa
    import logging
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


# TODO: local settings for for dev
try:
    from .local_settings import *  # noqa F401
except ImportError as e:
    print(e)
    pass
