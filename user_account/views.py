"""
Views for user authentication, profile management, and content interactions.
Handles registration, login, password reset, and CRUD for watchlist/favorites.
"""
import logging
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.urls import resolve, Resolver404, reverse
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode
from django.db import models

from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from dj_rest_auth.views import (
    PasswordChangeView,
    PasswordResetView, PasswordResetConfirmView as BasePasswordResetConfirmView
)
from dj_rest_auth.registration.views import RegisterView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample

from .models import WatchlistItem, FavoriteItem, RecentlyWatchedItem
from .tokens import account_activation_token
from .serializers import (
    CustomRegisterSerializer, UserProfileSerializer,
    WatchlistItemSerializer, FavoriteItemSerializer,
    RecentlyWatchedItemSerializer, CustomPasswordResetConfirmSerializer,
    GoogleSocialAuthSerializer, TwitterSocialAuthSerializer,
    CustomLoginSerializer, 
    # CustomTokenObtainPairSerializer, 
    CustomTokenRefreshSerializer, CustomTokenBlacklistSerializer,TokenVerifySerializer
)
from .permissions import (
     IsSelfOrAdmin
)
from .throttling import (
    LoginAttemptThrottle, RegisterThrottle
)

from rest_framework_simplejwt.views import (
    TokenRefreshView as BaseTokenRefreshView,
)
from .utils.token_manager import TokenManager

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# Authentication Views
# ============================================================================
@extend_schema(
    summary="User Registration",
    description="Create a new user account with email verification",
    request=CustomRegisterSerializer,
    responses={
        201: OpenApiExample(
            'Success',
            value={
                'detail': 'Registration successful',
                'email': 'user@example.com'
            }
        ),
        400: OpenApiExample(
            'Validation Error',
            value={
                'email': ['This field is required.']
            }
        )
    },
    tags=['Authentication']
)
class CustomRegisterView(RegisterView):
    """
    Handle user registration with email verification.
    Sends activation email after successful registration.
    """
    serializer_class = CustomRegisterSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        """
        Create new user account and send verification email.
        
        Returns:
            201: User created successfully
            400: Validation errors
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(request)
        
        logger.info(f"User registered: {user.email}")
        
        return Response(
            {
                "detail": _("Registration successful. Please check your email to activate your account."),
                "email": user.email
            },
            status=status.HTTP_201_CREATED
        )

@extend_schema_view(
    get=extend_schema(
        summary="Verify Email Address",
        description="Activate account using token from email.",
        
    ),
)
class CustomVerifyEmailView(APIView):
    """
    Verify user email address using token from activation link.
    Activates account upon successful verification.
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """
        Activate user account via email verification token.
        
        Args:
            uidb64: Base64 encoded user ID
            token: Email verification token
            
        Returns:
            200: Account activated successfully
            400: Invalid or expired token
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            logger.warning(f"Invalid UID in email verification: {uidb64}")
            return Response(
                {'error': _('Invalid activation link')},
                status=status.HTTP_400_BAD_REQUEST
            )

        if account_activation_token.check_token(user, token):
            user.activated = True
            user.is_active = True
            user.save(update_fields=['activated', 'is_active'])
            
            logger.info(f"Email verified for user: {user.email}")
            return Response(
                {'success': _('Email verified successfully. You can now log in.')},
                status=status.HTTP_200_OK
            )
        else:
            logger.warning(f"Invalid token for user: {user.email}")
            return Response(
                {'error': _('Invalid or expired activation link')},
                status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema_view(
    post=extend_schema(
        summary="Resend Verification Email",
        description="Send new activation link to user.",
    ),
)
class ResendEmailVerificationView(generics.GenericAPIView):
    """
    Resend email verification link to registered users.
    Useful when activation email was not received or expired.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Send new verification email to user.
        
        Request body:
            email: User's email address
            
        Returns:
            200: Email sent successfully
            404: User not found
            400: Account already activated
        """
        email = request.data.get('email', '').lower().strip()

        if not email:
            return Response(
                {"detail": _("Email is required")},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": _("No account found with this email")},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.activated:
            return Response(
                {"detail": _("This account is already activated")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate new activation link
        token = account_activation_token.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = request.build_absolute_uri(
            reverse('rest_verify_email', kwargs={'uidb64': uidb64, 'token': token})
        )

        # Send email
        subject = _('Activate Your Account')
        message = _('Please click the link to activate your account:\n{link}').format(link=activation_link)
        send_mail(subject, message, 'noreply@movielenz.com', [user.email])

        logger.info(f"Verification email resent to {user.email}")
        return Response(
            {"detail": _("Verification email sent successfully")},
            status=status.HTTP_200_OK
        )

@extend_schema_view(
    post=extend_schema(
        summary="User Login",
        description="Authenticate user and return JWT tokens.",
    ),
)
class CustomLoginView(APIView):
    """
    Handle user login with email and password.
    Returns JWT tokens upon successful authentication.
    """
    serializer_class = CustomLoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginAttemptThrottle]

    def post(self, request, *args, **kwargs):
        """
        Authenticate user and return access tokens.
        
        Request body:
            email: User's email
            password: User's password
            
        Returns:
            200: Login successful with tokens
            400: Invalid credentials or inactive account
        """
        email = request.data.get('email', 'unknown')
        logger.info(f"Login attempt for: {email}")

        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens using TokenManager
        tokens = TokenManager.generate_tokens_for_user(user)
        
        # Add user info to response
        tokens['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'subscription_status': user.subscription_status,
            'activated': user.activated,
        }
        
        logger.info(f"Login successful for: {email}")
        return Response(tokens, status=status.HTTP_200_OK)

@extend_schema_view(
    post=extend_schema(
        summary="User Logout",
        description="Invalidate tokens and logout user.",
    ),
)
class CustomLogoutView(APIView):
    """
    Handle user logout and token invalidation.
    Only accepts POST requests to prevent accidental logout.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Log out current user and invalidate tokens.
        
        Request body:
            refresh: Refresh token to blacklist
            
        Returns:
            200: Logout successful
        """
        user_email = request.user.email
        refresh_token = request.data.get('refresh')
        
        if refresh_token:
            try:
                TokenManager.blacklist_token(refresh_token)
                logger.info(f"User logged out: {user_email}")
                return Response(
                    {"detail": _("Logged out successfully")},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                logger.error(f"Logout error for {user_email}: {str(e)}")
                return Response(
                    {"detail": _("Logout failed")},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"detail": _("Refresh token required")},
                status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema_view(
    post=extend_schema(
        summary="Change Password",
        description="Update password for authenticated user.",
    ),
)
class CustomPasswordChangeView(PasswordChangeView):
    """
    Allow authenticated users to change their password.
    Requires old password for verification.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Change user password.
        
        Request body:
            old_password: Current password
            new_password1: New password
            new_password2: Confirm new password
            
        Returns:
            200: Password changed successfully
            400: Validation errors
        """
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"Password changed for user: {request.user.email}")
            return Response(
                {"detail": _("Password changed successfully")},
                status=status.HTTP_200_OK
            )
        
        return response

@extend_schema_view(
    post=extend_schema(
        summary="Request Password Reset",
        description="Send password reset email to user.",
    ),
)
class CustomPasswordResetView(PasswordResetView):
    """
    Send password reset email to user.
    Generates reset link with expiring token.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Send password reset email.
        
        Request body:
            email: User's email address
            
        Returns:
            200: Email sent (even if user doesn't exist for security)
            400: Invalid request
        """
        email = request.data.get('email', '').lower().strip()
        
        if not email:
            return Response(
                {"detail": _("Email is required")},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Password reset requested for: {email}")

        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == status.HTTP_200_OK:
                logger.info(f"Password reset email sent to: {email}")
                return Response(
                    {"detail": _("Password reset email sent. Please check your inbox.")},
                    status=status.HTTP_200_OK
                )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error sending password reset email: {str(e)}")
            return Response(
                {"detail": _("An error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema_view(
    post=extend_schema(
        summary="Confirm Password Reset",
        description="Set new password using reset token.",
    ),
)
class CustomPasswordResetConfirmView(BasePasswordResetConfirmView):
    """
    Confirm password reset and set new password.
    Validates reset token and updates user password.
    """
    serializer_class = CustomPasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        """
        Set new password using reset token.
        
        URL parameters:
            uidb64: Encoded user ID
            token: Password reset token
            
        Request body:
            new_password1: New password
            new_password2: Confirm new password
            
        Returns:
            200: Password reset successful
            400: Invalid token or validation errors
        """
        logger.debug(f"Password reset confirm request. UID: {kwargs.get('uidb64')}")

        # Prepare serializer data with URL parameters
        serializer_data = request.data.copy()
        serializer_data['uid'] = kwargs.get('uidb64')
        serializer_data['token'] = kwargs.get('token')

        serializer = self.get_serializer(data=serializer_data)

        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            logger.info(f"Password reset successful for UID: {kwargs.get('uidb64')}")
            return Response(
                {"detail": _("Password has been reset successfully")},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            logger.warning(f"Password reset validation error: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Unexpected error in password reset: {str(e)}")
            return Response(
                {"detail": _("An internal error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# Social Authentication Views
# ============================================================================
@extend_schema_view(
    post=extend_schema(
        summary="Google OAuth Login",
        description="Authenticate user via Google account.",
    ),
)
class GoogleSocialAuthView(APIView):
    """
    Handle Google OAuth authentication.
    Creates or authenticates user with Google credentials.
    """
    permission_classes = [AllowAny]
    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):
        """
        Login or register user via Google OAuth.
        
        Request body:
            access_token: Google OAuth access token
            
        Returns:
            200: Authentication successful with JWT tokens
            400: Invalid token or validation errors
        """
        serializer = self.serializer_class(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user_data = serializer.validated_data['user_data']

            email = user_data.get('email')
            if not email:
                return Response(
                    {'error': _('Email not provided by Google')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': user_data.get('given_name', ''),
                    'last_name': user_data.get('family_name', ''),
                    'activated': True,
                    'is_active': True
                }
            )

            if created:
                logger.info(f"New user created via Google: {email}")
            else:
                logger.info(f"Existing user logged in via Google: {email}")

            # Generate JWT tokens using TokenManager
            tokens = TokenManager.generate_tokens_for_user(user)
            
            tokens['user'] = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'activated': user.activated,
            }

            return Response(tokens, status=status.HTTP_200_OK)

        except ValidationError as e:
            logger.warning(f"Google auth validation error: {e.detail}")
            return Response(
                {'error': _('Invalid Google token')},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Google auth error: {str(e)}")
            return Response(
                {'error': _('Authentication failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema_view(
    post=extend_schema(
        summary="Twitter OAuth Login",
        description="Authenticate user via Twitter account.",
    ),
)
class TwitterSocialAuthView(APIView):
    """
    Handle Twitter OAuth authentication.
    Creates or authenticates user with Twitter credentials.
    """
    permission_classes = [AllowAny]
    serializer_class = TwitterSocialAuthSerializer

    def post(self, request):
        """
        Login or register user via Twitter OAuth.
        
        Request body:
            access_token: Twitter OAuth access token
            
        Returns:
            200: Authentication successful with JWT tokens
            400: Invalid token or validation errors
        """
        serializer = self.serializer_class(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user_data = serializer.validated_data['user_data']

            email = user_data.get('email')
            username = user_data.get('username')
            name = user_data.get('name', '')

            if not email and not username:
                return Response(
                    {'error': _('Email or username not provided by Twitter')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Use email if available, otherwise create placeholder
            lookup_email = email if email else f"{username}@twitter.placeholder"

            # Get or create user
            try:
                if email:
                    user = User.objects.get(email=email)
                else:
                    user = User.objects.filter(
                        models.Q(email__icontains=username) |
                        models.Q(username=username)
                    ).first()

                    if not user:
                        raise User.DoesNotExist

                logger.info(f"Existing user logged in via Twitter: {lookup_email}")

            except User.DoesNotExist:
                # Create new user
                name_parts = name.split(' ', 1) if name else ['', '']
                first_name = name_parts[0] if len(name_parts) > 0 else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                user = User.objects.create_user(
                    email=lookup_email,
                    username=username or lookup_email,
                    first_name=first_name,
                    last_name=last_name,
                    activated=True,
                    is_active=True
                )
                logger.info(f"New user created via Twitter: {lookup_email}")

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'activated': user.activated,
                }
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            logger.warning(f"Twitter auth validation error: {e.detail}")
            return Response(
                {'error': _('Invalid Twitter token')},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Twitter auth error: {str(e)}")
            return Response(
                {'error': _('Authentication failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# User Profile Views
# ============================================================================
@extend_schema_view(
    retrieve=extend_schema(
        summary="Get User Profile",
        description="Retrieve authenticated user's profile data.",
    ),
    partial_update=extend_schema(
        summary="Update User Profile",
        description="Partially update user profile information.",
    ),
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update authenticated user's profile.
    Supports partial updates (PATCH).
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsSelfOrAdmin]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        """Return current authenticated user."""
        return self.request.user

    def perform_update(self, serializer):
        """Save profile updates for current user."""
        serializer.save()
        logger.info(f"Profile updated for user: {self.request.user.email}")
    
    def get_queryset(self):
        return User.objects.prefetch_related('preferred_genres').select_related()


# ============================================================================
# Content Interaction Views
# ============================================================================

class BaseUserContentInteractionViewSet(viewsets.ModelViewSet):
    """
    Base viewset for user content interactions.
    Provides CRUD operations for watchlist, favorites, and watch history.
    """
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to current user's items only."""
        return self.Meta.model.objects.filter(user=self.request.user).select_related('content_type')

    def perform_create(self, serializer):
        """Set user to current authenticated user."""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Create new interaction or return existing one.
        
        Returns:
            201: Created new item
            200: Item already exists
            400: Validation errors
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # Check if item already existed
        current_status = status.HTTP_201_CREATED
        if hasattr(serializer, '_is_existing_instance') and serializer._is_existing_instance:
            current_status = status.HTTP_200_OK

        return Response(serializer.data, status=current_status, headers=headers)

    @action(detail=False, methods=['delete'], url_path='content')
    def delete_by_content_item(self, request, *args, **kwargs):
        """
        Delete interaction by content item URL.
        
        Request body:
            content_item_url: URL of content to remove
            
        Returns:
            204: Item deleted successfully
            404: Item not found
            400: Invalid URL
        """
        content_item_url = request.data.get('content_item_url')

        if not content_item_url:
            return Response(
                {"content_item_url": [_("This field is required")]},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_url = urlparse(content_item_url)
            path = parsed_url.path
            match = resolve(path)
        except Resolver404:
            return Response(
                {'content_item_url': _("URL path does not match any known patterns")},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'content_item_url': _("Invalid URL: {error}").format(error=str(e))},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get model class from URL
        serializer_class = self.get_serializer_class()
        temp_serializer = serializer_class()
        model_class = temp_serializer._get_model_from_view_match(match)

        if not model_class:
            return Response(
                {'content_item_url': _("Could not determine content type from URL")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract object ID
        object_pk_str = match.kwargs.get('pk')
        if not object_pk_str:
            for kw_val in match.kwargs.values():
                if isinstance(kw_val, (int, str)) and str(kw_val).isdigit():
                    object_pk_str = str(kw_val)
                    break

            if not object_pk_str:
                return Response(
                    {'content_item_url': _("Could not extract object ID from URL")},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            object_pk = int(object_pk_str)
        except ValueError:
            return Response(
                {'content_item_url': _("Object ID is not a valid integer")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete interaction
        content_type_resolved = ContentType.objects.get_for_model(model_class)
        deleted_count, _ = self.Meta.model.objects.filter(
            user=request.user,
            content_type=content_type_resolved,
            object_id=object_pk
        ).delete()

        if deleted_count > 0:
            logger.info(f"Deleted {self.Meta.model.__name__} for user {request.user.id}, content {object_pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": _("Item not found")},
                status=status.HTTP_404_NOT_FOUND
            )

@extend_schema_view(
    list=extend_schema(
        summary="List Watchlist Items",
        description="Get all watchlist items for user.",
    ),
    create=extend_schema(
        summary="Add to Watchlist",
        description="Add content item to watchlist.",
    ),
    destroy=extend_schema(
        summary="Remove from Watchlist",
        description="Delete item from user's watchlist.",
    ),
)
class WatchlistViewSet(BaseUserContentInteractionViewSet):
    """
    Manage user's watchlist.
    CRUD operations for items user wants to watch later.
    """
    serializer_class = WatchlistItemSerializer

    class Meta:
        model = WatchlistItem

@extend_schema_view(
    list=extend_schema(
        summary="List Favorite Items",
        description="Get all favorite items for user.",
    ),
    create=extend_schema(
        summary="Add to Favorites",
        description="Mark content item as favorite.",
    ),
    destroy=extend_schema(
        summary="Remove from Favorites",
        description="Delete item from user's favorites.",
    ),
)
class FavoriteViewSet(BaseUserContentInteractionViewSet):
    """
    Manage user's favorite items.
    CRUD operations for content user has marked as favorite.
    """
    serializer_class = FavoriteItemSerializer

    class Meta:
        model = FavoriteItem

@extend_schema_view(
    list=extend_schema(
        summary="List Watch History",
        description="Get recently watched items with progress.",
    ),
    create=extend_schema(
        summary="Add to Watch History",
        description="Record watched content with progress.",
    ),
    destroy=extend_schema(
        summary="Remove from History",
        description="Delete item from watch history.",
    ),
)
class RecentlyWatchedViewSet(BaseUserContentInteractionViewSet):
    """
    Manage user's watch history with progress tracking.
    Supports resume playback functionality.
    """
    serializer_class = RecentlyWatchedItemSerializer

    class Meta:
        model = RecentlyWatchedItem

    def get_queryset(self):
        """Return watch history ordered by most recent."""
        return super().get_queryset().order_by('-watched_at')
    
    
# ============================================================================
# JWT Token Views
# ============================================================================

# @extend_schema_view(
#     post=extend_schema(
#         summary="Obtain JWT Tokens",
#         description=(
#             "Authenticate with email and password to receive JWT access and refresh tokens. "
#             "Access token is short-lived (15 minutes) and used for API authentication. "
#             "Refresh token is long-lived (7 days) and used to obtain new access tokens."
#         ),
#         request=CustomTokenObtainPairSerializer,
#         responses={
#             200: OpenApiExample(
#                 'Success',
#                 value={
#                     'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
#                     'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
#                     'access_expires_at': '2025-10-13T12:30:00Z',
#                     'refresh_expires_at': '2025-10-20T12:15:00Z',
#                     'user': {
#                         'id': 1,
#                         'email': 'user@example.com',
#                         'role': 'NORMAL_USER',
#                         'subscription_status': 'free',
#                         'activated': True
#                     }
#                 }
#             ),
#             400: OpenApiExample(
#                 'Invalid Credentials',
#                 value={'detail': 'Invalid email or password'}
#             ),
#             401: OpenApiExample(
#                 'Email Not Verified',
#                 value={'detail': 'Please verify your email address before logging in'}
#             )
#         },
#         tags=['JWT Authentication']
#     ),
# )
# class CustomTokenObtainPairView(TokenObtainPairView):
#     """
#     Obtain JWT access and refresh tokens via email/password authentication.
    
#     Returns both tokens with custom claims including user role and subscription status.
#     Requires email to be verified before issuing tokens.
#     """
#     serializer_class = CustomTokenObtainPairSerializer
    
#     def post(self, request, *args, **kwargs):
#         """
#         Authenticate user and return JWT tokens.
        
#         Request body:
#             email: User's email address
#             password: User's password
            
#         Returns:
#             200: Tokens issued successfully
#             400: Invalid credentials
#             401: Email not verified or account inactive
#         """
#         email = request.data.get('email', 'unknown')
#         logger.info(f"Token obtain request for: {email}")
        
#         response = super().post(request, *args, **kwargs)
        
#         if response.status_code == 200:
#             logger.info(f"Tokens issued successfully for: {email}")
#         else:
#             logger.warning(f"Token obtain failed for: {email}")
        
#         return response


@extend_schema_view(
    post=extend_schema(
        summary="Refresh JWT Access Token",
        description=(
            "Exchange a valid refresh token for a new access token. "
            "If ROTATE_REFRESH_TOKENS is enabled, also returns a new refresh token "
            "and blacklists the old one."
        ),
        request=CustomTokenRefreshSerializer,
        responses={
            200: OpenApiExample(
                'Success',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'access_expires_at': '2025-10-13T12:45:00Z',
                    'refresh_expires_at': '2025-10-20T12:30:00Z'
                }
            ),
            401: OpenApiExample(
                'Invalid Token',
                value={'detail': 'Invalid or expired refresh token'}
            )
        },
        tags=['JWT Authentication']
    ),
)
class CustomTokenRefreshView(BaseTokenRefreshView):
    """
    Refresh JWT access token using valid refresh token.
    
    Supports automatic rotation of refresh tokens for enhanced security.
    Old refresh tokens are blacklisted after rotation.
    """
    serializer_class = CustomTokenRefreshSerializer
    
    def post(self, request, *args, **kwargs):
        """
        Generate new access token from refresh token.
        
        Request body:
            refresh: Valid JWT refresh token
            
        Returns:
            200: New tokens issued
            401: Invalid or expired refresh token
        """
        logger.info("Token refresh request received")
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info("Token refreshed successfully")
        else:
            logger.warning("Token refresh failed")
        
        return response


@extend_schema_view(
    post=extend_schema(
        summary="Blacklist Refresh Token (Logout)",
        description=(
            "Blacklist a refresh token to prevent further use. "
            "This effectively logs out the user by invalidating their refresh token. "
            "The access token will remain valid until it expires."
        ),
        request=CustomTokenBlacklistSerializer,
        responses={
            200: OpenApiExample(
                'Success',
                value={'detail': 'Token blacklisted successfully'}
            ),
            400: OpenApiExample(
                'Invalid Token',
                value={'detail': 'Invalid refresh token'}
            )
        },
        tags=['JWT Authentication']
    ),
)
class CustomTokenBlacklistView(APIView):
    """
    Blacklist refresh token during logout.
    
    Adds token to blacklist to prevent reuse.
    Access tokens remain valid until expiration.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomTokenBlacklistSerializer
    
    def post(self, request, *args, **kwargs):
        """
        Blacklist user's refresh token.
        
        Request body:
            refresh: JWT refresh token to blacklist
            
        Returns:
            200: Token blacklisted successfully
            400: Invalid token
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        logger.info(f"Token blacklisted for user: {request.user.email}")
        return Response(
            {'detail': _('Token blacklisted successfully')},
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    post=extend_schema(
        summary="Verify JWT Token",
        description="Verify token validity and decode payload without consuming it.",
        request=TokenVerifySerializer,
        responses={
            200: OpenApiExample(
                'Valid Token',
                value={
                    'valid': True,
                    'payload': {
                        'user_id': 1,
                        'email': 'user@example.com',
                        'role': 'NORMAL_USER',
                        'subscription_status': 'free',
                        'exp': 1697204400,
                        'iat': 1697200800
                    }
                }
            ),
            400: OpenApiExample(
                'Invalid Token',
                value={'detail': 'Token is invalid or expired'}
            )
        },
        tags=['JWT Authentication']
    ),
)
class CustomTokenVerifyView(APIView):
    """
    Verify JWT token validity and return payload.
    
    Useful for debugging or checking token status without making authenticated requests.
    """
    permission_classes = [AllowAny]
    serializer_class = TokenVerifySerializer
    
    def post(self, request, *args, **kwargs):
        """
        Verify token and return payload.
        
        Request body:
            token: JWT token to verify
            token_type: 'access' or 'refresh' (default: 'access')
            
        Returns:
            200: Token is valid with payload
            400: Token is invalid or expired
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    post=extend_schema(
        summary="Revoke All User Tokens",
        description=(
            "Blacklist all outstanding refresh tokens for the authenticated user. "
            "Useful after password change or for security purposes."
        ),
        responses={
            200: OpenApiExample(
                'Success',
                value={'detail': 'All tokens revoked', 'count': 3}
            )
        },
        tags=['JWT Authentication']
    ),
)
class RevokeAllTokensView(APIView):
    """
    Revoke all refresh tokens for authenticated user.
    
    Forces re-authentication by blacklisting all outstanding tokens.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """
        Blacklist all user's refresh tokens.
        
        Returns:
            200: Tokens revoked with count
        """
        count = TokenManager.revoke_all_user_tokens(request.user)
        
        logger.info(f"Revoked {count} tokens for user: {request.user.email}")
        return Response(
            {
                'detail': _('All tokens have been revoked'),
                'count': count
            },
            status=status.HTTP_200_OK
        )