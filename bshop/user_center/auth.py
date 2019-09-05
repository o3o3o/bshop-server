from django.conf import settings
from django.contrib.auth.models import User


def verified_phone(request, phone):
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
        raise NeedVerifyPhone


class ShopUserAuthBackend:
    # TODO: require phone verify
    def authenticate(self, request, username=None, **kw):
        verified_phone(request, phone=username)

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
