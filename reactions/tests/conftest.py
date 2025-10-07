"""
Pytest fixtures for reactions app tests.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from reactions.models import Reaction
   

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Fixture for DRF API client.
    
    Returns:
        APIClient: DRF test client instance.
    """
    return APIClient()


@pytest.fixture
def user(db):
    """
    Fixture for creating a test user.
    
    Returns:
        User: Test user instance.
    """
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def another_user(db):
    """
    Fixture for creating another test user.
    
    Returns:
        User: Another test user instance.
    """
    return User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='testpass123'
    )


@pytest.fixture
def staff_user(db):
    """
    Fixture for creating a staff user.
    
    Returns:
        User: Staff user instance.
    """
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def test_content_object(db, user):
    """
    Fixture for creating a test content object (User in this case).
    
    We use User model as test content since it's always available.
    In real tests, you'd use your actual content models.
    
    Returns:
        User: Test content object.
    """
    return User.objects.create_user(
        username='contentuser',
        email='content@example.com',
        password='testpass123'
    )


@pytest.fixture
def reaction_like(db, user, test_content_object):
    """
    Fixture for creating a like reaction.
    
    Returns:
        Reaction: Like reaction instance.
    """
    content_type = ContentType.objects.get_for_model(test_content_object)
    return Reaction.objects.create(
        user=user,
        content_type=content_type,
        object_id=test_content_object.pk,
        value='like'
    )


@pytest.fixture
def reaction_dislike(db, another_user, test_content_object):
    """
    Fixture for creating a dislike reaction.
    
    Returns:
        Reaction: Dislike reaction instance.
    """
    content_type = ContentType.objects.get_for_model(test_content_object)
    return Reaction.objects.create(
        user=another_user,
        content_type=content_type,
        object_id=test_content_object.pk,
        value='dislike'
    )


@pytest.fixture
def multiple_reactions(db, test_content_object):
    """
    Fixture for creating multiple reactions for testing statistics.
    
    Creates 7 likes and 3 dislikes for 70% popularity.
    
    Returns:
        list: List of Reaction instances.
    """
    reactions = []
    content_type = ContentType.objects.get_for_model(test_content_object)
    
    # Create 7 likes
    for i in range(7):
        user = User.objects.create_user(
            username=f'liker{i}',
            email=f'liker{i}@example.com',
            password='testpass123'
        )
        reaction = Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='like'
        )
        reactions.append(reaction)
    
    # Create 3 dislikes
    for i in range(3):
        user = User.objects.create_user(
            username=f'disliker{i}',
            email=f'disliker{i}@example.com',
            password='testpass123'
        )
        reaction = Reaction.objects.create(
            user=user,
            content_type=content_type,
            object_id=test_content_object.pk,
            value='dislike'
        )
        reactions.append(reaction)
    
    return reactions