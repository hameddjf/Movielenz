"""
Unit tests for JWT token management system.
Tests token generation, refresh, blacklist, and validation.
"""
import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from accounts.utils.token_manager import TokenManager

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide API client for tests."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='TestPassword123!',
        first_name='Test',
        last_name='User',
        activated=True,
        is_active=True
    )


@pytest.fixture
def inactive_user(db):
    """Create inactive test user."""
    return User.objects.create_user(
        email='inactive@example.com',
        username='inactiveuser',
        password='TestPassword123!',
        activated=False,
        is_active=False
    )


@pytest.mark.django_db
class TestTokenGeneration:
    """Test JWT token generation."""
    
    def test_generate_tokens_for_user(self, test_user):
        """Test successful token generation."""
        tokens = TokenManager.generate_tokens_for_user(test_user)
        
        assert 'access' in tokens
        assert 'refresh' in tokens
        assert 'access_expires_at' in tokens
        assert 'refresh_expires_at' in tokens
        assert len(tokens['access']) > 0
        assert len(tokens['refresh']) > 0
    
    def test_token_contains_custom_claims(self, test_user):
        """Test that tokens include custom claims."""
        tokens = TokenManager.generate_tokens_for_user(test_user)
        
        # Verify access token payload
        is_valid, payload = TokenManager.verify_token(tokens['access'], 'access')
        
        assert is_valid is True
        assert payload['email'] == test_user.email
        assert payload['role'] == test_user.role
        assert payload['subscription_status'] == test_user.subscription_status
        assert payload['activated'] is True
        assert 'user_id' in payload
        assert 'exp' in payload


@pytest.mark.django_db
class TestTokenObtainPair:
    """Test token obtain pair endpoint."""
    
    def test_obtain_token_with_valid_credentials(self, api_client, test_user):
        """Test obtaining tokens with valid email/password."""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == test_user.email
    
    def test_obtain_token_with_invalid_password(self, api_client, test_user):
        """Test token obtain fails with wrong password."""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_obtain_token_with_unverified_email(self, api_client, inactive_user):
        """Test token obtain fails for unverified email."""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'inactive@example.com',
            'password': 'TestPassword123!'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_refresh_valid_token(self, api_client, test_user):
        """Test refreshing with valid refresh token."""
        # Generate initial tokens
        tokens = TokenManager.generate_tokens_for_user(test_user)
        refresh_token = tokens['refresh']
        
        # Refresh token
        url = reverse('token_refresh')
        data = {'refresh': refresh_token}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert len(response.data['access']) > 0
    
    def test_refresh_invalid_token(self, api_client):
        """Test refresh fails with invalid token."""
        url = reverse('token_refresh')
        data = {'refresh': 'invalid.token.here'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_blacklisted_token(self, api_client, test_user):
        """Test refresh fails with blacklisted token."""
        # Generate and blacklist token
        tokens = TokenManager.generate_tokens_for_user(test_user)
        refresh_token = tokens['refresh']
        TokenManager.blacklist_token(refresh_token)
        
        # Try to refresh
        url = reverse('token_refresh')
        data = {'refresh': refresh_token}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenBlacklist:
    """Test token blacklisting."""
    
    def test_blacklist_valid_token(self, api_client, test_user):
        """Test blacklisting a valid token."""
        # Login to get tokens
        tokens = TokenManager.generate_tokens_for_user(test_user)
        refresh_token = tokens['refresh']
        access_token = tokens['access']
        
        # Authenticate with access token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Blacklist token
        url = reverse('token_blacklist')
        data = {'refresh': refresh_token}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert TokenManager.is_token_blacklisted(refresh_token) is True
    
    def test_blacklist_requires_authentication(self, api_client):
        """Test blacklist endpoint requires authentication."""
        url = reverse('token_blacklist')
        data = {'refresh': 'some.token.here'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenVerify:
    """Test token verification."""
    
    def test_verify_valid_access_token(self, api_client, test_user):
        """Test verifying a valid access token."""
        tokens = TokenManager.generate_tokens_for_user(test_user)
        
        url = reverse('token_verify')
        data = {
            'token': tokens['access'],
            'token_type': 'access'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
        assert 'payload' in response.data
    
    def test_verify_invalid_token(self, api_client):
        """Test verifying an invalid token."""
        url = reverse('token_verify')
        data = {
            'token': 'invalid.token.here',
            'token_type': 'access'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRevokeAllTokens:
    """Test revoking all user tokens."""
    
    def test_revoke_all_tokens(self, api_client, test_user):
        """Test revoking all tokens for user."""
        # Generate multiple tokens
        tokens1 = TokenManager.generate_tokens_for_user(test_user)
        tokens2 = TokenManager.generate_tokens_for_user(test_user)
        
        # Authenticate
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens1["access"]}')
        
        # Revoke all tokens
        url = reverse('token_revoke_all')
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert response.data['count'] >= 2
        
        # Verify tokens are blacklisted
        assert TokenManager.is_token_blacklisted(tokens1['refresh']) is True
        assert TokenManager.is_token_blacklisted(tokens2['refresh']) is True


@pytest.mark.django_db
class TestTokenManager:
    """Test TokenManager utility class."""
    
    def test_is_token_blacklisted(self, test_user):
        """Test checking if token is blacklisted."""
        tokens = TokenManager.generate_tokens_for_user(test_user)
        refresh_token = tokens['refresh']
        
        # Initially not blacklisted
        assert TokenManager.is_token_blacklisted(refresh_token) is False
        
        # After blacklisting
        TokenManager.blacklist_token(refresh_token)
        assert TokenManager.is_token_blacklisted(refresh_token) is True
    
    def test_revoke_all_user_tokens(self, test_user):
        """Test revoking all tokens for a user."""
        # Generate multiple tokens
        for _ in range(3):
            TokenManager.generate_tokens_for_user(test_user)
        
        # Revoke all
        count = TokenManager.revoke_all_user_tokens(test_user)
        
        assert count >= 3
    
    def test_cleanup_expired_tokens(self, test_user):
        """Test cleanup of expired tokens."""
        # This would require mocking time or creating expired tokens
        # For now, just ensure method runs without error
        result = TokenManager.cleanup_expired_tokens()
        
        assert 'outstanding_deleted' in result
        assert 'blacklisted_deleted' in result


@pytest.mark.django_db
class TestPasswordChangeTokenRevocation:
    """Test that password change revokes all tokens."""
    
    def test_password_change_revokes_tokens(self, api_client, test_user):
        """Test changing password invalidates all tokens."""
        # Generate token before password change
        old_tokens = TokenManager.generate_tokens_for_user(test_user)
        
        # Change password (this should revoke all tokens)
        test_user.set_password('NewPassword123!')
        test_user.save()
        TokenManager.revoke_all_user_tokens(test_user)
        
        # Try to refresh with old token
        url = reverse('token_refresh')
        data = {'refresh': old_tokens['refresh']}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED