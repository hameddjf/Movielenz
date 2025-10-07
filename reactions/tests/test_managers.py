"""
Tests for Reaction managers and querysets.
"""
import pytest
from django.contrib.contenttypes.models import ContentType

from ..models import Reaction


@pytest.mark.django_db
class TestReactionManager:
    """Test suite for Reaction manager methods."""

    def test_for_object_filter(self, reaction_like, reaction_dislike, test_content_object):
        """Test filtering reactions for a specific object."""
        reactions = Reaction.objects.for_object(test_content_object)
        
        assert reactions.count() == 2
        assert reaction_like in reactions
        assert reaction_dislike in reactions

    def test_for_user_filter(self, reaction_like, reaction_dislike, user):
        """Test filtering reactions by user."""
        reactions = Reaction.objects.for_user(user)
        
        assert reactions.count() == 1
        assert reaction_like in reactions
        assert reaction_dislike not in reactions

    def test_likes_filter(self, reaction_like, reaction_dislike):
        """Test filtering only like reactions."""
        likes = Reaction.objects.likes()
        
        assert likes.count() == 1
        assert reaction_like in likes
        assert reaction_dislike not in likes

    def test_dislikes_filter(self, reaction_like, reaction_dislike):
        """Test filtering only dislike reactions."""
        dislikes = Reaction.objects.dislikes()
        
        assert dislikes.count() == 1
        assert reaction_dislike in dislikes
        assert reaction_like not in dislikes

    def test_likes_count(self, multiple_reactions):
        """Test counting likes."""
        count = Reaction.objects.likes_count()
        assert count == 7

    def test_dislikes_count(self, multiple_reactions):
        """Test counting dislikes."""
        count = Reaction.objects.dislikes_count()
        assert count == 3

    def test_likes_count_for_object(self, multiple_reactions, test_content_object):
        """Test counting likes for specific object."""
        count = Reaction.objects.likes_count(test_content_object)
        assert count == 7

    def test_dislikes_count_for_object(self, multiple_reactions, test_content_object):
        """Test counting dislikes for specific object."""
        count = Reaction.objects.dislikes_count(test_content_object)
        assert count == 3

    def test_popularity_ratio(self, multiple_reactions):
        """Test calculating popularity ratio."""
        # 7 likes, 3 dislikes = 70% popularity
        popularity = Reaction.objects.popularity_ratio()
        assert popularity == 70.0

    def test_popularity_ratio_for_object(self, multiple_reactions, test_content_object):
        """Test calculating popularity ratio for specific object."""
        popularity = Reaction.objects.popularity_ratio(test_content_object)
        assert popularity == 70.0

    def test_popularity_ratio_no_reactions(self, user, test_content_object):
        """Test popularity ratio when no reactions exist."""
        # Create a new content object with no reactions
        new_user = type(test_content_object).objects.create(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        
        popularity = Reaction.objects.popularity_ratio(new_user)
        assert popularity == 0.0

    def test_popularity_ratio_all_likes(self, user, test_content_object):
        """Test popularity ratio with 100% likes."""
        Reaction.objects.all().delete()
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='like'
        )
        
        popularity = Reaction.objects.popularity_ratio()
        assert popularity == 100.0

    def test_popularity_ratio_all_dislikes(self, user, test_content_object):
        """Test popularity ratio with 0% likes."""
        Reaction.objects.all().delete()
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='dislike'
        )
        
        popularity = Reaction.objects.popularity_ratio()
        assert popularity == 0.0

    def test_get_statistics(self, multiple_reactions, test_content_object):
        """Test getting comprehensive statistics."""
        stats = Reaction.objects.get_statistics(test_content_object)
        
        assert stats['likes'] == 7
        assert stats['dislikes'] == 3
        assert stats['total'] == 10
        assert stats['popularity'] == 70.0

    def test_user_reaction(self, user, test_content_object, reaction_like):
        """Test getting a user's reaction to an object."""
        reaction = Reaction.objects.user_reaction(user, test_content_object)
        
        assert reaction is not None
        assert reaction == reaction_like

    def test_user_reaction_not_found(self, user):
        """Test getting reaction when user hasn't reacted."""
        new_user = type(user).objects.create_user(
            username='newuser2',
            email='new2@example.com',
            password='testpass123'
        )
        
        reaction = Reaction.objects.user_reaction(user, new_user)
        assert reaction is None

    def test_toggle_reaction_create(self, user, test_content_object):
        """Test toggle creates new reaction."""
        reaction, action = Reaction.objects.toggle_reaction(
            user, test_content_object, 'like'
        )
        
        assert action == 'created'
        assert reaction.value == 'like'
        assert Reaction.objects.count() == 1

    def test_toggle_reaction_update(self, user, test_content_object, reaction_like):
        """Test toggle updates existing different reaction."""
        reaction, action = Reaction.objects.toggle_reaction(
            user, test_content_object, 'dislike'
        )
        
        assert action == 'updated'
        assert reaction.value == 'dislike'
        assert Reaction.objects.count() == 1

    def test_toggle_reaction_delete(self, user, test_content_object, reaction_like):
        """Test toggle deletes existing same reaction."""
        reaction, action = Reaction.objects.toggle_reaction(
            user, test_content_object, 'like'
        )
        
        assert action == 'deleted'
        assert reaction is None
        assert Reaction.objects.count() == 0