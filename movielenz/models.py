from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from polymorphic.models import PolymorphicModel, PolymorphicManager
from polymorphic.managers import PolymorphicManager
from mptt.models import TreeForeignKey, MPTTModel

from celebrity.models import Actor, Director

from .managers import MovieManager

# Create your models here.

# class Type(models.TextChoices):
#     MOVIE = 'MV', 'فیلم سینمایی'
#     SERIES = 'SR', 'سریال'
#     ANIME = 'AN', 'انیمه'
#     DOCUMENTARY = 'DC', 'مستند'
#     CARTOON = 'CT', 'کارتون'
#     TV_SHOW = 'TV', 'برنامه تلویزیونی'
#     SHORT_FILM = 'SF', 'فیلم کوتاه'
#     MINISERIES = 'MS', 'مینی سریال'
#     SPECIAL = 'SP', 'ویژه'
#     UNSPECIFIED = 'UN', 'نامشخص'

class IpAddress(models.Model):
    ip_address = models.GenericIPAddressField(
        _("آدرس آیپی"), protocol="both", unpack_ipv4=False)
    
class Genre(models.Model):
    name = models.CharField(_("عنوان ژانر"), max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True, null=True)
    translated_genre = models.CharField(_("ژانر ترجمه شده"), max_length=50, default='None')
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = _("ژانر")
        verbose_name_plural = _("ژانرها")

    def __str__(self):
        return self.translated_genre if self.translated_genre else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            source_for_slug = self.translated_genre if self.translated_genre else self.name
            if source_for_slug:
                self.slug = slugify(source_for_slug, allow_unicode=True)
            else:
                raise ValueError(_("نام یا نام ترجمه شده برای تولید اسلاگ مورد نیاز است."))
        super().save(*args, **kwargs)

class Type(MPTTModel):
  parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", verbose_name=_("Parent Type"))
  name = models.CharField(max_length=120, verbose_name=_("Name"))
  slug = models.SlugField(unique=True, max_length=150, verbose_name=_("Name"))
  
  def __str__(self):
    return self.name
  
  class MPTTMeta:
    order_insertion_by = ['name']
  
  class Meta:
    verbose_name_plural = _("دسته بندی ها")
    db_table = "type"
    unique_together = [["parent", "slug"]]
  
  def save(self, *args, **kwargs):
    if not self.slug:
      self.slug = slugify(self.name)
    super().save(*args , **kwargs)
    
    

class Movie(PolymorphicModel):
    title = models.CharField(max_length=300, unique=True)
    slug = models.SlugField(max_length=500, unique=True,blank=True, null=True)
    
    # type = models.CharField(max_length=50, choices=Type.choices, default=Type.MOVIE, verbose_name=_("نوع"),blank=True, null=True)
    
    status = models.BooleanField(default=True)
    
    type = models.ForeignKey(Type ,blank=True, null=True, on_delete=models.SET_NULL, related_name="movies",verbose_name=_("Type"))
    
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField( auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    actors = models.ManyToManyField(Actor, related_name='movies_actor', blank=True)
    directors = models.ManyToManyField(Director, related_name='movies_director', blank=True)

    description = models.TextField(blank=True)

    imdb_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)
    imdb_rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)

    genres = models.ManyToManyField('Genre',blank=True)
    duration = models.PositiveIntegerField(help_text=_("مدت زمان فیلم به دقیقه"), null=True, blank=True)
    # poster = models.ImageField(upload_to='media/movies/%Y/%m/%d/', max_length=500, blank=True, null=True)
    poster = models.URLField(max_length=500, blank=True, null=True)
    trailer = models.URLField(blank=True, null=True, verbose_name=_("تریلر")) 
    
    production_country = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField( max_length=100, blank=True, null=True)
    network = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("شبکه"))

    is_dubbed = models.BooleanField(default=False, verbose_name=_("دوبله شده"))
    is_subtitled = models.BooleanField(default=False, verbose_name=_("زیرنویس شده"))

    tmdb_user_score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    tmdb_popularity = models.PositiveIntegerField(blank=True, null=True)

    # comments = GenericRelation(Comment)
    # rating = GenericRelation(Rating)
    
    objects = MovieManager()

    class Meta:
        verbose_name = _("فیلم")
        verbose_name_plural = _("فیلم‌ها")
        ordering = ['-release_date', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title
    
    @property
    def object_type(self):
        return self.__class__.__name__

class Series(Movie):
    number_of_seasons = models.PositiveIntegerField(
        _("تعداد فصل‌ها"), default=1)
    episode_count = models.PositiveIntegerField(
        _("تعداد قسمت‌ها"), null=True, blank=True)
    series_status_choices = [
        ('ongoing', _('در حال پخش')),
        ('ended', _('به پایان رسیده')),
        ('canceled', _('لغو شده')),
        ('upcoming', _('به زودی')),
        ('pilot', _('پایلوت')),
    ]
    series_status = models.CharField(
        _("وضعیت سریال"), max_length=50, blank=True, null=True,
        choices=series_status_choices,
        default='ongoing')

    class Meta:
        verbose_name = _("سریال")
        verbose_name_plural = _("سریال‌ها")
        

    def save(self, *args, **kwargs):
        if not self.type_id:
            series_type_obj, _ = Type.objects.get_or_create(slug='series', defaults={'name': 'سریال'})
            self.type = series_type_obj
        super().save(*args, **kwargs)

