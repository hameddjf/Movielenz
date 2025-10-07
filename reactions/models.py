import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .managers import ReactionManager

User = get_user_model()

class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-managed created_at and updated_at fields.
    
    This model should be inherited by all models that require timestamp tracking.
    It automatically handles creation and modification timestamps.
    
    Attributes:
        created_at (DateTimeField): Timestamp when the object was created.
        updated_at (DateTimeField): Timestamp when the object was last modified.
    """
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        db_index=True,
        help_text=_('Date and time when this object was created')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('Date and time when this object was last updated')
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def save(self, *args, **kwargs):
        """
        Override save method to perform custom operations before saving.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        # Perform any pre-save operations here
        super().save(*args, **kwargs)


class UUIDModel(models.Model):
    """
    Abstract base model that uses UUID as primary key.
    
    This provides better security and scalability compared to sequential integers.
    UUIDs are globally unique and don't expose information about record count.
    
    Attributes:
        id (UUIDField): UUID primary key for the model.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for this object')
    )

    class Meta:
        abstract = True


class AbstractBaseModel(UUIDModel, TimeStampedModel):
    """
    Combined abstract base model with UUID primary key and timestamp fields.
    
    This is the recommended base model for most models in the application.
    It combines UUID-based identification with automatic timestamp tracking.
    
    Features:
        - UUID primary key for security and scalability
        - Automatic created_at and updated_at timestamps
        - Ordering by creation date (newest first)
    """
    
    class Meta:
        abstract = True




class Reaction(AbstractBaseModel):
    """
    Model to store user reactions (like/dislike) to any content type.
    
    This model uses Django's ContentType framework to create generic relations,
    allowing reactions to be attached to any model in the project.
    
    Attributes:
        user (ForeignKey): The user who created the reaction. Can be null for anonymous users.
        session_key (CharField): Session key for anonymous users.
        ip_address (GenericIPAddressField): IP address of the user.
        content_type (ForeignKey): The content type of the related object.
        object_id (CharField): The ID of the related object.
        content_object (GenericForeignKey): Generic relation to any model.
        value (CharField): The reaction type ('like' or 'dislike').
    """

    class ReactionValue(models.TextChoices):
        """
        Enumeration of possible reaction values.
        """
        LIKE = 'like', _('Like')
        DISLIKE = 'dislike', _('Dislike')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name=_('user'),
        help_text=_('The user who created this reaction'),
        db_index=True,
        null=True, 
        blank=True
    )
    
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text=_('Session key for anonymous users'),
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('IP address for anonymous users')
    )

    # Generic relation fields
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('content type'),
        help_text=_('The type of content this reaction is attached to'),
        db_index=True
    )
    object_id = models.CharField(
        max_length=255,
        verbose_name=_('object id'),
        help_text=_('The ID of the content object'),
        db_index=True
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    value = models.CharField(
        max_length=10,
        choices=ReactionValue.choices,
        verbose_name=_('reaction value'),
        help_text=_('The type of reaction (like or dislike)'),
        db_index=True
    )

    # Custom manager
    objects = ReactionManager()

    class Meta:
        verbose_name = _('reaction')
        verbose_name_plural = _('reactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'user']),
            models.Index(fields=['content_type', 'object_id', 'session_key']),
            models.Index(fields=['user', 'value']),
            models.Index(fields=['content_type', 'object_id', 'value']),
        ]
        constraints = [
            # A reaction must be associated with either a user or a session key.
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False) | 
                    models.Q(session_key__isnull=False)
                ),
                name='user_or_session_required'
            ),
            # Ensure one reaction per authenticated user per object.
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                condition=models.Q(user__isnull=False),
                name='unique_user_reaction_per_object'
            ),
            # Ensure one reaction per anonymous session per object.
            models.UniqueConstraint(
                fields=['session_key', 'content_type', 'object_id'],
                condition=models.Q(session_key__isnull=False),
                name='unique_session_reaction_per_object'
            )
        ]

    def __str__(self):
        """
        String representation of the reaction.
        
        Returns:
            str: Human-readable description of the reaction.
        """
        actor = self.user.username if self.user else f"Anonymous User ({self.session_key[-5:] if self.session_key else '...'})"
        return f"{actor} {self.get_value_display()} {self.content_object}"

    def __repr__(self):
        """
        Developer-friendly representation of the reaction.
        
        Returns:
            str: Detailed representation for debugging.
        """
        actor = f"user={self.user.username}" if self.user else f"session={self.session_key}"
        return (
            f"<Reaction(id={self.id}, {actor}, "
            f"value={self.value}, object={self.content_object})>"
        )

    def clean(self):
        """
        Validate the model before saving.
        
        Raises:
            ValidationError: If validation fails.
        """
        super().clean()

        if not self.user and not self.session_key:
            raise ValidationError(_('A reaction must have either a user or a session key.'))

        # Validate that content_object exists
        if self.content_type and self.object_id:
            try:
                model_class = self.content_type.model_class()
                if not model_class.objects.filter(pk=self.object_id).exists():
                    raise ValidationError({
                        'object_id': _('The specified object does not exist.')
                    })
            except Exception as e:
                raise ValidationError({
                    'content_object': _(f'Invalid content object: {str(e)}')
                })

    def save(self, *args, **kwargs):
        """
        Override save to ensure validation and handle business logic.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_like(self):
        """
        Check if this is a like reaction.
        
        Returns:
            bool: True if reaction is a like.
        """
        return self.value == self.ReactionValue.LIKE

    @property
    def is_dislike(self):
        """
        Check if this is a dislike reaction.
        
        Returns:
            bool: True if reaction is a dislike.
        """
        return self.value == self.ReactionValue.DISLIKE

    def toggle(self):
        """
        Toggle the reaction value between like and dislike.
        
        Returns:
            Reaction: The updated reaction instance.
        """
        if self.is_like:
            self.value = self.ReactionValue.DISLIKE
        else:
            self.value = self.ReactionValue.LIKE
        
        self.save(update_fields=['value', 'updated_at'])
        return self