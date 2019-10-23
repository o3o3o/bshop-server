from django.contrib import admin
from wallet.models import Fund, HoldFund


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("id", "shop_user", "currency", "cash")
    search_fields = ["shop_user__phone", "shop_user__user__username"]


@admin.register(HoldFund)
class HoldFundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "fund",
        "amount",
        "expired_at",
        "order_id",
        "created_at",
        "updated_at",
    )
    search_fields = ["fund__shop_user__phone", "fund__shop_user__user__username"]
