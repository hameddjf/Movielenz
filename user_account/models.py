"""
User account models for authentication and content interaction.
Includes User model and models for watchlist, favorites, and watch history.
"""
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from model_utils import FieldTracker

from .managers import UserManager
from .enums import SubscriptionStatus, UserRole


class User(AbstractUser):
    """
    Custom user model with email-based authentication.
    Extends Django's AbstractUser with additional fields for subscriptions and preferences.
    """
    
    # Override username to make it non-unique (email is the unique identifier)
    username = models.CharField(
        _('Username'),
        max_length=150,
        unique=False,
        help_text=_('Non-unique username for display purposes'),
    )
    
    # Primary authentication field
    email = models.EmailField(
        _('Email Address'),
        unique=True,
        db_index=True,
        error_messages={
            'unique': _("A user with this email already exists"),
        }
    )
    
    # Account activation status
    activated = models.BooleanField(
        _('Activated'),
        default=False,
        help_text=_('Account activation status. Inactive users cannot log in')
    )
    
    # Personal information
    first_name = models.CharField(_('First Name'), max_length=150, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=150, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        verbose_name=_('Profile Picture')
    )
    tracker = FieldTracker(fields=['subscription_status', 'is_active', 'activated'])
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date of Birth')
    )
    
    # Subscription fields
    subscription_status = models.CharField(
        max_length=10,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
        verbose_name=_('Subscription Status'),
        db_index=True
    )
    subscription_start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Subscription Start Date')
    )
    subscription_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Subscription End Date'),
        db_index=True
    )
    
    # User preferences
    preferred_language = models.CharField(
        max_length=10,
        default='fa',
        verbose_name=_('Preferred Language'),
        help_text=_("Example: 'fa' for Persian, 'en' for English")
    )
    preferred_genres = models.ManyToManyField(
        'movielenz.Genre',
        blank=True,
        related_name='users_preferring',
        verbose_name=_('Preferred Genres')
    )
    
    # Role and permissions
    role = models.CharField(
        _('User Role'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.NORMAL_USER,
        help_text=_('User role in the system'),
        db_index=True
    )
    
    # Generic relations for content interactions
    watchlist = GenericRelation(
        'WatchlistItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_watchlist'
    )
    favorites = GenericRelation(
        'FavoriteItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_favorites'
    )
    recently_watched_log = GenericRelation(
        'RecentlyWatchedItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_recently_watched'
    )
    
    # Many-to-many relationships (with custom related names to avoid conflicts)
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('Groups'),
        blank=True,
        help_text=_('Groups this user belongs to'),
        related_name="account_users",
        related_query_name="account_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('User Permissions'),
        blank=True,
        help_text=_('Specific permissions for this user'),
        related_name="account_users",
        related_query_name="account_user",
    )

    # Authentication configuration
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['subscription_status', 'subscription_end_date']),
            models.Index(fields=['role']),
            models.Index(fields=['-date_joined']),
            models.Index(fields=['is_active', 'activated']),
        ]

    def __str__(self):
        """Return email as string representation."""
        return self.email

    @property
    def is_staff(self):
        """Check if user has staff privileges based on role."""
        return self.role in UserRole.get_staff_roles()

    @is_staff.setter
    def is_staff(self, value):
        """Set staff status by adjusting user role."""
        if value and self.role not in UserRole.get_staff_roles():
            self.role = UserRole.ADMIN

    @property
    def is_superuser_property(self):
        """Check if user is superuser (owner role)."""
        return self.role == UserRole.OWNER

    def get_full_name(self):
        """Return user's full name."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Return user's first name or email."""
        return self.first_name or self.email.split('@')[0]

    def has_active_premium_subscription(self):
        """
        Check if user has an active premium subscription.
        
        Returns:
            bool: True if subscription is active and not expired
        """
        if self.subscription_status != SubscriptionStatus.PREMIUM:
            return False
        
        if self.subscription_end_date is None:
            return False
        
        return self.subscription_end_date >= timezone.now()

    def activate_premium_subscription(self, duration_days=30):
        """
        Activate premium subscription for specified duration.
        
        Args:
            duration_days: Subscription duration in days (default: 30)
        """
        now = timezone.now()
        self.subscription_status = SubscriptionStatus.PREMIUM
        self.subscription_start_date = now
        self.subscription_end_date = now + timezone.timedelta(days=duration_days)
        self.save(update_fields=['subscription_status', 'subscription_start_date', 'subscription_end_date'])

    def cancel_subscription(self):
        """Cancel user's premium subscription."""
        self.subscription_status = SubscriptionStatus.CANCELLED
        self.save(update_fields=['subscription_status'])

    def add_to_watchlist(self, content_object):
        """
        Add content item to user's watchlist.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            bool: True if added, False if already exists
        """
        content_type = ContentType.objects.get_for_model(content_object)
        item, created = WatchlistItem.objects.get_or_create(
            user=self,
            content_type=content_type,
            object_id=content_object.pk
        )
        return created

    def remove_from_watchlist(self, content_object):
        """
        Remove content item from user's watchlist.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            bool: True if removed, False if not found
        """
        content_type = ContentType.objects.get_for_model(content_object)
        deleted_count, _ = WatchlistItem.objects.filter(
            user=self,
            content_type=content_type,
            object_id=content_object.pk
        ).delete()
        return deleted_count > 0

    def add_to_favorites(self, content_object):
        """
        Add content item to user's favorites.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            bool: True if added, False if already exists
        """
        content_type = ContentType.objects.get_for_model(content_object)
        item, created = FavoriteItem.objects.get_or_create(
            user=self,
            content_type=content_type,
            object_id=content_object.pk
        )
        return created

    def remove_from_favorites(self, content_object):
        """
        Remove content item from user's favorites.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            bool: True if removed, False if not found
        """
        content_type = ContentType.objects.get_for_model(content_object)
        deleted_count, _ = FavoriteItem.objects.filter(
            user=self,
            content_type=content_type,
            object_id=content_object.pk
        ).delete()
        return deleted_count > 0

    def add_or_update_recently_watched(self, content_object, progress_seconds=None):
        """
        Add or update recently watched content with progress tracking.
        
        Args:
            content_object: Movie or Series instance
            progress_seconds: Playback progress in seconds (optional)
            
        Returns:
            RecentlyWatchedItem instance
        """
        content_type = ContentType.objects.get_for_model(content_object)
        item, created = RecentlyWatchedItem.objects.update_or_create(
            user=self,
            content_type=content_type,
            object_id=content_object.pk,
            defaults={
                'watched_at': timezone.now(),
                'progress_seconds': progress_seconds
            }
        )
        return item

    def get_watchlist_items(self, limit=None):
        """
        Retrieve user's watchlist items ordered by date added.
        
        Args:
            limit: Maximum number of items to return (optional)
            
        Returns:
            QuerySet of WatchlistItem objects
        """
        queryset = self.watchlist.all().select_related('content_type').order_by('-added_at')
        return queryset[:limit] if limit else queryset

    def get_favorite_items(self, limit=None):
        """
        Retrieve user's favorite items ordered by date added.
        
        Args:
            limit: Maximum number of items to return (optional)
            
        Returns:
            QuerySet of FavoriteItem objects
        """
        queryset = self.favorites.all().select_related('content_type').order_by('-added_at')
        return queryset[:limit] if limit else queryset

    def get_recently_watched_items(self, limit=20):
        """
        Retrieve user's recently watched items ordered by watch time.
        
        Args:
            limit: Maximum number of items to return (default: 20)
            
        Returns:
            QuerySet of RecentlyWatchedItem objects
        """
        return self.recently_watched_log.all().select_related('content_type').order_by('-watched_at')[:limit]

    def clean(self):
        """Validate user data before saving."""
        super().clean()
        
        # Validate subscription dates
        if self.subscription_start_date and self.subscription_end_date:
            if self.subscription_end_date < self.subscription_start_date:
                raise ValidationError(_('Subscription end date cannot be before start date'))


