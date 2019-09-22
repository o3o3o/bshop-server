from django.db import models
from django.db import transaction
from django.contrib.auth.models import User

from common.base_models import BaseModel, ModelWithExtraInfo
from common import exceptions


class ShopUserManager(models.Manager):
    @transaction.atomic
    def create_user(self, phone):
        user = User.objects.create_user(username=phone)
        shop_user = self.create(phone=phone, user=user)
        return shop_user


class ShopUser(BaseModel, ModelWithExtraInfo):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="shop_user"
    )
    phone = models.CharField(max_length=32, null=True, blank=True)
    nickname = models.CharField(max_length=128, null=True, blank=True, unique=True)
    avatar_url = models.CharField(max_length=512, null=True, blank=True)
    wechat_id = models.CharField(max_length=512, null=True, blank=True)
    alipay_id = models.CharField(max_length=512, null=True, blank=True)

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

    def bind_openid(self, open_id, login_provider):
        from common.schema import LoginProvider

        bind_map = {
            LoginProvider.WECHAT: "wechat_id",
            LoginProvider.ALIPAY: "alipay_id",
        }
        if login_provider not in bind_map:
            raise exceptions.DoNotSupportBindType

        field = bind_map[login_provider]

        val = getattr(self, field)
        if val:
            if val != open_id:
                raise exceptions.AlreadyBinded
        else:
            setattr(self, field, open_id)
            self.update_fields([field])
