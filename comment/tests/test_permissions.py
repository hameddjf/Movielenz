"""
Tests for comment permissions.

This module contains tests for custom permission classes.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from comment.permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdmin
from comment.views import CommentViewSet

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestIsOwnerOrAdminOrReadOnly:
    """Test cases for IsOwnerOrAdminOrReadOnly permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrAdminOrReadOnly()
        self.view = CommentViewSet()

    def test_read_permission_for_anonymous(self):
        """Test that anonymous users can read."""
        request = self.factory.get('/comments/')
        request.user = None
        
        assert self.permission.has_permission(request, self.view)

    def test_create_permission_for_anonymous(self):
        """Test that anonymous users can create comments."""
        request = self.factory.post('/comments/')
        request.user = None
        
        assert self.permission.has_permission(request, self.view)

    def test_update_permission_denied_for_anonymous(self, root_comment):
        """Test that anonymous users cannot update."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = None
        
        assert not self.permission.has_permission(request, self.view)

    def test_owner_can_update(self, user, root_comment):
        """Test that comment owner can update."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)

    def test_non_owner_cannot_update(self, another_user, root_comment):
        """Test that non-owner cannot update."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = another_user
        
        assert not self.permission.has_object_permission(request, self.view, root_comment)

    def test_admin_can_update_any(self, admin_user, root_comment):
        """Test that admin can update any comment."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = admin_user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)


class TestIsOwnerOrAdmin:
    """Test cases for IsOwnerOrAdmin permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrAdmin()
        self.view = CommentViewSet()

    def test_permission_denied_for_anonymous(self):
        """Test that anonymous users have no access."""
        request = self.factory.patch('/comments/1/')
        request.user = None
        
        assert not self.permission.has_permission(request, self.view)

    def test_owner_role_has_permission(self, db):
        """Test that user with OWNER role has permission."""
        from user_account.enums import UserRole
        
        owner_user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='ownerpass123'
        )
        owner_user.role = UserRole.OWNER
        owner_user.save()
        
        request = self.factory.patch('/comments/1/')
        request.user = owner_user
        
        assert self.permission.has_permission(request, self.view)

    def test_admin_role_has_permission(self, db):
        """Test that user with ADMIN role has permission."""
        from user_account.enums import UserRole
        
        admin_user = User.objects.create_user(
            username='admin_role',
            email='admin_role@example.com',
            password='adminpass123'
        )
        admin_user.role = UserRole.ADMIN
        admin_user.save()
        
        request = self.factory.patch('/comments/1/')
        request.user = admin_user
        
        assert self.permission.has_permission(request, self.view)

    def test_django_staff_has_permission(self, admin_user):
        """Test that Django staff/superuser has permission."""
        request = self.factory.patch('/comments/1/')
        request.user = admin_user
        
        assert self.permission.has_permission(request, self.view)

    def test_comment_author_has_object_permission(self, user, root_comment):
        """Test that comment author has object-level permission."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)

    def test_non_author_no_object_permission(self, another_user, root_comment):
        """Test that non-author without special role has no object-level permission."""
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = another_user
        
        assert not self.permission.has_object_permission(request, self.view, root_comment)

    def test_owner_role_has_object_permission(self, db, root_comment):
        """Test that user with OWNER role has object-level permission on any comment."""
        from user_account.enums import UserRole
        
        owner_user = User.objects.create_user(
            username='owner2',
            email='owner2@example.com',
            password='ownerpass123'
        )
        owner_user.role = UserRole.OWNER
        owner_user.save()
        
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = owner_user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)

    def test_admin_role_has_object_permission(self, db, root_comment):
        """Test that user with ADMIN role has object-level permission on any comment."""
        from user_account.enums import UserRole
        
        admin_user = User.objects.create_user(
            username='admin_role2',
            email='admin_role2@example.com',
            password='adminpass123'
        )
        admin_user.role = UserRole.ADMIN
        admin_user.save()
        
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = admin_user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)

    def test_normal_user_no_object_permission(self, db, root_comment):
        """Test that normal user without author access has no object-level permission."""
        from user_account.enums import UserRole
        
        normal_user = User.objects.create_user(
            username='normal',
            email='normal@example.com',
            password='normalpass123'
        )
        normal_user.role = UserRole.NORMAL_USER
        normal_user.save()
        
        request = self.factory.patch(f'/comments/{root_comment.id}/')
        request.user = normal_user
        
        assert not self.permission.has_object_permission(request, self.view, root_comment)