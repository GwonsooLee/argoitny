"""
Security Headers Middleware

Sets security-related HTTP headers including Cross-Origin-Opener-Policy

ASGI-Compatible: This middleware works with both WSGI and ASGI
"""
import asyncio
from asgiref.sync import iscoroutinefunction, markcoroutinefunction


class SecurityHeadersMiddleware:
    """
    Add security headers to responses

    ASGI-compatible middleware that works in both sync and async contexts.
    Django automatically detects if the middleware should run in async mode.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Check if get_response is a coroutine function (async view)
        if iscoroutinefunction(self.get_response):
            # Mark this middleware as coroutine function for async support
            markcoroutinefunction(self)

    def __call__(self, request):
        # Sync path (for WSGI or sync views under ASGI)
        response = self.get_response(request)
        return self._add_security_headers(response)

    async def __acall__(self, request):
        # Async path (for async views under ASGI)
        response = await self.get_response(request)
        return self._add_security_headers(response)

    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Set Cross-Origin-Opener-Policy to same-origin-allow-popups
        # This allows Google OAuth popup/iframe to work while maintaining security
        response['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'

        # Set Cross-Origin-Embedder-Policy (optional, for additional security)
        # Use 'unsafe-none' to allow Google OAuth to work
        response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'

        return response
