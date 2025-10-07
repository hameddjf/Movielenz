from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

from .permissions import IsAdminOrOwner

class AdminPanelViewSetMixin:
    """
    میکسینی که تنظیمات مشترک برای ViewSet های پنل ادمین را فراهم می‌کند.
    این میکسین سطح دسترسی، بک‌اند فیلترها و فیلدهای جستجو و مرتب‌سازی را تنظیم می‌کند.
    """
    permission_classes = [IsAdminOrOwner]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['title', 'description']
    
    ordering_fields = ['created_at', 'production_year', 'title']
    
    ordering = ['-created_at']