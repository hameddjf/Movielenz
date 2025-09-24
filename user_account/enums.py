from django.db import models
from django.utils.translation import gettext_lazy as _

class SubscriptionStatus(models.TextChoices):
    FREE = 'free', _('رایگان')
    PREMIUM = 'premium', _('ویژه')
    CANCELLED = 'cancelled', _('لغو شده')
    EXPIRED = 'expired', _('منقضی شده')
    
class UserRole(models.TextChoices):
    OWNER = 'OWNER', _('مالک')
    ADMIN = 'ADMIN', _('مدیر')
    PREMIUM_USER = 'PREMIUM_USER', _('کاربر ویژه')
    NORMAL_USER = 'NORMAL_USER', _('کاربر عادی')