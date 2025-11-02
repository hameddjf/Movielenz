"""
Custom throttling classes for API rate limiting.
Protects against abuse and ensures fair usage.
"""
from rest_framework.throttling import (
    AnonRateThrottle, UserRateThrottle, SimpleRateThrottle
)
from django.core.cache import cache
from django.utils import timezone


class LoginAttemptThrottle(SimpleRateThrottle):
    """
    Throttle for login attempts.
    Prevents brute force attacks on login endpoint.
    """
    scope = 'login_attempts'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on email or IP.
        """
        email = request.data.get('email', '')
        if email:
            ident = email.lower()
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
    
    def allow_request(self, request, view):
        """
        Check if request should be allowed.
        After too many failed attempts, block for longer period.
        """
        if request.method != 'POST':
            return True
        
        # Check if already blocked
        email = request.data.get('email', '')
        if email:
            block_key = f'login_blocked:{email.lower()}'
            if cache.get(block_key):
                return False
        
        return super().allow_request(request, view)


class RegisterThrottle(SimpleRateThrottle):
    """
    Throttle for registration attempts.
    Prevents mass account creation.
    """
    scope = 'register'
    
    def get_cache_key(self, request, view):
        """Generate cache key based on IP."""
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class PasswordResetThrottle(SimpleRateThrottle):
    """
    Throttle for password reset requests.
    Prevents email flooding.
    """
    scope = 'password_reset'
    
    def get_cache_key(self, request, view):
        """Generate cache key based on email or IP."""
        email = request.data.get('email', '')
        if email:
            ident = email.lower()
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class EmailVerificationThrottle(SimpleRateThrottle):
    """
    Throttle for email verification resend.
    Prevents spam.
    """
    scope = 'email_verification'
    
    def get_cache_key(self, request, view):
        """Generate cache key based on email."""
        email = request.data.get('email', '')
        if email:
            ident = email.lower()
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class PremiumUserThrottle(UserRateThrottle):
    """
    Higher rate limit for premium users.
    """
    scope = 'premium_user'
    
    def allow_request(self, request, view):
        """
        Check if user is premium and apply appropriate limit.
        """
        if not request.user.is_authenticated:
            return super().allow_request(request, view)
        
        # Premium users get higher limits
        if request.user.has_active_premium_subscription():
            self.rate = self.get_rate()
            self.num_requests, self.duration = self.parse_rate(self.rate)
            # Double the limit for premium users
            self.num_requests *= 2
        
        return super().allow_request(request, view)


class SocialAuthThrottle(SimpleRateThrottle):
    """
    Throttle for social authentication attempts.
    """
    scope = 'social_auth'
    
    def get_cache_key(self, request, view):
        """Generate cache key based on IP."""
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class BurstRateThrottle(UserRateThrottle):
    """
    Short burst rate limit for API calls.
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Long-term sustained rate limit.
    """
    scope = 'sustained'


# Custom throttle for specific actions
class WatchlistThrottle(UserRateThrottle):
    """
    Throttle for watchlist operations.
    """
    scope = 'watchlist'


class FavoriteThrottle(UserRateThrottle):
    """
    Throttle for favorite operations.
    """
    scope = 'favorite'