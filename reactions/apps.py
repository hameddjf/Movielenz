from django.apps import AppConfig


class ReactionsConfig(AppConfig):
    """
    Application configuration for the reactions app.
    
    This app manages user reactions (likes/dislikes) to various content types
    using Django's ContentType framework for generic relations.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reactions'
    verbose_name = 'User Reactions'

    def ready(self):
        """
        Import signals when app is ready.
        """
        # Import signals here if needed in future
        pass