from django.apps import AppConfig
from django.conf import settings
import os, logging

# Define TRACE level (5 is below DEBUG which is 10)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# Add trace method to the Logger class
def trace(self, message, *args, **kwargs):
    """Log a message with TRACE level (more detailed than DEBUG)"""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

# Add the trace method to the Logger class
logging.Logger.trace = trace

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Import signals to ensure they get registered
        import core.signals
