"""
Django signals for user-related events.
Handles automated actions on user lifecycle events.
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

import logging

from .models import WatchlistItem, FavoriteItem, RecentlyWatchedItem
from .enums import SubscriptionStatus

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handle actions after user is saved.
    
    Actions:
    - Send welcome email for new users
    - Log user creation
    - Create default preferences
    """
    if created:
        logger.info(f"New user created: {instance.email}")
        
        # Send welcome email (if activated)
        if instance.activated:
            try:
                send_welcome_email(instance)
            except Exception as e:
                logger.error(f"Failed to send welcome email to {instance.email}: {str(e)}")
        
        # Initialize user stats or preferences here if needed
        # Example: create default watchlist folder, etc.


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """
    Handle actions before user is saved.
    
    Actions:
    - Update subscription status based on dates
    - Normalize email
    """
    # Normalize email
    if instance.email:
        instance.email = instance.email.lower().strip()
    
    # Auto-expire subscriptions
    if instance.subscription_end_date:
        if instance.subscription_end_date < timezone.now():
            if instance.subscription_status == SubscriptionStatus.PREMIUM:
                instance.subscription_status = SubscriptionStatus.EXPIRED
                logger.info(f"Subscription expired for user: {instance.email}")


@receiver(post_save, sender=User)
def subscription_status_changed(sender, instance, created, **kwargs):
    """
    Handle subscription status changes.
    
    Actions:
    - Send notification email
    - Update user privileges
    - Log subscription changes
    """
    if not created and instance.tracker.has_changed('subscription_status'):
        old_status = instance.tracker.previous('subscription_status')
        new_status = instance.subscription_status
        
        logger.info(
            f"Subscription changed for {instance.email}: "
            f"{old_status} -> {new_status}"
        )
        
        # Send appropriate email
        if new_status == SubscriptionStatus.PREMIUM:
            send_premium_activated_email(instance)
        elif new_status == SubscriptionStatus.EXPIRED:
            send_subscription_expired_email(instance)
        elif new_status == SubscriptionStatus.CANCELLED:
            send_subscription_cancelled_email(instance)


@receiver(post_save, sender=WatchlistItem)
def watchlist_item_added(sender, instance, created, **kwargs):
    """
    Handle watchlist item addition.
    
    Actions:
    - Log addition
    - Update user stats
    """
    if created:
        logger.info(
            f"User {instance.user.email} added item to watchlist: "
            f"{instance.content_object}"
        )


@receiver(post_delete, sender=WatchlistItem)
def watchlist_item_removed(sender, instance, **kwargs):
    """
    Handle watchlist item removal.
    
    Actions:
    - Log removal
    """
    logger.info(
        f"User {instance.user.email} removed item from watchlist: "
        f"{instance.content_object}"
    )


@receiver(post_save, sender=FavoriteItem)
def favorite_item_added(sender, instance, created, **kwargs):
    """
    Handle favorite item addition.
    
    Actions:
    - Log addition
    - Update content popularity
    """
    if created:
        logger.info(
            f"User {instance.user.email} favorited: "
            f"{instance.content_object}"
        )


@receiver(post_save, sender=RecentlyWatchedItem)
def recently_watched_updated(sender, instance, created, **kwargs):
    """
    Handle watch history updates.
    
    Actions:
    - Log view
    - Update content view count
    - Track user preferences
    """
    action = "started watching" if created else "continued watching"
    logger.info(
        f"User {instance.user.email} {action}: "
        f"{instance.content_object} at {instance.progress_seconds}s"
    )


# Email sending functions
def send_welcome_email(user):
    """
    Send welcome email to new user.
    
    Args:
        user: User instance
    """
    subject = 'خوش آمدید به MovieLenz!'
    message = f"""
    سلام {user.get_full_name() or user.email}،
    
    به MovieLenz خوش آمدید! حساب کاربری شما با موفقیت ایجاد شد.
    
    اکنون می‌توانید از تمامی امکانات پلتفرم استفاده کنید.
    
    با احترام،
    تیم MovieLenz
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )


def send_premium_activated_email(user):
    """
    Send premium activation confirmation email.
    
    Args:
        user: User instance
    """
    subject = 'اشتراک پرمیوم شما فعال شد!'
    message = f"""
    سلام {user.get_full_name() or user.email}،
    
    اشتراک پرمیوم شما با موفقیت فعال شد.
    تاریخ انقضا: {user.subscription_end_date.strftime('%Y-%m-%d')}
    
    از امکانات ویژه خود لذت ببرید!
    
    با احترام،
    تیم MovieLenz
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )


def send_subscription_expired_email(user):
    """
    Send subscription expiration notification.
    
    Args:
        user: User instance
    """
    subject = 'اشتراک پرمیوم شما منقضی شد'
    message = f"""
    سلام {user.get_full_name() or user.email}،
    
    اشتراک پرمیوم شما به پایان رسیده است.
    
    برای ادامه استفاده از امکانات ویژه، اشتراک خود را تمدید کنید.
    
    با احترام،
    تیم MovieLenz
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )


def send_subscription_cancelled_email(user):
    """
    Send subscription cancellation confirmation.
    
    Args:
        user: User instance
    """
    subject = 'اشتراک شما لغو شد'
    message = f"""
    سلام {user.get_full_name() or user.email}،
    
    اشتراک پرمیوم شما لغو شد.
    
    امیدواریم به زودی شما را دوباره ببینیم!
    
    با احترام،
    تیم MovieLenz
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )