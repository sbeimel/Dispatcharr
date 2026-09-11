"""
STB Profil V1 - Celery Tasks für automatische Updates
"""

from celery import shared_task
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)


@shared_task(name='stb_profil.auto_update_live_tv')
def auto_update_live_tv():
    """
    Automatischer Live TV-Import Task.
    Wird von Celery Beat ausgeführt.
    """
    try:
        logger.info("STB Profil: Starte automatischen Live TV-Import...")
        
        # Lade Plugin-Konfiguration
        from apps.plugins.models import PluginConfig
        
        try:
            config = PluginConfig.objects.get(key='stb_profil_v1', enabled=True)
        except PluginConfig.DoesNotExist:
            logger.warning("STB Profil: Plugin nicht konfiguriert oder deaktiviert")
            return
        
        settings = config.settings or {}
        
        # Importiere Plugin
        from .plugin import Plugin
        
        plugin = Plugin()
        
        # Erstelle Logger-Context
        class LoggerContext:
            def info(self, msg):
                logger.info(f"STB Profil: {msg}")
            
            def warning(self, msg):
                logger.warning(f"STB Profil: {msg}")
            
            def error(self, msg):
                logger.error(f"STB Profil: {msg}")
            
            def debug(self, msg):
                logger.debug(f"STB Profil: {msg}")
        
        logger_ctx = LoggerContext()
        
        # Führe Live TV-Import aus
        context = {
            'settings': settings,
            'logger': logger_ctx
        }
        
        result = plugin.run('import_live_tv', {}, context)
        
        if result and result.get('status') == 'success':
            logger.info(f"STB Profil: Live TV-Import erfolgreich - {result.get('message', '')}")
        else:
            logger.error(f"STB Profil: Live TV-Import fehlgeschlagen - {result.get('message', 'Unbekannter Fehler')}")
        
        return result
        
    except Exception as e:
        logger.error(f"STB Profil: Fehler beim automatischen Live TV-Import: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': str(e)}


# Celery Beat Schedule
# Diese Tasks werden automatisch registriert wenn das Plugin geladen wird
# HINWEIS: Muss manuell in Dispatcharr's Celery Beat Konfiguration eingetragen werden!
CELERY_BEAT_SCHEDULE = {
    'stb-profil-auto-update-live-tv': {
        'task': 'stb_profil.auto_update_live_tv',
        'schedule': crontab(hour='*/6', minute=0),  # Alle 6 Stunden um :00
        'options': {
            'expires': 3600,  # Task läuft max 1 Stunde
        }
    },
}
