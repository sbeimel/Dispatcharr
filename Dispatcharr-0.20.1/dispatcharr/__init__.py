# dispatcharr/__init__.py

# For Celery:
from .celery import app as celery_app

__all__ = ("celery_app",)
