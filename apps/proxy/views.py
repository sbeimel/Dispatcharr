from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.apps import apps
from django.http import JsonResponse
from core.utils import RedisClient
import logging

logger = logging.getLogger(__name__)

class ProxyViewSet(viewsets.ViewSet):
    """ViewSet for managing proxy servers"""

    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a proxy server for a channel"""
        try:
            proxy_type = request.data.get('type', 'hls')
            channel_id = request.data.get('channel', 'default')
            url = request.data.get('url')

            if not url:
                return Response(
                    {'error': 'URL is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            proxy_app = apps.get_app_config('proxy')
            proxy_server = getattr(proxy_app, f'{proxy_type}_proxy')
            proxy_server.initialize_channel(url, channel_id)

            return Response({
                'message': f'{proxy_type.upper()} proxy started',
                'channel': channel_id,
                'url': url
            })

        except Exception as e:
            logger.error(f"Error starting proxy: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def stop(self, request):
        """Stop a proxy server for a channel"""
        try:
            proxy_type = request.data.get('type', 'hls')
            channel_id = request.data.get('channel', 'default')

            proxy_app = apps.get_app_config('proxy')
            proxy_server = getattr(proxy_app, f'{proxy_type}_proxy')
            proxy_server.stop_channel(channel_id)

            return Response({
                'message': f'{proxy_type.upper()} proxy stopped',
                'channel': channel_id
            })

        except Exception as e:
            logger.error(f"Error stopping proxy: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Failover Test Endpoints
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_streams(request):
    """Get list of active streams/channels with viewers."""
    try:
        redis_client = RedisClient.get_client()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        active_streams = []
        
        # Cache für Channel-Lookups
        from apps.channels.models import Channel
        channel_cache = {}
        
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
                            # Hole Channel-ID aus der Datenbank
                            if channel_uuid not in channel_cache:
                                try:
                                    ch = Channel.objects.get(uuid=channel_uuid)
                                    channel_cache[channel_uuid] = {'id': ch.id, 'name': ch.name}
                                except Channel.DoesNotExist:
                                    channel_cache[channel_uuid] = {'id': None, 'name': 'Unknown'}
                            
                            ch_info = channel_cache[channel_uuid]
                            
                            active_streams.append({
                                'channel_id': ch_info['id'],
                                'channel_uuid': channel_uuid,
                                'channel_name': ch_info['name'],
                                'status': metadata.get('status', 'unknown'),
                                'stream_url': metadata.get('stream_url', ''),
                                'client_count': client_count,
                                'worker_id': metadata.get('worker_id', ''),
                                'started_at': metadata.get('started_at', ''),
                            })
                except Exception as e:
                    logger.debug(f"Error processing key {key}: {e}")
                    continue
            
            if cursor == 0:
                break
        
        return JsonResponse(active_streams, safe=False)
        
    except Exception as e:
        logger.error(f"Error getting active streams: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kill_stream(request, channel_id):
    """Kill/terminate an active stream to trigger failover."""
    try:
        import time
        import datetime
        
        redis_client = RedisClient.get_client()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        # Hole die Channel UUID aus der Datenbank
        from apps.channels.models import Channel
        try:
            channel = Channel.objects.get(id=channel_id)
            channel_uuid = str(channel.uuid)
        except Channel.DoesNotExist:
            return JsonResponse({'error': f'Channel {channel_id} not found'}, status=404)
        
        # Set the stopping flag for the channel (use UUID)
        stopping_key = f'ts_proxy:channel:{channel_uuid}:stopping'
        redis_client.set(stopping_key, '1', ex=30)
        
        # Publish stop event to trigger immediate termination
        events_channel = f'ts_proxy:events:{channel_uuid}'
        redis_client.publish(events_channel, 'stop')
        
        # Also try to signal all clients to stop
        clients_key = f'ts_proxy:channel:{channel_uuid}:clients'
        clients = redis_client.smembers(clients_key) or []
        
        for client_id in clients:
            try:
                client_stop_key = f'ts_proxy:channel:{channel_uuid}:client:{client_id}:stop'
                redis_client.set(client_stop_key, '1', ex=30)
            except Exception:
                pass
        
        # Clear channel metadata to force reconnection
        metadata_key = f'ts_proxy:channel:{channel_uuid}:metadata'
        redis_client.delete(metadata_key)
        
        # Log the kill event (WebSocket removed - failover test system removed)
        logger.info(f"Stream killed manually for channel {channel.name} (UUID: {channel_uuid})")
        
        return JsonResponse({
            'success': True,
            'message': f'Stream for channel {channel.name} killed',
            'channel_uuid': channel_uuid,
            'clients_notified': len(clients),
        })
        
    except Exception as e:
        logger.error(f"Error killing stream for channel {channel_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_error(request, channel_id):
    """Simulate stream error to trigger failover behavior."""
    try:
        import time
        import datetime
        import json
        
        redis_client = RedisClient.get_client()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        # Hole die Channel UUID aus der Datenbank
        from apps.channels.models import Channel
        try:
            channel = Channel.objects.get(id=channel_id)
            channel_uuid = str(channel.uuid)
        except Channel.DoesNotExist:
            return JsonResponse({'error': f'Channel {channel_id} not found'}, status=404)
        
        # Setze force_failover Flag - der StreamManager wird dies erkennen und _try_next_stream() aufrufen
        failover_key = f'ts_proxy:channel:{channel_uuid}:force_failover'
        redis_client.set(failover_key, '1', ex=30)
        
        # Publiziere FORCE_FAILOVER Event als JSON
        events_channel = f'ts_proxy:events:{channel_uuid}'
        failover_event = {
            'event': 'force_failover',
            'channel_id': channel_uuid,
            'reason': 'manual_test',
            'timestamp': time.time()
        }
        redis_client.publish(events_channel, json.dumps(failover_event))
        
        # Log failover trigger (WebSocket removed - failover test system removed)
        logger.info(f"Failover manually triggered for channel {channel.name} (UUID: {channel_uuid})")
        
        return JsonResponse({
            'success': True,
            'message': f'Failover triggered for channel {channel.name}',
            'channel_uuid': channel_uuid,
        })
        
    except Exception as e:
        logger.error(f"Error triggering failover for channel {channel_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)
