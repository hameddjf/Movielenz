"""
Serializers for user authentication and profile management.
Handles registration, login, password reset, and social authentication.
"""
import logging
import requests
from urllib.parse import urlparse

from django.contrib.auth import get_user_model, authenticate
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.urls import resolve, Resolver404, reverse, NoReverseMatch
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetConfirmSerializer as BasePasswordResetConfirmSerializer

from .models import WatchlistItem, FavoriteItem, RecentlyWatchedItem
from .tokens import account_activation_token
from .validators import (
    StrongPasswordValidator, AgeValidator
)
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed

from movielenz.models import Genre

from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer as BaseTokenRefreshSerializer,
    TokenBlacklistSerializer as BaseTokenBlacklistSerializer
)
from .utils.token_manager import TokenManager

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# Authentication Serializers
# ============================================================================

class CustomRegisterSerializer(RegisterSerializer):
    """
    Custom registration serializer with additional user fields.
    Handles email-based registration with email verification.
    """
    
    # Remove default fields
    username = None
    password1 = None
    password2 = None
    
    # Define custom fields
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[StrongPasswordValidator()],
        style={'input_type': 'password'},
        help_text=_("User password (minimum 8 characters)")
    )
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text=_("User's first name")
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text=_("User's last name")
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        validators=[AgeValidator(min_age=13)],
        help_text=_("User's date of birth (YYYY-MM-DD)")
    )

    def validate_email(self, email):
        """Ensure email is unique and properly formatted."""
        email = email.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("A user with this email already exists"))
        return email

    def validate_password(self, password):
        """Validate password strength."""
        if len(password) < 8:
            raise serializers.ValidationError(_("Password must be at least 8 characters long"))
        return password

    def validate(self, attrs):
        """Skip parent validation to avoid password2 requirement."""
        return attrs

    def save(self, request):
        """
        Create new user with email verification.
        
        Args:
            request: HTTP request object for building activation link
            
        Returns:
            User instance (inactive until email is verified)
        """
        email = self.validated_data.get('email')
        password = self.validated_data.get('password')
        first_name = self.validated_data.get('first_name', '')
        last_name = self.validated_data.get('last_name', '')
        date_of_birth = self.validated_data.get('date_of_birth')

        # Create user (inactive by default)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            activated=False
        )

        # Generate activation token and send email
        self._send_activation_email(user, request)
        
        logger.info(f"New user registered: {email}")
        return user

    def _send_activation_email(self, user, request):
        """
        Send account activation email to user.
        
        Args:
            user: User instance
            request: HTTP request for building absolute URL
        """
        try:
            token = account_activation_token.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = request.build_absolute_uri(
                reverse('rest_verify_email', kwargs={'uidb64': uidb64, 'token': token})
            )

            subject = _('Activate Your Account')
            message = _(
                'Please click the following link to activate your account:\n\n'
                '{link}\n\n'
                'This link will expire in 24 hours.'
            ).format(link=activation_link)

            send_mail(
                subject,
                message,
                'noreply@movielenz.com',
                [user.email],
                fail_silently=False
            )
            
            logger.info(f"Activation email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send activation email to {user.email}: {str(e)}")


class CustomLoginSerializer(serializers.Serializer):
    """
    Custom login serializer for email-based authentication.
    Validates credentials and ensures account is activated.
    """
    
    email = serializers.EmailField(
        required=True,
        write_only=True,
        help_text=_("User's email address")
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text=_("User's password")
    )

    def validate(self, attrs):
        """
        Authenticate user with email and password.
        
        Args:
            attrs: Dictionary with email and password
            
        Returns:
            attrs: Dictionary with authenticated user
            
        Raises:
            ValidationError: If credentials are invalid or account is inactive
        """
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password')
        request = self.context.get('request')

        if not email or not password:
            raise serializers.ValidationError(
                _('Email and password are required'),
                code='authorization'
            )

        logger.info(f"Login attempt for email: {email}")

        # Authenticate user
        user = authenticate(request=request, email=email, password=password)

        if not user:
            logger.warning(f"Authentication failed for {email}: Invalid credentials")
            raise serializers.ValidationError(
                _('Invalid email or password'),
                code='authorization'
            )

        # Check if account is activated
        if not user.activated:
            logger.warning(f"Authentication failed for {email}: Account not activated")
            raise serializers.ValidationError(
                _('Please activate your account via the email verification link'),
                code='authorization'
            )

        # Check if account is active
        if not user.is_active:
            logger.warning(f"Authentication failed for {email}: Account is disabled")
            raise serializers.ValidationError(
                _('Your account has been disabled'),
                code='authorization'
            )

        attrs['user'] = user
        logger.info(f"Authentication successful for {email}")
        return attrs


