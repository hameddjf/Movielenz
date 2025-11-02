"""
Django management command for cleaning up expired JWT tokens.
Run periodically via cron or scheduled task.
"""
from django.core.management.base import BaseCommand
from user_account.utils.token_manager import TokenManager


class Command(BaseCommand):
    help = 'Remove expired JWT tokens from database'

    def handle(self, *args, **options):
        """Execute token cleanup."""
        self.stdout.write("Starting token cleanup...")
        
        result = TokenManager.cleanup_expired_tokens()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully removed {result['outstanding_deleted']} "
                f"outstanding and {result['blacklisted_deleted']} blacklisted tokens"
            )
        )
        
# python manage.py cleanup_expired_tokens