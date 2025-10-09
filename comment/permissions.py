"""
Custom permission classes for the comment application.

This module provides permission classes to control access to comment
resources based on user authentication and ownership.
"""

from rest_framework import permissions


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only comment owners or admins to edit/delete.
    
    This permission class allows:
    - Read access (GET, HEAD, OPTIONS) to all users including anonymous
    - Write access (POST) to all users including anonymous
    - Update/Delete access (PUT, PATCH, DELETE) only to the comment author or admin
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to perform the request.
        
        Args:
            request: The incoming HTTP request.
            view: The view being accessed.
            
        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # Allow read access to everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow POST (create) to everyone
        if request.method == 'POST':
            return True

        # For other methods (PUT, PATCH, DELETE), require authentication
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to perform the request on a specific object.
        
        Args:
            request: The incoming HTTP request.
            view: The view being accessed.
            obj: The comment object being accessed.
            
        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # Allow read access to everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # For modifications, require authentication
        if not request.user or not request.user.is_authenticated:
            return False

        is_admin = request.user.is_staff or request.user.is_superuser
        is_owner = obj.author == request.user

        return is_admin or is_owner


class IsAuthenticatedOrCreateOnly(permissions.BasePermission):
    """
    Custom permission to allow anonymous users to create comments.
    
    This permission allows:
    - Create access (POST) to all users including anonymous
    - All other actions require authentication
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to perform the request.
        
        Args:
            request: The incoming HTTP request.
            view: The view being accessed.
            
        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # Allow POST to everyone
        if request.method == 'POST':
            return True

        # For other methods, require authentication
        return request.user and request.user.is_authenticated


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow only comment owners or admin/owner to modify.
    
    This permission checks user role from user_account.enums.UserRole:
    - OWNER: Full access
    - ADMIN: Full access
    - Comment author: Can modify their own comments
    - Others: No access
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to perform the request.
        
        Args:
            request: The incoming HTTP request.
            view: The view being accessed.
            
        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # Require authentication
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is OWNER or ADMIN based on role field
        if hasattr(request.user, 'role'):
            from user_account.enums import UserRole
            if request.user.role in [UserRole.OWNER, UserRole.ADMIN]:
                return True
        
        # Allow if user is Django admin/staff
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # For object-level permissions, allow and check in has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to perform the request on a specific object.
        
        Args:
            request: The incoming HTTP request.
            view: The view being accessed.
            obj: The comment object being accessed.
            
        Returns:
            bool: True if permission is granted, False otherwise.
        """
        # Require authentication
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is OWNER or ADMIN based on role field
        if hasattr(request.user, 'role'):
            from user_account.enums import UserRole
            if request.user.role in [UserRole.OWNER, UserRole.ADMIN]:
                return True

        # Allow if user is Django admin/staff
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if user is the comment author
        is_author = obj.author == request.user

        return is_author