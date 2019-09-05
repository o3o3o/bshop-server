import pytz
from django.utils.timezone import activate

from ipware import get_client_ip


def ParseRemoteAddrMiddleware(get_response):
    def middleware(request):
        request.META["REMOTE_ADDR"] = get_client_ip(request)[0]
        response = get_response(request)
        return response

    return middleware


class AdminTimezoneMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(self.process_request(request))
        return response

    @staticmethod
    def process_request(request):
        if request.path.startswith("/admin"):
            activate(pytz.timezone("Asia/Shanghai"))
        return request
