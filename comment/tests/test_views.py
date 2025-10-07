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
    """
    Test suite for ReactionViewSet.
    تست‌ها برای مطابقت با API مبتنی بر action بازنویسی شده‌اند.
    """

    # --- تست‌های مربوط به action: toggle ---

    def test_toggle_action_create_authenticated(self, api_client, user, test_content_object):
        """Test toggle action creates a new reaction for an authenticated user."""
        api_client.force_authenticate(user=user)
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
        assert reaction.user == user
        assert reaction.value == 'like'
        assert response.data['value'] == 'like'

    def test_toggle_action_create_unauthenticated(self, api_client, test_content_object):
        """Test toggle action creates a new reaction for an anonymous user."""
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
        assert response.data['value'] == 'like'

    def test_toggle_action_update_existing_reaction(self, api_client, user, reaction_like):
        """Test toggle action updates an existing reaction's value."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-toggle')
        
        content_type = ContentType.objects.get_for_model(reaction_like.content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(reaction_like.object_id),
            'value': 'dislike'  # تغییر مقدار
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert Reaction.objects.count() == 1
        reaction_like.refresh_from_db()
        assert reaction_like.value == 'dislike'
        assert response.data['value'] == 'dislike'

    def test_toggle_action_delete_same_reaction_authenticated(self, api_client, user, reaction_like):
        """Test toggle action deletes a reaction if the same value is sent again for an authenticated user."""
        api_client.force_authenticate(user=user)
        url = reverse('reactions:reaction-toggle')
        
        content_type = ContentType.objects.get_for_model(reaction_like.content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(reaction_like.object_id),
            'value': 'like'  # ارسال مقدار یکسان
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Reaction.objects.count() == 0

    def test_toggle_action_delete_same_reaction_anonymous(self, api_client, test_content_object):
        """Test toggle action deletes a reaction for an anonymous user on the second identical request."""
        url = reverse('reactions:reaction-toggle')
        content_type = ContentType.objects.get_for_model(test_content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(test_content_object.pk),
            'value': 'like'
        }
        
        # درخواست اول: ایجاد reaction
        response_create = api_client.post(url, data)
        assert response_create.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 1

        # درخواست دوم با همان داده‌ها: حذف reaction
        # از همان کلاینت استفاده می‌شود، بنابراین session key یکسان است
        response_delete = api_client.post(url, data)
        assert response_delete.status_code == status.HTTP_204_NO_CONTENT
        assert Reaction.objects.count() == 0

    def test_toggle_action_forbidden_for_other_user(self, api_client, another_user, reaction_like):
        """
        Test that a user cannot modify another user's reaction via toggle.
        این تست فرض می‌کند که منطق `toggle_reaction` در مدل، مالکیت را بررسی می‌کند.
        اگر این منطق وجود نداشته باشد، این تست fail خواهد شد و نشان می‌دهد که باید منطق مجوز در مدل اضافه شود.
        """
        # `reaction_like` متعلق به `user` است.
        api_client.force_authenticate(user=another_user)
        url = reverse('reactions:reaction-toggle')

        content_type = ContentType.objects.get_for_model(reaction_like.content_object)
        data = {
            'content_type_id': content_type.id,
            'object_id': str(reaction_like.object_id),
            'value': 'dislike'
        }

        # کاربر دیگر تلاش می‌کند reaction را تغییر دهد.
        # این کار یک reaction جدید برای `another_user` ایجاد می‌کند،
        # و reaction اصلی دست‌نخورده باقی می‌ماند.
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Reaction.objects.count() == 2 # یک reaction جدید ایجاد شد
        reaction_like.refresh_from_db()
        assert reaction_like.value == 'like' # reaction اصلی تغییری نکرد

    # --- تست‌های مربوط به action: object_stats ---

    def test_object_stats_action(self, api_client, multiple_reactions, test_content_object):
        """Test object_stats endpoint returns correct statistics."""
        url = reverse('reactions:reaction-object-stats')
        content_type = ContentType.objects.get_for_model(test_content_object)
        params = {'content_type_id': content_type.id, 'object_id': str(test_content_object.pk)}
        
        response = api_client.get(url, params)
        
        assert response.status_code == status.HTTP_200_OK
        # با توجه به fixture، انتظار می‌رود 7 لایک و 3 دیس‌لایک وجود داشته باشد
        assert response.data['likes'] == 7
        assert response.data['dislikes'] == 3
        assert response.data['total'] == 10
        assert response.data['popularity'] == 70.0

    def test_object_stats_action_missing_params(self, api_client):
        """Test object_stats endpoint returns 400 if params are missing."""
        url = reverse('reactions:reaction-object-stats')
        
        # بدون پارامتر
        response = api_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # با یک پارامتر
        response = api_client.get(url, {'content_type_id': 1})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_object_stats_action_invalid_object(self, api_client, test_content_object):
        """Test object_stats with invalid content_type or object_id."""
        url = reverse('reactions:reaction-object-stats')
        content_type = ContentType.objects.get_for_model(test_content_object)

        # content_type نامعتبر
        params_invalid_ct = {'content_type_id': 999, 'object_id': str(test_content_object.pk)}
        response = api_client.get(url, params_invalid_ct)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # object_id نامعتبر
        params_invalid_obj = {'content_type_id': content_type.id, 'object_id': '999'}
        response = api_client.get(url, params_invalid_obj)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # تست‌های زیر حذف شده‌اند
    # - test_list_reactions
    # - test_list_reactions_unauthenticated
    # - test_retrieve_reaction
    # - test_update_own_reaction (منطق آن در test_toggle_action_update_existing_reaction پوشش داده شده)
    # - test_update_others_reaction_forbidden (منطق آن در test_toggle_action_forbidden_for_other_user بررسی شده)
    # - test_delete_own_reaction (منطق آن در test_toggle_action_delete_same_reaction_authenticated پوشش داده شده)
    # - test_delete_others_reaction_forbidden
    # - test_popularity_action (با test_object_stats_action جایگزین شده)
    # - test_filter_by_value