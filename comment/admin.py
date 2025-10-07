"""
Django admin configuration for the comment application.

This module customizes the Django admin interface for managing comments
with advanced filtering, search, and display options.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from mptt.admin import MPTTModelAdmin

from .models import Comment


class CommentInlineAdmin(admin.TabularInline):
    """
    Inline admin for displaying child comments.
    
    Shows replies to a comment in the parent comment's admin page.
    """

    model = Comment
    fk_name = 'parent'
    extra = 0
    fields = ['author', 'display_name', 'text', 'is_active', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        """Disable adding comments through inline."""
        return False


@admin.register(Comment)
class CommentAdmin(MPTTModelAdmin):
    """
    Admin interface for Comment model.
    
    Provides comprehensive management interface with:
    - List display with key fields
    - Advanced filtering options
    - Search functionality
    - Bulk actions
    - Inline display of replies
    - Tree structure visualization using MPTT
    """

    list_display = [
        'id_short',
        'author_link',
        'content_preview',
        'content_object_link',
        'depth_display',
        'is_active_display',
        'has_spoiler',
        'reply_count_display',
        'created_at',
    ]

    list_filter = [
        'is_active',
        'has_spoiler',
        'created_at',
        'updated_at',
        'level',
        'content_type',
    ]

    search_fields = [
        'id',
        'text',
        'display_name',
        'author__username',
        'author__email',
        'author__first_name',
        'author__last_name',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'level',
        'lft',
        'rght',
        'tree_id',
        'reply_count_display',
        'content_object_link',
    ]

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'author', 'display_name', 'text', 'is_active', 'has_spoiler')
        }),
        (_('Content Object'), {
            'fields': ('content_type', 'object_id', 'content_object_link')
        }),
        (_('Tree Structure'), {
            'fields': ('parent', 'level', 'lft', 'rght', 'tree_id'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at', 'reply_count_display'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['activate_comments', 'deactivate_comments', 'delete_with_replies']
    inlines = [CommentInlineAdmin]

    mptt_level_indent = 20

    def id_short(self, obj):
        """Display shortened UUID."""
        return str(obj.id)[:8]
    id_short.short_description = _('ID')

    def author_link(self, obj):
        """Display clickable link to author's admin page."""
        if not obj.author:
            return format_html(
                '<em style="color: #666;">{}</em>',
                obj.display_name or 'Anonymous'
            )
        
        # ✅ اصلاح: استفاده از ContentType برای یافتن URL صحیح
        try:
            content_type = ContentType.objects.get_for_model(obj.author.__class__)
            url = reverse(
                f'admin:{content_type.app_label}_{content_type.model}_change',
                args=[obj.author.pk]
            )
            display_text = obj.author.username or obj.author.email
            return format_html('<a href="{}">{}</a>', url, display_text)
        except Exception:
            return format_html(
                '<span>{}</span>',
                obj.author.username or obj.author.email or 'User'
            )
    
    author_link.short_description = _('Author')

    def content_preview(self, obj):
        """Display truncated comment text."""
        max_length = 60
        if len(obj.text) > max_length:
            return f'{obj.text[:max_length]}...'
        return obj.text
    content_preview.short_description = _('Comment')

    def content_object_link(self, obj):
        """Display link to the content object if available."""
        if obj.content_object is None:
            return format_html('<em style="color: #999;">Object deleted</em>')
        
        try:
            content_type = obj.content_type
            app_label = content_type.app_label
            model_name = content_type.model
            url = reverse(
                f'admin:{app_label}_{model_name}_change',
                args=[obj.object_id]
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                str(obj.content_object)[:50]
            )
        except Exception:
            return format_html('<em style="color: #999;">Unavailable</em>')
    content_object_link.short_description = _('Content Object')

    def depth_display(self, obj):
        """Display comment depth/level in tree."""
        return f'Level {obj.level}'
    depth_display.short_description = _('Depth')

    def is_active_display(self, obj):
        """Display active status with icon."""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">●</span> Active'
            )
        return format_html(
            '<span style="color: red;">●</span> Inactive'
        )
    is_active_display.short_description = _('Status')
    is_active_display.admin_order_field = 'is_active'

    def reply_count_display(self, obj):
        """Display number of replies."""
        count = obj.children.count()
        if count == 0:
            return '0 replies'
        return format_html(
            '<strong>{}</strong> {}',
            count,
            'reply' if count == 1 else 'replies'
        )
    reply_count_display.short_description = _('Replies')

    def activate_comments(self, request, queryset):
        """Bulk action to activate selected comments."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _(f'{updated} comment(s) have been activated.')
        )
    activate_comments.short_description = _('Activate selected comments')

    def deactivate_comments(self, request, queryset):
        """Bulk action to deactivate selected comments and their descendants."""
        count = 0
        for comment in queryset:
            comment.deactivate()
            count += 1
        self.message_user(
            request,
            _(f'{count} comment(s) and their replies have been deactivated.')
        )
    deactivate_comments.short_description = _('Deactivate selected comments and replies')

    def delete_with_replies(self, request, queryset):
        """Bulk action to delete comments with their replies."""
        total_deleted = 0
        for comment in queryset:
            descendants_count = comment.get_descendant_count()
            comment.delete()
            total_deleted += descendants_count + 1
        
        self.message_user(
            request,
            _(f'{total_deleted} comment(s) including replies have been deleted.')
        )
    delete_with_replies.short_description = _('Delete selected comments with replies')

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('author', 'content_type', 'parent')