class CustomPasswordResetConfirmSerializer(BasePasswordResetConfirmSerializer):
    """
    Custom password reset confirmation serializer.
    Handles password reset with token validation.
    """
    
    def save(self):
        """
        Save new password for user.
        Calls parent implementation which handles token validation.
        
        Returns:
            User instance with updated password
        """
        return super().save()


class ResendEmailVerificationSerializer(serializers.Serializer):
    """Serializer for resending email verification link."""
    
    email = serializers.EmailField(
        required=True,
        help_text=_("Email address to resend verification to")
    )

    def validate_email(self, email):
        """Ensure user exists and is not already activated."""
        email = email.lower().strip()
        try:
            user = User.objects.get(email=email)
            if user.activated:
                raise serializers.ValidationError(_("This account is already activated"))
        except User.DoesNotExist:
            raise serializers.ValidationError(_("No account found with this email"))
        return email


# ============================================================================
# Social Authentication Serializers
# ============================================================================

class SocialAuthSerializer(serializers.Serializer):
    """Base serializer for social authentication providers."""
    
    access_token = serializers.CharField(
        required=True,
        write_only=True,
        help_text=_("OAuth access token from social provider")
    )

    def validate_access_token(self, access_token):
        """Validate that access token is provided."""
        if not access_token:
            raise serializers.ValidationError(_("Access token is required"))
        return access_token


class GoogleSocialAuthSerializer(SocialAuthSerializer):
    """Serializer for Google OAuth authentication."""
    
    def validate(self, attrs):
        """
        Validate Google access token and retrieve user info.
        
        Args:
            attrs: Dictionary with access_token
            
        Returns:
            attrs: Dictionary with validated user_data
            
        Raises:
            ValidationError: If token is invalid or email not verified
        """
        access_token = attrs.get('access_token')
        
        try:
            # Verify token with Google API
            google_user_info_url = f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}"
            response = requests.get(google_user_info_url, timeout=10)
            
            if response.status_code != 200:
                raise serializers.ValidationError(_("Invalid Google access token"))
            
            user_data = response.json()
            
            # Verify email is confirmed by Google
            if not user_data.get('verified_email', False):
                raise serializers.ValidationError(_("Google email is not verified"))
            
            attrs['user_data'] = user_data
            return attrs
            
        except requests.RequestException as e:
            logger.error(f"Google token verification failed: {str(e)}")
            raise serializers.ValidationError(_("Failed to verify Google token"))


