"""
Tests for Reaction model.
"""
import uuid
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from ..models import Reaction


@pytest.mark.django_db
class TestReactionModel:
    """Test suite for Reaction model."""

    def test_create_like_reaction(self, user, test_content_object):
        """Test creating a like reaction for an authenticated user."""
        content_type = ContentType.objects.get_for_model(test_content_object)
        reaction = Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='like'
        )
        
        assert reaction.id is not None
        assert reaction.user == user
        assert reaction.session_key is None
        assert reaction.value == 'like'
        assert reaction.is_like is True
        assert reaction.is_dislike is False
        assert reaction.content_object == test_content_object

    def test_create_anonymous_reaction(self, test_content_object):
        """Test creating a reaction for an anonymous user."""
        content_type = ContentType.objects.get_for_model(test_content_object)
        session_key = "test_session_key_12345"
        reaction = Reaction.objects.create(
            session_key=session_key,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='dislike'
        )

        assert reaction.id is not None
        assert reaction.user is None
        assert reaction.session_key == session_key
        assert reaction.value == 'dislike'
        assert reaction.is_dislike is True

    def test_create_dislike_reaction(self, user, test_content_object):
        """Test creating a dislike reaction."""
        content_type = ContentType.objects.get_for_model(test_content_object)
        reaction = Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='dislike'
        )
        
        assert reaction.value == 'dislike'
        assert reaction.is_dislike is True
        assert reaction.is_like is False

    def test_unique_user_reaction_constraint(self, user, test_content_object):
      """Test that a user can only have one reaction per object."""
      content_type = ContentType.objects.get_for_model(test_content_object)
      
      Reaction.objects.create(
          user=user, content_type=content_type, object_id=test_content_object.pk, value='like'
      )
      
      with pytest.raises(IntegrityError):
          Reaction.objects.create(
              user=user, content_type=content_type, object_id=test_content_object.pk, value='dislike'
          )

    def test_unique_session_reaction_constraint(self, test_content_object):
        """Test that an anonymous session can only have one reaction per object."""
        content_type = ContentType.objects.get_for_model(test_content_object)
        session_key = "test_session_key_abcde"
        
        Reaction.objects.create(
            session_key=session_key, content_type=content_type, object_id=test_content_object.pk, value='like'
        )

        with pytest.raises(IntegrityError):
            Reaction.objects.create(
                session_key=session_key, content_type=content_type, object_id=test_content_object.pk, value='dislike'
            )

    def test_user_or_session_required_constraint(self, test_content_object):
        """Test that either user or session_key is required."""
        content_type = ContentType.objects.get_for_model(test_content_object)
        with pytest.raises(IntegrityError):
            # This should fail the CheckConstraint
            Reaction.objects.create(
                user=None,
                session_key=None,
                content_type=content_type,
                object_id=test_content_object.pk,
                value='like'
            )

    def test_reaction_str_representation(self, reaction_like):
        """Test string representation of reaction."""
        expected = f"{reaction_like.user.username} Like {reaction_like.content_object}"
        assert str(reaction_like) == expected

    def test_reaction_toggle_method(self, reaction_like):
        """Test toggling reaction value."""
        assert reaction_like.value == 'like'
        
        reaction_like.toggle()
        assert reaction_like.value == 'dislike'
        
        reaction_like.toggle()
        assert reaction_like.value == 'like'

    def test_reaction_validation_invalid_object(self, user):
        """Test validation fails for non-existent object."""
        content_type = ContentType.objects.get_for_model(user)
        reaction = Reaction(
            user=user,
            content_type=content_type,
            object_id=str(uuid.uuid4()),
            value='like'
        )
        
        with pytest.raises(ValidationError):
            reaction.full_clean()

    def test_reaction_created_and_updated_timestamps(self, reaction_like):
        """Test that timestamps are set correctly."""
        assert reaction_like.created_at is not None
        assert reaction_like.updated_at is not None
        assert reaction_like.updated_at >= reaction_like.created_at