"""
Tests for Reaction views and API endpoints.
"""
import pytest
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from ..models import Reaction


@pytest.mark.django_db
class TestReactionViewSet:
    """Test suite for ReactionViewSet."""

    def test_list_reactions(self, api_client, reaction_like, reaction_dislike):
        """Test listing all reactions is public."""
        url = reverse('reactions:reaction-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_list_reactions_unauthenticated(self, api_client, reaction_like):
        """Test that unauthenticated users CAN list reactions."""
        url = reverse('reactions:reaction-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_create_reaction_authenticated(self, api_client, user, test_content_object):
        """Test creating a reaction by an authenticated user."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-list')
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 1
        reaction = Reaction.objects.first()
        assert reaction.user == user
        assert reaction.value == 'like'

    def test_create_reaction_unauthenticated(self, api_client, test_content_object):
        """Test that unauthenticated users CAN create reactions."""
        url = reverse('reactions:reaction-list')
        
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 1
        reaction = Reaction.objects.first()
        assert reaction.user is None
        assert reaction.session_key is not None

    def test_retrieve_reaction(self, api_client, reaction_like):
        """Test retrieving a specific reaction is public."""
        url = reverse('reactions:reaction-detail', args=[reaction_like.id])
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(reaction_like.id)

    def test_update_own_reaction(self, api_client, user, reaction_like):
        """Test updating own reaction."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-detail', args=[reaction_like.id])
        
        data = {'value': 'dislike'}
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        reaction_like.refresh_from_db()
        assert reaction_like.value == 'dislike'

    def test_update_others_reaction_forbidden(self, api_client, another_user, reaction_like):
        """Test that users cannot update others' reactions."""
        api_client.force_authenticate(user=another_user)
        url = reverse('reactions:reaction-detail', args=[reaction_like.id])
        
        data = {'value': 'dislike'}
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_own_reaction(self, api_client, user, reaction_like):
        """Test deleting own reaction."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-detail', args=[reaction_like.id])
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Reaction.objects.count() == 0

    def test_delete_others_reaction_forbidden(self, api_client, another_user, reaction_like):
        """Test that users cannot delete others' reactions."""
        api_client.force_authenticate(user=another_user)
        url = reverse('reactions:reaction-detail', args=[reaction_like.id])
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_popularity_action(self, api_client, multiple_reactions, test_content_object):
        """Test popularity endpoint is public."""
        reaction = Reaction.objects.for_object(test_content_object).first()
        url = reverse('reactions:reaction-popularity', args=[reaction.id])
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['likes'] == 7
        assert response.data['dislikes'] == 3

    def test_toggle_action_create_unauthenticated(self, api_client, test_content_object):
        """Test toggle action creates new reaction for anonymous user."""
        url = reverse('reactions:reaction-toggle')
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 1
        reaction = Reaction.objects.first()
        assert reaction.user is None
        assert reaction.session_key is not None

    def test_toggle_action_update(self, api_client, user, reaction_like):
        """Test toggle action updates existing reaction."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-toggle')
        
        content_type = ContentType.objects.get_for_model(reaction_like.content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(reaction_like.object_id),
            'value': 'dislike'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert Reaction.objects.count() == 1
        reaction_like.refresh_from_db()
        assert reaction_like.value == 'dislike'

    def test_toggle_action_delete_authenticated(self, api_client, user, reaction_like):
        """Test toggle action deletes same reaction for authenticated user."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-toggle')
        
        content_type = ContentType.objects.get_for_model(reaction_like.content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(reaction_like.object_id),
            'value': 'like' # Same value
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Reaction.objects.count() == 0

    def test_toggle_action_delete_anonymous(self, api_client, test_content_object):
        """Test toggle action deletes same reaction for anonymous user."""
        url = reverse('reactions:reaction-toggle')
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        # First request creates the reaction
        response_create = api_client.post(url, data)
        assert response_create.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 1

        # Second request with the same data should delete it
        response_delete = api_client.post(url, data)
        assert response_delete.status_code == status.HTTP_204_NO_CONTENT
        assert Reaction.objects.count() == 0

    # def test_my_reactions_action(self, api_client, user, reaction_like, reaction_dislike):
    #     """This action is deprecated and commented out."""
    #     pass

    def test_object_stats_action(self, api_client, multiple_reactions, test_content_object):
        """Test object_stats endpoint is public."""
        url = reverse('reactions:reaction-object-stats')
        content_type = ContentType.objects.get_for_model(test_content_object)
        params = {'content_type_id': content_type.id, 'object_id': str(test_content_object.pk)}
        
        response = api_client.get(url, params)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['likes'] == 7
        assert response.data['dislikes'] == 3

    def test_filter_by_value(self, api_client, reaction_like, reaction_dislike):
        """Test filtering reactions by value."""
        url = reverse('reactions:reaction-list')
        response = api_client.get(url, {'value': 'like'})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == str(reaction_like.id)