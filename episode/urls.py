from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CombinedEpisodeQualityViewSet # مسیر view خود را تنظیم کنید

router = DefaultRouter()
router.register(r'episode', CombinedEpisodeQualityViewSet, basename='combined-episode-quality')

urlpatterns = [
    path('', include(router.urls)),
    path('episodes/<str:movie_slug>/', CombinedEpisodeQualityViewSet.as_view({'get': 'list'}), name='combined-episode-detail-by-slug'),
]

