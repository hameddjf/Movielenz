# Create your models here.
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from .managers import PublishedManager

# class Category(models.Model):
#     name = models.CharField(max_length=100, unique=True, verbose_name="نام دسته‌بندی")
#     slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="اسلاگ (آدرس)")

#     class Meta:
#         verbose_name = "دسته‌بندی"
#         verbose_name_plural = "دسته‌بندی‌ها"
#         ordering = ['name']

#     def __str__(self):
#         return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام برچسب")
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="اسلاگ (آدرس)")

    class Meta:
        verbose_name = "برچسب"
        verbose_name_plural = "برچسب‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name

class Article(models.Model):
    
    STATUS_CHOICES = (
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('deleted', 'حذف شده'),
        # ('cancelled', 'کنسل شده'),
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name="نویسنده"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان مقاله")
    slug = models.SlugField(max_length=220, unique=True, allow_unicode=True, verbose_name="اسلاگ (آدرس)")
    content = models.TextField(verbose_name="محتوای مقاله")
    
    featured_image = models.ImageField(
        upload_to='article_images/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="تصویر"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ انتشار")
    
    objects = models.Manager() 
    published = PublishedManager()

    # categories = models.ManyToManyField(Category, related_name='articles', blank=True, verbose_name="دسته‌بندی‌ها")
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True, verbose_name="برچسب‌ها")

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ['-published_at'] 

    def __str__(self):
        return self.title

    #انتشار مقاله
    def publish(self):
        self.published_at = timezone.now()
        self.status = 'published'
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        
        if self.status == 'published' and self.published_at is None:
            self.published_at = timezone.now()
            
        super().save(*args, **kwargs)

# class Comment(models.Model):
#     article = models.ForeignKey(
#         Article,
#         on_delete=models.CASCADE,
#         related_name='comments',
#         verbose_name="مقاله"
#     )
#     author = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='comments',
#         verbose_name="نویسنده نظر"
#     )
#     content = models.TextField(verbose_name="متن نظر")
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
#     is_approved = models.BooleanField(default=False, verbose_name="تایید شده")

#     parent = models.ForeignKey(
#         'self',
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name='replies',
#         verbose_name="پاسخ به"
#     )

#     class Meta:
#         verbose_name = "نظر"
#         verbose_name_plural = "نظرات"
#         ordering = ['created_at'] # نظرات قدیمی‌تر در ابتدا نمایش داده می‌شوند

#     def __str__(self):
#         return f"نظری از {self.author.username} برای مقاله '{self.article.title}'"