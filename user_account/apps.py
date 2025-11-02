from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_account'
    verbose_name = 'User Accounts'
    
    def ready(self):
        """Import signals when app is ready."""
        import user_account.signals  # noqa