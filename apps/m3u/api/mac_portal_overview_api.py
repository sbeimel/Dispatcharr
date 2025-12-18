"""
MAC Portal Overview API - Zentrale Übersichtsseite für alle MAC Portale.

Zeigt:
- Alle M3UAccounts mit account_type='MAC'
- MAC-Adressen aus dem mac_address Feld oder M3UAccountMac Objekten
- Status und Health-Informationen
- Aktive Streams pro Portal
- Failover-Statistiken pro Portal
"""

import logging
import re
from typing import Dict, Any, List
from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


def _get_active_streams_by_portal() -> Dict[int, int]:
    """
    Holt aktive Streams aus Redis und gruppiert sie nach Portal-ID.
    
    Returns:
        Dict mapping portal_id -> active_stream_count
    """
    try:
        from core.utils import RedisClient
        redis_client = RedisClient.get_client()
        if not redis_client:
            return {}
        
        portal_streams = {}
        
        # Scan for active channel metadata
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match='ts_proxy:channel:*:metadata', count=100)
            
            for key in keys:
                try:
                    metadata = redis_client.hgetall(key)
                    if metadata:
                        channel_uuid = key.split(':')[2]
                        
                        # Get client count
                        clients_key = f'ts_proxy:channel:{channel_uuid}:clients'
                        client_count = redis_client.scard(clients_key) or 0
                        
                        if client_count > 0 or metadata.get('status') == 'streaming':
                            # Versuche Portal-ID aus metadata zu holen
                            account_id = metadata.get('account_id') or metadata.get('m3u_account_id')
                            
                            if not account_id:
                                # Fallback: Hole aus Channel-Datenbank
                                try:
                                    from apps.channels.models import Channel
                                    ch = Channel.objects.get(uuid=channel_uuid)
                                    # Hole den ersten Stream und dessen Account
                                    stream = ch.streams.first()
                                    if stream and stream.m3u_account_id:
                                        account_id = stream.m3u_account_id
                                except Exception:
                                    pass
                            
                            if account_id:
                                try:
                                    account_id = int(account_id)
                                    portal_streams[account_id] = portal_streams.get(account_id, 0) + 1
                                except (ValueError, TypeError):
                                    pass
                except Exception as e:
                    logger.debug(f"Error processing key {key}: {e}")
                    continue
            
            if cursor == 0:
                break
        
        return portal_streams
        
    except Exception as e:
        logger.error(f"Error getting active streams by portal: {e}")
        return {}


def _get_failover_counts_by_portal(hours: int = 24) -> Dict[int, int]:
    """
    Holt Failover-Counts aus der Datenbank für die letzten X Stunden.
    
    Args:
        hours: Zeitraum in Stunden (default 24)
        
    Returns:
        Dict mapping portal_id -> failover_count
    """
    try:
        from apps.m3u.mac_portal_models import FailoverEvent
        from django.db.models import Count
        
        since = timezone.now() - timedelta(hours=hours)
        
        # Gruppiere Failover-Events nach m3u_account
        failover_counts = (
            FailoverEvent.objects
            .filter(
                timestamp__gte=since,
                failover_type__in=['mac', 'stream']
            )
            .values('m3u_account_id')
            .annotate(count=Count('id'))
        )
        
        return {
            item['m3u_account_id']: item['count']
            for item in failover_counts
            if item['m3u_account_id']
        }
        
    except Exception as e:
        logger.debug(f"Could not get failover counts: {e}")
        return {}


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
            
            # Hole aktive Streams und Failover-Counts
            active_streams_by_portal = _get_active_streams_by_portal()
            failover_counts_by_portal = _get_failover_counts_by_portal(hours=24)
            
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
                    'total_active_streams': 0,
                    'total_failovers_24h': 0,
                }
            }
            
            for portal in portals:
                portal_data = self._get_portal_data(portal)
                
                # Füge aktive Streams und Failover-Count hinzu
                portal_data['active_streams'] = active_streams_by_portal.get(portal.id, 0)
                portal_data['failover_count_24h'] = failover_counts_by_portal.get(portal.id, 0)
                
                result['portals'].append(portal_data)
                
                # Statistiken aktualisieren
                if portal_data['status'] == 'online':
                    result['statistics']['online_portals'] += 1
                else:
                    result['statistics']['offline_portals'] += 1
                
                result['statistics']['total_active_streams'] += portal_data['active_streams']
                result['statistics']['total_failovers_24h'] += portal_data['failover_count_24h']
                
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
        
        # Hole Portal-Typ und Version aus custom_properties
        custom_props = portal.custom_properties or {}
        portal_type = custom_props.get('portal_type', 'unknown')
        portal_version = custom_props.get('portal_version')
        portal_engine = custom_props.get('portal_engine', 'auto')
        
        # Hole Benchmark-Ergebnisse aus custom_properties
        fastest_engine = custom_props.get('fastest_engine')
        fastest_engine_time_ms = custom_props.get('fastest_engine_time_ms')
        fastest_has_stream_link = custom_props.get('fastest_has_stream_link', False)
        benchmark_date = custom_props.get('benchmark_date')
        
        # Hole max_connections aus custom_properties
        portal_max_conn = custom_props.get('max_connections', getattr(portal, 'max_streams', 1))
        
        portal_data = {
            'id': portal.id,
            'account_id': portal.id,  # Alias for consistency with other APIs
            'name': portal.name,
            'url': portal.server_url or '',
            'type': 'MAC/STB Portal',
            'portal_type': portal_type,  # stalker, xtream, xui, ministra
            'portal_version': portal_version,  # z.B. "5.3.0"
            'portal_engine': portal_engine,  # macreplay, ob2_2025, auto, etc.
            # Benchmark-Ergebnisse
            'fastest_engine': fastest_engine,
            'fastest_engine_time_ms': fastest_engine_time_ms,
            'fastest_has_stream_link': fastest_has_stream_link,
            'benchmark_date': benchmark_date,
            'status': 'online' if portal.is_active and getattr(portal, 'status', '') != 'error' else 'offline',
            'last_check': portal.updated_at.isoformat() if portal.updated_at else None,
            'macs': [],
            'mac_count': 0,
            'available_count': 0,
            'max_streams': getattr(portal, 'max_streams', 1),
            'max_connections': portal_max_conn,  # max_connections pro Portal
            'is_active': portal.is_active,
        }
        
        # Versuche zuerst M3UAccountMac Objekte zu laden (bevorzugt)
        mac_objects = M3UAccountMac.objects.filter(account=portal).order_by('priority')
        
        if mac_objects.exists():
            # Verwende M3UAccountMac Objekte
            for mac_obj in mac_objects:
                # Hole max_connections aus custom_properties oder default 1
                mac_custom_props = getattr(mac_obj, 'custom_properties', {}) or {}
                max_conn = mac_custom_props.get('max_connections', 1)
                
                mac_data = {
                    'id': mac_obj.id,
                    'mac_address': mac_obj.address,
                    'status': mac_obj.status or 'unknown',
                    'priority': mac_obj.priority,
                    'expiry_date': None,
                    'last_used': mac_obj.last_checked.isoformat() if mac_obj.last_checked else None,
                    'cooldown_until': None,
                    'max_connections': max_conn,
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

    # NOTE: Benchmark endpoints moved to /api/m3u/benchmark/<id>/run/ and /api/m3u/benchmark/<id>/result/
    # See apps/m3u/api/simple_benchmark_api.py for the new implementation
