"""
MAC Portal Overview API - Zentrale Übersichtsseite für alle MAC Portale.

Zeigt:
- Alle M3UAccounts mit account_type='MAC'
- MAC-Adressen aus dem mac_address Feld oder M3UAccountMac Objekten
- Status und Health-Informationen
"""

import logging
import re
from typing import Dict, Any, List

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class MACPortalOverviewViewSet(viewsets.ViewSet):
    """
    API ViewSet für MAC Portal Übersicht.
    
    Endpoints:
    - GET /api/mac-portal/overview/ - Vollständige Übersicht
    - GET /api/mac-portal/overview/statistics/ - Nur Statistiken
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/mac-portal/overview/ - Vollständige Übersicht."""
        try:
            from apps.m3u.models import M3UAccount
            
            # Hole alle MAC-Accounts (account_type = 'MAC')
            portals = M3UAccount.objects.filter(account_type='MAC')
            
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
                    
                    mac_status = mac.get('status', 'unknown')
                    if mac_status in ('active', 'valid'):
                        result['statistics']['available_macs'] += 1
                    elif mac_status == 'in_use':
                        result['statistics']['in_use_macs'] += 1
                    elif mac_status == 'cooldown':
                        result['statistics']['cooldown_macs'] += 1
                    elif mac_status in ('expired', 'error'):
                        result['statistics']['expired_macs'] += 1
                    
                    if mac.get('health_score') is not None:
                        health_scores.append(mac['health_score'])
            
            # Durchschnittlicher Health Score
            if health_scores:
                result['statistics']['avg_health_score'] = round(
                    sum(health_scores) / len(health_scores), 1
                )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting MAC portal overview: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_portal_data(self, portal) -> Dict[str, Any]:
        """Holt alle Daten für ein Portal."""
        from apps.m3u.models import M3UAccountMac
        
        portal_data = {
            'id': portal.id,
            'name': portal.name,
            'url': portal.server_url or '',
            'type': 'MAC/STB Portal',
            'status': 'online' if portal.is_active and getattr(portal, 'status', '') != 'error' else 'offline',
            'last_check': portal.updated_at.isoformat() if portal.updated_at else None,
            'macs': [],
            'mac_count': 0,
            'available_count': 0,
            'max_streams': getattr(portal, 'max_streams', 1),
            'is_active': portal.is_active,
        }
        
        # Versuche zuerst M3UAccountMac Objekte zu laden (bevorzugt)
        mac_objects = M3UAccountMac.objects.filter(account=portal).order_by('priority')
        
        if mac_objects.exists():
            # Verwende M3UAccountMac Objekte
            for mac_obj in mac_objects:
                mac_data = {
                    'id': mac_obj.id,
                    'mac_address': mac_obj.address,
                    'status': mac_obj.status or 'unknown',
                    'priority': mac_obj.priority,
                    'expiry_date': None,
                    'health_score': 100,
                    'last_used': mac_obj.last_checked.isoformat() if mac_obj.last_checked else None,
                    'cooldown_until': None,
                    'max_connections': 1,
                    'expires_text': getattr(mac_obj, 'expires_text', '') or '',
                    'last_error': getattr(mac_obj, 'last_error', '') or '',
                }
                
                # Versuche Cooldown-Status zu laden
                try:
                    from apps.m3u.mac_portal_models import MACCooldown
                    cooldown = MACCooldown.objects.filter(
                        mac=mac_obj,
                        is_active=True,
                        expires_at__gt=timezone.now()
                    ).first()
                    if cooldown:
                        mac_data['status'] = 'cooldown'
                        mac_data['cooldown_until'] = cooldown.expires_at.isoformat()
                except Exception as e:
                    logger.debug(f"Could not load cooldown for MAC {mac_obj.address}: {e}")
                
                portal_data['macs'].append(mac_data)
                portal_data['mac_count'] += 1
                
                if mac_data['status'] in ('active', 'valid', 'unknown'):
                    portal_data['available_count'] += 1
        else:
            # Fallback: Parse MAC-Adressen aus dem mac_address Feld
            mac_addresses = self._parse_mac_addresses(getattr(portal, 'mac_address', '') or '')
            
            for i, mac_addr in enumerate(mac_addresses):
                mac_data = {
                    'id': i + 1,
                    'mac_address': mac_addr,
                    'status': 'unknown',
                    'priority': i,
                    'expiry_date': None,
                    'health_score': 100,
                    'last_used': None,
                    'cooldown_until': None,
                    'max_connections': 1,
                }
                
                portal_data['macs'].append(mac_data)
                portal_data['mac_count'] += 1
                portal_data['available_count'] += 1
        
        return portal_data
    
    def _parse_mac_addresses(self, mac_string: str) -> List[str]:
        """Parst MAC-Adressen aus einem String (komma-, leerzeichen- oder zeilengetrennt)."""
        if not mac_string:
            return []
        
        # MAC-Adress-Pattern (XX:XX:XX:XX:XX:XX oder XX-XX-XX-XX-XX-XX)
        mac_pattern = re.compile(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}')
        
        # Finde alle MAC-Adressen im String mit finditer
        full_matches = list(mac_pattern.finditer(mac_string))
        
        if full_matches:
            result = []
            for m in full_matches:
                mac = m.group(0).upper().replace('-', ':')
                if mac not in result:
                    result.append(mac)
            return result
        
        # Fallback: Splitte nach Komma, Leerzeichen oder Newline
        parts = re.split(r'[,\s\n]+', mac_string)
        result = []
        mac_check_pattern = re.compile(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$')
        
        for p in parts:
            p = p.strip().upper().replace('-', ':')
            # Prüfe ob es wie eine MAC-Adresse aussieht
            if mac_check_pattern.match(p):
                if p not in result:
                    result.append(p)
        
        return result
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Liefert nur die Statistiken."""
        overview = self.list(request)
        if overview.status_code == 200:
            return Response(overview.data.get('statistics', {}))
        return overview
