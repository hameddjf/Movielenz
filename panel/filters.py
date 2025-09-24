# admin_panel/filters.py

import django_filters
from django.utils.translation import gettext_lazy as _

from user_account.models import User
from user_account.enums import SubscriptionStatus , UserRole


class UserFilter(django_filters.FilterSet):
    """
    کلاس فیلتر برای مدل User در پنل ادمین.
    """
    # فیلتر برای وضعیت اشتراک: 'true' برای دارای اشتراک، 'false' برای بدون اشتراک
    subscription_status = django_filters.ChoiceFilter(
        choices=SubscriptionStatus.choices,
        method='filter_by_subscription_status',
        label=_('وضعیت اشتراک')
    )

    class Meta:
        model = User
        fields = {
            'role': ['exact'], 
            'activated': ['exact'],
        }

    def filter_by_subscription_status(self, queryset, name, value):
        """
        متد سفارشی برای فیلتر کردن بر اساس وضعیت اشتراک.
        value: مقدار انتخاب شده از بین choices (مثلا 'free', 'premium' و ...)
        """
        if value:
            return queryset.filter(subscription_status=value)
        return queryset