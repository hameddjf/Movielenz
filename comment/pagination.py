"""
Custom pagination classes for the comment application.

This module provides pagination classes for controlling the number
of results returned in API responses.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class CommentPagination(PageNumberPagination):
    """
    Custom pagination class for comment listings.
    
    This pagination class provides:
    - Default page size
    - Customizable page size via query parameter
    - Maximum page size limit
    - Enhanced response format with metadata
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = MAX_PAGE_SIZE
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Return a paginated response with additional metadata.
        
        Args:
            data: The serialized page data.
            
        Returns:
            Response: DRF Response object with pagination metadata.
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'results': data
        })