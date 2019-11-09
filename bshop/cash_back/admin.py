from django.contrib import admin
from cash_back.models import PayCashBack, DepositCashBack


@admin.register(PayCashBack)
class PayCashBackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "start_at",
        "end_at",
        "total_paied_amount",
        "cash_back_amount",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    ordering = ["-id"]
    list_editable = (
        "name",
        "start_at",
        "end_at",
        "total_paied_amount",
        "cash_back_amount",
        "is_active",
    )


@admin.register(DepositCashBack)
class DepositCashBackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "deposit_amount",
        "cash_back_amount",
        "cash_back_expired_day",
        "is_active",
        "created_at",
    )
    list_editable = (
        "deposit_amount",
        "cash_back_amount",
        "cash_back_expired_day",
        "is_active",
    )
