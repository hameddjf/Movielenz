"""
Custom managers for the Reaction model.
"""
from django.db import models
from django.db.models import Count, Case, When
from django.contrib.contenttypes.models import ContentType


class ReactionQuerySet(models.QuerySet):
    """
    Custom QuerySet for Reaction model with analytical methods.
    """

    def for_object(self, obj):
        """
        Filter reactions for a specific object.
        """
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(
            content_type=content_type,
            object_id=obj.pk
        )

    def for_user(self, user):
        """
        Filter reactions created by a specific user.
        """
        return self.filter(user=user)

    def likes(self):
        """
        Filter only 'like' reactions.
        """
        return self.filter(value='like')

    def dislikes(self):
        """
        Filter only 'dislike' reactions.
        """
        return self.filter(value='dislike')

    def with_stats(self):
        """
        Annotate queryset with reaction statistics.
        """
        return self.annotate(
            likes_count=Count(
                Case(When(value='like', then=1)),
                distinct=True
            ),
            dislikes_count=Count(
                Case(When(value='dislike', then=1)),
                distinct=True
            ),
            total_count=Count('id', distinct=True)
        )


class ReactionManager(models.Manager):
    """
    Custom manager for Reaction model with analytical methods.
    """

    def get_queryset(self):
        """
        Return the custom QuerySet for all Reaction queries.
        """
        return ReactionQuerySet(self.model, using=self._db)

    def for_object(self, obj):
        """Proxy method to QuerySet.for_object()."""
        return self.get_queryset().for_object(obj)

    def for_user(self, user):
        """Proxy method to QuerySet.for_user()."""
        return self.get_queryset().for_user(user)

    def likes(self):
        """Proxy method to QuerySet.likes()."""
        return self.get_queryset().likes()

    def dislikes(self):
        """Proxy method to QuerySet.dislikes()."""
        return self.get_queryset().dislikes()

    def likes_count(self, obj=None):
        """
        Count total likes, optionally filtered by object.
        """
        queryset = self.get_queryset()
        if obj:
            queryset = queryset.for_object(obj)
        return queryset.likes().count()

    def dislikes_count(self, obj=None):
        """
        Count total dislikes, optionally filtered by object.
        """
        queryset = self.get_queryset()
        if obj:
            queryset = queryset.for_object(obj)
        return queryset.dislikes().count()

    def popularity_ratio(self, obj=None):
        """
        Calculate popularity ratio as percentage.
        """
        queryset = self.get_queryset()
        if obj:
            queryset = queryset.for_object(obj)

        likes = queryset.likes().count()
        dislikes = queryset.dislikes().count()
        total = likes + dislikes

        if total == 0:
            return 0.0

        popularity = (likes / total) * 100
        return round(popularity, 2)

    def get_statistics(self, obj=None):
        """
        Get comprehensive statistics dictionary.
        """
        queryset = self.get_queryset()
        if obj:
            queryset = queryset.for_object(obj)

        likes = queryset.likes().count()
        dislikes = queryset.dislikes().count()
        total = likes + dislikes

        return {
            'likes': likes,
            'dislikes': dislikes,
            'total': total,
            'popularity': self.popularity_ratio(obj) if obj else self.popularity_ratio()
        }

    def user_reaction(self, user, obj):
        """
        Get a user's reaction to a specific object.
        """
        if not user or not user.is_authenticated:
            return None
        try:
            return self.get_queryset().for_object(obj).get(user=user)
        except self.model.DoesNotExist:
            return None

    def toggle_reaction(self, request, obj, value):
        """
        Create, update, or delete a reaction for an authenticated or anonymous user.
        """
        content_type = ContentType.objects.get_for_model(obj)
        user = request.user

        lookup_kwargs = {
            'content_type': content_type,
            'object_id': obj.pk,
        }
        
        if user.is_authenticated:
            lookup_kwargs['user'] = user
        else:
            # For anonymous users, use session key
            if not request.session.session_key:
                request.session.create()
            lookup_kwargs['session_key'] = request.session.session_key

        try:
            reaction = self.get(**lookup_kwargs)
            
            if reaction.value == value:
                # Same reaction - remove it (toggle off)
                reaction.delete()
                return None, 'deleted'
            else:
                # Different reaction - update it
                reaction.value = value
                reaction.save(update_fields=['value', 'updated_at'])
                return reaction, 'updated'
                
        except self.model.DoesNotExist:
            # No reaction exists - create a new one
            create_kwargs = lookup_kwargs.copy()
            create_kwargs['value'] = value
            if not user.is_authenticated:
                create_kwargs['ip_address'] = request.META.get('REMOTE_ADDR')

            reaction = self.create(**create_kwargs)
            return reaction, 'created'