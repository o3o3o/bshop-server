from django.contrib import admin
from common.models import SystemQuota


@admin.register(SystemQuota)
class SystemQuotaAdmin(admin.ModelAdmin):
    list_display = ("name", "quota")
    search_fields = ["name"]
