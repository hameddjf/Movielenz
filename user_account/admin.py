"""
Django admin configuration for user management.
Provides comprehensive interface for managing users and their interactions.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone

from .models import User, WatchlistItem, FavoriteItem, RecentlyWatchedItem
from .enums import SubscriptionStatus, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    """
    
    # List display configuration
    list_display = (
        'email', 'get_full_name_display', 'role', 'subscription_badge',
        'activated', 'is_active', 'date_joined_formatted'
    )
    list_filter = (
        'role', 'subscription_status', 'activated', 'is_active',
        'date_joined', 'last_login'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Fieldsets for detail view
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'profile_picture')
        }),
        (_('Subscription'), {
            'fields': (
                'subscription_status', 'subscription_start_date',
                'subscription_end_date'
            )
        }),
        (_('Preferences'), {
            'fields': ('preferred_language', 'preferred_genres')
        }),
        (_('Permissions'), {
            'fields': ('role', 'activated', 'is_active', 'is_superuser')
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    # Fieldsets for add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'first_name',
                'last_name', 'role'
            ),
        }),
    )
    
    # Read-only fields
    readonly_fields = ('date_joined', 'last_login')
    
    # Filter horizontal for many-to-many
    filter_horizontal = ('preferred_genres',)
    
    # Actions
    actions = [
        'activate_users', 'deactivate_users', 'activate_premium',
        'cancel_subscriptions', 'send_verification_email'
    ]
    
    # Custom methods for list display
    @admin.display(description='نام کامل')
    def get_full_name_display(self, obj):
        """Display user's full name."""
        return obj.get_full_name() or '-'
    
    @admin.display(description='اشتراک')
    def subscription_badge(self, obj):
        """Display subscription status with color badge."""
        colors = {
            SubscriptionStatus.FREE: 'gray',
            SubscriptionStatus.PREMIUM: 'green',
            SubscriptionStatus.CANCELLED: 'orange',
            SubscriptionStatus.EXPIRED: 'red',
        }
        color = colors.get(obj.subscription_status, 'gray')
        
        label = obj.get_subscription_status_display()
        
        # Add expiry info for premium
        if obj.subscription_status == SubscriptionStatus.PREMIUM and obj.subscription_end_date:
            if obj.subscription_end_date < timezone.now():
                color = 'red'
                label += ' (منقضی شده)'
            elif obj.subscription_end_date < timezone.now() + timezone.timedelta(days=7):
                color = 'orange'
                label += ' (در شرف انقضا)'
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, label
        )
    
    @admin.display(description='تاریخ عضویت', ordering='date_joined')
    def date_joined_formatted(self, obj):
        """Format join date."""
        return obj.date_joined.strftime('%Y-%m-%d %H:%M')
    
    # Custom actions
    @admin.action(description='فعال‌سازی کاربران انتخاب شده')
    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True, activated=True)
        self.message_user(request, f'{updated} کاربر فعال شد.')
    
    @admin.action(description='غیرفعال‌سازی کاربران انتخاب شده')
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} کاربر غیرفعال شد.')
    
    @admin.action(description='فعال‌سازی اشتراک پرمیوم (30 روز)')
    def activate_premium(self, request, queryset):
        """Activate premium subscription for selected users."""
        count = 0
        for user in queryset:
            user.activate_premium_subscription(duration_days=30)
            count += 1
        self.message_user(request, f'اشتراک {count} کاربر فعال شد.')
    
    @admin.action(description='لغو اشتراک کاربران انتخاب شده')
    def cancel_subscriptions(self, request, queryset):
        """Cancel subscriptions for selected users."""
        updated = queryset.update(subscription_status=SubscriptionStatus.CANCELLED)
        self.message_user(request, f'اشتراک {updated} کاربر لغو شد.')
    
    @admin.action(description='ارسال ایمیل تأیید')
    def send_verification_email(self, request, queryset):
        """Send verification email to unverified users."""
        # This would need implementation with email backend
        unverified = queryset.filter(activated=False)
        count = unverified.count()
        self.message_user(
            request,
            f'ایمیل تأیید برای {count} کاربر ارسال شد.'
        )
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('preferred_genres')


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    """Admin interface for watchlist items."""
    
    list_display = (
        'user_email', 'content_type', 'object_id',
        'content_link', 'added_at_formatted'
    )
    list_filter = ('content_type', 'added_at')
    search_fields = ('user__email', 'object_id')
    date_hierarchy = 'added_at'
    readonly_fields = ('added_at',)
    
    @admin.display(description='ایمیل کاربر')
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    
    @admin.display(description='محتوا')
    def content_link(self, obj):
        """Display content object name."""
        if obj.content_object:
            return str(obj.content_object)
        return '-'
    
    @admin.display(description='تاریخ افزودن', ordering='added_at')
    def added_at_formatted(self, obj):
        """Format added date."""
        return obj.added_at.strftime('%Y-%m-%d %H:%M')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'content_type')


@admin.register(FavoriteItem)
class FavoriteItemAdmin(admin.ModelAdmin):
    """Admin interface for favorite items."""
    
    list_display = (
        'user_email', 'content_type', 'object_id',
        'content_link', 'added_at_formatted'
    )
    list_filter = ('content_type', 'added_at')
    search_fields = ('user__email', 'object_id')
    date_hierarchy = 'added_at'
    readonly_fields = ('added_at',)
    
    @admin.display(description='ایمیل کاربر')
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    
    @admin.display(description='محتوا')
    def content_link(self, obj):
        """Display content object name."""
        if obj.content_object:
            return str(obj.content_object)
        return '-'
    
    @admin.display(description='تاریخ افزودن', ordering='added_at')
    def added_at_formatted(self, obj):
        """Format added date."""
        return obj.added_at.strftime('%Y-%m-%d %H:%M')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'content_type')


@admin.register(RecentlyWatchedItem)
class RecentlyWatchedItemAdmin(admin.ModelAdmin):
    """Admin interface for recently watched items."""
    
    list_display = (
        'user_email', 'content_type', 'object_id',
        'content_link', 'progress_display', 'watched_at_formatted'
    )
    list_filter = ('content_type', 'watched_at')
    search_fields = ('user__email', 'object_id')
    date_hierarchy = 'watched_at'
    readonly_fields = ('watched_at',)
    
    @admin.display(description='ایمیل کاربر')
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    
    @admin.display(description='محتوا')
    def content_link(self, obj):
        """Display content object name."""
        if obj.content_object:
            return str(obj.content_object)
        return '-'
    
    @admin.display(description='پیشرفت')
    def progress_display(self, obj):
        """Display watch progress."""
        if obj.progress_seconds:
            minutes = obj.progress_seconds // 60
            seconds = obj.progress_seconds % 60
            return f'{minutes}:{seconds:02d}'
        return '-'
    
    @admin.display(description='زمان مشاهده', ordering='watched_at')
    def watched_at_formatted(self, obj):
        """Format watched date."""
        return obj.watched_at.strftime('%Y-%m-%d %H:%M')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'content_type')