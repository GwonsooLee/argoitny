"""
ASGI config for algoitny project.

This module sets up ASGI application for Django with full async support.
Supports Uvicorn, Daphne, and Hypercorn ASGI servers.

Run with:
    uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
    or
    daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""
import os
from django.core.asgi import get_asgi_application

# Set Django settings module before importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Get the Django ASGI application
# This must be called before importing models or anything that touches the database
application = get_asgi_application()
