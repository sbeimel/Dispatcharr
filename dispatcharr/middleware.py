"""
Custom middleware for Dispatcharr.
"""
from django.middleware.csrf import CsrfViewMiddleware


class CsrfExemptAPIMiddleware(CsrfViewMiddleware):
    """
    CSRF Middleware that exempts API endpoints.
    
    API endpoints use JWT authentication, not session-based auth,
    so CSRF protection is not needed and causes issues.
    """
    
    def _should_exempt(self, request):
        """Check if the request path should be exempt from CSRF."""
        path = request.path_info
        
        # Exempt all API endpoints
        if path.startswith('/api/'):
            return True
        
        # Exempt WebSocket endpoints
        if path.startswith('/ws/'):
            return True
            
        return False
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        """Skip CSRF check for exempt paths."""
        if self._should_exempt(request):
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)