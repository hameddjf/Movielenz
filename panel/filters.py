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
      
      
# blog

import django_filters
from blog.models import Article # مدل از اپ blog وارد می‌شود

class ArticlePanelFilter(django_filters.FilterSet):
    """
    فیلترهای پیشرفته برای پنل مدیریت مقالات.
    """
    # فیلتر بر اساس تاریخ شروع و پایان انتشار
    published_after = django_filters.DateFilter(field_name='published_at', lookup_expr='gte')
    published_before = django_filters.DateFilter(field_name='published_at', lookup_expr='lte')

    class Meta:
        model = Article
        fields = {
            'status': ['exact'],      # مثال: /articles/?status=draft
            'author': ['exact'], # مثال: /articles/?authorusername=admin
        }
        
# MOVIE

class ContentFilterSet(django_filters.FilterSet):
    """
    فیلترستی قابل استفاده مجدد برای مدل‌های Movie و Series.
    این فیلترست می‌تواند در پنل ادمین و صفحات عمومی سایت استفاده شود.
    """
    # فیلتر بر اساس بخشی از عنوان (case-insensitive)
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')
    
    # مثال: /api/movies/?production_year__gt=2020 (بزرگتر از)
    production_year = django_filters.NumberFilter(field_name='production_year')
    production_year__gt = django_filters.NumberFilter(field_name='production_year', lookup_expr='gt')
    production_year__lt = django_filters.NumberFilter(field_name='production_year', lookup_expr='lt')

    # فیلتر بر اساس ژانر (بر اساس نام ژانر)
    genre = django_filters.CharFilter(field_name='genres__name', lookup_expr='iexact')

    class Meta:
        fields = ['title', 'production_year', 'status', 'genre']