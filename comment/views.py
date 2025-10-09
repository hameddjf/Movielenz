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
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Comment
from .serializers import (
    CommentSerializer,
    CreateCommentSerializer,
    UpdateCommentSerializer,
    CommentListSerializer,
    BulkActionSerializer
)
from .permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdmin
from .filters import CommentFilter
from .pagination import CommentPagination


@extend_schema_view(
    list=extend_schema(
        summary="List Comments",
        description="Retrieve a list of all active comments. By default, only root comments (without parent) are displayed. Use the show_all=true parameter to display all comments in a flat structure.",
        parameters=[
            OpenApiParameter(
                name='show_all',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Display all comments in flat structure (without tree hierarchy)',
                required=False
            ),
        ]
    ),
    create=extend_schema(
        summary="Post New Comment",
        description="Create a new comment. Both authenticated and anonymous users can create comments. For anonymous comments, the display_name field is required.",
    ),
    partial_update=extend_schema(
        summary="Partial Update Comment",
        description="Partially update comment fields. Only the comment owner or admin/owner can edit the comment.",
    ),
    destroy=extend_schema(
        summary="Delete Comment",
        description="Delete a comment. Only the comment owner or admin/owner can delete the comment.",
    ),
)
class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments.
    
    This ViewSet provides CRUD operations for comments with the following features:
    - List all comments with filtering, searching, and ordering
    - Create new comments (authenticated and anonymous users)
    - Update comments (only owner or admin/owner)
    - Delete comments (only owner or admin/owner)
    - Custom actions for specific queries
    
    Endpoints:
        GET /comments/ - List all comments
        POST /comments/ - Create a new comment
        PATCH /comments/{id}/ - Partially update a comment (owner/admin/owner only)
        DELETE /comments/{id}/ - Delete a comment (owner/admin/owner only)
        POST /comments/deactivate/ - Deactivate multiple comments (admin/owner only)
        POST /comments/activate/ - Activate multiple comments (admin/owner only)
    """

    queryset = Comment.objects.all().select_related('author').prefetch_related('children')
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    pagination_class = CommentPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = CommentFilter
    search_fields = ['text', 'author__username', 'author__email', 'display_name']
    ordering_fields = ['created_at', 'updated_at', 'level']
    ordering = ['-created_at']
    
    # Disable retrieve and update methods
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        """
        Return appropriate serializer class based on action.
        
        Returns:
            Serializer class: The serializer class to use for this action.
        """
        if self.action == 'create':
            return CreateCommentSerializer
        elif self.action == 'partial_update':
            return UpdateCommentSerializer
        elif self.action == 'list':
            return CommentListSerializer
        elif self.action in ['deactivate', 'activate']:
            return BulkActionSerializer
        return CommentSerializer

    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        For partial_update, destroy, deactivate, and activate actions,
        only owner or admin/owner users have access.
        
        Returns:
            list: List of permission instances.
        """
        if self.action in ['partial_update', 'destroy', 'deactivate', 'activate']:
            return [IsOwnerOrAdmin()]
        return super().get_permissions()

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

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve method is disabled.
        Use list or custom actions instead.
        """
        return Response(
            {'detail': 'Method not allowed. Use list endpoint or custom actions.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        """
        Full update method is disabled.
        Use partial_update (PATCH) instead.
        """
        return Response(
            {'detail': 'Method not allowed. Use PATCH for partial updates.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

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

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a comment.
        
        Args:
            request: The HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Returns:
            Response: HTTP response with updated comment data.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        output_serializer = CommentSerializer(serializer.instance)
        return Response(output_serializer.data)

    @extend_schema(
        summary="Deactivate Comments",
        description="Deactivate one or multiple comments along with all their replies. Only admin/owner users can perform this action. You can deactivate a single comment by providing 'comment_id' or multiple comments by providing 'comment_ids' list.",
        request=BulkActionSerializer,
        responses={200: {'type': 'object', 'properties': {
            'message': {'type': 'string'},
            'deactivated_count': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['post'], url_path='deactivate', permission_classes=[IsOwnerOrAdmin])
    def deactivate(self, request):
        """
        Deactivate one or multiple comments and all their descendants.
        
        Only available to admin/owner users.
        Accepts either 'comment_id' for single comment or 'comment_ids' for multiple comments.
        
        Args:
            request: The HTTP request.
            
        Returns:
            Response: Success message with count of deactivated comments.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment_ids = serializer.validated_data.get('comment_ids', [])
        
        if not comment_ids:
            return Response(
                {'detail': 'No comment IDs provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comments = Comment.objects.filter(id__in=comment_ids)
        
        if not comments.exists():
            return Response(
                {'detail': 'No valid comments found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        deactivated_count = 0
        for comment in comments:
            # Check permission for each comment
            self.check_object_permissions(request, comment)
            comment.deactivate()
            # Count the comment itself plus all descendants
            deactivated_count += 1 + comment.get_descendants().count()
        
        return Response(
            {
                'message': f'{deactivated_count} comment(s) and their replies have been deactivated.',
                'deactivated_count': deactivated_count
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Activate Comments",
        description="Activate one or multiple comments. Only admin/owner users can perform this action. You can activate a single comment by providing 'comment_id' or multiple comments by providing 'comment_ids' list.",
        request=BulkActionSerializer,
        responses={200: {'type': 'object', 'properties': {
            'message': {'type': 'string'},
            'activated_count': {'type': 'integer'}
        }}}
    )
    @action(detail=False, methods=['post'], url_path='activate', permission_classes=[IsOwnerOrAdmin])
    def activate(self, request):
        """
        Activate one or multiple comments.
        
        Only available to admin/owner users.
        Accepts either 'comment_id' for single comment or 'comment_ids' for multiple comments.
        
        Args:
            request: The HTTP request.
            
        Returns:
            Response: Success message with count of activated comments.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment_ids = serializer.validated_data.get('comment_ids', [])
        
        if not comment_ids:
            return Response(
                {'detail': 'No comment IDs provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comments = Comment.objects.filter(id__in=comment_ids)
        
        if not comments.exists():
            return Response(
                {'detail': 'No valid comments found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        activated_count = 0
        for comment in comments:
            comment.activate()
            activated_count += 1
        
        return Response(
            {
                'message': f'{activated_count} comment(s) have been activated.',
                'activated_count': activated_count
            },
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