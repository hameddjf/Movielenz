# accounts/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from .models import User
from django.utils import timezone

@shared_task
def send_welcome_email_async(user_id):
    """Send welcome email asynchronously."""
    try:
        user = User.objects.get(id=user_id)
        # ارسال ایمیل
    except User.DoesNotExist:
        pass

@shared_task
def clean_expired_subscriptions():
    """Clean expired subscriptions daily."""
    expired = User.objects.filter(
        subscription_end_date__lt=timezone.now(),
        subscription_status='premium'
    )
    expired.update(subscription_status='expired')

@shared_task
def send_subscription_expiry_reminders():
    """Send reminders 7 days before expiry."""
    threshold = timezone.now() + timezone.timedelta(days=7)
    expiring_soon = User.objects.filter(
        subscription_end_date__lte=threshold,
        subscription_status='premium'
    )
    for user in expiring_soon:
        # ارسال ایمیل یادآوری
        pass