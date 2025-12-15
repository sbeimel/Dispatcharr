"""
WebSocket Consumer for Predictive Failover System.

This module provides real-time updates for:
- Risk score changes
- Failover events
- Warmup status updates

Requirements: 7.2, 7.5
"""

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class PredictiveFailoverConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for predictive failover real-time updates.
    
    Clients connect to receive:
    - Risk score updates for active streams
    - Failover event notifications
    - Warmup status changes
    
    Requirements: 7.2, 7.5
    """
    
    GROUP_NAME = "predictive_failover"
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Add to group for broadcast messages
        await self.channel_layer.group_add(
            self.GROUP_NAME,
            self.channel_name
        )
        await self.accept()
        
        # Send initial state
        await self.send_initial_state()
        
        logger.info(f"Predictive failover WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.GROUP_NAME,
            self.channel_name
        )
        logger.info(f"Predictive failover WebSocket disconnected: {self.channel_name}")
    
    async def receive_json(self, content):
        """
        Handle incoming messages from client.
        
        Supported message types:
        - subscribe: Subscribe to specific channel updates
        - unsubscribe: Unsubscribe from channel updates
        - get_status: Request current status
        """
        message_type = content.get('type')
        
        if message_type == 'subscribe':
            channel_id = content.get('channel_id')
            if channel_id:
                await self.channel_layer.group_add(
                    f"predictive_{channel_id}",
                    self.channel_name
                )
                await self.send_json({
                    'type': 'subscribed',
                    'channel_id': channel_id
                })
        
        elif message_type == 'unsubscribe':
            channel_id = content.get('channel_id')
            if channel_id:
                await self.channel_layer.group_discard(
                    f"predictive_{channel_id}",
                    self.channel_name
                )
                await self.send_json({
                    'type': 'unsubscribed',
                    'channel_id': channel_id
                })
        
        elif message_type == 'get_status':
            await self.send_initial_state()
    
    async def send_initial_state(self):
        """Send initial state to newly connected client."""
        try:
            state = await self.get_current_state()
            await self.send_json({
                'type': 'initial_state',
                'data': state
            })
        except Exception as e:
            logger.error(f"Error sending initial state: {e}")
    
    @database_sync_to_async
    def get_current_state(self):
        """Get current predictive failover state."""
        from .config import get_predictive_config
        from .warmup_manager import get_warmup_manager
        from .metrics_collector import get_metrics_collector
        from .risk_calculator import RiskScoreCalculator
        
        try:
            config = get_predictive_config()
        except Exception:
            config = type('Config', (), {
                'enabled': False,
                'warmup_threshold': 60,
                'failover_threshold': 80
            })()
        
        try:
            warmup_manager = get_warmup_manager()
            warmup_status = warmup_manager.get_all_warmup_status()
        except Exception:
            warmup_status = {}
        
        try:
            collector = get_metrics_collector()
            calculator = RiskScoreCalculator()
            
            # Get active streams with risk scores
            active_streams = []
            for stream_info in collector.get_monitored_streams():
                stream_id = stream_info.get('stream_id')
                if stream_id:
                    risk_result = calculator.calculate_risk_score(stream_id)
                    active_streams.append({
                        'stream_id': stream_id,
                        'channel_id': stream_info.get('channel_id'),
                        'channel_name': stream_info.get('channel_name', 'Unknown'),
                        'risk_score': risk_result.score,
                        'reasons': risk_result.reasons,
                    })
        except Exception:
            active_streams = []
        
        # Get recent events - handle missing table gracefully
        recent_events = []
        try:
            from .models import PredictiveFailoverEvent
            recent_events = list(
                PredictiveFailoverEvent.objects.all()[:10].values(
                    'id', 'event_type', 'channel_name', 'risk_score', 
                    'reason', 'timestamp', 'success'
                )
            )
        except Exception as e:
            # Table might not exist yet - this is OK
            logger.debug(f"Could not fetch recent events (table may not exist): {e}")
        
        return {
            'enabled': getattr(config, 'enabled', False),
            'warmup_threshold': getattr(config, 'warmup_threshold', 60),
            'failover_threshold': getattr(config, 'failover_threshold', 80),
            'active_streams': active_streams,
            'warmup_status': warmup_status,
            'recent_events': recent_events,
        }
    
    # =========================================================================
    # Event Handlers for Group Messages
    # =========================================================================
    
    async def risk_score_update(self, event):
        """
        Handle risk score update broadcast.
        
        Requirement 7.2: Push risk score updates to clients
        """
        await self.send_json({
            'type': 'risk_score_update',
            'stream_id': event.get('stream_id'),
            'channel_id': event.get('channel_id'),
            'channel_name': event.get('channel_name'),
            'risk_score': event.get('risk_score'),
            'reasons': event.get('reasons', []),
            'timestamp': event.get('timestamp'),
        })
    
    async def failover_event(self, event):
        """
        Handle failover event broadcast.
        
        Requirement 7.5: Push failover events to clients
        """
        await self.send_json({
            'type': 'failover_event',
            'event_type': event.get('event_type'),
            'channel_id': event.get('channel_id'),
            'channel_name': event.get('channel_name'),
            'risk_score': event.get('risk_score'),
            'reason': event.get('reason'),
            'success': event.get('success'),
            'timestamp': event.get('timestamp'),
        })
    
    async def warmup_status_update(self, event):
        """
        Handle warmup status update broadcast.
        
        Requirement 7.5: Push warmup status updates to clients
        """
        await self.send_json({
            'type': 'warmup_status_update',
            'channel_id': event.get('channel_id'),
            'status': event.get('status'),
            'backup_stream_id': event.get('backup_stream_id'),
            'timestamp': event.get('timestamp'),
        })
    
    async def config_update(self, event):
        """Handle configuration update broadcast."""
        await self.send_json({
            'type': 'config_update',
            'enabled': event.get('enabled'),
            'warmup_threshold': event.get('warmup_threshold'),
            'failover_threshold': event.get('failover_threshold'),
        })


# =============================================================================
# Helper Functions for Broadcasting
# =============================================================================

async def broadcast_risk_score_update(
    stream_id: str,
    channel_id: str,
    channel_name: str,
    risk_score: int,
    reasons: list = None
):
    """
    Broadcast risk score update to all connected clients.
    
    Args:
        stream_id: Stream identifier
        channel_id: Channel UUID
        channel_name: Channel display name
        risk_score: Current risk score (0-100)
        reasons: List of reasons contributing to score
    """
    from channels.layers import get_channel_layer
    from django.utils import timezone
    
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    
    await channel_layer.group_send(
        PredictiveFailoverConsumer.GROUP_NAME,
        {
            'type': 'risk_score_update',
            'stream_id': stream_id,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'risk_score': risk_score,
            'reasons': reasons or [],
            'timestamp': timezone.now().isoformat(),
        }
    )


async def broadcast_failover_event(
    event_type: str,
    channel_id: str,
    channel_name: str,
    risk_score: int = None,
    reason: str = "",
    success: bool = None
):
    """
    Broadcast failover event to all connected clients.
    
    Args:
        event_type: Type of failover event
        channel_id: Channel UUID
        channel_name: Channel display name
        risk_score: Risk score at time of event
        reason: Reason for the event
        success: Whether the action was successful
    """
    from channels.layers import get_channel_layer
    from django.utils import timezone
    
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    
    await channel_layer.group_send(
        PredictiveFailoverConsumer.GROUP_NAME,
        {
            'type': 'failover_event',
            'event_type': event_type,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'risk_score': risk_score,
            'reason': reason,
            'success': success,
            'timestamp': timezone.now().isoformat(),
        }
    )


async def broadcast_warmup_status(
    channel_id: str,
    status: str,
    backup_stream_id: str = None
):
    """
    Broadcast warmup status update to all connected clients.
    
    Args:
        channel_id: Channel UUID
        status: Warmup status (warming, ready, released, failed)
        backup_stream_id: ID of the backup stream
    """
    from channels.layers import get_channel_layer
    from django.utils import timezone
    
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    
    await channel_layer.group_send(
        PredictiveFailoverConsumer.GROUP_NAME,
        {
            'type': 'warmup_status_update',
            'channel_id': channel_id,
            'status': status,
            'backup_stream_id': backup_stream_id,
            'timestamp': timezone.now().isoformat(),
        }
    )


# Synchronous wrappers for use in non-async code
def sync_broadcast_risk_score_update(*args, **kwargs):
    """Synchronous wrapper for broadcast_risk_score_update."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast_risk_score_update(*args, **kwargs))
        else:
            loop.run_until_complete(broadcast_risk_score_update(*args, **kwargs))
    except RuntimeError:
        asyncio.run(broadcast_risk_score_update(*args, **kwargs))


def sync_broadcast_failover_event(*args, **kwargs):
    """Synchronous wrapper for broadcast_failover_event."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast_failover_event(*args, **kwargs))
        else:
            loop.run_until_complete(broadcast_failover_event(*args, **kwargs))
    except RuntimeError:
        asyncio.run(broadcast_failover_event(*args, **kwargs))


def sync_broadcast_warmup_status(*args, **kwargs):
    """Synchronous wrapper for broadcast_warmup_status."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast_warmup_status(*args, **kwargs))
        else:
            loop.run_until_complete(broadcast_warmup_status(*args, **kwargs))
    except RuntimeError:
        asyncio.run(broadcast_warmup_status(*args, **kwargs))
