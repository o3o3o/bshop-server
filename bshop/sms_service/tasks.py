from bshop.celery import app
from smsish.sms import send_sms
from django.conf import settings

VALID_FROM_NUMBER = settings.TWILIO_MAGIC_FROM_NUMBER


@app.task
def async_send_single_msg(phone, message):
    send_sms(message, VALID_FROM_NUMBER, (phone,))
