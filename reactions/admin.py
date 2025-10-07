"""
Django admin configuration for Reaction model.
"""
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q

from .models import Reaction


class ReactionValueFilter(admin.SimpleListFilter):
    """Custom filter for reaction values."""
    
    title = 'reaction type'
    parameter_name = 'value'

    def lookups(self, request, model_admin):
        """Return filter options."""
        return Reaction.ReactionValue.choices

    def queryset(self, request, queryset):
        """Filter queryset based on selection."""
        if self.value():
            return queryset.filter(value=self.value())
        return queryset


class ContentTypeFilter(admin.SimpleListFilter):
    """Custom filter for content types."""
    
    title = 'content type'
    parameter_name = 'content_type'

    def lookups(self, request, model_admin):
        """Return filter options based on existing content types."""
        content_types = ContentType.objects.filter(
            id__in=Reaction.objects.values_list(
                'content_type', flat=True
            ).distinct()
        )
        return [(ct.id, ct.name) for ct in content_types]

    def queryset(self, request, queryset):
        """Filter queryset based on selection."""
        if self.value():
            return queryset.filter(content_type_id=self.value())
        return queryset


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    """
    Admin interface for Reaction model.
    
    Features:
    - List display with key fields
    - Filtering by user, content type, value, and dates
    - Search by username and object ID
    - Readonly fields for timestamps and ID
    - Custom actions for bulk operations
    - Statistics display
    """
    
    list_display = [
        'id_short',
        'user_link',
        'content_type',
        'object_id_short',
        'value_badge',
        'created_at',
    ]
    
    list_filter = [
        ReactionValueFilter,
        ContentTypeFilter,
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'object_id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'content_object_link',
    ]
    
    fieldsets = (
        ('Reaction Information', {
            'fields': ('id', 'user', 'value')
        }),
        ('Content Object', {
            'fields': ('content_type', 'object_id', 'content_object_link')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    actions = [
        'convert_to_like',
        'convert_to_dislike',
    ]

    def id_short(self, obj):
        """Display shortened UUID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'

    def user_link(self, obj):
        """Display clickable link to user."""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def object_id_short(self, obj):
        """Display shortened object ID."""
        if len(str(obj.object_id)) > 12:
            return str(obj.object_id)[:12] + '...'
        return obj.object_id
    object_id_short.short_description = 'Object ID'

    def value_badge(self, obj):
        """Display reaction value as colored badge."""
        color = '#28a745' if obj.is_like else '#dc3545'
        icon = '👍' if obj.is_like else '👎'
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_value_display()
        )
    value_badge.short_description = 'Value'
    value_badge.admin_order_field = 'value'

    def content_object_link(self, obj):
        """Display link to content object if possible."""
        try:
            ct = obj.content_type
            url = reverse(
                f'admin:{ct.app_label}_{ct.model}_change',
                args=[obj.object_id]
            )
            return format_html(
                '<a href="{}">{} - {}</a>',
                url, ct.model, obj.object_id
            )
        except:
            return f'{obj.content_type.model} - {obj.object_id}'
    content_object_link.short_description = 'Content Object'

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'content_type')

    @admin.action(description='Convert selected to Like')
    def convert_to_like(self, request, queryset):
        """Bulk action to convert reactions to likes."""
        updated = queryset.update(value=Reaction.ReactionValue.LIKE)
        self.message_user(
            request,
            f'{updated} reaction(s) converted to Like.'
        )

    @admin.action(description='Convert selected to Dislike')
    def convert_to_dislike(self, request, queryset):
        """Bulk action to convert reactions to dislikes."""
        updated = queryset.update(value=Reaction.ReactionValue.DISLIKE)
        self.message_user(
            request,
            f'{updated} reaction(s) converted to Dislike.'
        )

    def changelist_view(self, request, extra_context=None):
        """Add statistics to changelist view."""
        extra_context = extra_context or {}
        
        # Get statistics
        stats = Reaction.objects.aggregate(
            total=Count('id'),
            likes=Count('id', filter=Q(value='like')),
            dislikes=Count('id', filter=Q(value='dislike'))
        )
        
        stats['popularity'] = Reaction.objects.popularity_ratio()
        extra_context['stats'] = stats
        
        return super().changelist_view(request, extra_context)