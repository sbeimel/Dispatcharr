"""
Standalone debug entry point for the Django application.
This provides a cleaner way to debug without uWSGI complications.

Run this directly with Python to debug:
    python standalone_debug.py
"""
import os
import sys
import debugpy
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger('standalone_debug')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')

# Setup debugpy and wait for connection
logger.info("Setting up debugpy...")
debugpy.listen(("0.0.0.0", 5678))
logger.info("Waiting for debugger to attach... Connect to 0.0.0.0:5678")
debugpy.wait_for_client()
logger.info("Debugger attached!")

# Import Django and run the development server
logger.info("Starting Django development server...")
import django
django.setup()

from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
