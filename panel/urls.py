# admin_panel/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserAdminViewSet

# یک روتر برای ثبت خودکار URLهای ViewSet ایجاد می‌کنیم
router = DefaultRouter()
router.register(r'users', UserAdminViewSet, basename='admin-user')

urlpatterns = [
    path('', include(router.urls)),
]