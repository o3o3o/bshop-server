from django.db.models import Q
from user_center.models import ShopUser


class MixinAdmin4ShopUserId(object):
    """
    Support search by phone, username, nickname for Interfield with `shop_user_id`

    NOTE: MixinAdmin4ShopUserId must be the front of admin.ModelAdmin
    """

    def shop_user(self, obj):
        """ `shop_user` must be in list_display """
        return ShopUser.objects.get(id=obj.shop_user_id)

    shop_user.short_description = "ShopUser"

    def get_search_results(self, request, queryset, search_term):
        """
           search_fields must be not empty.
        """
        use_distinct = False
        search_term = search_term.strip()
        shop_user_ids = ShopUser.objects.filter(
            Q(phone__icontains=search_term) | Q(_nickname__icontains=search_term)
        ).values_list("id", flat=True)

        if len(shop_user_ids) > 0:
            return queryset.filter(shop_user_id__in=shop_user_ids), use_distinct
        else:
            return queryset.none(), use_distinct
