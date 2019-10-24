from django.contrib import admin
from wallet.models import Fund, HoldFund, FundTransfer, FundAction


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


@admin.register(FundAction)
class FundActionAdmin(admin.ModelAdmin):
    list_display = ("fund", "transfer", "balance", "created_at", "updated_at")
    search_fields = ["fund__shop_user__phone", "fund__shop_user__user__username"]


@admin.register(FundTransfer)
class FundTransferAdmin(admin.ModelAdmin):
    list_display = (
        "from_fund",
        "to_fund",
        "amount",
        "status",
        "type",
        "note",
        "order_id",
        "created_at",
        "updated_at",
    )
    search_fields = [
        "from_fund__shop_user__phone",
        "from_fund__shop_user__user__username",
        "to_fund__shop_user__phone",
        "to_fund__shop_user__user__username",
    ]
