"""
Tests for Reaction serializers.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIRequestFactory

from ..serializers import (
    ReactionSerializer,
    ReactionCreateSerializer,
    ReactionStatsSerializer,
)
from ..models import Reaction


@pytest.mark.django_db
class TestReactionSerializer:
    """Test suite for ReactionSerializer."""

    def test_serialize_reaction(self, reaction_like):
        """Test serializing a reaction."""
        serializer = ReactionSerializer(reaction_like)
        data = serializer.data
        
        assert data['id'] == str(reaction_like.id)
        assert data['user']['username'] == reaction_like.user.username
        assert data['value'] == 'like'
        assert data['value_display'] == 'Like'
        assert data['is_like'] is True
        assert data['is_dislike'] is False

    def test_content_type_name_field(self, reaction_like):
        """Test content_type_name field."""
        serializer = ReactionSerializer(reaction_like)
        data = serializer.data
        
        assert 'content_type_name' in data
        assert data['content_type_name'] == reaction_like.content_type.model


@pytest.mark.django_db
class TestReactionCreateSerializer:
    """Test suite for ReactionCreateSerializer."""

    def test_create_reaction(self, user, test_content_object):
        """Test creating a reaction via serializer."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        serializer = ReactionCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        assert serializer.is_valid()
        reaction = serializer.save()
        
        assert reaction.user == user
        assert reaction.value == 'like'
        assert reaction.content_object == test_content_object

    def test_update_existing_reaction(self, user, test_content_object, reaction_like):
        """Test that creating duplicate updates instead."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'dislike'
        }
        
        serializer = ReactionCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        assert serializer.is_valid()
        reaction = serializer.save()
        
        # Should update, not create new
        assert Reaction.objects.count() == 1
        assert reaction.id == reaction_like.id
        assert reaction.value == 'dislike'

    def test_invalid_content_type(self, user):
        """Test validation with invalid content type."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        data = {
            'content_type_id': 99999,
            'object_id': '123',
            'value': 'like'
        }
        
        serializer = ReactionCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        assert not serializer.is_valid()
        assert 'content_type_id' in serializer.errors

    def test_invalid_object_id(self, user, test_content_object):
      """Test validation with non-existent object."""
      factory = APIRequestFactory()
      request = factory.post('/')
      request.user = user
      
      content_type = ContentType.objects.get_for_model(test_content_object)
      data = {
          'content_type_id': content_type.id,
          'object_id': '99999999',
          'value': 'like'
      }
      
      serializer = ReactionCreateSerializer(
          data=data,
          context={'request': request}
      )
      
      assert not serializer.is_valid()
      assert 'object_id' in serializer.errors or 'non_field_errors' in serializer.errors


@pytest.mark.django_db
class TestReactionStatsSerializer:
    """Test suite for ReactionStatsSerializer."""

    def test_serialize_stats(self, multiple_reactions):
        """Test serializing reaction statistics."""
        stats = {
            'likes': 7,
            'dislikes': 3,
            'total': 10,
            'popularity': 70.0
        }
        
        serializer = ReactionStatsSerializer(stats)
        data = serializer.data
        
        assert data['likes'] == 7
        assert data['dislikes'] == 3
        assert data['total'] == 10
        assert data['popularity'] == 70.0