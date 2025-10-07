"""
API views for the comment application.

This module provides ViewSets for handling CRUD operations on comments
with filtering, searching, ordering, and pagination capabilities.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Comment
from .serializers import (
    CommentSerializer,
    CreateCommentSerializer,
    UpdateCommentSerializer,
    CommentListSerializer
)
from .permissions import IsOwnerOrAdminOrReadOnly
from .filters import CommentFilter
from .pagination import CommentPagination


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments.
    
    This ViewSet provides CRUD operations for comments with the following features:
    - List all comments with filtering, searching, and ordering
    - Retrieve individual comments with nested replies
    - Create new comments (authenticated and anonymous users)
    - Update comments (only owner or admin)
    - Delete comments (only owner or admin)
    - Custom actions for specific queries
    
    Endpoints:
        GET /comments/ - List all comments
        POST /comments/ - Create a new comment
        GET /comments/{id}/ - Retrieve a specific comment
        PUT /comments/{id}/ - Update a comment (owner/admin only)
        PATCH /comments/{id}/ - Partially update a comment (owner/admin only)
        DELETE /comments/{id}/ - Delete a comment (owner/admin only)
        GET /comments/root/ - List only root comments
        GET /comments/{id}/replies/ - Get all replies for a comment
    """

    queryset = Comment.objects.all().select_related('author').prefetch_related('children')
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    pagination_class = CommentPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = CommentFilter
    search_fields = ['text', 'author__username', 'author__email', 'display_name']
    ordering_fields = ['created_at', 'updated_at', 'level']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """
        Return appropriate serializer class based on action.
        
        Returns:
            Serializer class: The serializer class to use for this action.
        """
        if self.action == 'create':
            return CreateCommentSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateCommentSerializer
        elif self.action == 'list':
            return CommentListSerializer
        return CommentSerializer

    def get_queryset(self):
        """
        Get the queryset for this view.
        
        Filters active comments for non-staff users.
        
        Returns:
            QuerySet: Filtered queryset.
        """
        queryset = super().get_queryset()
        
        user = self.request.user
        if not user.is_authenticated or not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset

    def perform_create(self, serializer):
        """
        Perform comment creation.
        
        Sets the author to the current user if authenticated, otherwise leaves it as None.
        
        Args:
            serializer: The serializer instance.
        """
        # Automatically set author from authenticated user
        if self.request.user.is_authenticated:
            serializer.save(author=self.request.user)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Create a new comment.
        
        Args:
            request: The HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Returns:
            Response: HTTP response with created comment data.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        output_serializer = CommentSerializer(serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """
        Update a comment.
        
        Args:
            request: The HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Returns:
            Response: HTTP response with updated comment data.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        output_serializer = CommentSerializer(serializer.instance)
        return Response(output_serializer.data)

    @action(detail=False, methods=['get'], url_path='root')
    def root_comments(self, request):
        """
        Get all root-level comments.
        
        Returns only comments without parents.
        
        Args:
            request: The HTTP request.
            
        Returns:
            Response: Paginated list of root comments.
        """
        queryset = self.filter_queryset(self.get_queryset().filter(parent__isnull=True))
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='replies')
    def get_replies(self, request, pk=None):
        """
        Get all replies for a specific comment.
        
        Args:
            request: The HTTP request.
            pk: Primary key of the parent comment.
            
        Returns:
            Response: List of reply comments.
        """
        comment = self.get_object()
        replies = comment.children.filter(is_active=True).select_related('author')
        serializer = CommentSerializer(replies, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """
        Deactivate a comment and all its descendants.
        
        Only available to comment owner or admin.
        
        Args:
            request: The HTTP request.
            pk: Primary key of the comment.
            
        Returns:
            Response: Success message.
        """
        comment = self.get_object()
        self.check_object_permissions(request, comment)
        
        comment.deactivate()
        
        return Response(
            {'message': 'Comment and all replies have been deactivated.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """
        Activate a comment.
        
        Only available to admin users.
        
        Args:
            request: The HTTP request.
            pk: Primary key of the comment.
            
        Returns:
            Response: Success message.
        """
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {'error': 'Only administrators can activate comments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment = self.get_object()
        comment.activate()
        
        return Response(
            {'message': 'Comment has been activated.'},
            status=status.HTTP_200_OK
        )
        
def list(self, request, *args, **kwargs):
    """
    List comments.
    
    By default, only returns root comments with their replies.
    Use ?show_all=true to show all comments in flat structure.
    
    Args:
        request: The HTTP request.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
        
    Returns:
        Response: Paginated list of comments.
    """
    queryset = self.filter_queryset(self.get_queryset())
    
    # By default, show only root comments in list view
    show_all = request.query_params.get('show_all', 'false').lower() == 'true'
    if not show_all:
        queryset = queryset.filter(parent__isnull=True)
    
    page = self.paginate_queryset(queryset)
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)