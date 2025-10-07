from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.db.models import Prefetch

from collections import defaultdict

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Genre,  Movie, Type
from .serializers import (
    GenreSerializer,  BaseMovieSerializer
    )
from .mixins import MovieAPIMixin

class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    این ViewSet اطلاعات ژانرها را فقط برای خواندن (GET) فراهم می‌کند.
    رکوردها با استفاده از اسلاگ قابل دسترسی هستند.
    """
    queryset = Genre.objects.all().order_by('name')
    serializer_class = GenreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    lookup_field = 'slug'

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'slug']
    ordering_fields = ['name'] 

class MovieViewSet(MovieAPIMixin, viewsets.ReadOnlyModelViewSet):

    serializer_class = BaseMovieSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    search_fields = ['title', 'description', 'actors__name', 'directors__name', 'imdb_id', 'tmdb_id']
    ordering_fields = ['title', 'release_date', 'imdb_rating', 'created_at', 'tmdb_popularity', 'type__name']
    ordering = ['type__name', '-release_date', 'title']


    @action(detail=False, methods=['get'], url_path='type/(?P<slug_url>[^/.]+)', permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def by_type_slug(self, request, type_slug_url=None):
        """
        لیستی از فیلم‌ها/سریال‌ها را برای یک نوع (type) خاص بر اساس اسلاگ آن نوع از URL برمی‌گرداند.
        """
        if not type_slug_url:
            return Response({"error": "Type slug not provided"}, status=status.HTTP_400_BAD_REQUEST) # استفاده از _ نیازمند import gettext_lazy است

        qs = Movie.objects.all().prefetch_related(
            'genres', 'actors', 'directors'
        ).select_related('type')
        if not request.user.is_staff:
            qs = qs.filter(status=True)

        qs = qs.filter(type__slug=type_slug_url.lower())

        filtered_qs = self.filter_queryset(qs.distinct())

        page = self.paginate_queryset(filtered_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='latest')
    def latest_content(self, request):
        """
        ۱۰ مورد از جدیدترین فیلم‌ها و سریال‌های منتشر شده را برمی‌گرداند.
        امکان فیلتر بر اساس type_slug از پارامترهای کوئری وجود دارد.
        """
        qs = Movie.objects.all().prefetch_related(
            'genres', 'actors', 'directors'
        ).select_related('type')
        if not request.user.is_staff:
            qs = qs.filter(status=True)

        type_slug_param = self.request.query_params.get('type_slug')
        if type_slug_param:
            qs = qs.filter(type__slug=type_slug_param.lower())

        latest_items = qs.order_by('-release_date', '-created_at')[:10]

        serializer = self.get_serializer(latest_items, many=True)
        return Response(serializer.data)