from django.contrib import admin
from user_center.models import ShopUser


@admin.register(ShopUser)
class ShopUserAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "created_at")
    search_fields = ["phone", "user__username"]
