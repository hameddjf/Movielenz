"""
Serializers for Reaction model.
OPTIMIZED VERSION
"""
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Reaction

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for reactions."""
    
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = fields


class ReactionSerializer(serializers.ModelSerializer):
    """
    Main serializer for displaying Reaction instances.
    Used for list, retrieve, and toggle responses.
    """
    
    user = UserBasicSerializer(read_only=True, allow_null=True)
    content_type_name = serializers.SerializerMethodField()
    value_display = serializers.CharField(source='get_value_display', read_only=True)

    class Meta:
        model = Reaction
        fields = [
            'id',
            'user',
            'content_type',
            'content_type_name',
            'object_id',
            'value',
            'value_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_content_type_name(self, obj):
        """Get human-readable content type name."""
        return obj.content_type.model


class ReactionToggleSerializer(serializers.Serializer):
    """
    Serializer for toggling reactions (create/update/delete).
    This is the PRIMARY way to create/modify reactions.
    """
    
    content_type_id = serializers.IntegerField()
    object_id = serializers.CharField(max_length=255)
    value = serializers.ChoiceField(choices=Reaction.ReactionValue.choices)

    def validate_content_type_id(self, value):
        """Validate content type exists."""
        try:
            ContentType.objects.get(id=value)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError("Invalid content type ID.")
        return value

    def validate(self, attrs):
        """Validate content object exists."""
        content_type_id = attrs.get('content_type_id')
        object_id = attrs.get('object_id')
        
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            
            if not model_class.objects.filter(pk=object_id).exists():
                raise serializers.ValidationError({
                    'object_id': f'No {content_type.model} found with this ID.'
                })
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({
                'content_type_id': 'Invalid content type.'
            })
        return attrs

    @transaction.atomic
    def save(self):
        """
        Toggle the reaction using the manager method.
        
        Returns:
            tuple: (Reaction or None, str) - Reaction instance and action taken.
        """
        request = self.context['request']
        content_type = ContentType.objects.get(id=self.validated_data['content_type_id'])
        model_class = content_type.model_class()
        obj = model_class.objects.get(pk=self.validated_data['object_id'])
        
        return Reaction.objects.toggle_reaction(
            request=request,
            obj=obj,
            value=self.validated_data['value']
        )


class ReactionStatsSerializer(serializers.Serializer):
    """Serializer for reaction statistics."""
    
    content_type_id = serializers.IntegerField(help_text='Content Type ID of the object')
    object_id = serializers.CharField(help_text='Object ID of the object')
    likes = serializers.IntegerField(help_text='Number of like reactions')
    dislikes = serializers.IntegerField(help_text='Number of dislike reactions')
    total = serializers.IntegerField(help_text='Total number of reactions')
    popularity = serializers.FloatField(help_text='Popularity ratio as percentage (0-100)')