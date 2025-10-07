"""
Database models for the comment application.

This module defines the Comment model and related base models for managing
user comments on various objects throughout the application.
"""

import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from .managers import CommentManager
from .validators import validate_comment_text, validate_display_name
from .constants import MAX_REPLY_DEPTH, MAX_COMMENT_LENGTH

from user_account.models import User


class TimeStampedModel(models.Model):
    """
    Abstract base model providing timestamp fields.
    
    This model provides self-updating created_at and updated_at fields
    for tracking when records are created and modified.
    
    Attributes:
        created_at (DateTimeField): Timestamp when the record was created.
        updated_at (DateTimeField): Timestamp when the record was last updated.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('Timestamp when this record was created')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when this record was last updated')
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Comment(MPTTModel, TimeStampedModel):
    """
    Model representing a user comment.
    
    This model implements a hierarchical comment system using MPTT
    (Modified Preorder Tree Traversal) for efficient tree queries.
    Comments can be attached to any model using GenericForeignKey.
    
    Attributes:
        id (UUIDField): Unique identifier for the comment.
        author (ForeignKey): User who created the comment.
        display_name (CharField): Display name for the comment author.
        content_type (ForeignKey): Content type of the related object.
        object_id (PositiveIntegerField): ID of the related object.
        content_object (GenericForeignKey): The related object.
        parent (TreeForeignKey): Parent comment for nested replies.
        text (TextField): The comment text content.
        is_active (BooleanField): Whether the comment is active/visible.
        has_spoiler (BooleanField): Whether the comment contains spoilers.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for this comment')
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Author'),
        help_text=_('User who created this comment'),
        null=True,
        blank=True
    )

    display_name = models.CharField(
        max_length=100,
        validators=[validate_display_name],
        verbose_name=_('Display Name'),
        help_text=_('Name to display for this comment'),
        blank=False  
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content Type'),
        help_text=_('Type of the object this comment is attached to')
    )

    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID'),
        help_text=_('ID of the object this comment is attached to')
    )

    content_object = GenericForeignKey('content_type', 'object_id')

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Comment'),
        help_text=_('Parent comment for nested replies')
    )

    text = models.TextField(
        max_length=MAX_COMMENT_LENGTH,
        validators=[validate_comment_text],
        verbose_name=_('Comment Text'),
        help_text=_('The content of the comment')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active'),
        help_text=_('Whether this comment is active and visible')
    )

    has_spoiler = models.BooleanField(
        default=False,
        verbose_name=_('Has Spoiler'),
        help_text=_('Whether this comment contains spoilers')
    )

    objects = CommentManager()

    class MPTTMeta:
        order_insertion_by = ['-created_at']

    class Meta:
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        """Return string representation of the comment."""
        author_name = self.display_name or (self.author.get_full_name() if self.author else 'Anonymous')
        return f'Comment by {author_name} - {self.text[:50]}...'

    def clean(self):
        """
        Validate the comment before saving.
        
        Ensures that the reply depth doesn't exceed the maximum allowed depth.
        If a comment would be at depth 4 or higher, it adjusts the parent to
        maintain a maximum depth of 3.
        
        Raises:
            ValidationError: If validation fails.
        """
        # Don't call super().clean() before setting display_name
        # to avoid issues with MPTT
        
        if self.parent:
            parent_level = self.parent.level
            if parent_level >= MAX_REPLY_DEPTH - 1:
                self.parent = self.parent.parent

        # Set display_name if not provided
        # if not self.display_name:
        #     if self.author:
        #         self.display_name = self.author.get_full_name() or self.author.username
        #     else:
        #         self.display_name = 'Anonymous'
        
        # Now call super to run text validation
        super().clean()

    def save(self, *args, **kwargs):
        """
        Save the comment instance.
        
        Calls full_clean() before saving to ensure validation.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_root(self):
        """
        Check if this comment is a root comment.
        
        Returns:
            bool: True if this is a root comment, False otherwise.
        """
        return self.parent is None

    @property
    def reply_count(self):
        """
        Get the number of direct replies to this comment.
        
        Returns:
            int: Number of direct child comments.
        """
        return self.children.count()

    def get_descendants_active(self):
        """
        Get all active descendant comments.
        
        Returns:
            QuerySet: All active descendant comments.
        """
        return self.get_descendants().filter(is_active=True)

    def deactivate(self):
        """
        Deactivate this comment and all its descendants.
        
        This method sets is_active to False for this comment and all
        its child comments.
        """
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
        self.get_descendants().update(is_active=False)

    def activate(self):
        """
        Activate this comment.
        
        Note: This only activates the current comment, not its descendants.
        """
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])