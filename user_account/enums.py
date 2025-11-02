"""
User account enumerations for subscription status and user roles.
Provides type-safe choices for user-related fields.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionStatus(models.TextChoices):
    """Defines available subscription status options for users."""
    FREE = 'free', _('Free')
    PREMIUM = 'premium', _('Premium')
    CANCELLED = 'cancelled', _('Cancelled')
    EXPIRED = 'expired', _('Expired')


class UserRole(models.TextChoices):
    """Defines hierarchical user roles within the system."""
    OWNER = 'OWNER', _('Owner')
    ADMIN = 'ADMIN', _('Administrator')
    PREMIUM_USER = 'PREMIUM_USER', _('Premium User')
    NORMAL_USER = 'NORMAL_USER', _('Normal User')

    @classmethod
    def get_staff_roles(cls):
        """Returns roles that have staff privileges."""
        return [cls.ADMIN, cls.OWNER]

    @classmethod
    def get_premium_roles(cls):
        """Returns roles that have premium access."""
        return [cls.PREMIUM_USER, cls.ADMIN, cls.OWNER]