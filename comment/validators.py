"""
Custom validators for the comment application.

This module provides validation functions for comment-related data
to ensure data integrity and business rule compliance.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .constants import MIN_COMMENT_LENGTH, MAX_COMMENT_LENGTH


def validate_comment_text(value):
    """
    Validate comment text content.
    
    Ensures that the comment text meets length requirements and
    doesn't contain only whitespace.
    
    Args:
        value (str): The comment text to validate.
        
    Raises:
        ValidationError: If the text doesn't meet validation criteria.
    """
    if not value or not value.strip():
        raise ValidationError(
            _('Comment text cannot be empty or contain only whitespace.'),
            code='empty_text'
        )
    
    stripped_value = value.strip()
    
    if len(stripped_value) < MIN_COMMENT_LENGTH:
        raise ValidationError(
            _('Comment text must be at least %(min_length)d character(s) long.'),
            code='min_length',
            params={'min_length': MIN_COMMENT_LENGTH}
        )
    
    if len(stripped_value) > MAX_COMMENT_LENGTH:
        raise ValidationError(
            _('Comment text cannot exceed %(max_length)d characters.'),
            code='max_length',
            params={'max_length': MAX_COMMENT_LENGTH}
        )
def validate_display_name(value):
    """
    Validate display name.
    
    Ensures that the display name is not empty and doesn't contain only whitespace.
    
    Args:
        value (str): The display name to validate.
        
    Raises:
        ValidationError: If the display name doesn't meet validation criteria.
    """
    if not value or not value.strip():
        raise ValidationError(
            _('Display name cannot be empty or contain only whitespace.'),
            code='empty_display_name'
        )
    
    if len(value.strip()) < 1:
        raise ValidationError(
            _('Display name must be at least 1 character long.'),
            code='min_length'
        )