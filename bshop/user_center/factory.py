import factory
from user_center.models import ShopUser
from django.contrib.auth.models import User


def fake_phone_number():
    from faker import Faker

    fake = Faker("zh-CN")
    return "+86" + fake.phone_number()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(fake_phone_number)
    password = "coin.pwd"


def lazy_vendor_name(o):
    if getattr(o, "is_vendor", False):
        return o.nickname
    else:
        return None


class ShopUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ShopUser

    user = factory.SubFactory(UserFactory)
    phone = factory.LazyAttribute(lambda o: o.user.username)
    nickname = factory.Faker("name")

    vendor_name = factory.LazyAttribute(lazy_vendor_name)
