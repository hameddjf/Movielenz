"""
URL configuration for the comment application.

This module defines URL patterns for the comment API endpoints
using Django REST Framework's routers.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CommentViewSet

app_name = 'comment'

router = DefaultRouter()
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]