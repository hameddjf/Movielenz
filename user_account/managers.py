from django.contrib.auth.models import BaseUserManager
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from movielenz.models import Genre

from .enums import SubscriptionStatus , UserRole

class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('ایمیل برای کاربر ضروری است'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        # extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        # extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_active', True)

        # if extra_fields.get('is_staff') is not True:
        #     raise ValueError(_('سوپریوزر باید is_staff=True داشته باشد.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('سوپریوزر باید is_superuser=True داشته باشد.'))
        
        extra_fields['is_staff'] = extra_fields.get('role') in [UserRole.ADMIN, UserRole.OWNER]
        
        return self._create_user(email, password, **extra_fields)

    def get_users_with_active_premium_subscription(self):
        """کاربرانی که اشتراک ویژه فعال دارند را برمی‌گرداند."""
        now = timezone.now()
        return self.filter(
            subscription_status= SubscriptionStatus.PREMIUM,
            # subscription_status='premium',
            subscription_end_date__gte=now,
            is_active=True
        )

    def get_users_by_preferred_genre(self, genre_input):
        """کاربرانی که ژانر مشخصی را ترجیح می‌دهند، برمی‌گرداند. ورودی می‌تواند نمونه Genre، اسلاگ یا نام ژانر باشد."""
        try:
            if isinstance(genre_input, Genre):
                genre = genre_input
            elif isinstance(genre_input, str):
                from django.db.models import Q
                genre = Genre.objects.get(Q(slug=genre_input) | Q(name=genre_input))
            else:
                raise ValueError(_("ورودی باید یک نمونه از Genre یا یک رشته (اسلاگ/نام) باشد."))
        except Genre.DoesNotExist:
            return self.none()

        return self.filter(preferred_genres=genre, is_active=True)

    def get_users_who_favorited_item(self, content_object):
        """کاربرانی که یک آیتم محتوایی خاص (فیلم یا سریال) را به علاقه‌مندی‌ها اضافه کرده‌اند، برمی‌گرداند."""
        content_type = ContentType.objects.get_for_model(content_object)
        return self.filter(
            is_active=True,
            user_favorites__content_type=content_type,
            user_favorites__object_id=content_object.pk
        ).distinct()

    def get_users_with_watchlist_item(self, content_object):
        """کاربرانی که یک آیتم محتوایی خاص را در لیست تماشای خود دارند، برمی‌گرداند."""
        content_type = ContentType.objects.get_for_model(content_object)
        return self.filter(
            is_active=True,
            user_watchlist__content_type=content_type,
            user_watchlist__object_id=content_object.pk
        ).distinct()

    def get_inactive_users(self, days_inactive=30):
        """کاربرانی که برای مدت زمان مشخصی وارد نشده‌اند را برمی‌گرداند."""
        threshold_date = timezone.now() - timezone.timedelta(days=days_inactive)
        # last_login
        return self.filter(last_login__lt=threshold_date, is_active=True)