"""
Custom exception classes for user-related errors.
Provides consistent error handling across the application.
"""
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status
from django.utils.translation import gettext_lazy as _


class UserNotActivatedException(APIException):
    """
    Exception raised when user tries to login without email verification.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('لطفاً ابتدا ایمیل خود را تأیید کنید.')
    default_code = 'user_not_activated'


class SubscriptionExpiredException(APIException):
    """
    Exception raised when premium feature accessed with expired subscription.
    """
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _('اشتراک شما منقضی شده است. لطفاً تمدید کنید.')
    default_code = 'subscription_expired'


class SubscriptionRequiredException(APIException):
    """
    Exception raised when premium feature accessed without subscription.
    """
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _('این قابلیت فقط برای کاربران پرمیوم در دسترس است.')
    default_code = 'subscription_required'


class InvalidTokenException(APIException):
    """
    Exception for invalid or expired tokens.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('توکن نامعتبر یا منقضی شده است.')
    default_code = 'invalid_token'


class DuplicateEmailException(APIException):
    """
    Exception when trying to register with existing email.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('این ایمیل قبلاً ثبت شده است.')
    default_code = 'duplicate_email'


class RateLimitExceededException(APIException):
    """
    Exception when rate limit is exceeded.
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _('تعداد درخواست‌های شما از حد مجاز گذشته است. لطفاً بعداً تلاش کنید.')
    default_code = 'rate_limit_exceeded'


class PasswordTooWeakException(ValidationError):
    """
    Exception for weak passwords.
    """
    default_detail = _('رمز عبور شما کافی قوی نیست.')
    default_code = 'password_too_weak'


class InvalidCredentialsException(APIException):
    """
    Exception for invalid login credentials.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('ایمیل یا رمز عبور اشتباه است.')
    default_code = 'invalid_credentials'


class AccountDisabledException(APIException):
    """
    Exception when disabled account tries to login.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('حساب کاربری شما غیرفعال شده است.')
    default_code = 'account_disabled'


class SocialAuthException(APIException):
    """
    Base exception for social authentication errors.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('خطا در احراز هویت از طریق شبکه اجتماعی.')
    default_code = 'social_auth_error'


class GoogleAuthException(SocialAuthException):
    """
    Exception for Google authentication errors.
    """
    default_detail = _('خطا در احراز هویت Google.')
    default_code = 'google_auth_error'


class TwitterAuthException(SocialAuthException):
    """
    Exception for Twitter authentication errors.
    """
    default_detail = _('خطا در احراز هویت Twitter.')
    default_code = 'twitter_auth_error'


class ContentNotFoundException(APIException):
    """
    Exception when referenced content is not found.
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _('محتوای مورد نظر یافت نشد.')
    default_code = 'content_not_found'


class WatchlistLimitExceededException(APIException):
    """
    Exception when watchlist limit is reached.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('تعداد آیتم‌های لیست پخش شما به حد مجاز رسیده است.')
    default_code = 'watchlist_limit_exceeded'


class PermissionDeniedException(APIException):
    """
    Exception for permission denied scenarios.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('شما مجوز انجام این عملیات را ندارید.')
    default_code = 'permission_denied'


class EmailSendFailedException(APIException):
    """
    Exception when email sending fails.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _('خطا در ارسال ایمیل. لطفاً بعداً تلاش کنید.')
    default_code = 'email_send_failed'


# Custom exception handler
def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF views.
    Provides consistent error response format.
    
    Args:
        exc: Exception instance
        context: Exception context
        
    Returns:
        Response with error details
    """
    from rest_framework.views import exception_handler
    from rest_framework.response import Response
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize error response format
        custom_response_data = {
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                'status_code': response.status_code
            }
        }
        
        # Add field-specific errors for validation errors
        if isinstance(exc, ValidationError) and hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                custom_response_data['error']['fields'] = exc.detail
        
        response.data = custom_response_data
        
        # Log error
        logger.error(
            f"API Error: {exc.__class__.__name__} - {str(exc)} "
            f"[Status: {response.status_code}]"
        )
    
    return response