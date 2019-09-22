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
from os import getenv

# import environ
# env = environ.Env(DEBUG=(bool, False))
## reading .env file
# environ.Env.read_env()

RUN_IN_DOCKER = getenv("IN_DOCKER") == "YES"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv(
    "DJANOG_SECRET_KEY", "#5!23i=@=21j(7uytn&z07e$z--h@@m8ws*(ioyjz8_rgtfv3#"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getenv("DJANGO_DEBUG", False)

ALLOWED_HOSTS = (
    getenv("ALLOWED_HOSTS", "localhost, 127.0.0.1").replace(" ", "").split(",")
)


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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
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
            "level": getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "factory": {"level": "ERROR"},
        "faker": {"level": "ERROR"},
    },
}

# Avoid to be guessed the admin url by pentester
SUB_ADMIN_URL = getenv("SUB_ADMIN_URL", "")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
STATIC_URL = "/static/"
if RUN_IN_DOCKER:
    REDIS_HOST = os.environ["REDIS_HOST"] if "REDIS_HOST" in os.environ else "redis"
    STATIC_ROOT = "/data/static"
else:
    REDIS_HOST = "localhost"
    STATIC_ROOT = os.path.join(BASE_DIR, "static")


# Graphql Settings

SHOW_GRAPHQL_DOC = getenv("SHOW_GRAPHQL_DOC", False)

if getenv("HIDE_GQL_SCHEMA") == "true":
    ProdGQLMiddleware = ["gql.middleware.HideIntrospectMiddleware"]
else:
    ProdGQLMiddleware = []

if getenv("DEBUG_GQL") == "true":
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
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
    "JWT_REFRESH_EXPIRED_HANDLER": lambda orig_iat, context: False,
    "JWT_AUTH_TOKEN_WITH_PASSWORD": False,
}

AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    "user_center.auth.ShopUserAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Test settings
TEST_RUNNER = "django_nose.NoseTestSuiteRunner"

if getenv("DISABLE_COVERAGE") != "true":
    NOSE_ARGS = [
        "--with-coverage",
        "--cover-package=gql,wallet,user_center",
        "--cover-min-percentage=60",
    ]

# SMS settings
SMS_BACKEND_CONSOLE = "smsish.sms.backends.console.SMSBackend"
SMS_BACKEND_DUMMY = "smsish.sms.backends.dummy.SMSBackend"
SMS_BACKEND_TWILIO = "smsish.sms.backends.twilio.SMSBackend"

ENABLE_SMS = getenv("ENABLE_SMS") == "true"

if ENABLE_SMS:
    SMS_BACKEND = SMS_BACKEND_TWILIO
else:
    SMS_BACKEND = SMS_BACKEND_CONSOLE

TWILIO_ACCOUNT_SID = getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = getenv("TWILIO_AUTH_TOKEN")
TWILIO_MAGIC_FROM_NUMBER = "+15005550006"  # This number passes all validation.
TWILIO_FROM_NUMBER = getenv("TWILIO_FROM_NUMBER", TWILIO_MAGIC_FROM_NUMBER)


# Wechat settings

WECHAT_APP_ID = getenv("WECHAT_APP_ID")
WECHAT_APP_SECRET = getenv("WECHAT_APP_SECRET")


# TODO: local settings for for dev
try:
    from .local_settings import *  # noqa F401
except ImportError as e:
    print(e)
    pass
