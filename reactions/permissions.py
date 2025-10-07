"""
Custom permissions for Reaction views.
"""
from rest_framework import permissions


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow any user to read reactions, but require authentication for modifications.
    
    This permission class allows:
    - Unauthenticated users: Read-only access (GET, HEAD, OPTIONS)
    - Authenticated users: Full access (GET, POST, PUT, PATCH, DELETE)
    """

    def has_permission(self, request, view):
        """
        Check if user has permission to access the view.
        
        Args:
            request: The incoming request.
            view: The view being accessed.
            
        Returns:
            bool: True if permission granted, False otherwise.
        """
        # Allow read-only access for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication for write operations
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow users to edit/delete only their own reactions.
    
    This permission class ensures:
    - Any user can view reactions
    - Only the reaction owner can modify or delete it
    - Staff users can modify any reaction
    - Anonymous users cannot modify or delete any reaction
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access a specific reaction.
        
        Args:
            request: The incoming request.
            view: The view being accessed.
            obj: The Reaction object being accessed.
            
        Returns:
            bool: True if permission granted, False otherwise.
        """
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only for the reaction owner (if authenticated) or staff.
        # Anonymous users (obj.user is None) cannot own objects, so they get no write access.
        is_owner = obj.user and obj.user == request.user
        is_staff = request.user and request.user.is_staff
        
        return is_owner or is_staff