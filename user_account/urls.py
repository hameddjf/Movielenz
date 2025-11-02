# accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dj_rest_auth.jwt_auth import get_refresh_view
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    UserProfileView,
    WatchlistViewSet, FavoriteViewSet, RecentlyWatchedViewSet,
    # UserRegistrationView,
    CustomRegisterView,
    CustomLoginView,
    CustomLogoutView,
    # CustomUserDetailsView,
    CustomPasswordChangeView,
    CustomPasswordResetView,
    CustomVerifyEmailView,
    ResendEmailVerificationView,
    CustomPasswordResetConfirmView,
    
    GoogleSocialAuthView, 
    TwitterSocialAuthView,
    
    # CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenBlacklistView,
    CustomTokenVerifyView,
    RevokeAllTokensView,
)
CONFIRM_RESET_URL_NAME = 'password_reset_confirm'
router = DefaultRouter()
router.register(r'watchlist', WatchlistViewSet, basename='watchlist')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'history', RecentlyWatchedViewSet, basename='recentlywatched')

urlpatterns = [
    # Authentication URLs
    path('register/', CustomRegisterView.as_view(), name='rest_register'),
    path('login/', CustomLoginView.as_view(), name='rest_login'),
    path('logout/', CustomLogoutView.as_view(), name='rest_logout'),
    
    # Social Authentication 
    path('login/google/', GoogleSocialAuthView.as_view(), name='google_social_auth'),
    path('login/twitter/', TwitterSocialAuthView.as_view(), name='twitter_social_auth'),
    
    # Password management
    path('password/change/', CustomPasswordChangeView.as_view(), name='rest_password_change'),
    path('password/reset/', CustomPasswordResetView.as_view(), name='rest_password_reset'),
    path('password/reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
    
    # Email verification
    path('verify-email/<uidb64>/<token>/', CustomVerifyEmailView.as_view(), name='rest_verify_email'),
    path('resend-email/', ResendEmailVerificationView.as_view(), name='rest_resend_email'),
    
    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),

    # JWT Token endpoints
    # path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', CustomTokenBlacklistView.as_view(), name='token_blacklist'),
    path('token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('token/revoke-all/', RevokeAllTokensView.as_view(), name='token_revoke_all'),

    path('', include(router.urls)),
    

]
