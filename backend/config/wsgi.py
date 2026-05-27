"""
WSGI (Web Server Gateway Interface) entry point for CarbonTrail backend.

WSGI is the standard interface between Python web applications and web servers.
This module is used by production servers (Gunicorn, uWSGI, etc.) to run Django.

DEPLOYMENT FLOW:
1. Production server starts (e.g., gunicorn config.wsgi:application)
2. Calls this module to get the 'application' WSGI callable
3. Server sends HTTP requests to application callable
4. Django processes requests, returns HTTP responses

USAGE:
gunicorn config.wsgi:application --bind 0.0.0.0:8000
"""

import os

from django.core.wsgi import get_wsgi_application

# Tell Django which settings module to use (config/settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Get the WSGI application callable
# This is what production servers call to handle requests
application = get_wsgi_application()
