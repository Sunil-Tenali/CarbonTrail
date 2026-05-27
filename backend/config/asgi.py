"""
ASGI entry point for async web servers (Daphne, Uvicorn).

Enables WebSocket and async request handling.
Usage: daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