class UserContentInteractionBase(models.Model):
    """
    Abstract base model for user-content interactions.
    Provides common fields for watchlist, favorites, and watch history.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    
    # Generic foreign key for flexible content types
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type")
    )
    object_id = models.PositiveIntegerField(verbose_name=_("Object ID"))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Added At")
    )

    class Meta:
        abstract = True
        unique_together = ('user', 'content_type', 'object_id')
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['user', 'content_type', 'object_id']),
            models.Index(fields=['-added_at']),
        ]

    def __str__(self):
        """Return string representation of interaction."""
        return f"{self.user.email} - {self.content_object}"


class WatchlistItem(UserContentInteractionBase):
    """User's watchlist items - content they want to watch later."""
    
    class Meta(UserContentInteractionBase.Meta):
        verbose_name = _("Watchlist Item")
        verbose_name_plural = _("Watchlist Items")


class FavoriteItem(UserContentInteractionBase):
    """User's favorite items - content they liked."""
    
    class Meta(UserContentInteractionBase.Meta):
        verbose_name = _("Favorite Item")
        verbose_name_plural = _("Favorite Items")


class RecentlyWatchedItem(models.Model):
    """
    Tracks user's recently watched content with progress.
    Allows resuming playback from last position.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recently_watched_entries',
        verbose_name=_("User")
    )
    
    # Generic foreign key for content
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type")
    )
    object_id = models.PositiveIntegerField(verbose_name=_("Object ID"))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    watched_at = models.DateTimeField(
        verbose_name=_("Watched At"),
        db_index=True
    )
    progress_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Progress (seconds)"),
        help_text=_("Playback progress in seconds")
    )

    class Meta:
        verbose_name = _("Recently Watched Item")
        verbose_name_plural = _("Recently Watched Items")
        ordering = ['-watched_at']
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['user', '-watched_at']),
            models.Index(fields=['user', 'content_type', 'object_id']),
        ]

    def __str__(self):
        """Return string representation with watch timestamp."""
        return f"{self.user.email} - {self.content_object} @ {self.watched_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """Auto-set watched_at timestamp if not provided."""
        if not self.watched_at:
            self.watched_at = timezone.now()
        super().save(*args, **kwargs)

    def get_progress_percentage(self, total_duration_seconds):
        """
        Calculate watch progress percentage.
        
        Args:
            total_duration_seconds: Total content duration in seconds
            
        Returns:
            float: Progress percentage (0-100)
        """
        if not self.progress_seconds or not total_duration_seconds:
            return 0.0
        return min((self.progress_seconds / total_duration_seconds) * 100, 100.0)