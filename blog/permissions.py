from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    دسترسی سفارشی که فقط به نویسنده یک شی اجازه ویرایش آن را می‌دهد.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user