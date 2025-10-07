from django.apps import AppConfig

class CommentConfig(AppConfig):
    """Configuration class for the comment application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comment'
    verbose_name = 'Comment Management'

    def ready(self):
        """
        Import signal handlers when the application is ready.
        
        This method is called when Django starts and is used to import
        signal handlers and perform other initialization tasks.
        """
        pass  # Import signals here if needed