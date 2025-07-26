from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .managers import UserManager
from .enums import SubscriptionStatus

from movielenz.models import Genre

class User(AbstractUser):
    username = models.CharField(
        _('نام کاربری'),
        max_length=150,
        unique=True,
        help_text=_('یک نام کاربری منحصر به فرد برای ورود به سیستم.'),
        error_messages={
            'unique': _("یک کاربر با این نام کاربری وجود دارد."),
        },
    )
    email = models.EmailField(_('آدرس ایمیل'), unique=True)
    activated = models.BooleanField(
        _('فعال شده'),
        default=False,
        help_text=_('وضعیت فعال‌سازی حساب کاربری. اگر غیرفعال باشد، کاربر نمی‌تواند وارد سیستم شود.')
    )
    first_name = models.CharField(_('نام'), max_length=150, blank=True)
    last_name = models.CharField(_('نام خانوادگی'), max_length=150, blank=True)
    
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        null=True, blank=True, 
        verbose_name=_('عکس پروفایل')
    )
    date_of_birth = models.DateField(
        null=True, blank=True, 
        verbose_name=_('تاریخ تولد')
    )
    subscription_status = models.CharField(
        max_length=10,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
        verbose_name=_('وضعیت اشتراک')
    )
    subscription_start_date = models.DateTimeField(
        null=True, blank=True, 
        verbose_name=_('تاریخ شروع اشتراک')
    )
    subscription_end_date = models.DateTimeField(
        null=True, blank=True, 
        verbose_name=_('تاریخ پایان اشتراک')
    )
    preferred_language = models.CharField(
        max_length=10, default='fa', 
        verbose_name=_('زبان ترجیحی'), 
        help_text=_("مثال: 'fa' برای فارسی, 'en' برای انگلیسی")
    )
    preferred_genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name='users_preferring',
        verbose_name=_('ژانرهای مورد علاقه')
    )

    watchlist = GenericRelation(
        'WatchlistItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_watchlist'
    )
    favorites = GenericRelation(
        'FavoriteItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_favorites'
    )
    recently_watched_log = GenericRelation(
        'RecentlyWatchedItem',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='user_recently_watched'
    )
    
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('گروه‌ها'),
        blank=True,
        help_text=_(
            'گروه‌هایی که این کاربر به آن‌ها تعلق دارد. یک کاربر تمام مجوزهای '
            'اعطا شده به هر یک از گروه‌های خود را دریافت می‌کند.'
        ),
        related_name="user_account_user_groups",  # نام منحصربه‌فرد برای related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('مجوزهای کاربر'),
        blank=True,
        help_text=_('مجوزهای خاص برای این کاربر.'),
        related_name="user_account_user_permissions",  # نام منحصربه‌فرد برای related_name
        related_query_name="user",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('کاربر')
        verbose_name_plural = _('کاربران')
        ordering = ['email']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def has_active_premium_subscription(self):
        """بررسی می‌کند آیا کاربر اشتراک ویژه فعال دارد یا خیر."""
        now = timezone.now()
        return (self.subscription_status == SubscriptionStatus.PREMIUM and
                self.subscription_end_date is not None and
                self.subscription_end_date >= now)

    def add_to_watchlist(self, content_object):
        """یک آیتم (فیلم یا سریال) را به لیست تماشای کاربر اضافه می‌کند."""
        content_type = ContentType.objects.get_for_model(content_object)
        if not self.watchlist.filter(object_id=content_object.pk, content_type=content_type).exists():
            WatchlistItem.objects.create(user=self, content_object=content_object)
            return True
        return False

    def remove_from_watchlist(self, content_object):
        """یک آیتم را از لیست تماشای کاربر حذف می‌کند."""
        content_type = ContentType.objects.get_for_model(content_object)
        item = self.watchlist.filter(object_id=content_object.pk, content_type=content_type).first()
        if item:
            item.delete()
            return True
        return False

    def add_to_favorites(self, content_object):
        """یک آیتم را به علاقه‌مندی‌های کاربر اضافه می‌کند."""
        content_type = ContentType.objects.get_for_model(content_object)
        if not self.favorites.filter(object_id=content_object.pk, content_type=content_type).exists():
            FavoriteItem.objects.create(user=self, content_object=content_object)
            return True
        return False

    def remove_from_favorites(self, content_object):
        """یک آیتم را از علاقه‌مندی‌های کاربر حذف می‌کند."""
        content_type = ContentType.objects.get_for_model(content_object)
        item = self.favorites.filter(object_id=content_object.pk, content_type=content_type).first()
        if item:
            item.delete()
            return True
        return False

    def add_or_update_recently_watched(self, content_object, progress_seconds=None):
        """
        یک آیتم را به لیست اخیراً تماشا شده اضافه می‌کند یا اگر قبلاً وجود داشته، زمان تماشا و پیشرفت آن را به‌روز می‌کند.
        """
        content_type = ContentType.objects.get_for_model(content_object)
        item, created = RecentlyWatchedItem.objects.update_or_create(
            user=self,
            content_type=content_type,
            object_id=content_object.pk,
            defaults={'watched_at': timezone.now(), 'progress_seconds': progress_seconds}
        )
        return item

    def get_watchlist_items_ordered(self):
        """آیتم‌های لیست تماشا را به ترتیب زمان اضافه شدن برمی‌گرداند."""
        return self.watchlist.all().order_by('-added_at') # WatchlistItem objects

    def get_favorite_items_ordered(self):
        """آیتم‌های مورد علاقه را به ترتیب زمان اضافه شدن برمی‌گرداند."""
        return self.favorites.all().order_by('-added_at') # FavoriteItem objects

    def get_recently_watched_items_ordered(self, limit=20):
        """آیتم‌های اخیراً تماشا شده را به ترتیب زمان تماشا برمی‌گرداند."""
        return self.recently_watched_log.all().order_by('-watched_at')[:limit] # RecentlyWatchedItem objects


