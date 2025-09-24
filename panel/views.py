from django.shortcuts import render

# Create your views here.
# admin_panel/views.py

from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from user_account.models import User

from .serializers import UserAdminSerializer
from .filters import UserFilter

class UserAdminViewSet(viewsets.ModelViewSet):
    """
    یک ViewSet برای مشاهده، ایجاد، ویرایش و حذف کاربران توسط ادمین.
    
    - دسترسی فقط برای ادمین‌ها (`is_staff=True`).
    - قابلیت جستجو در ایمیل، نام کاربری و نام خانوادگی.
    - قابلیت فیلتر بر اساس نقش، وضعیت حساب و وضعیت اشتراک.
    - قابلیت مرتب‌سازی بر اساس تاریخ عضویت و ایمیل.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser] # فقط ادمین‌ها دسترسی دارند

    # فعال‌سازی بک‌اند‌های فیلتر، جستجو و مرتب‌سازی
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # کلاس فیلتر سفارشی که در گام قبل ساختیم
    filterset_class = UserFilter
    
    # فیلدهایی که می‌توان در آن‌ها جستجو کرد
    search_fields = ['email', 'username', 'first_name', 'last_name']
    
    # فیلدهایی که می‌توان بر اساس آن‌ها خروجی را مرتب کرد
    ordering_fields = ['date_joined', 'email', 'role']