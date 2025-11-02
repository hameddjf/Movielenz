"""
Custom pagination classes for API responses.
Provides flexible pagination options for different use cases.
"""
from rest_framework.pagination import (
    PageNumberPagination, LimitOffsetPagination, CursorPagination
)
from rest_framework.response import Response
from collections import OrderedDict


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination with page number.
    Default page size: 20
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Return paginated response with metadata.
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('results', data)
        ]))


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for large datasets.
    Default page size: 50
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    
    def get_paginated_response(self, data):
        """
        Return paginated response with metadata.
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.page_size),
            ('results', data)
        ]))


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for small datasets or mobile.
    Default page size: 10
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class WatchlistPagination(PageNumberPagination):
    """
    Pagination for user watchlist.
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100


class RecentlyWatchedPagination(CursorPagination):
    """
    Cursor-based pagination for recently watched items.
    Efficient for time-ordered data.
    """
    page_size = 20
    ordering = '-watched_at'
    cursor_query_param = 'cursor'


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """
    Limit/offset pagination with custom defaults.
    """
    default_limit = 20
    max_limit = 100
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    
    def get_paginated_response(self, data):
        """
        Return paginated response with metadata.
        """
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('limit', self.limit),
            ('offset', self.offset),
            ('results', data)
        ]))


class InfinitePagination(CursorPagination):
    """
    Cursor pagination for infinite scroll.
    No page numbers, just next/previous cursors.
    """
    page_size = 25
    ordering = '-id'
    cursor_query_param = 'cursor'