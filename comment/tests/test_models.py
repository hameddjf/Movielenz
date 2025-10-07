"""
Tests for comment models.

This module contains unit tests for the Comment model and its methods.
"""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from comment.models import Comment
from comment.constants import MAX_REPLY_DEPTH

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestCommentModel:
    """Test cases for the Comment model."""

    def test_create_root_comment(self, user, content_type):
        """Test creating a root comment."""
        comment = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            text='Test comment'
        )
        
        assert comment.id is not None
        assert comment.author == user
        assert comment.text == 'Test comment'
        assert comment.is_active is True
        assert comment.parent is None
        assert comment.is_root is True

    def test_create_reply_comment(self, user, content_type, root_comment):
        """Test creating a reply to a comment."""
        reply = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=root_comment,
            text='Test reply'
        )
        
        assert reply.parent == root_comment
        assert reply.is_root is False
        assert reply.level == 1

    def test_max_depth_enforcement(self, user, content_type):
        """Test that reply depth is enforced to maximum 3 levels."""
        level1 = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            text='Level 1'
        )
        
        level2 = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=level1,
            text='Level 2'
        )
        
        level3 = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=level2,
            text='Level 3'
        )
        
        level4_attempt = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=level3,
            text='Level 4 - should become Level 3'
        )
        
        assert level4_attempt.parent == level2
        assert level4_attempt.level == 2

    def test_comment_text_validation(self, user, content_type):
        """Test that empty or whitespace-only text raises validation error."""
        with pytest.raises(ValidationError):
            comment = Comment(
                author=user,
                content_type=content_type,
                object_id=user.id,
                text='   '
            )
            comment.full_clean()

    def test_deactivate_comment(self, root_comment, reply_comment):
        """Test deactivating a comment and its descendants."""
        root_comment.deactivate()
        
        root_comment.refresh_from_db()
        reply_comment.refresh_from_db()
        
        assert root_comment.is_active is False
        assert reply_comment.is_active is False

    def test_activate_comment(self, inactive_comment):
        """Test activating a comment."""
        inactive_comment.activate()
        inactive_comment.refresh_from_db()
        
        assert inactive_comment.is_active is True

    def test_comment_str_representation(self, user, content_type):
        """Test string representation of comment."""
        comment = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            text='Test comment for string representation'
        )
        
        str_repr = str(comment)
        assert 'testuser' in str_repr or user.get_full_name() in str_repr
        assert 'Test comment for string representation'[:50] in str_repr

    def test_reply_count_property(self, root_comment):
        """Test reply_count property."""
        assert root_comment.reply_count == 0
        
        Comment.objects.create(
            author=root_comment.author,
            content_type=root_comment.content_type,
            object_id=root_comment.object_id,
            parent=root_comment,
            text='Reply 1'
        )
        
        assert root_comment.reply_count == 1

    def test_get_descendants_active(self, root_comment, user, content_type):
        """Test getting only active descendants."""
        reply1 = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=root_comment,
            text='Active reply',
            is_active=True
        )
        
        reply2 = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            parent=root_comment,
            text='Inactive reply',
            is_active=False
        )
        
        active_descendants = root_comment.get_descendants_active()
        assert reply1 in active_descendants
        assert reply2 not in active_descendants

    def test_anonymous_comment_creation(self, content_type, user):
        """Test creating a comment without an author."""
        comment = Comment.objects.create(
            author=None,
            content_type=content_type,
            object_id=user.id,
            text='Anonymous comment'
        )
        
        assert comment.author is None
        assert 'Anonymous' in str(comment)


class TestCommentManager:
    """Test cases for the Comment manager and queryset."""

    def test_active_queryset(self, root_comment, inactive_comment):
        """Test active() queryset method."""
        active_comments = Comment.objects.active()
        
        assert root_comment in active_comments
        assert inactive_comment not in active_comments

    def test_inactive_queryset(self, root_comment, inactive_comment):
        """Test inactive() queryset method."""
        inactive_comments = Comment.objects.inactive()
        
        assert inactive_comment in inactive_comments
        assert root_comment not in inactive_comments

    def test_by_author_queryset(self, user, another_user, content_type):
        """Test by_author() queryset method."""
        user_comment = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            text='User comment'
        )
        
        another_comment = Comment.objects.create(
            author=another_user,
            content_type=content_type,
            object_id=another_user.id,
            text='Another user comment'
        )
        
        user_comments = Comment.objects.by_author(user)
        
        assert user_comment in user_comments
        assert another_comment not in user_comments

    def test_for_object_queryset(self, user, another_user, content_type):
        """Test for_object() queryset method."""
        comment_for_user = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=user.id,
            text='Comment for user'
        )
        
        comment_for_another = Comment.objects.create(
            author=user,
            content_type=content_type,
            object_id=another_user.id,
            text='Comment for another user'
        )
        
        comments_for_user = Comment.objects.for_object(user)
        
        assert comment_for_user in comments_for_user
        assert comment_for_another not in comments_for_user

    def test_root_comments_queryset(self, root_comment, reply_comment):
        """Test root_comments() queryset method."""
        root_comments = Comment.objects.root_comments()
        
        assert root_comment in root_comments
        assert reply_comment not in root_comments