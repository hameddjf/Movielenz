from django.db import models

class PublishedManager(models.Manager):
    """
    یک مدیر سفارشی برای مدل Article که فقط مقالات با وضعیت 'published' را برمی‌گرداند.
    """
    def get_queryset(self):
        return super().get_queryset().filter(status='published')