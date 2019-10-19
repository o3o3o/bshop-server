from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.hashers import make_password, check_password

from provider import get_provider_cls
from common.base_models import BaseModel, ModelWithExtraInfo
from common import exceptions


class ShopUserManager(models.Manager):
    @transaction.atomic
    def create_user(self, phone):
        user = User.objects.create_user(username=phone)
        shop_user = self.create(phone=phone, user=user)
        return shop_user

    def get_user_by_auth_code(self, provider, auth_code):
        cls = get_provider_cls(provider)
        obj = cls()
        openid = obj.get_openid(auth_code)
        kw = {obj.field: openid}
        shop_user = self.get(**kw)
        return shop_user

    def get_user_by_openid(self, provider, openid):
        cls = get_provider_cls(provider)
        obj = cls()
        kw = {obj.field: openid}
        shop_user = self.get(**kw)
        return shop_user


class ShopUser(BaseModel, ModelWithExtraInfo):

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="shop_user"
    )
    phone = models.CharField(max_length=32, null=True, blank=True)
    nickname = models.CharField(max_length=128, null=True, blank=True, unique=True)
    avatar_url = models.CharField(max_length=512, null=True, blank=True)
    wechat_id = models.CharField(max_length=512, null=True, blank=True, unique=True)
    alipay_id = models.CharField(max_length=512, null=True, blank=True, unique=True)
    vendor_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Vendor Name"),
    )
    is_vendor = models.BooleanField(default=False, verbose_name=_("Is vendor"))

    # TODO: use secret + sixdigit to encrypt the raw password
    payment_password = models.CharField(
        max_length=1024, null=True, blank=True, verbose_name=_("Payment password")
    )

    objects = ShopUserManager()

    def __str__(self):
        return f"Id:{self.id}, Username:{self.user.username}, Phone:{self.phone}"

    @property
    def username(self):
        return self.user.username

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def first_name(self):
        return self.user.first_name

    # @property
    # def nickname(self):
    #    return self._nickname

    # @nickname.setter
    # def nickname(self, value):
    #    self._nickname = value
    #    self.save(update_fields=["_nickname"])

    @property
    def avatar(self):
        return self.avatar_url

    @avatar.setter
    def avatar(self, value):
        self.avatar_url = value
        self.save(update_fields=["avatar_url"])

    @property
    def has_payment_password(self):
        return bool(self.payment_password)

    def set_payment_password(self, password):
        self.payment_password = make_password(password)
        self.save(update_fields=["payment_password"])

    def check_payemnt_password(self, password):
        res = check_password(password, self.payment_password)
        if res is False:
            key = "payment_password_retries"
            cnt = self.extra_info.get(key, 0)
            cnt += 1
            self.extra_info[key] = cnt
            self.save(update_fields=["extra_info"])

        return res

    def bind_third_account(self, provider, auth_code):

        cls = get_provider_cls(provider)
        obj = cls()
        openid = obj.get_openid(auth_code)

        val = getattr(self, obj.field)
        if val and val != openid:
            raise exceptions.AlreadyBinded
        else:
            setattr(self, obj.field, openid)
            self.save(update_fields=[obj.field])
