"""
Views for Reaction model using Django REST Framework.
OPTIMIZED VERSION - Minimal and focused
"""
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Reaction
from .serializers import (
    ReactionSerializer,
    ReactionStatsSerializer,
    ReactionToggleSerializer,
)
from .filters import ReactionFilter
from .permissions import IsOwnerOrReadOnly


@extend_schema_view(
    list=extend_schema(summary='List all reactions', tags=['Reactions']),
    retrieve=extend_schema(summary='Retrieve a reaction', tags=['Reactions']),
)
class ReactionViewSet(
    # mixins.ListModelMixin,
    # mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for managing Reaction instances.
    
    Provides:
    - List reactions (with filtering)
    - Retrieve a specific reaction
    - Toggle reactions (create/update/delete)
    - Get statistics for content objects
    
    Note: Direct CRUD operations are disabled. Use 'toggle' action instead.
    """

    queryset = Reaction.objects.all().select_related('user', 'content_type')
    serializer_class = ReactionSerializer
    permission_classes = [AllowAny]
    
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = ReactionFilter
    # ordering = ['-created_at']

    @extend_schema(
        summary='Toggle a reaction',
        description='''
        Create, update, or delete a reaction in one action. This endpoint
        works for both authenticated and anonymous users.
        
        Behavior:
        - If no reaction exists: Creates a new reaction (201 Created)
        - If a reaction exists with the same value: Deletes the reaction (204 No Content)
        - If a reaction exists with a different value: Updates the reaction (200 OK)
        
        Examples:
        1. First like: POST {"content_type_id": 1, "object_id": "5", "value": "like"} → 201
        2. Toggle off: POST {"content_type_id": 1, "object_id": "5", "value": "like"} → 204
        3. Switch to dislike: POST {"content_type_id": 1, "object_id": "5", "value": "dislike"} → 200
        ''',
        request=ReactionToggleSerializer,
        responses={
            200: ReactionSerializer,
            201: ReactionSerializer,
            204: None
        },
        tags=['Reactions'],
    )
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def toggle(self, request, *args, **kwargs):
        """
        Toggle a reaction (create/update/delete).
        This is the PRIMARY way to interact with reactions.
        """
        serializer = ReactionToggleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        reaction, action_taken = serializer.save()
        
        if action_taken == 'deleted':
            return Response(
                {'detail': 'Reaction removed successfully.'},
                status=status.HTTP_204_NO_CONTENT
            )
        
        response_serializer = ReactionSerializer(reaction, context={'request': request})
        
        if action_taken == 'created':
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        # 'updated'
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Get object statistics',
        description='''
        Get popularity statistics for a specific content object.
        
        Returns:
        - content_type_id: ID of the content type
        - object_id: ID of the object
        - likes: Number of like reactions
        - dislikes: Number of dislike reactions
        - total: Total reactions
        - popularity: Percentage ratio (0-100)
        ''',
        parameters=[
            OpenApiParameter(
                'content_type_id',
                OpenApiTypes.INT,
                description='Content Type ID',
                required=True
            ),
            OpenApiParameter(
                'object_id',
                OpenApiTypes.STR,
                description='Object ID',
                required=True
            ),
        ],
        responses={200: ReactionStatsSerializer},
        tags=['Reactions'],
    )
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def object_stats(self, request):
        """
        Get statistics for a specific content object.
        """
        from django.contrib.contenttypes.models import ContentType
        
        content_type_id = request.query_params.get('content_type_id')
        object_id = request.query_params.get('object_id')
        
        if not content_type_id or not object_id:
            return Response(
                {'error': 'Both content_type_id and object_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            obj = model_class.objects.get(pk=object_id)
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Invalid content type.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except model_class.DoesNotExist:
            return Response(
                {'error': 'Object not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = Reaction.objects.get_statistics(obj)

        # Combine stats with the identifiers for the response
        data_for_serializer = {
            'content_type_id': content_type.id,
            'object_id': object_id,
            **stats
        }
        
        serializer = ReactionStatsSerializer(data_for_serializer)
        return Response(serializer.data)