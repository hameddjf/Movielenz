# your_app/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, TagViewSet

# ایجاد یک روتر
router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]
