from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bshop.settings")
app = Celery("bshop")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#crontab-schedules
app.conf.beat_schedule = {
    "check_expired_holdfund": {
        "task": "wallet.tasks.check_expired_holdfund",
        "schedule": crontab(hour="16", minute="00"),  # utc+8 0:00
    }
}

app.conf.task_routes = {"wallet.tasks.*": {"queue": "wallet"}}
