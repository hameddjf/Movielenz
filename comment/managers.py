"""
Custom managers for comment models.

This module provides custom QuerySet and Manager classes for the Comment model
to encapsulate common query patterns and business logic.
"""

from django.db import models
from mptt.managers import TreeManager
from mptt.querysets import TreeQuerySet


class CommentQuerySet(TreeQuerySet):
    """Custom QuerySet for Comment model with additional filtering methods."""

    def active(self):
        """
        Return only active comments.
        
        Returns:
            QuerySet: Filtered queryset containing only active comments.
        """
        return self.filter(is_active=True)

    def inactive(self):
        """
        Return only inactive comments.
        
        Returns:
            QuerySet: Filtered queryset containing only inactive comments.
        """
        return self.filter(is_active=False)

    def by_author(self, user):
        """
        Return comments by a specific author.
        
        Args:
            user: User instance to filter comments by.
            
        Returns:
            QuerySet: Filtered queryset containing comments by the specified author.
        """
        return self.filter(author=user)

    def for_object(self, obj):
        """
        Return comments for a specific object.
        
        Args:
            obj: Django model instance to get comments for.
            
        Returns:
            QuerySet: Filtered queryset containing comments for the object.
        """
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, object_id=obj.pk)

    def root_comments(self):
        """
        Return only root-level comments (comments without parents).
        
        Returns:
            QuerySet: Filtered queryset containing only root comments.
        """
        return self.filter(parent__isnull=True)

    def with_author_details(self):
        """
        Optimize query by selecting related author information.
        
        Returns:
            QuerySet: Queryset with author information prefetched.
        """
        return self.select_related('author')


class CommentManager(TreeManager):
    """Custom manager for Comment model."""

    def get_queryset(self):
        """
        Return the custom CommentQuerySet.
        
        Returns:
            CommentQuerySet: Custom queryset with additional methods.
        """
        return CommentQuerySet(self.model, using=self._db)

    def active(self):
        """Proxy method to CommentQuerySet.active()."""
        return self.get_queryset().active()

    def inactive(self):
        """Proxy method to CommentQuerySet.inactive()."""
        return self.get_queryset().inactive()

    def by_author(self, user):
        """Proxy method to CommentQuerySet.by_author()."""
        return self.get_queryset().by_author(user)

    def for_object(self, obj):
        """Proxy method to CommentQuerySet.for_object()."""
        return self.get_queryset().for_object(obj)

    def root_comments(self):
        """Proxy method to CommentQuerySet.root_comments()."""
        return self.get_queryset().root_comments()

    def with_author_details(self):
        """Proxy method to CommentQuerySet.with_author_details()."""
        return self.get_queryset().with_author_details()