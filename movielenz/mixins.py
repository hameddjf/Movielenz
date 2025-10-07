# core/mixins.py

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from .models import Movie, Type

class MovieAPIMixin:
    """
    یک Mixin برای ViewSetهای فیلم و سریال که شامل منطق مشترک است.
    این Mixin شامل موارد زیر است:
    - queryset پایه با prefetch برای بهینه‌سازی کوئری‌ها.
    - تنظیمات کامل فیلتر، جستجو و مرتب‌سازی.
    """
    # queryset پایه که شامل prefetch و select_related برای بهینه‌سازی است.
    queryset = Movie.objects.all().prefetch_related(
        'genres', 'actors', 'directors',
        Prefetch('type', queryset=Type.objects.all())
    ).select_related('type').order_by('-created_at')

    # فعال‌سازی بک‌اند‌های فیلتر، جستجو و مرتب‌سازی
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # تعریف فیلدهایی که می‌توان بر اساس آن‌ها محتوا را فیلتر کرد
    filterset_fields = {
        'release_date': ['exact', 'year', 'year__gte', 'year__lte'],
        'type__slug': ['exact', 'in'],  # فیلتر بر اساس اسلاگ نوع (movie, series)
        'status': ['exact'],            # فیلتر بر اساس وضعیت (منتشر شده/پیش‌نویس)
        'is_dubbed': ['exact'],
        'is_subtitled': ['exact'],
        'genres__slug': ['exact', 'in'], # فیلتر بر اساس اسلاگ ژانر
        'imdb_rating': ['gte', 'lte'],
    }
    
    # تعریف فیلدهایی که در جستجوی متنی استفاده می‌شوند
    search_fields = ['title', 'description', 'actors__name', 'directors__name']
    
    # تعریف فیلدهایی که می‌توان بر اساس آن‌ها نتایج را مرتب کرد
    ordering_fields = ['title', 'release_date', 'imdb_rating', 'created_at', 'tmdb_popularity']
    
    # مرتب‌سازی پیش‌فرض
    ordering = ['-release_date', 'title']

    def get_queryset(self):
        """
        کوئری‌ست را بر اساس دسترسی کاربر (ادمین یا عادی) فیلتر می‌کند.
        کاربران عادی فقط محتوای منتشر شده (status=True) را می‌بینند،
        در حالی که ادمین‌ها به همه موارد دسترسی دارند.
        """
        qs = super().get_queryset()
        
        # اگر کاربر لاگین کرده، ادمین (is_staff) نباشد، فقط موارد منتشر شده را نشان بده
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            qs = qs.filter(status=True)
            
        return qs.distinct()