"""
Tests for comment views and API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from comment.models import Comment


@pytest.mark.django_db
class TestCommentViewSet:
    """Test suite for CommentViewSet."""

    # --- List Tests ---

    def test_list_comments_shows_root_by_default(self, api_client, root_comment, reply_comment):
        """Test that list endpoint shows only root comments by default."""
        url = reverse('comment:comment-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Only root comments are displayed
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == root_comment.id

    def test_list_comments_show_all(self, api_client, root_comment, reply_comment):
        """Test that list endpoint shows all comments with show_all=true."""
        url = reverse('comment:comment-list')
        response = api_client.get(url, {'show_all': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # All comments are displayed
        assert len(response.data['results']) == 2

    def test_list_comments_filters_inactive_for_non_admin(self, api_client, root_comment, inactive_comment):
        """Test that inactive comments are filtered for non-admin users."""
        url = reverse('comment:comment-list')
        response = api_client.get(url, {'show_all': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # Only active comments are displayed
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['is_active'] is True

    def test_list_comments_shows_inactive_for_admin(self, api_client, admin_user, root_comment, inactive_comment):
        """Test that admin users can see inactive comments."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-list')
        response = api_client.get(url, {'show_all': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # Both active and inactive comments are displayed
        assert len(response.data['results']) == 2

    # --- Create Tests ---

    def test_create_comment_authenticated(self, api_client, user, content_type):
        """Test creating a comment as authenticated user."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-list')
        data = {
            'content_type': content_type.id,
            'object_id': user.id,
            'text': 'Test comment by authenticated user',
            'display_name': 'TestUser'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Comment.objects.count() == 1
        comment = Comment.objects.first()
        assert comment.author == user
        assert comment.text == 'Test comment by authenticated user'

    def test_create_comment_anonymous(self, api_client, user, content_type):
        """Test creating a comment as anonymous user."""
        url = reverse('comment:comment-list')
        data = {
            'content_type': content_type.id,
            'object_id': user.id,
            'text': 'Test comment by anonymous',
            'display_name': 'Anonymous User'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Comment.objects.count() == 1
        comment = Comment.objects.first()
        assert comment.author is None
        assert comment.display_name == 'Anonymous User'

    def test_create_reply_comment(self, api_client, user, content_type, root_comment):
        """Test creating a reply to an existing comment."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-list')
        data = {
            'content_type': content_type.id,
            'object_id': user.id,
            'parent': root_comment.id,
            'text': 'This is a reply',
            'display_name': 'Replier'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        reply = Comment.objects.get(id=response.data['id'])
        assert reply.parent == root_comment
        assert reply.level == 1

    # --- Retrieve Tests (Disabled) ---

    def test_retrieve_comment_not_allowed(self, api_client, root_comment):
        """Test that retrieve endpoint is disabled."""
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # --- Update Tests (Disabled) ---

    def test_full_update_not_allowed(self, api_client, user, root_comment):
        """Test that PUT method is disabled."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {
            'text': 'Updated text',
            'is_active': True,
            'has_spoiler': False
        }
        
        response = api_client.put(url, data)
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # --- Partial Update Tests ---

    def test_partial_update_own_comment(self, api_client, user, root_comment):
        """Test that owner can partially update their comment."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {'text': 'Updated comment text'}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        root_comment.refresh_from_db()
        assert root_comment.text == 'Updated comment text'

    def test_partial_update_others_comment_forbidden(self, api_client, another_user, root_comment):
        """Test that non-owner cannot update others' comments."""
        api_client.force_authenticate(user=another_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {'text': 'Trying to update'}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_by_admin(self, api_client, admin_user, root_comment):
        """Test that admin can update any comment."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {'text': 'Admin updated this'}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        root_comment.refresh_from_db()
        assert root_comment.text == 'Admin updated this'

    def test_partial_update_by_owner_role(self, api_client, db, root_comment):
        """Test that user with OWNER role can update any comment."""
        from django.contrib.auth import get_user_model
        from user_account.enums import UserRole
        
        User = get_user_model()
        owner_user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='ownerpass123'
        )
        owner_user.role = UserRole.OWNER
        owner_user.save()
        
        api_client.force_authenticate(user=owner_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {'text': 'Owner role updated this'}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        root_comment.refresh_from_db()
        assert root_comment.text == 'Owner role updated this'

    def test_partial_update_anonymous_forbidden(self, api_client, root_comment):
        """Test that anonymous users cannot update comments."""
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        data = {'text': 'Anonymous trying to update'}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # --- Delete Tests ---

    def test_delete_own_comment(self, api_client, user, root_comment):
        """Test that owner can delete their comment."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Comment.objects.count() == 0

    def test_delete_others_comment_forbidden(self, api_client, another_user, root_comment):
        """Test that non-owner cannot delete others' comments."""
        api_client.force_authenticate(user=another_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Comment.objects.count() == 1

    def test_delete_by_admin(self, api_client, admin_user, root_comment):
        """Test that admin can delete any comment."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Comment.objects.count() == 0

    def test_delete_by_admin_role(self, api_client, db, root_comment):
        """Test that user with ADMIN role can delete any comment."""
        from django.contrib.auth import get_user_model
        from user_account.enums import UserRole
        
        User = get_user_model()
        admin_user = User.objects.create_user(
            username='admin_role',
            email='admin_role@example.com',
            password='adminpass123'
        )
        admin_user.role = UserRole.ADMIN
        admin_user.save()
        
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Comment.objects.count() == 0

    def test_delete_anonymous_forbidden(self, api_client, root_comment):
        """Test that anonymous users cannot delete comments."""
        url = reverse('comment:comment-detail', kwargs={'pk': root_comment.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Comment.objects.count() == 1

    # --- Custom Actions Tests ---

    # --- Deactivate Tests (Bulk Actions) ---

    def test_deactivate_single_comment_with_comment_id(self, api_client, user, root_comment):
        """Test deactivating a single comment using comment_id."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_id': root_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'deactivated_count' in response.data
        root_comment.refresh_from_db()
        assert root_comment.is_active is False

    def test_deactivate_single_comment_with_comment_ids(self, api_client, user, root_comment):
        """Test deactivating a single comment using comment_ids list."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_ids': [root_comment.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'deactivated_count' in response.data
        root_comment.refresh_from_db()
        assert root_comment.is_active is False

    def test_deactivate_multiple_comments(self, api_client, admin_user, root_comment, reply_comment):
        """Test deactivating multiple comments at once."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_ids': [root_comment.id, reply_comment.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'deactivated_count' in response.data
        # Refresh and check both comments
        root_comment.refresh_from_db()
        reply_comment.refresh_from_db()
        assert root_comment.is_active is False
        assert reply_comment.is_active is False

    def test_deactivate_comment_with_descendants(self, api_client, user, root_comment, reply_comment):
        """Test that deactivating a comment also deactivates its descendants."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_id': root_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        # Should deactivate root + reply = 2 comments
        assert response.data['deactivated_count'] >= 1
        root_comment.refresh_from_db()
        reply_comment.refresh_from_db()
        assert root_comment.is_active is False
        assert reply_comment.is_active is False

    def test_deactivate_without_comment_ids(self, api_client, admin_user):
        """Test that deactivate fails without comment IDs."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-deactivate')
        data = {}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deactivate_with_invalid_comment_ids(self, api_client, admin_user):
        """Test deactivating with non-existent comment IDs."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_ids': [99999, 88888]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_others_comment_forbidden(self, api_client, another_user, root_comment):
        """Test that non-owner cannot deactivate others' comments."""
        api_client.force_authenticate(user=another_user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_id': root_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_by_admin(self, api_client, admin_user, root_comment):
        """Test that admin can deactivate any comment."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_id': root_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        root_comment.refresh_from_db()
        assert root_comment.is_active is False

    def test_deactivate_anonymous_forbidden(self, api_client, root_comment):
        """Test that anonymous users cannot deactivate comments."""
        url = reverse('comment:comment-deactivate')
        data = {'comment_id': root_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # --- Activate Tests (Bulk Actions) ---

    def test_activate_single_comment_with_comment_id(self, api_client, admin_user, inactive_comment):
        """Test activating a single comment using comment_id."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {'comment_id': inactive_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'activated_count' in response.data
        assert response.data['activated_count'] == 1
        inactive_comment.refresh_from_db()
        assert inactive_comment.is_active is True

    def test_activate_single_comment_with_comment_ids(self, api_client, admin_user, inactive_comment):
        """Test activating a single comment using comment_ids list."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {'comment_ids': [inactive_comment.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'activated_count' in response.data
        assert response.data['activated_count'] == 1
        inactive_comment.refresh_from_db()
        assert inactive_comment.is_active is True

    def test_activate_multiple_comments(self, api_client, admin_user, db):
        """Test activating multiple comments at once."""
        from comment.models import Comment
        
        # Create multiple inactive comments
        comment1 = Comment.objects.create(
            text='Inactive 1',
            display_name='User1',
            is_active=False
        )
        comment2 = Comment.objects.create(
            text='Inactive 2',
            display_name='User2',
            is_active=False
        )
        
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {'comment_ids': [comment1.id, comment2.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['activated_count'] == 2
        comment1.refresh_from_db()
        comment2.refresh_from_db()
        assert comment1.is_active is True
        assert comment2.is_active is True

    def test_activate_without_comment_ids(self, api_client, admin_user):
        """Test that activate fails without comment IDs."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_with_invalid_comment_ids(self, api_client, admin_user):
        """Test activating with non-existent comment IDs."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {'comment_ids': [99999, 88888]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activate_by_owner_role(self, api_client, db, inactive_comment):
        """Test that user with OWNER role can activate comments."""
        from django.contrib.auth import get_user_model
        from user_account.enums import UserRole
        
        User = get_user_model()
        owner_user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='ownerpass123'
        )
        owner_user.role = UserRole.OWNER
        owner_user.save()
        
        api_client.force_authenticate(user=owner_user)
        url = reverse('comment:comment-activate')
        data = {'comment_id': inactive_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        inactive_comment.refresh_from_db()
        assert inactive_comment.is_active is True

    def test_activate_by_regular_user_forbidden(self, api_client, user, inactive_comment):
        """Test that regular users cannot activate comments."""
        api_client.force_authenticate(user=user)
        url = reverse('comment:comment-activate')
        data = {'comment_id': inactive_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_activate_anonymous_forbidden(self, api_client, inactive_comment):
        """Test that anonymous users cannot activate comments."""
        url = reverse('comment:comment-activate')
        data = {'comment_id': inactive_comment.id}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_with_duplicate_ids(self, api_client, admin_user, root_comment):
        """Test that duplicate IDs are rejected."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-deactivate')
        data = {'comment_ids': [root_comment.id, root_comment.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_with_duplicate_ids(self, api_client, admin_user, inactive_comment):
        """Test that duplicate IDs are rejected."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('comment:comment-activate')
        data = {'comment_ids': [inactive_comment.id, inactive_comment.id]}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST