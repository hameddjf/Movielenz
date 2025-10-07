"""
Tests for Reaction serializers.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError

from ..serializers import (
    ReactionSerializer,
    ReactionToggleSerializer,
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
        # فیلدهای is_like و is_dislike حذف شده‌اند، بنابراین تست آنها نیز حذف می‌شود.

    def test_content_type_name_field(self, reaction_like):
        """Test content_type_name field."""
        serializer = ReactionSerializer(reaction_like)
        data = serializer.data
        
        assert 'content_type_name' in data
        assert data['content_type_name'] == reaction_like.content_type.model


@pytest.mark.django_db
class TestReactionToggleSerializer:
    """
    Test suite for ReactionToggleSerializer.
    این کلاس جایگزین TestReactionCreateSerializer شده است.
    """

    def test_valid_data(self, user, test_content_object):
        """Test that serializer is valid with correct data."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        serializer = ReactionToggleSerializer(
            data=data,
            context={'request': request}
        )
        
        assert serializer.is_valid(raise_exception=True)

    def test_invalid_content_type_id(self, user):
        """Test validation with a non-existent content type ID."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        data = {
            'content_type_id': 99999,  # ID نامعتبر
            'object_id': '123',
            'value': 'like'
        }
        
        serializer = ReactionToggleSerializer(
            data=data,
            context={'request': request}
        )
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert 'content_type_id' in excinfo.value.detail

    def test_invalid_object_id(self, user, test_content_object):
        """Test validation with a non-existent object ID for a valid content type."""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
      
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': '99999999',  # ID آبجکت نامعتبر
            'value': 'like'
        }
      
        serializer = ReactionToggleSerializer(
            data=data,
            context={'request': request}
        )
      
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert 'object_id' in excinfo.value.detail

    def test_save_method_calls_toggle_reaction(self, mocker, user, test_content_object):
        """
        Test that the save method correctly calls the manager's toggle_reaction method.
        ما اینجا متد toggle_reaction را mock می‌کنیم تا از عملکرد داخلی آن صرف نظر کرده و فقط فراخوانی آن را تست کنیم.
        """
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user

        # Mock کردن متد toggle_reaction در مدیر مدل Reaction
        mock_toggle = mocker.patch('reactions.models.Reaction.objects.toggle_reaction')
        # یک مقدار بازگشتی ساختگی برای mock تعریف می‌کنیم
        mock_toggle.return_value = (mocker.MagicMock(spec=Reaction), 'created')

        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        serializer = ReactionToggleSerializer(
            data=data,
            context={'request': request}
        )
        
        assert serializer.is_valid(raise_exception=True)
        serializer.save()

        # بررسی می‌کنیم که آیا متد toggle_reaction با آرگومان‌های صحیح فراخوانی شده است یا خیر
        mock_toggle.assert_called_once_with(
            request=request,
            obj=test_content_object,
            value='like'
        )


@pytest.mark.django_db
class TestReactionStatsSerializer:
    """Test suite for ReactionStatsSerializer."""

    def test_serialize_stats(self):
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