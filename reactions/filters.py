"""
Filters for Reaction model using django-filter.
"""
import django_filters
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

from .models import Reaction

User = get_user_model()


class ReactionFilter(django_filters.FilterSet):
    """
    FilterSet for Reaction model with comprehensive filtering options.
    
    This filter allows filtering reactions by:
    - User (exact match or username search)
    - Content type (by ID or model name)
    - Object ID
    - Reaction value (like/dislike)
    - Date ranges (created_at, updated_at)
    
    Example usage in API:
        /api/reactions/?user=123
        /api/reactions/?value=like
        /api/reactions/?content_type=article
        /api/reactions/?created_after=2025-01-01
        /api/reactions/?username=john
    """

    # User filters
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        field_name='user',
        label='User ID'
    )
    # username = django_filters.CharFilter(
    #     field_name='user__username',
    #     lookup_expr='icontains',
    #     label='Username contains'
    # )

    # Content type filters
    content_type = django_filters.ModelChoiceFilter(
        queryset=ContentType.objects.all(),
        field_name='content_type',
        label='Content Type ID'
    )
    content_type_model = django_filters.CharFilter(
        field_name='content_type__model',
        lookup_expr='iexact',
        label='Content Type Model'
    )

    # Object ID filter
    object_id = django_filters.CharFilter(
        field_name='object_id',
        lookup_expr='exact',
        label='Object ID'
    )

    # Reaction value filter
    value = django_filters.ChoiceFilter(
        choices=Reaction.ReactionValue.choices,
        field_name='value',
        label='Reaction Value'
    )

    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created after'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created before'
    )
    updated_after = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='gte',
        label='Updated after'
    )
    updated_before = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='lte',
        label='Updated before'
    )

    class Meta:
        model = Reaction
        fields = {
            'user': ['exact'],
            'content_type': ['exact'],
            'value': ['exact'],
            'created_at': ['gte', 'lte'],
            'updated_at': ['gte', 'lte'],
        }

    @property
    def qs(self):
        """
        Override queryset to optimize database queries.
        
        Returns:
            QuerySet: Optimized queryset with select_related.
        """
        parent = super().qs
        return parent.select_related('user', 'content_type')