"""
Custom user manager with specialized query methods.
Handles user creation and provides filtered querysets.
"""
from django.contrib.auth.models import BaseUserManager
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q

from .enums import SubscriptionStatus, UserRole


class UserManager(BaseUserManager):
    """Custom manager for User model with enhanced creation methods."""

    def _create_user(self, email, password, **extra_fields):
        """
        Internal method to create and save a user with email and password.
        
        Args:
            email: User's email address (required)
            password: User's password (required)
            **extra_fields: Additional fields for user model
            
        Returns:
            User instance
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError(_('Email address is required for user creation'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with the given email and password.
        
        Args:
            email: User's email address
            password: User's password (optional)
            **extra_fields: Additional user fields
            
        Returns:
            User instance with default permissions
        """
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', UserRole.NORMAL_USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with admin privileges.
        
        Args:
            email: Superuser's email address
            password: Superuser's password
            **extra_fields: Additional superuser fields
            
        Returns:
            User instance with superuser permissions
            
        Raises:
            ValueError: If is_superuser is not True
        """
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('activated', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        # Auto-set is_staff based on role
        extra_fields['is_staff'] = extra_fields.get('role') in UserRole.get_staff_roles()

        return self._create_user(email, password, **extra_fields)

    def get_active_premium_users(self):
        """
        Retrieve users with active premium subscriptions.
        
        Returns:
            QuerySet of users with valid premium subscriptions
        """
        now = timezone.now()
        return self.filter(
            subscription_status=SubscriptionStatus.PREMIUM,
            subscription_end_date__gte=now,
            is_active=True
        )

    def get_users_by_preferred_genre(self, genre_input):
        """
        Find users who prefer a specific genre.
        
        Args:
            genre_input: Genre instance, slug, or name
            
        Returns:
            QuerySet of users preferring the specified genre
        """
        from movielenz.models import Genre

        try:
            if isinstance(genre_input, Genre):
                genre = genre_input
            elif isinstance(genre_input, str):
                genre = Genre.objects.get(Q(slug=genre_input) | Q(name=genre_input))
            else:
                raise ValueError(_("Input must be a Genre instance or string (slug/name)"))
        except Genre.DoesNotExist:
            return self.none()

        return self.filter(preferred_genres=genre, is_active=True)

    def get_users_who_favorited_item(self, content_object):
        """
        Find users who favorited a specific content item.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            QuerySet of users who favorited the content
        """
        content_type = ContentType.objects.get_for_model(content_object)
        return self.filter(
            is_active=True,
            user_favorites__content_type=content_type,
            user_favorites__object_id=content_object.pk
        ).distinct()

    def get_users_with_watchlist_item(self, content_object):
        """
        Find users who added a specific item to their watchlist.
        
        Args:
            content_object: Movie or Series instance
            
        Returns:
            QuerySet of users with the item in watchlist
        """
        content_type = ContentType.objects.get_for_model(content_object)
        return self.filter(
            is_active=True,
            user_watchlist__content_type=content_type,
            user_watchlist__object_id=content_object.pk
        ).distinct()

    def get_inactive_users(self, days_inactive=30):
        """
        Find users who haven't logged in for a specified period.
        
        Args:
            days_inactive: Number of days of inactivity (default: 30)
            
        Returns:
            QuerySet of inactive users
        """
        threshold_date = timezone.now() - timezone.timedelta(days=days_inactive)
        return self.filter(
            last_login__lt=threshold_date,
            is_active=True
        )

    def get_expiring_subscriptions(self, days_before_expiry=7):
        """
        Find users whose premium subscriptions are expiring soon.
        
        Args:
            days_before_expiry: Days before expiration to check (default: 7)
            
        Returns:
            QuerySet of users with expiring subscriptions
        """
        now = timezone.now()
        expiry_threshold = now + timezone.timedelta(days=days_before_expiry)
        
        return self.filter(
            subscription_status=SubscriptionStatus.PREMIUM,
            subscription_end_date__gte=now,
            subscription_end_date__lte=expiry_threshold,
            is_active=True
        )