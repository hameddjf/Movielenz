"""
Filter classes for the comment application.

This module provides filtering capabilities for comment querysets
using django-filter.
"""

from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model

from .models import Comment

User = get_user_model()


class CommentFilter(filters.FilterSet):
    """
    FilterSet for Comment model.
    
    Provides filtering options for:
    - Author (exact match and search)
    - Creation date (range filtering)
    - Active status
    - Content type and object ID
    - Parent comment
    """

    author = filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        field_name='author',
        label='Author'
    )

    author_username = filters.CharFilter(
        field_name='author__username',
        lookup_expr='icontains',
        label='Author Username'
    )

    created_after = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )

    created_before = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )

    is_active = filters.BooleanFilter(
        field_name='is_active',
        label='Is Active'
    )

    content_type = filters.NumberFilter(
        field_name='content_type',
        label='Content Type ID'
    )

    object_id = filters.NumberFilter(
        field_name='object_id',
        label='Object ID'
    )

    parent = filters.UUIDFilter(
        field_name='parent__id',
        label='Parent Comment ID'
    )

    is_root = filters.BooleanFilter(
        method='filter_is_root',
        label='Is Root Comment'
    )

    text = filters.CharFilter(
        field_name='text',
        lookup_expr='icontains',
        label='Search in Text'
    )

    class Meta:
        model = Comment
        fields = [
            'author',
            'author_username',
            'created_after',
            'created_before',
            'is_active',
            'content_type',
            'object_id',
            'parent',
            'is_root',
            'text'
        ]

    def filter_is_root(self, queryset, name, value):
        """
        Filter for root comments.
        
        Args:
            queryset: The initial queryset.
            name: The filter field name.
            value: The filter value (True/False).
            
        Returns:
            QuerySet: Filtered queryset.
        """
        if value:
            return queryset.filter(parent__isnull=True)
        return queryset.filter(parent__isnull=False)