"""
MAC Portal Overview API - Zentrale Übersichtsseite für alle MAC Portale.

Zeigt:
- Alle Portale mit Status
- Alle MACs pro Portal mit Details
- Activity Level, Watchdog Timeout, Max Streams
- Aggregierte Statistiken
"""

import logging
from datetime import timedelta
from typing import Dict, Any, List, Optional

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class MACPortalOverviewViewSet(viewsets.ViewSet):
    """
    API ViewSet für MAC Portal Übersicht.
    
    Endpoints:
    - GET /api/mac-portal/overview/ - Vollständige Übersicht
    - GET /api/mac-portal/overview/statistics/ - Nur Statistiken
    - POST /api/mac-portal/overview/refresh-status/ - Status aktualisieren
    """
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Liefert vollständige MAC Portal Übersicht.
        
        Response:
        {
            "portals": [...],
            "statistics": {...}
        }
        """
        try:
            from apps.m3u.models import M3UAccount
            from apps.m3u.mac_portal_models import MACHealthRecord, FailoverEvent
            
            # Hole alle MAC-Accounts
            portals = M3UAccount.objects.filter(account_type='mac')
            
            result = {
                'portals': [],
                'statistics': {
                    'total_portals': portals.count(),
                    'online_portals': 0,
                    'offline_portals': 0,
                    'total_macs': 0,
                    'available_macs': 0,
                    'in_use_macs': 0,
                    'cooldown_macs': 0,
                    'expired_macs': 0,
                    'expiring_soon': 0,
                    'avg_health_score': 0,
                    'total_failovers_24h': 0,
                }
            }
            
            health_scores = []
            
            for portal in portals:
                portal_data = self._get_portal_data(portal)
                result['portals'].append(portal_data)
                
                # Statistiken aktualisieren
                if portal_data['status'] == 'online':
                    result['statistics']['online_portals'] += 1
                else:
                    result['statistics']['offline_portals'] += 1
                
                for mac in portal_data['macs']:
                    result['statistics']['total_macs'] += 1
                    
                    if mac['status'] == 'active':
                        result['statistics']['available_macs'] += 1
                    elif mac['status'] == 'in_use':
                        result['statistics']['in_use_macs'] += 1
                    elif mac['status'] == 'cooldown':
                        result['statistics']['cooldown_macs'] += 1
                    elif mac['status'] == 'expired':
                        result['statistics']['expired_macs'] += 1
                    
                    if mac['expiry_date']:
                        try:
                            from datetime import datetime
                            if isinstance(mac['expiry_date'], str):
                                expiry = datetime.fromisoformat(mac['expiry_date'].replace('Z', '+00:00'))
                            else:
                                expiry = mac['expiry_date']
                            
                            if hasattr(expiry, 'tzinfo') and expiry.tzinfo is None:
                                expiry = timezone.make_aware(expiry)
                            
                            days_until = (expiry - timezone.now()).days
                            if 0 < days_until < 7:
                                result['statistics']['expiring_soon'] += 1
                        except (ValueError, TypeError, AttributeError):
                            pass
                    
                    if mac['health_score'] is not None:
                        health_scores.append(mac['health_score'])
            
            # Durchschnittlicher Health Score
            if health_scores:
                result['statistics']['avg_health_score'] = round(
                    sum(health_scores) / len(health_scores), 1
                )
            
            # Failovers in den letzten 24h
            try:
                yesterday = timezone.now() - timedelta(hours=24)
                result['statistics']['total_failovers_24h'] = FailoverEvent.objects.filter(
                    timestamp__gte=yesterday
                ).count()
            except Exception:
                pass
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting MAC portal overview: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_portal_data(self, portal) -> Dict[str, Any]:
        """Holt alle Daten für ein Portal."""
        from apps.m3u.mac_portal_models import MACHealthRecord
        
        portal_data = {
            'id': portal.id,
            'name': portal.name,
            'url': portal.url,
            'type': getattr(portal, 'portal_type', 'unknown'),
            'status': 'unknown',
            'last_check': None,
            'macs': [],
            'mac_count': 0,
            'available_count': 0,
        }
        
        # Hole MACs für dieses Portal
        try:
            # Versuche M3UAccountMac Model
            from apps.m3u.models import M3UAccountMac
            macs = M3UAccountMac.objects.filter(account=portal)
        except (ImportError, Exception):
            # Fallback: MACs aus mac_addresses Feld
            macs = []
            mac_addresses = getattr(portal, 'mac_addresses', None)
            if mac_addresses:
                if isinstance(mac_addresses, str):
                    mac_list = [m.strip() for m in mac_addresses.split('\n') if m.strip()]
                else:
                    mac_list = mac_addresses
                
                for i, mac_addr in enumerate(mac_list):
                    macs.append({
                        'id': i,
                        'mac_address': mac_addr,
                        'status': 'active',
                        'priority': i,
                    })
        
        portal_online = False
        
        for mac in macs:
            mac_data = self._get_mac_data(portal, mac)
            portal_data['macs'].append(mac_data)
            portal_data['mac_count'] += 1
            
            if mac_data['status'] == 'active':
                portal_data['available_count'] += 1
                portal_online = True
        
        portal_data['status'] = 'online' if portal_online else 'offline'
        
        return portal_data
    
    def _get_mac_data(self, portal, mac) -> Dict[str, Any]:
        """Holt alle Daten für eine MAC."""
        from apps.m3u.mac_portal_models import MACHealthRecord
        
        # Basis-Daten
        if isinstance(mac, dict):
            mac_data = {
                'id': mac.get('id', 0),
                'mac_address': mac.get('mac_address', ''),
                'status': mac.get('status', 'active'),
                'priority': mac.get('priority', 0),
                'expiry_date': mac.get('expiry_date'),
                'last_used': mac.get('last_used'),
                'cooldown_until': mac.get('cooldown_until'),
                'max_connections': mac.get('max_connections', 1),
            }
        else:
            mac_data = {
                'id': mac.id,
                'mac_address': mac.mac_address,
                'status': mac.status,
                'priority': mac.priority,
                'expiry_date': mac.expiry_date,
                'last_used': getattr(mac, 'last_used', None),
                'cooldown_until': getattr(mac, 'cooldown_until', None),
                'max_connections': getattr(mac, 'max_connections', 1),
            }
        
        # Health Score
        mac_data['health_score'] = 100
        try:
            health = MACHealthRecord.objects.filter(
                mac_address=mac_data['mac_address']
            ).first()
            if health:
                mac_data['health_score'] = health.get_health_score()
        except Exception:
            pass
        
        # Activity Level (wenn verfügbar)
        mac_data['activity_level'] = self._get_activity_level(portal, mac_data['mac_address'])
        
        # Watchdog Timeout (wenn verfügbar)
        mac_data['watchdog_timeout'] = self._get_watchdog_timeout(portal, mac_data['mac_address'])
        
        # Current Streams
        mac_data['current_streams'] = self._get_current_streams(mac_data['mac_address'])
        
        # Expiry Countdown
        mac_data['days_until_expiry'] = None
        if mac_data['expiry_date']:
            try:
                from datetime import datetime
                if isinstance(mac_data['expiry_date'], str):
                    expiry = datetime.fromisoformat(mac_data['expiry_date'].replace('Z', '+00:00'))
                else:
                    expiry = mac_data['expiry_date']
                
                if hasattr(expiry, 'tzinfo') and expiry.tzinfo is None:
                    expiry = timezone.make_aware(expiry)
                
                mac_data['days_until_expiry'] = (expiry - timezone.now()).days
            except (ValueError, TypeError, AttributeError):
                pass
        
        return mac_data
    
    def _get_activity_level(self, portal, mac_address: str) -> Optional[int]:
        """Holt Activity Level vom Portal (wenn unterstützt)."""
        # TODO: Implementierung abhängig vom Portal-Typ
        # Manche Portale liefern activity_level in get_main_info
        return None
    
    def _get_watchdog_timeout(self, portal, mac_address: str) -> Optional[int]:
        """Holt Watchdog Timeout vom Portal (wenn unterstützt)."""
        # TODO: Implementierung abhängig vom Portal-Typ
        # Manche Portale liefern watchdog_timeout in get_profile
        return None
    
    def _get_current_streams(self, mac_address: str) -> int:
        """Zählt aktive Streams für diese MAC."""
        try:
            # Versuche über Redis/Stream Manager
            from django.core.cache import cache
            key = f"mac_active_streams:{mac_address}"
            count = cache.get(key)
            return count or 0
        except Exception:
            return 0
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Liefert nur die Statistiken."""
        overview = self.overview(request)
        if overview.status_code == 200:
            return Response(overview.data.get('statistics', {}))
        return overview
    
    @action(detail=False, methods=['post'], url_path='refresh-status')
    def refresh_status(self, request):
        """
        Aktualisiert den Status aller MACs.
        
        Führt einen Batch-Test aller MACs durch.
        """
        try:
            from apps.m3u.tasks import check_mac_status_batch
            
            # Starte Celery Task
            task = check_mac_status_batch.delay()
            
            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': 'MAC status refresh started'
            })
        except Exception as e:
            logger.error(f"Error starting MAC status refresh: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='portal-details')
    def portal_details(self, request, pk=None):
        """Liefert detaillierte Informationen für ein einzelnes Portal."""
        try:
            from apps.m3u.models import M3UAccount
            
            portal = M3UAccount.objects.get(pk=pk)
            portal_data = self._get_portal_data(portal)
            
            # Zusätzliche Details
            portal_data['recent_failovers'] = self._get_recent_failovers(portal)
            portal_data['health_history'] = self._get_health_history(portal)
            
            return Response(portal_data)
            
        except M3UAccount.DoesNotExist:
            return Response(
                {'error': 'Portal not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting portal details: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_recent_failovers(self, portal, limit: int = 10) -> List[Dict]:
        """Holt die letzten Failover-Events für ein Portal."""
        try:
            from apps.m3u.mac_portal_models import FailoverEvent
            
            events = FailoverEvent.objects.filter(
                account=portal
            ).order_by('-timestamp')[:limit]
            
            return [
                {
                    'id': e.id,
                    'timestamp': e.timestamp,
                    'strategy': e.strategy,
                    'from_mac': e.from_mac,
                    'to_mac': e.to_mac,
                    'reason': e.reason,
                    'success': e.success,
                }
                for e in events
            ]
        except Exception:
            return []
    
    def _get_health_history(self, portal, days: int = 7) -> List[Dict]:
        """Holt Health-Score-Verlauf für ein Portal."""
        try:
            from apps.m3u.mac_portal_models import MACHealthRecord
            from django.db.models import Avg
            from django.db.models.functions import TruncDate
            
            start_date = timezone.now() - timedelta(days=days)
            
            # Aggregiere Health Scores pro Tag
            history = MACHealthRecord.objects.filter(
                account=portal,
                timestamp__gte=start_date
            ).annotate(
                date=TruncDate('timestamp')
            ).values('date').annotate(
                avg_score=Avg('health_score')
            ).order_by('date')
            
            return [
                {
                    'date': h['date'].isoformat() if h['date'] else None,
                    'avg_health_score': round(h['avg_score'], 1) if h['avg_score'] else None,
                }
                for h in history
            ]
        except Exception:
            return []
