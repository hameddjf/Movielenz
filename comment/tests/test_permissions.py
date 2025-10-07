"""
Tests for comment permissions.

This module contains tests for custom permission classes.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from comment.permissions import IsOwnerOrAdminOrReadOnly
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
        request = self.factory.put(f'/comments/{root_comment.id}/')
        request.user = None
        
        assert not self.permission.has_permission(request, self.view)

    def test_owner_can_update(self, user, root_comment):
        """Test that comment owner can update."""
        request = self.factory.put(f'/comments/{root_comment.id}/')
        request.user = user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)

    def test_non_owner_cannot_update(self, another_user, root_comment):
        """Test that non-owner cannot update."""
        request = self.factory.put(f'/comments/{root_comment.id}/')
        request.user = another_user
        
        assert not self.permission.has_object_permission(request, self.view, root_comment)

    def test_admin_can_update_any(self, admin_user, root_comment):
        """Test that admin can update any comment."""
        request = self.factory.put(f'/comments/{root_comment.id}/')
        request.user = admin_user
        
        assert self.permission.has_object_permission(request, self.view, root_comment)