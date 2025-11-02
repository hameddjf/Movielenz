"""
Centralized JWT Token Manager for user authentication.
Handles token generation, validation, refresh, and blacklisting.
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError

User = get_user_model()
logger = logging.getLogger('jwt_tokens')


class TokenManager:
    """
    Centralized manager for JWT token operations.
    
    Provides methods for:
    - Token generation with custom claims
    - Token validation and verification
    - Token refresh with rotation
    - Token blacklisting and revocation
    - Bulk token operations (revoke all user tokens)
    """
    
    @staticmethod
    def generate_tokens_for_user(user: User) -> Dict[str, str]:
        """
        Generate access and refresh tokens for authenticated user.
        
        Includes custom claims:
        - user_id: User primary key
        - email: User email address
        - role: User role from UserRole enum
        - subscription_status: User subscription level
        - activated: Whether email is verified
        - exp: Token expiration timestamp
        
        Args:
            user: Authenticated User instance
            
        Returns:
            Dictionary containing:
            - access: JWT access token (short-lived)
            - refresh: JWT refresh token (long-lived)
            - access_expires_at: ISO timestamp of access token expiration
            - refresh_expires_at: ISO timestamp of refresh token expiration
            
        Example:
            >>> from accounts.utils.token_manager import TokenManager
            >>> user = User.objects.get(email='user@example.com')
            >>> tokens = TokenManager.generate_tokens_for_user(user)
            >>> print(tokens['access'])
        """
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims to both access and refresh tokens
        custom_claims = {
            'email': user.email,
            'role': user.role,
            'subscription_status': user.subscription_status,
            'activated': user.activated,
        }
        
        # Add claims to refresh token (will be inherited by access token)
        for claim_key, claim_value in custom_claims.items():
            refresh[claim_key] = claim_value
        
        # Calculate expiration timestamps
        access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=15))
        refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))
        
        now = timezone.now()
        access_expires_at = now + access_lifetime
        refresh_expires_at = now + refresh_lifetime
        
        logger.info(
            f"Generated tokens for user {user.id} ({user.email}). "
            f"Access expires: {access_expires_at}, Refresh expires: {refresh_expires_at}"
        )
        
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'access_expires_at': access_expires_at.isoformat(),
            'refresh_expires_at': refresh_expires_at.isoformat(),
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Dict[str, str]:
        """
        Generate new access token from valid refresh token.
        
        If ROTATE_REFRESH_TOKENS is enabled, also generates new refresh token
        and blacklists the old one.
        
        Args:
            refresh_token: Valid JWT refresh token string
            
        Returns:
            Dictionary containing:
            - access: New JWT access token
            - refresh: New refresh token (if rotation enabled)
            - access_expires_at: Expiration timestamp
            
        Raises:
            TokenError: If refresh token is invalid, expired, or blacklisted
            
        Example:
            >>> tokens = TokenManager.refresh_access_token(old_refresh_token)
            >>> new_access = tokens['access']
        """
        try:
            refresh = RefreshToken(refresh_token)
            
            # Check if token is blacklisted
            if TokenManager.is_token_blacklisted(refresh_token):
                logger.warning(f"Attempted to refresh blacklisted token: {refresh_token[:20]}...")
                raise TokenError("Token is blacklisted")
            
            # Get user from token
            user_id = refresh.get('user_id')
            user = User.objects.get(id=user_id)
            
            # Verify user is still active and verified
            if not user.is_active:
                logger.warning(f"Refresh attempt for inactive user: {user.email}")
                raise AuthenticationFailed("User account is disabled")
            
            if not user.activated:
                logger.warning(f"Refresh attempt for unverified user: {user.email}")
                raise AuthenticationFailed("Email not verified")
            
            # Generate new access token
            new_access = refresh.access_token
            
            access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=15))
            access_expires_at = timezone.now() + access_lifetime
            
            result = {
                'access': str(new_access),
                'access_expires_at': access_expires_at.isoformat(),
            }
            
            # Handle refresh token rotation
            rotate_refresh = settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False)
            if rotate_refresh:
                # Generate new refresh token
                new_refresh = RefreshToken.for_user(user)
                
                # Copy custom claims from old token
                for claim in ['email', 'role', 'subscription_status', 'activated']:
                    if claim in refresh:
                        new_refresh[claim] = refresh[claim]
                
                result['refresh'] = str(new_refresh)
                
                refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))
                result['refresh_expires_at'] = (timezone.now() + refresh_lifetime).isoformat()
                
                # Blacklist old refresh token if configured
                blacklist_after_rotation = settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False)
                if blacklist_after_rotation:
                    TokenManager.blacklist_token(refresh_token)
                    logger.info(f"Rotated and blacklisted old refresh token for user {user.email}")
            
            logger.info(f"Refreshed access token for user {user.email}")
            return result
            
        except User.DoesNotExist:
            logger.error(f"User not found for refresh token")
            raise TokenError("User not found")
        except TokenError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during token refresh: {str(e)}")
            raise TokenError("Token refresh failed")
    
    @staticmethod
    def blacklist_token(refresh_token: str) -> bool:
        """
        Blacklist a refresh token to prevent further use.
        
        Typically called during logout or when revoking access.
        
        Args:
            refresh_token: JWT refresh token to blacklist
            
        Returns:
            True if token was blacklisted, False if already blacklisted
            
        Raises:
            TokenError: If token is invalid
            
        Example:
            >>> TokenManager.blacklist_token(user_refresh_token)
        """
        try:
            token = RefreshToken(refresh_token)
            
            # Check if already blacklisted
            if TokenManager.is_token_blacklisted(refresh_token):
                logger.info("Token already blacklisted")
                return False
            
            # Add to blacklist
            token.blacklist()
            
            user_id = token.get('user_id')
            logger.info(f"Blacklisted refresh token for user {user_id}")
            return True
            
        except TokenError as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during token blacklisting: {str(e)}")
            raise TokenError("Token blacklist failed")
    
    @staticmethod
    def is_token_blacklisted(refresh_token: str) -> bool:
        """
        Check if a refresh token is blacklisted.
        
        Args:
            refresh_token: JWT refresh token to check
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            token = RefreshToken(refresh_token)
            jti = token.get('jti')
            
            # Check if JTI exists in blacklist
            return BlacklistedToken.objects.filter(
                token__jti=jti
            ).exists()
            
        except TokenError:
            # Invalid tokens are considered blacklisted
            return True
        except Exception as e:
            logger.error(f"Error checking blacklist status: {str(e)}")
            return True
    
    @staticmethod
    def verify_token(token: str, token_type: str = 'access') -> Tuple[bool, Optional[Dict]]:
        """
        Verify token validity and decode payload.
        
        Args:
            token: JWT token string
            token_type: Type of token ('access' or 'refresh')
            
        Returns:
            Tuple of (is_valid, payload_dict)
            - is_valid: Boolean indicating token validity
            - payload_dict: Decoded token payload or None if invalid
            
        Example:
            >>> is_valid, payload = TokenManager.verify_token(access_token)
            >>> if is_valid:
            >>>     user_email = payload['email']
        """
        try:
            if token_type == 'access':
                token_obj = AccessToken(token)
            else:
                token_obj = RefreshToken(token)
            
            # Check expiration
            exp_timestamp = token_obj.get('exp')
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.now():
                logger.warning("Token has expired")
                return False, None
            
            # Extract payload
            payload = {
                'user_id': token_obj.get('user_id'),
                'email': token_obj.get('email'),
                'role': token_obj.get('role'),
                'subscription_status': token_obj.get('subscription_status'),
                'activated': token_obj.get('activated'),
                'exp': token_obj.get('exp'),
                'iat': token_obj.get('iat'),
                'jti': token_obj.get('jti'),
            }
            
            return True, payload
            
        except TokenError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            return False, None
    
    @staticmethod
    def revoke_all_user_tokens(user: User) -> int:
        """
        Blacklist all outstanding refresh tokens for a user.
        
        Useful for:
        - Password changes (force re-authentication)
        - Account security incidents
        - Administrative actions
        
        Args:
            user: User instance whose tokens should be revoked
            
        Returns:
            Number of tokens blacklisted
            
        Example:
            >>> user = User.objects.get(email='user@example.com')
            >>> count = TokenManager.revoke_all_user_tokens(user)
            >>> print(f"Revoked {count} tokens")
        """
        try:
            # Get all outstanding tokens for user
            outstanding_tokens = OutstandingToken.objects.filter(
                user_id=user.id
            ).exclude(
                id__in=BlacklistedToken.objects.values_list('token_id', flat=True)
            )
            
            count = 0
            for token_record in outstanding_tokens:
                try:
                    # Blacklist each token
                    BlacklistedToken.objects.create(token=token_record)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to blacklist token {token_record.jti}: {str(e)}")
            
            logger.info(f"Revoked {count} tokens for user {user.email}")
            return count
            
        except Exception as e:
            logger.exception(f"Error revoking user tokens: {str(e)}")
            return 0
    
    @staticmethod
    def cleanup_expired_tokens() -> Dict[str, int]:
        """
        Remove expired tokens from database.
        
        Should be run periodically (e.g., daily cron job) to prevent
        database bloat from expired outstanding tokens.
        
        Returns:
            Dictionary with counts:
            - outstanding_deleted: Number of expired outstanding tokens removed
            - blacklisted_deleted: Number of blacklisted tokens removed
            
        Example:
            >>> from django.core.management import BaseCommand
            >>> class Command(BaseCommand):
            >>>     def handle(self, *args, **options):
            >>>         result = TokenManager.cleanup_expired_tokens()
            >>>         self.stdout.write(f"Cleaned up {result['outstanding_deleted']} tokens")
        """
        try:
            now = timezone.now()
            
            # Delete expired outstanding tokens
            expired_outstanding = OutstandingToken.objects.filter(
                expires_at__lt=now
            )
            outstanding_count = expired_outstanding.count()
            expired_outstanding.delete()
            
            # Delete orphaned blacklisted tokens
            orphaned_blacklist = BlacklistedToken.objects.filter(
                token__expires_at__lt=now
            )
            blacklisted_count = orphaned_blacklist.count()
            orphaned_blacklist.delete()
            
            logger.info(
                f"Token cleanup: {outstanding_count} outstanding, "
                f"{blacklisted_count} blacklisted tokens removed"
            )
            
            return {
                'outstanding_deleted': outstanding_count,
                'blacklisted_deleted': blacklisted_count,
            }
            
        except Exception as e:
            logger.exception(f"Error during token cleanup: {str(e)}")
            return {'outstanding_deleted': 0, 'blacklisted_deleted': 0}