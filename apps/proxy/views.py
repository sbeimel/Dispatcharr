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
        redis_client = RedisClient.get_instance()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        active_streams = []
        
        # Scan for active channel metadata
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match='ts_proxy:channel:*:metadata', count=100)
            
            for key in keys:
                try:
                    metadata = redis_client.hgetall(key)
                    if metadata:
                        channel_id = key.split(':')[2]
                        
                        # Get client count
                        clients_key = f'ts_proxy:channel:{channel_id}:clients'
                        client_count = redis_client.scard(clients_key) or 0
                        
                        if client_count > 0 or metadata.get('status') == 'streaming':
                            active_streams.append({
                                'channel_id': int(channel_id),
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
        redis_client = RedisClient.get_instance()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        # Set the stopping flag for the channel
        stopping_key = f'ts_proxy:channel:{channel_id}:stopping'
        redis_client.set(stopping_key, '1', ex=30)
        
        # Publish stop event to trigger immediate termination
        events_channel = f'ts_proxy:events:{channel_id}'
        redis_client.publish(events_channel, 'stop')
        
        # Also try to signal all clients to stop
        clients_key = f'ts_proxy:channel:{channel_id}:clients'
        clients = redis_client.smembers(clients_key) or []
        
        for client_id in clients:
            try:
                client_stop_key = f'ts_proxy:channel:{channel_id}:client:{client_id}:stop'
                redis_client.set(client_stop_key, '1', ex=30)
            except Exception:
                pass
        
        # Clear channel metadata to force reconnection
        metadata_key = f'ts_proxy:channel:{channel_id}:metadata'
        redis_client.delete(metadata_key)
        
        # Log the kill event
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'failover_test',
                    {
                        'type': 'failover_event',
                        'data': {
                            'id': f'kill_{channel_id}_{int(__import__("time").time() * 1000)}',
                            'timestamp': __import__("datetime").datetime.now().isoformat(),
                            'event_type': 'stream_killed',
                            'channel_id': channel_id,
                            'message': f'Stream for channel {channel_id} was manually killed',
                            'success': True,
                        }
                    }
                )
        except Exception as e:
            logger.debug(f"Could not send WebSocket event: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'Stream for channel {channel_id} killed',
            'clients_notified': len(clients),
        })
        
    except Exception as e:
        logger.error(f"Error killing stream for channel {channel_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_error(request, channel_id):
    """Simulate various stream errors to test failover behavior."""
    try:
        import time
        import datetime
        
        error_type = request.data.get('error_type', 'timeout')
        
        redis_client = RedisClient.get_instance()
        if not redis_client:
            return JsonResponse({'error': 'Redis not available'}, status=503)
        
        # Simuliere verschiedene Fehlertypen
        error_messages = {
            'timeout': 'Connection timeout - no response from server',
            'connection_reset': 'Connection reset by peer',
            'http_403': 'HTTP 403 Forbidden - Access denied',
            'http_404': 'HTTP 404 Not Found - Stream not available',
            'stream_corrupt': 'Stream data corrupt - invalid TS packets',
        }
        
        message = error_messages.get(error_type, f'Unknown error: {error_type}')
        
        # Setze Error-Flag für den Channel
        error_key = f'ts_proxy:channel:{channel_id}:simulated_error'
        redis_client.set(error_key, error_type, ex=60)
        
        # Publiziere Error-Event
        events_channel = f'ts_proxy:events:{channel_id}'
        redis_client.publish(events_channel, f'error:{error_type}')
        
        # Sende WebSocket Event
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'failover_test',
                    {
                        'type': 'failover_event',
                        'data': {
                            'id': f'error_{channel_id}_{int(time.time() * 1000)}',
                            'timestamp': datetime.datetime.now().isoformat(),
                            'event_type': 'error_simulated',
                            'channel_id': channel_id,
                            'error_type': error_type,
                            'message': message,
                            'success': True,
                        }
                    }
                )
        except Exception as e:
            logger.debug(f"Could not send WebSocket event: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'Error simulated for channel {channel_id}',
            'error_type': error_type,
            'error_message': message,
        })
        
    except Exception as e:
        logger.error(f"Error simulating error for channel {channel_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)
