
from rest_framework import permissions
from rest_framework.permissions import BasePermission

from user_account.enums import UserRole 

class IsAdminOrAuthor(permissions.BasePermission):
    """
    - ادمین (is_staff) دسترسی کامل دارد.
    - نویسنده فقط می‌تواند مقالات خودش را ویرایش یا حذف کند (تا زمانی که پیش‌نویس هستند).
    - همه کاربران احراز هویت شده می‌توانند مقاله جدید ایجاد کنند.
    """
    def has_object_permission(self, request, view, obj):
        # ادمین‌ها به همه چیز دسترسی دارند
        if request.user.is_staff:
            return True
        
        if obj.author == request.user and obj.status == 'draft':
            return request.method in ['GET', 'PUT', 'PATCH', 'DELETE']
            
        return obj.author == request.user and request.method in permissions.SAFE_METHODS
      

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    کلاس دسترسی سفارشی که اجازه می‌دهد:
    - ادمین (ADMIN) و مالک (OWNER) به همه اطلاعات دسترسی داشته باشند.
    - سایر کاربران فقط به اطلاعات خودشان دسترسی داشته باشند.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        این متد دسترسی به یک آبجکت خاص (یک کاربر خاص) را کنترل می‌کند.
        """
        if request.user.role in [UserRole.ADMIN, UserRole.OWNER]:
            return True
        
        return obj == request.user
    
class IsAdminOrOwner(BasePermission):
    """
    سطح دسترسی سفارشی که فقط به کاربران با نقش ADMIN یا OWNER اجازه دسترسی می‌دهد.
    """
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        # کاربر باید احراز هویت شده باشد
        if not request.user or not request.user.is_authenticated:
            return False
        
        # نقش کاربر باید ADMIN یا OWNER باشد
        return request.user.role in [UserRole.ADMIN, UserRole.OWNER]