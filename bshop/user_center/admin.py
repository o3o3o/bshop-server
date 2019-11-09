from django.contrib import admin
from user_center.models import ShopUser


@admin.register(ShopUser)
class ShopUserAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "is_vendor", "vendor_name", "created_at")
    search_fields = ["phone", "user__username", "vendor_name"]
    list_editable = ("is_vendor", "vendor_name")
