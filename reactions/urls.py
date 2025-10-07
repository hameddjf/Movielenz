from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReactionViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'reactions', ReactionViewSet, basename='reaction')

app_name = 'reactions'

urlpatterns = [
    path('', include(router.urls)),
]