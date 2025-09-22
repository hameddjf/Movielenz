# Create your views here.
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Article, Tag
from .serializers import ArticleSerializer, TagSerializer
from .permissions import IsAuthorOrReadOnly

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import Article, Tag
from .serializers import ArticleSerializer, TagSerializer

class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت تگ‌ها.
    این ViewSet بدون تغییر باقی می‌ماند.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAdminUser]

class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet ریفکتور شده برای مدیریت مقالات.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    lookup_field = 'slug' 

    def get_queryset(self):
        """
        *** تغییر کلیدی: بازنویسی و بهینه‌سازی کوئری با Q objects و prefetch_related ***

        این متد برای خوانایی بیشتر و بهینه‌سازی کوئری‌های دیتابیس ریفکتور شده است.
        """
        user = self.request.user

        base_queryset = Article.objects.select_related('author').prefetch_related('tags')

        # ادمین‌ها و کارمندان تمام مقالات را می‌بینند.
        if user.is_authenticated and user.is_staff:
            return base_queryset.all()
        
        if user.is_authenticated:
            query_filter = Q(status='published') | Q(author=user, status='draft')
            return base_queryset.filter(query_filter).distinct()

        # کاربران مهمان (احراز هویت نشده) فقط مقالات منتشر شده را می‌بینند.
        return base_queryset.filter(status='published')

    def get_serializer_context(self):
        """
        ارسال context به سریالایزر. بدون تغییر.
        """
        return {'request': self.request}

    @action(detail=True, methods=['post'], permission_classes=[IsAuthorOrReadOnly])
    def publish(self, request, slug=None):
        """
        اکشن سفارشی برای انتشار مقاله. بدون تغییر.
        """
        article = self.get_object()
        if article.status == 'published':
            return Response({'message': 'این مقاله قبلاً منتشر شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        
        article.publish() 
        serializer = self.get_serializer(article)
        return Response(serializer.data)
