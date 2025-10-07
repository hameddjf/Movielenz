from django.shortcuts import render

# Create your views here.
# admin_panel/views.py

from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from user_account.models import User
from user_account.enums import UserRole

from .serializers import UserAdminSerializer
from .filters import UserFilter
from .permissions import IsOwnerOrAdmin

# users

class UserAdminViewSet(viewsets.ModelViewSet):
    """
    یک ViewSet برای مدیریت پروفایل کاربران.

    - OWNER/ADMIN: دسترسی کامل به اطلاعات و مدیریت همه کاربران.
    - PREMIUM_USER/NORMAL_USER: دسترسی به مشاهده و ویرایش فقط پروفایل خودشان.
    """
    serializer_class = UserAdminSerializer
    permission_classes = [IsOwnerOrAdmin] # استفاده از کلاس دسترسی جدید

    # قابلیت‌های فیلتر، جستجو و مرتب‌سازی برای ادمین‌ها
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email', 'role']

    def get_queryset(self):
        """
        این متد queryset را بر اساس نقش کاربر درخواست‌دهنده تعیین می‌کند.
        """
        user = self.request.user

        # اگر کاربر ادمین یا مالک باشد، لیست تمام کاربران را برمی‌گرداند.
        if user.role in [UserRole.ADMIN, UserRole.OWNER]:
            return User.objects.all().order_by('-date_joined')
            
        # اگر کاربر عادی است، یک queryset شامل فقط پروفایل خودش را برمی‌گرداند.
        return User.objects.filter(pk=user.pk)

    def get_serializer_context(self):
        """
        اضافه کردن 'request' به context سریالایزر تا بتوانیم در سریالایزر
        به کاربر درخواست‌دهنده دسترسی داشته باشیم.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
# blog
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from blog.models import Article, Tag
from .serializers import ArticleSerializer, TagSerializer
from .permissions import IsAdminOrAuthor # دسترسی سفارشی
from .filters import ArticlePanelFilter # فیلتر سفارشی

class TagViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت کامل تگ‌ها (فقط برای ادمین)."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAdminUser]

class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت کامل مقالات توسط کارمندان و نویسندگان.
    """
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrAuthor]
    lookup_field = 'slug'
    
    # اتصال بک‌اند فیلتر
    filter_backends = [DjangoFilterBackend]
    filterset_class = ArticlePanelFilter

    def get_queryset(self):
        """
        - ادمین/کارمند: همه مقالات را می‌بیند.
        - نویسنده عادی: فقط مقالات خودش را (با هر وضعیتی) می‌بیند.
        """
        user = self.request.user
        base_queryset = Article.objects.select_related('author').prefetch_related('tags')

        if user.is_staff:
            return base_queryset.all()
        
        return base_queryset.filter(author=user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def publish(self, request, slug=None):
        """اکشن سفارشی برای انتشار مقاله (فقط توسط ادمین)."""
        article = self.get_object()
        if article.status == 'published':
            return Response({'message': 'این مقاله قبلاً منتشر شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        
        article.publish() 
        serializer = self.get_serializer(article)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
# movies
from movielenz.models import Movie, Series
from episode.models import Episode, EpisodeQuality

from .mixins import AdminPanelViewSetMixin
from .filters import ContentFilterSet
from .serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    SeriesListSerializer,
    SeriesDetailSerializer,
    EpisodeSerializer,
    EpisodeQualitySerializer
)
class MovieViewSet(AdminPanelViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت فیلم‌ها.
    """
    # بهینه‌سازی کوئری با prefetch_related تودرتو
    queryset = Movie.objects.all().prefetch_related('genres', 'episodes__qualities')
    filterset_class = ContentFilterSet

    def get_serializer_class(self):
        if self.action == 'list':
            return MovieListSerializer
        return MovieDetailSerializer

class SeriesViewSet(AdminPanelViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت سریال‌ها.
    """
    # بهینه‌سازی کوئری با prefetch_related تودرتو
    queryset = Series.objects.all().prefetch_related('genres', 'episodes__qualities')
    filterset_class = ContentFilterSet

    def get_serializer_class(self):
        if self.action == 'list':
            return SeriesListSerializer
        return SeriesDetailSerializer

# --- ViewSet های جدید برای Episode و EpisodeQuality ---

class EpisodeViewSet(AdminPanelViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت کامل (CRUD) قسمت‌ها.
    این ViewSet به صورت مستقل عمل می‌کند و در زمان ایجاد، ID فیلم یا سریال مادر
    را از بدنه درخواست (request body) دریافت می‌کند.
    """
    queryset = Episode.objects.all().prefetch_related('qualities').order_by('season', 'title')
    serializer_class = EpisodeSerializer
    # فیلترها و جستجو برای قسمت‌ها
    search_fields = ['title']
    filterset_fields = ['movie', 'season'] # امکان فیلتر قسمت‌ها بر اساس فیلم/سریال مادر و فصل

class EpisodeQualityViewSet(AdminPanelViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت کیفیت‌های یک قسمت.
    """
    queryset = EpisodeQuality.objects.all()
    serializer_class = EpisodeQualitySerializer
    # غیرفعال کردن جستجوی عمومی چون برای این مدل کاربردی نیست
    search_fields = []
    # فیلتر بر اساس قسمتی که به آن تعلق دارد
    filterset_fields = ['episode', 'quality']