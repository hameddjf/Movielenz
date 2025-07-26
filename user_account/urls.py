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
    CustomUserDetailsView,
    CustomPasswordChangeView,
    CustomPasswordResetView,
    CustomVerifyEmailView,
    ResendEmailVerificationView,
    CustomPasswordResetConfirmView,
)
CONFIRM_RESET_URL_NAME = 'password_reset_confirm'
router = DefaultRouter()
router.register(r'watchlist', WatchlistViewSet, basename='watchlist')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'history', RecentlyWatchedViewSet, basename='recentlywatched')

urlpatterns = [
    # path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    
    # path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ثبت‌نام و تایید ایمیل
    path('register/', CustomRegisterView.as_view(), name='rest_register'),
    # path('register/verify-email/', CustomVerifyEmailView.as_view(), name='rest_verify_email'),
    path('register/verify-email/<uidb64>/<token>/', CustomVerifyEmailView.as_view(), name='rest_verify_email'),

    path('register/resend-email/', ResendEmailVerificationView.as_view(), name='rest_resend_email'),
    
    # ورود و خروج
    path('login/', CustomLoginView.as_view(), name='rest_login'),
    path('logout/', CustomLogoutView.as_view(), name='rest_logout'),

    # مدیریت پروفایل کاربر
    path('user/', CustomUserDetailsView.as_view(), name='rest_user_details'),

    # مدیریت رمز عبور
    path('password/change/', CustomPasswordChangeView.as_view(), name='rest_password_change'),
    path('password/reset/', CustomPasswordResetView.as_view(), name='rest_password_reset'),
    path(
        'password/reset/confirm/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),
# path('password/reset/confirm/<uidb64>/<token>/', MyPasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # --- URLهای مربوط به JWT (معمولاً نیازی به سفارشی‌سازی ندارند) ---
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/refresh/', get_refresh_view().as_view(), name='token_refresh'),

    path('', include(router.urls)),
    

]
