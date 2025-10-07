from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    اجازه دسترسی کامل به ادمین‌ها، و دسترسی فقط خواندنی به دیگران.
    """
    def has_permission(self, request, view):
        # اگر متد درخواست از نوع امن (GET, HEAD, OPTIONS) باشد، همه اجازه دارند.
        if request.method in permissions.SAFE_METHODS: 
            return True
        # در غیر این صورت، فقط کاربرانی که ادمین هستند (is_staff) اجازه دارند.
        return request.user and request.user.is_staff

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    اجازه ویرایش فقط به صاحب آبجکت. دیگران فقط دسترسی خواندنی دارند.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # این پرمیژن برای مدل‌هایی کاربرد دارد که فیلد user دارند.
        # در مدل Movie فعلی، این فیلد وجود ندارد.
        return obj.user == request.user