class TwitterSocialAuthSerializer(SocialAuthSerializer):
    """Serializer for Twitter OAuth authentication."""
    
    def validate(self, attrs):
        """
        Validate Twitter access token and retrieve user info.
        
        Args:
            attrs: Dictionary with access_token
            
        Returns:
            attrs: Dictionary with validated user_data
            
        Raises:
            ValidationError: If token is invalid
        """
        access_token = attrs.get('access_token')
        
        try:
            # Verify token with Twitter API v2
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            
            twitter_user_info_url = "https://api.twitter.com/2/users/me?user.fields=email,verified"
            response = requests.get(twitter_user_info_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                raise serializers.ValidationError(_("Invalid Twitter access token"))
            
            user_data = response.json().get('data', {})
            attrs['user_data'] = user_data
            return attrs
            
        except requests.RequestException as e:
            logger.error(f"Twitter token verification failed: {str(e)}")
            raise serializers.ValidationError(_("Failed to verify Twitter token"))


# ============================================================================
# User Profile Serializers
# ============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile with genre preferences.
    Provides read and write operations for user data.
    """
    
    # Write-only field for genre IDs
    preferred_genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.none(),
        many=True,
        source='preferred_genres',
        write_only=True,
        required=False,
        help_text=_("List of preferred genre IDs")
    )
    
    # Read-only hyperlinks to genres
    preferred_genres_hyperlinks = serializers.HyperlinkedRelatedField(
        many=True,
        source='preferred_genres',
        read_only=True,
        view_name='genre-detail',
        help_text=_("Hyperlinks to preferred genres")
    )
    
    # Read-only genre names
    preferred_genres_display = serializers.StringRelatedField(
        source='preferred_genres',
        many=True,
        read_only=True,
        help_text=_("Names of preferred genres")
    )
    
    # Computed field for subscription status
    has_active_subscription = serializers.SerializerMethodField(
        help_text=_("Whether user has active premium subscription")
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'activated',
            'profile_picture', 'date_of_birth', 'subscription_status',
            'subscription_end_date', 'preferred_language', 'role',
            'preferred_genres_display', 'preferred_genres_hyperlinks',
            'preferred_genre_ids', 'has_active_subscription',
            'last_login', 'date_joined'
        )
        read_only_fields = (
            'id', 'email', 'subscription_status', 'subscription_end_date',
            'last_login', 'date_joined', 'activated', 'role'
        )
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'profile_picture': {'required': False, 'allow_null': True},
            'date_of_birth': {'required': False, 'allow_null': True},
            'preferred_language': {'required': False},
        }

    def __init__(self, *args, **kwargs):
        """Initialize serializer with Genre queryset."""
        super().__init__(*args, **kwargs)
        if 'preferred_genre_ids' in self.fields:
            self.fields['preferred_genre_ids'].queryset = Genre.objects.all()

    def get_has_active_subscription(self, obj):
        """Check if user has active premium subscription."""
        return obj.has_active_premium_subscription()

    def validate_profile_picture(self, value):
        """Validate profile picture file size and format."""
        if value:
            # Maximum file size: 5MB
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(_("Profile picture must be smaller than 5MB"))
            
            # Allowed formats
            allowed_formats = ['image/jpeg', 'image/png', 'image/webp']
            if value.content_type not in allowed_formats:
                raise serializers.ValidationError(_("Only JPEG, PNG, and WebP images are allowed"))
        
        return value


# ============================================================================
# Content Interaction Serializers
# ============================================================================

class BaseUserContentInteractionSerializer(serializers.ModelSerializer):
    """
    Base serializer for user-content interactions.
    Handles watchlist, favorites, and recently watched items.
    """
    
    content_item_url = serializers.URLField(
        write_only=True,
        help_text=_('URL of the content item (e.g., http://example.com/movie/3/)')
    )
    content_details = serializers.SerializerMethodField(
        read_only=True,
        help_text=_("Details about the content item")
    )

    class Meta:
        model = None
        fields = ('id', 'user', 'content_item_url', 'content_details', 'added_at')
        read_only_fields = ('user', 'added_at', 'id')

    def _get_model_from_view_match(self, match):
        """
        Extract model class from resolved URL match.
        
        Args:
            match: ResolverMatch object from Django URL resolver
            
        Returns:
            Model class or None if not found
        """
        view_class = getattr(match.func, 'cls', None)
        if not view_class:
            return None

        # Try to get model from queryset
        queryset = getattr(view_class, 'queryset', None)
        if queryset is not None:
            return queryset.model

        # Try to get model from serializer
        serializer_class = getattr(view_class, 'serializer_class', None)
        if serializer_class and hasattr(serializer_class, 'Meta'):
            return getattr(serializer_class.Meta, 'model', None)

        return None

    def get_content_details(self, obj):
        """
        Get detailed information about the content object.
        
        Args:
            obj: Interaction instance (WatchlistItem, FavoriteItem, etc.)
            
        Returns:
            Dictionary with content details or None
        """
        if not obj.content_object:
            return None

        request = self.context.get('request')
        item_url = None
        
        # Get view name from context mapping
        model_to_view_name_map = self.context.get('model_to_view_name_map', {})
        view_name = model_to_view_name_map.get(obj.content_type.model)

        # Build absolute URL
        if request and view_name:
            try:
                item_url = reverse(
                    view_name,
                    kwargs={'pk': obj.content_object.pk},
                    request=request
                )
            except NoReverseMatch:
                logger.warning(f"Could not reverse URL for {view_name}")
                item_url = None

        return {
            'id': obj.content_object.pk,
            'title': getattr(obj.content_object, 'title', str(obj.content_object)),
            'type': obj.content_type.model,
            'url': item_url
        }

    def validate(self, attrs):
        """
        Validate content URL and resolve to model instance.
        
        Args:
            attrs: Dictionary of field values
            
        Returns:
            attrs: Validated attributes with resolved content type and object ID
            
        Raises:
            ValidationError: If URL is invalid or content doesn't exist
        """
        content_item_url = attrs.get('content_item_url')
        current_user = self.context['request'].user

        # Skip validation for updates without URL
        if self.instance and not content_item_url:
            return super().validate(attrs)

        # URL is required for creation
        if not self.instance and not content_item_url:
            raise serializers.ValidationError({
                "content_item_url": _("This field is required for creation")
            })

        if content_item_url:
            # Parse and resolve URL
            try:
                parsed_url = urlparse(content_item_url)
                path = parsed_url.path
                match = resolve(path)
            except Resolver404:
                raise serializers.ValidationError({
                    'content_item_url': _("URL path does not match any known patterns")
                })
            except Exception as e:
                raise serializers.ValidationError({
                    'content_item_url': _("Invalid URL format: {error}").format(error=str(e))
                })

            # Extract model class from URL
            model_class = self._get_model_from_view_match(match)
            if not model_class:
                raise serializers.ValidationError({
                    'content_item_url': _("Could not determine content type from URL")
                })

            # Extract object ID from URL
            object_pk_str = match.kwargs.get('pk')
            if not object_pk_str:
                # Fallback: search all kwargs for numeric value
                for kw_val in match.kwargs.values():
                    if isinstance(kw_val, (int, str)) and str(kw_val).isdigit():
                        object_pk_str = str(kw_val)
                        break
                
                if not object_pk_str:
                    raise serializers.ValidationError({
                        'content_item_url': _("Could not extract object ID from URL")
                    })

            try:
                object_pk = int(object_pk_str)
            except ValueError:
                raise serializers.ValidationError({
                    'content_item_url': _("Object ID is not a valid integer")
                })

            # Verify content object exists
            if not model_class.objects.filter(pk=object_pk).exists():
                raise serializers.ValidationError({
                    'content_item_url': _("Content object does not exist")
                })

            content_type_resolved = ContentType.objects.get_for_model(model_class)

            # Store resolved values
            attrs['resolved_content_type'] = content_type_resolved
            attrs['resolved_object_id'] = object_pk

            # Check for duplicates on creation
            if not self.instance:
                InteractionModel = self.Meta.model
                existing_item = InteractionModel.objects.filter(
                    user=current_user,
                    content_type=content_type_resolved,
                    object_id=object_pk
                ).first()
                
                if existing_item:
                    attrs['existing_item_instance'] = existing_item

        return attrs

    def create(self, validated_data):
        """
        Create or return existing interaction item.
        
        Args:
            validated_data: Validated serializer data
            
        Returns:
            Interaction instance (created or existing)
        """
        # Return existing item if found
        existing_item = validated_data.pop('existing_item_instance', None)
        if existing_item:
            self.instance = existing_item
            self._is_existing_instance = True
            return self.instance

        self._is_existing_instance = False

        # Remove URL and add resolved values
        validated_data.pop('content_item_url', None)
        content_type = validated_data.pop('resolved_content_type')
        object_id = validated_data.pop('resolved_object_id')

        validated_data['user'] = self.context['request'].user
        validated_data['content_type'] = content_type
        validated_data['object_id'] = object_id

        try:
            return super().create(validated_data)
        except IntegrityError:
            # Handle race condition: item created between validation and save
            InteractionModel = self.Meta.model
            instance = InteractionModel.objects.filter(
                user=validated_data['user'],
                content_type=content_type,
                object_id=object_id
            ).first()
            
            if instance:
                self.instance = instance
                self._is_existing_instance = True
                return instance
            
            raise serializers.ValidationError(_("Database constraint violation"))


class WatchlistItemSerializer(BaseUserContentInteractionSerializer):
    """Serializer for watchlist items."""
    
    class Meta(BaseUserContentInteractionSerializer.Meta):
        model = WatchlistItem


class FavoriteItemSerializer(BaseUserContentInteractionSerializer):
    """Serializer for favorite items."""
    
    class Meta(BaseUserContentInteractionSerializer.Meta):
        model = FavoriteItem


class RecentlyWatchedItemSerializer(BaseUserContentInteractionSerializer):
    """Serializer for recently watched items with progress tracking."""
    
    progress_seconds = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text=_("Playback progress in seconds")
    )

    class Meta:
        model = RecentlyWatchedItem
        fields = (
            'id', 'user', 'content_item_url', 'content_details',
            'watched_at', 'progress_seconds'
        )
        read_only_fields = ('user', 'id', 'watched_at')

    def create(self, validated_data):
        """
        Create or update recently watched item with progress.
        
        Args:
            validated_data: Validated serializer data
            
        Returns:
            RecentlyWatchedItem instance
        """
        user_instance = validated_data['user']
        content_type = validated_data.pop('resolved_content_type')
        object_id = validated_data.pop('resolved_object_id')
        validated_data.pop('content_item_url', None)

        lookup_data = {
            'user': user_instance,
            'content_type': content_type,
            'object_id': object_id,
        }
        
        defaults_data = {
            'progress_seconds': validated_data.get('progress_seconds'),
            'watched_at': timezone.now()
        }

        instance, created = RecentlyWatchedItem.objects.update_or_create(
            **lookup_data,
            defaults=defaults_data
        )
        return instance

    def update(self, instance, validated_data):
        """
        Update watch progress and timestamp.
        
        Args:
            instance: Existing RecentlyWatchedItem
            validated_data: New data
            
        Returns:
            Updated instance
        """
        instance.progress_seconds = validated_data.get('progress_seconds', instance.progress_seconds)
        instance.watched_at = timezone.now()
        instance.save(update_fields=['progress_seconds', 'watched_at'])
        return instance
    
from .utils.token_manager import TokenManager


# ============================================================================
# JWT Token Serializers
# ============================================================================

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     """
#     Custom token serializer with additional user claims.
    
#     Extends default TokenObtainPairSerializer to include:
#     - User email
#     - User role
#     - Subscription status
#     - Email verification status
#     """
    
#     @classmethod
#     def get_token(cls, user):
#         """
#         Generate token with custom claims for user.
        
#         Args:
#             user: Authenticated User instance
            
#         Returns:
#             RefreshToken with custom claims
#         """
#         token = super().get_token(user)
        
#         # Add custom claims
#         token['email'] = user.email
#         token['role'] = user.role
#         token['subscription_status'] = user.subscription_status
#         token['activated'] = user.activated
        
#         return token
    
#     def validate(self, attrs):
#         """
#         Validate credentials and generate tokens.
        
#         Ensures user account is active and email is verified
#         before issuing tokens.
        
#         Args:
#             attrs: Dictionary with username and password
            
#         Returns:
#             Dictionary with tokens and user info
            
#         Raises:
#             ValidationError: If account is inactive or not verified
#         """
#         data = super().validate(attrs)
        
#         # Check if user is activated
#         if not self.user.activated:
#             logger.warning(f"Login attempt with unverified email: {self.user.email}")
#             raise serializers.ValidationError(
#                 _("Please verify your email address before logging in"),
#                 code='email_not_verified'
#             )
        
#         # Add user information to response
#         data['user'] = {
#             'id': self.user.id,
#             'email': self.user.email,
#             'first_name': self.user.first_name,
#             'last_name': self.user.last_name,
#             'role': self.user.role,
#             'subscription_status': self.user.subscription_status,
#             'activated': self.user.activated,
#         }
        
#         # Add token expiration info
#         access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=15))
#         refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))
        
#         now = timezone.now()
#         data['access_expires_at'] = (now + access_lifetime).isoformat()
#         data['refresh_expires_at'] = (now + refresh_lifetime).isoformat()
        
#         logger.info(f"Tokens issued for user: {self.user.email}")
#         return data


class CustomTokenRefreshSerializer(BaseTokenRefreshSerializer):
    """
    Custom token refresh serializer with rotation support.
    
    Handles refresh token rotation and blacklisting of old tokens.
    """
    
    def validate(self, attrs):
        """
        Validate refresh token and generate new access token.
        
        Args:
            attrs: Dictionary with refresh token
            
        Returns:
            Dictionary with new tokens and expiration info
            
        Raises:
            ValidationError: If refresh token is invalid or blacklisted
        """
        refresh_token = attrs.get('refresh')
        
        try:
            # Use TokenManager for refresh logic
            tokens = TokenManager.refresh_access_token(refresh_token)
            
            logger.info("Token refreshed successfully")
            return tokens
            
        except (TokenError, InvalidToken) as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            raise serializers.ValidationError(
                _("Invalid or expired refresh token"),
                code='token_not_valid'
            )
        except AuthenticationFailed as e:
            logger.warning(f"Authentication failed during refresh: {str(e)}")
            raise serializers.ValidationError(str(e), code='authentication_failed')
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise serializers.ValidationError(
                _("An error occurred while refreshing token"),
                code='token_refresh_failed'
            )


class CustomTokenBlacklistSerializer(BaseTokenBlacklistSerializer):
    """
    Custom serializer for blacklisting refresh tokens.
    
    Used during logout to invalidate user's refresh token.
    """
    
    def validate(self, attrs):
        """
        Validate and blacklist refresh token.
        
        Args:
            attrs: Dictionary with refresh token
            
        Returns:
            Empty dictionary on success
            
        Raises:
            ValidationError: If token cannot be blacklisted
        """
        refresh_token = attrs.get('refresh')
        
        try:
            TokenManager.blacklist_token(refresh_token)
            logger.info("Token blacklisted successfully")
            return {}
            
        except TokenError as e:
            logger.warning(f"Token blacklist failed: {str(e)}")
            raise serializers.ValidationError(
                _("Invalid refresh token"),
                code='token_not_valid'
            )


class TokenVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying token validity.
    
    Checks if a token is valid and returns its payload.
    """
    
    token = serializers.CharField(
        required=True,
        help_text=_("JWT token to verify")
    )
    token_type = serializers.ChoiceField(
        choices=['access', 'refresh'],
        default='access',
        help_text=_("Type of token to verify")
    )
    
    def validate(self, attrs):
        """
        Verify token and return payload.
        
        Args:
            attrs: Dictionary with token and token_type
            
        Returns:
            Dictionary with validation result and payload
            
        Raises:
            ValidationError: If token is invalid
        """
        token = attrs.get('token')
        token_type = attrs.get('token_type', 'access')
        
        is_valid, payload = TokenManager.verify_token(token, token_type)
        
        if not is_valid:
            raise serializers.ValidationError(
                _("Token is invalid or expired"),
                code='token_not_valid'
            )
        
        return {
            'valid': True,
            'payload': payload
        }