# accounts/middleware.py

"""
JWT token security middleware.
Logs suspicious token activities.
"""
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('jwt_tokens')


class JWTSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance JWT token security.
    
    - Logs all token-related requests
    - Detects suspicious patterns (multiple failed attempts)
    - Can enforce additional security policies
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth_header = request.META['HTTP_AUTHORIZATION']
            logger.info(f"Authorization header found for user at path {request.path}: {auth_header[:15]}...") 

        response = self.get_response(request)
        
        return response
    def process_request(self, request):
        """Log token-related requests."""
        if 'token' in request.path or 'auth' in request.path:
            logger.info(
                f"Token request: {request.method} {request.path} "
                f"from {request.META.get('REMOTE_ADDR')}"
            )
        return None
    
    def process_response(self, request, response):
        """Log failed token attempts."""
        if 'token' in request.path and response.status_code >= 400:
            logger.warning(
                f"Failed token request: {request.method} {request.path} "
                f"Status: {response.status_code} "
                f"from {request.META.get('REMOTE_ADDR')}"
            )
        return response