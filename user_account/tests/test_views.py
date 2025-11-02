# accounts/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user_account.models import User

class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('rest_register')
    
    def test_user_registration_success(self):
        """Test successful user registration."""
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
    
    def test_duplicate_email_registration(self):
        """Test registration with duplicate email fails."""
        User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        data = {
            'email': 'test@example.com',
            'password': 'NewPass123!'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)