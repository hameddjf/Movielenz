"""
Pytest fixtures for comment application tests.

This module provides reusable fixtures for testing the comment application.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from comment.models import Comment

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide an API client for testing."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a regular user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def another_user(db):
    """Create and return another regular user."""
    return User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='anotherpass123'
    )


@pytest.fixture
def content_type(db):
    """Get or create a content type for testing."""
    return ContentType.objects.get_for_model(User)


@pytest.fixture
def root_comment(db, user, content_type):
    """Create and return a root comment."""
    return Comment.objects.create(
        author=user,
        content_type=content_type,
        object_id=user.id,
        text='This is a root comment for testing.',
        is_active=True
    )


@pytest.fixture
def reply_comment(db, user, content_type, root_comment):
    """Create and return a reply comment."""
    return Comment.objects.create(
        author=user,
        content_type=content_type,
        object_id=user.id,
        parent=root_comment,
        text='This is a reply comment for testing.',
        is_active=True
    )


@pytest.fixture
def inactive_comment(db, user, content_type):
    """Create and return an inactive comment."""
    return Comment.objects.create(
        author=user,
        content_type=content_type,
        object_id=user.id,
        text='This is an inactive comment.',
        is_active=False
    )


@pytest.fixture
def anonymous_comment(db, content_type, user):
    """Create and return a comment without author (anonymous)."""
    return Comment.objects.create(
        author=None,
        content_type=content_type,
        object_id=user.id,
        text='This is an anonymous comment.',
        is_active=True
    )