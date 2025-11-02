"""
Custom permissions for user access control.
Handles role-based, subscription-based, and object-level permissions.
"""
from rest_framework import permissions
from django.utils import timezone
from .enums import UserRole, SubscriptionStatus


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit.
    Read permissions are allowed to any authenticated user.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for owner
        return obj.user == request.user


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Permission to only allow users to edit their own profile.
    Admins can edit any profile.
    """
    
    message = 'شما فقط می‌توانید پروفایل خود را ویرایش کنید.'
    
    def has_object_permission(self, request, view, obj):
        # Check if user is admin/owner
        if request.user.role in UserRole.get_staff_roles():
            return True
        
        # Check if editing own profile
        return obj == request.user


class HasActivePremiumSubscription(permissions.BasePermission):
    """
    Permission for premium-only features.
    Allows access only to users with active premium subscription.
    """
    
    message = 'این قابلیت فقط برای کاربران پرمیوم در دسترس است.'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user has premium role or active subscription
        if request.user.role in UserRole.get_premium_roles():
            return True
        
        return request.user.has_active_premium_subscription()


class IsAdminOrOwner(permissions.BasePermission):
    """
    Permission for admin/owner only actions.
    """
    
    message = 'فقط مدیران سیستم به این بخش دسترسی دارند.'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.role in [UserRole.ADMIN, UserRole.OWNER]


class CanManageUsers(permissions.BasePermission):
    """
    Permission for user management operations.
    Only admins and owners can manage other users.
    """
    
    message = 'شما اجازه مدیریت کاربران را ندارید.'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.role in UserRole.get_staff_roles()
    
    def has_object_permission(self, request, view, obj):
        # Owners can manage anyone
        if request.user.role == UserRole.OWNER:
            return True
        
        # Admins cannot manage owners
        if request.user.role == UserRole.ADMIN:
            return obj.role != UserRole.OWNER
        
        return False


class IsEmailVerified(permissions.BasePermission):
    """
    Permission requiring verified email.
    Some actions need verified account.
    """
    
    message = 'لطفاً ابتدا ایمیل خود را تأیید کنید.'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.activated


class CanAccessOwnContent(permissions.BasePermission):
    """
    Permission for user's own content (watchlist, favorites, etc.).
    Users can only access their own lists.
    """
    
    message = 'شما فقط می‌توانید لیست‌های خود را مشاهده کنید.'
    
    def has_object_permission(self, request, view, obj):
        # Check if user owns this content
        return obj.user == request.user


class RateLimitExempt(permissions.BasePermission):
    """
    Exempts premium users from certain rate limits.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Premium users get exemption
        return request.user.has_active_premium_subscription()


class CanChangeSubscription(permissions.BasePermission):
    """
    Permission for subscription management.
    Users can manage own subscription, admins can manage any.
    """
    
    message = 'شما نمی‌توانید این اشتراک را مدیریت کنید.'
    
    def has_object_permission(self, request, view, obj):
        # Admins can manage any subscription
        if request.user.role in UserRole.get_staff_roles():
            return True
        
        # Users can manage own subscription
        return obj == request.user


class IsActiveUser(permissions.BasePermission):
    """
    Permission requiring active account.
    """
    
    message = 'حساب کاربری شما غیرفعال است.'
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.is_active


# Composite permissions for common use cases
class IsPremiumOrAdmin(permissions.BasePermission):
    """
    Allows access to premium users or admins.
    """
    
    def has_permission(self, request, view):
        premium_check = HasActivePremiumSubscription()
        admin_check = IsAdminOrOwner()
        
        return (
            premium_check.has_permission(request, view) or
            admin_check.has_permission(request, view)
        )


class IsVerifiedAndActive(permissions.BasePermission):
    """
    Requires both email verification and active account.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.activated and request.user.is_active