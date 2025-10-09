"""
Security Headers Middleware

Sets security-related HTTP headers including Cross-Origin-Opener-Policy
"""


class SecurityHeadersMiddleware:
    """Add security headers to responses"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Set Cross-Origin-Opener-Policy to same-origin-allow-popups
        # This allows Google OAuth popup/iframe to work while maintaining security
        response['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'

        # Set Cross-Origin-Embedder-Policy (optional, for additional security)
        # Use 'unsafe-none' to allow Google OAuth to work
        response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'

        return response
