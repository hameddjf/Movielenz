"""
Serializers for the comment application.

This module provides serializer classes for converting Comment model
instances to and from JSON representations.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import Comment
from .constants import MAX_REPLY_DEPTH

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying user information in comments.
    
    This is a read-only serializer used for displaying author information
    in comment responses.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name']
        read_only_fields = fields

    def get_full_name(self, obj):
        """
        Get the full name of the user.
        
        Args:
            obj: User instance.
            
        Returns:
            str: Full name or username if full name is not available.
        """
        return obj.get_full_name() or obj.username


class RecursiveCommentSerializer(serializers.Serializer):
    """
    Recursive serializer for nested comment replies.
    
    This serializer is used to serialize the reply tree structure
    of comments up to the maximum allowed depth.
    """

    def to_representation(self, instance):
        """
        Convert comment instance to nested representation.
        
        Args:
            instance: Comment instance.
            
        Returns:
            dict: Serialized comment with nested replies.
        """
        serializer = CommentSerializer(instance, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    """
    Main serializer for Comment model.
    
    This serializer provides full representation of comments including
    author information and nested replies.
    """

    # author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.IntegerField(read_only=True, source='children.count')
    depth = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            # 'author',
            'display_name',
            'content_type',
            'object_id',
            'parent',
            'text',
            'is_active',
            'has_spoiler',
            'created_at',
            'updated_at',
            'replies',
            'reply_count',
            'depth'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at',  'display_name'
                            # 'author',
                            ]

    def get_depth(self, obj):
        """
        Get the depth level of the comment.
        0 = root comment (parent)
        1 = first level reply
        2 = second level reply (deepest allowed)
        
        Args:
            obj: Comment instance.
            
        Returns:
            int: Depth level (0, 1, or 2).
        """
        return obj.level

    def get_replies(self, obj):
        """
        Get nested replies for this comment.
        
        Only returns active replies and respects the maximum depth limit.
        
        Args:
            obj: Comment instance.
            
        Returns:
            list: List of serialized child comments.
        """
        if obj.level >= MAX_REPLY_DEPTH - 1:
            return []

        children = obj.children.filter(is_active=True)#.select_related('author')
        return CommentSerializer(children, many=True, context=self.context).data


class CreateCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new comments.
    
    This serializer handles comment creation with validation for
    reply depth and parent comment existence.
    
    Note: author_id field has been removed. Author is automatically set
    from the authenticated user or left as None for anonymous comments.
    """

    display_name = serializers.CharField(max_length=100, required=True, allow_blank=False)

    class Meta:
        model = Comment
        fields = [
            'display_name',
            'content_type',
            'object_id',
            'parent',
            'text',
            'has_spoiler'
        ]

    def validate_parent(self, value):
        """
        Validate parent comment.
        
        Ensures that the parent comment exists and is active.
        Adjusts parent if depth would exceed maximum.
        
        Args:
            value: Parent comment instance.
            
        Returns:
            Comment: Validated (and possibly adjusted) parent comment.
            
        Raises:
            serializers.ValidationError: If parent is invalid.
        """
        if value is None:
            return value

        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot reply to an inactive comment."
            )

        # Ensure maximum depth is not exceeded
        if value.level >= MAX_REPLY_DEPTH - 1:
            return value.parent

        return value

    def validate_content_type(self, value):
        """
        Validate content type.
        
        Args:
            value: ContentType instance or ID.
            
        Returns:
            ContentType: Validated content type.
        """
        if isinstance(value, int):
            try:
                value = ContentType.objects.get(pk=value)
            except ContentType.DoesNotExist:
                raise serializers.ValidationError("Invalid content type.")
        
        if not isinstance(value, ContentType):
            raise serializers.ValidationError("Invalid content type.")
        return value

    def validate_text(self, value):
        """
        Validate comment text.
        
        Args:
            value: Comment text string.
            
        Returns:
            str: Validated and stripped text.
            
        Raises:
            serializers.ValidationError: If text is invalid.
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Comment text cannot be empty or contain only whitespace."
            )
        return value.strip()

    def validate_display_name(self, value):
        """
        Validate display name.
        
        Args:
            value: Display name string.
            
        Returns:
            str: Validated and stripped display name.
            
        Raises:
            serializers.ValidationError: If display name is invalid.
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Display name cannot be empty or contain only whitespace."
            )
        return value.strip()

    def create(self, validated_data):
        """
        Create a new comment instance.
        
        Author is automatically set from request.user in the view.
        
        Args:
            validated_data: Validated data dictionary.
            
        Returns:
            Comment: Created comment instance.
        """
        return Comment.objects.create(**validated_data)


class UpdateCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing comments.
    
    This serializer only allows updating the text, has_spoiler, and is_active fields.
    """

    class Meta:
        model = Comment
        fields = ['text', 'is_active', 'has_spoiler']

    def validate_text(self, value):
        """
        Validate comment text.
        
        Args:
            value: Comment text string.
            
        Returns:
            str: Validated and stripped text.
            
        Raises:
            serializers.ValidationError: If text is invalid.
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Comment text cannot be empty or contain only whitespace."
            )
        return value.strip()

    def update(self, instance, validated_data):
        """
        Update comment instance.
        
        Args:
            instance: Comment instance to update.
            validated_data: Validated data dictionary.
            
        Returns:
            Comment: Updated comment instance.
        """
        instance.text = validated_data.get('text', instance.text)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.has_spoiler = validated_data.get('has_spoiler', instance.has_spoiler)
        instance.save()
        return instance


class CommentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for comment listings.
    
    This serializer is optimized for list views and only shows root comments
    with their direct replies (not nested further).
    """

    # author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.IntegerField(read_only=True, source='children.count')
    depth = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            # 'author',
            'display_name',
            'text',
            'is_active',
            'has_spoiler',
            'created_at',
            'updated_at',
            'reply_count',
            'depth',
            'parent',
            'replies'
        ]
        read_only_fields = fields

    def get_depth(self, obj):
        """
        Get the depth level of the comment.
        0 = root comment (parent)
        1 = first level reply
        2 = second level reply (deepest allowed)
        
        Args:
            obj: Comment instance.
            
        Returns:
            int: Depth level (0, 1, or 2).
        """
        return obj.level

    def get_replies(self, obj):
        """
        Get direct replies for this comment.
        
        Returns only first level replies to avoid deep nesting in list view.
        """
        if obj.parent is not None:
            # Don't show replies for reply comments in list view
            return []
        
        children = obj.children.filter(is_active=True)#.select_related('author')
        # Use CommentSerializer for nested replies to get full structure
        return CommentSerializer(children, many=True, context=self.context).data
    
class BulkActionSerializer(serializers.Serializer):
    """
    Serializer for bulk activate/deactivate actions.
    
    This serializer accepts either a single comment_id or a list of comment_ids.
    """
    
    comment_id = serializers.IntegerField(required=False, help_text="Single comment ID to activate/deactivate")
    comment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of comment IDs to activate/deactivate"
    )
    
    def validate(self, attrs):
        """
        Validate that at least one of comment_id or comment_ids is provided.
        If comment_id is provided, convert it to comment_ids list.
        """
        comment_id = attrs.get('comment_id')
        comment_ids = attrs.get('comment_ids')
        
        if not comment_id and not comment_ids:
            raise serializers.ValidationError(
                "Either 'comment_id' or 'comment_ids' must be provided."
            )
        
        # Convert single ID to list
        if comment_id and not comment_ids:
            attrs['comment_ids'] = [comment_id]
        elif comment_id and comment_ids:
            # If both provided, add comment_id to comment_ids if not already there
            if comment_id not in comment_ids:
                attrs['comment_ids'].append(comment_id)
        
        # Remove comment_id from final data as we only use comment_ids
        attrs.pop('comment_id', None)
        
        # Validate that comment_ids is not empty and contains valid integers
        if not attrs.get('comment_ids'):
            raise serializers.ValidationError("comment_ids cannot be empty.")
        
        # Check for duplicates
        comment_ids_list = attrs['comment_ids']
        if len(comment_ids_list) != len(set(comment_ids_list)):
            raise serializers.ValidationError("Duplicate comment IDs found.")
        
        return attrs