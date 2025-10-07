# admin_panel/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# یک روتر برای ثبت خودکار URLهای ViewSet ایجاد می‌کنیم
router = DefaultRouter()
router.register(r'users', views.UserAdminViewSet, basename='panel-user')
router.register(r'blogs', views.ArticleViewSet, basename='panel-article')
router.register(r'tags', views.TagViewSet, basename='panel-tag')

router.register(r'movies', views.MovieViewSet, basename='movie')
router.register(r'series', views.SeriesViewSet, basename='series')

router.register(r'episodes', views.EpisodeViewSet, basename='episode')
router.register(r'qualities', views.EpisodeQualityViewSet, basename='episode-quality')

urlpatterns = [
    path('', include(router.urls)),
]
