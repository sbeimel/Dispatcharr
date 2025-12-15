"""
MAC Portal Overview API - Zentrale Übersichtsseite für alle MAC Portale.

Zeigt:
- Alle M3UAccounts mit account_type='MAC'
- MAC-Adressen aus dem mac_address Feld
- Status und Health-Informationen
"""

import logging

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
        """Alias für overview."""
        return self.overview(request)
    
    def overview(self, request):
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
                    
                    if mac['status'] == 'active':
                        result['statistics']['available_macs'] += 1
                    elif mac['status'] == 'in_use':
                        result['statistics']['in_use_macs'] += 1
                    elif mac['status'] == 'cooldown':
                        result['statistics']['cooldown_macs'] += 1
                    elif mac['status'] == 'expired':
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
            logger.error(f"Error getting MAC portal overview: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_portal_data(self, portal) -> Dict[str, Any]:
        """Holt alle Daten für ein Portal."""
        portal_data = {
            'id': portal.id,
            'name': portal.name,
            'url': portal.server_url or '',
            'type': 'MAC/STB Portal',
            'status': 'online' if portal.is_active and portal.status != 'error' else 'offline',
            'last_check': portal.updated_at.isoformat() if portal.updated_at else None,
            'macs': [],
            'mac_count': 0,
            'available_count': 0,
            'max_streams': portal.max_streams,
            'is_active': portal.is_active,
        }
        
        # Parse MAC-Adressen aus dem mac_address Feld
        mac_addresses = self._parse_mac_addresses(portal.mac_address)
        
        for i, mac_addr in enumerate(mac_addresses):
            mac_data = {
                'id': i + 1,
                'mac_address': mac_addr,
                'status': 'active',  # Default status
                'priority': i,
                'expiry_date': None,
                'health_score': 100,
                'last_used': None,
                'cooldown_until': None,
                'max_connections': 1,
            }
            
            # Versuche Health-Daten zu laden
            try:
                from apps.m3u.mac_portal_models import MACHealthRecord, MACCooldown
                
                # Health Score
                health = MACHealthRecord.objects.filter(
                    mac_address=mac_addr
                ).order_by('-timestamp').first()
                if health:
                    mac_data['health_score'] = health.health_score if hasattr(health, 'health_score') else 100
                
                # Cooldown Status
                cooldown = MACCooldown.objects.filter(
                    mac_address=mac_addr,
                    cooldown_until__gt=timezone.now()
                ).first()
                if cooldown:
                    mac_data['status'] = 'cooldown'
                    mac_data['cooldown_until'] = cooldown.cooldown_until.isoformat()
                    
            except Exception as e:
                logger.debug(f"Could not load health data for MAC {mac_addr}: {e}")
            
            portal_data['macs'].append(mac_data)
            portal_data['mac_count'] += 1
            
            if mac_data['status'] == 'active':
                portal_data['available_count'] += 1
        
        return portal_data
    
    def _parse_mac_addresses(self, mac_string: str) -> List[str]:
        """Parst MAC-Adressen aus einem String (komma-, leerzeichen- oder zeilengetrennt)."""
        if not mac_string:
            return []
        
        import re
        
        # MAC-Adress-Pattern
        mac_pattern = re.compile(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}')
        
        # Finde alle MAC-Adressen
        macs = mac_pattern.findall(mac_string)
        
        # Wenn keine gefunden, versuche den String zu splitten
        if not macs:
            # Splitte nach Komma, Leerzeichen oder Newline
            parts = re.split(r'[,\s\n]+', mac_string)
            macs = [p.strip().upper() for p in parts if p.strip()]
        else:
            # Extrahiere vollständige MACs
            macs = [m[0] + m[1:] for m in re.finditer(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}', mac_string)]
            macs = [mac_string[m.start():m.end()].upper().replace('-', ':') for m in re.finditer(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}', mac_string)]
        
        # Normalisiere: Uppercase und Doppelpunkte
        result = []
        for mac in macs:
            mac = mac.upper().replace('-', ':')
            if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', mac):
                result.append(mac)
        
        return result
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Liefert nur die Statistiken."""
        overview = self.list(request)
        if overview.status_code == 200:
            return Response(overview.data.get('statistics', {}))
        return overview
