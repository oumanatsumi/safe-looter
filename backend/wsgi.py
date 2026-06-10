"""WSGI entry point for production deployment with gunicorn.

Usage:
    gunicorn wsgi:app -w 2 -b 127.0.0.1:5001
"""

from app import create_app

app = create_app()