class UserContentInteractionBase(models.Model):
    """
    یک مدل پایه انتزاعی برای تعاملات کاربر با محتوا مانند لیست تماشا و علاقه‌مندی‌ها.
    این مدل فیلدهای مشترک و متا دیتا را فراهم می‌کند.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    # Content-object (محتوای جنریک)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("نوع محتوا"))
    object_id = models.PositiveIntegerField(verbose_name=_("شناسه شیء محتوا"))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان افزودن"))

    class Meta:
        abstract = True
        unique_together = ('user', 'content_type', 'object_id')
        ordering = ['-added_at']


class WatchlistItem(UserContentInteractionBase):
    class Meta(UserContentInteractionBase.Meta):
        verbose_name = _("لیست تماشا فیلم")
        verbose_name_plural = _("لیست تماشا فیلم ها")


class FavoriteItem(UserContentInteractionBase):
    class Meta(UserContentInteractionBase.Meta):
        verbose_name = _("فیلم مورد علاقه")
        verbose_name_plural = _("فیلم های مورد علاقه")


class RecentlyWatchedItem(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='recently_watched_entries',
        verbose_name=_("کاربر")
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("نوع محتوا"))
    object_id = models.PositiveIntegerField(verbose_name=_("شناسه شیء محتوا"))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    watched_at = models.DateTimeField(verbose_name=_("زمان تماشا"))
    progress_seconds = models.PositiveIntegerField(
        null=True, blank=True, 
        verbose_name=_("پیشرفت (ثانیه)"),
        help_text=_("میزان تماشای فیلم یا سریال به ثانیه")
    )

    class Meta:
        verbose_name = _("فیلم اخیراً تماشا شده")
        verbose_name_plural = _("فیلم های اخیراً تماشا شده")
        ordering = ['-watched_at']
        unique_together = ('user', 'content_type', 'object_id')

    def save(self, *args, **kwargs):
        if not self.watched_at:
            self.watched_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.content_object} @ {self.watched_at.strftime('%Y-%m-%d %H:%M')}"