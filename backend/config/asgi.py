"""
ASGI (Asynchronous Server Gateway Interface) entry point for CarbonTrail backend.

ASGI is the newer async-capable version of WSGI, enabling real-time features:
- WebSocket connections (live data updates)
- Concurrent request handling
- Background task integration

Currently used with Daphne or Uvicorn servers for async support.
Fallback to WSGI if async features not needed.

USAGE (with Daphne):
daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""

import os

from django.core.asgi import get_asgi_application

# Tell Django which settings module to use (config/settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Get the ASGI application callable
# This is what async servers use to handle requests
application = get_asgi_application()
