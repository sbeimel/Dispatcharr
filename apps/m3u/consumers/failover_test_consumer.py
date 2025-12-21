"""
WebSocket Consumer for Failover Test Page.

Provides real-time updates for failover test events.
"""

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class FailoverTestConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for failover test real-time updates.
    
    Clients connect to receive:
    - Failover event notifications
    - Simulation status updates
    - Log entries in real-time
    """
    
    GROUP_NAME = "failover_test"
    
    async def connect(self):
        """Handle WebSocket connection."""
        await self.channel_layer.group_add(
            self.GROUP_NAME,
            self.channel_name
        )
        await self.accept()
        await self.send_initial_state()
        logger.info(f"Failover test WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.GROUP_NAME,
            self.channel_name
        )
        logger.info(f"Failover test WebSocket disconnected: {self.channel_name}")
    
    async def receive_json(self, content):
        """Handle incoming messages from client."""
        message_type = content.get('type')
        
        if message_type == 'get_status':
            await self.send_initial_state()
        
        elif message_type == 'get_logs':
            limit = content.get('limit', 50)
            logs = await self.get_recent_logs(limit)
            await self.send_json({
                'type': 'logs',
                'data': logs,
            })
        
        elif message_type == 'subscribe_channel':
            channel_id = content.get('channel_id')
            if channel_id:
                await self.channel_layer.group_add(
                    f"failover_test_{channel_id}",
                    self.channel_name
                )
                await self.send_json({
                    'type': 'subscribed',
                    'channel_id': channel_id,
                })
        
        elif message_type == 'unsubscribe_channel':
            channel_id = content.get('channel_id')
            if channel_id:
                await self.channel_layer.group_discard(
                    f"failover_test_{channel_id}",
                    self.channel_name
                )
    
    async def send_initial_state(self):
        """Send initial state to newly connected client."""
        try:
            state = await self.get_current_state()
            await self.send_json({
                'type': 'initial_state',
                'data': state,
            })
        except Exception as e:
            logger.error(f"Error sending initial state: {e}")
            # Send empty state on error
            await self.send_json({
                'type': 'initial_state',
                'data': {
                    'test_channels': [],
                    'statistics': {},
                    'active_simulations': [],
                    'recent_logs': [],
                    'settings': {},
                },
            })
    
    @database_sync_to_async
    def get_current_state(self):
        """Get current failover test state."""
        try:
            from ..failover_test_service import get_failover_test_service
            from ..stream_simulation_service import get_stream_simulation_service
            from ..mac_portal_models import FailoverSettings
            
            test_service = get_failover_test_service()
            sim_service = get_stream_simulation_service()
            
            channels = [ch.to_dict() for ch in test_service.get_all_test_channels()]
            stats = test_service.get_statistics().to_dict()
            simulations = sim_service.get_active_simulations()
            logs = [e.to_dict() for e in test_service.get_log_entries(limit=20)]
            settings = FailoverSettings.get_settings()
            
            return {
                'test_channels': channels,
                'statistics': stats,
                'active_simulations': simulations,
                'recent_logs': logs,
                'settings': {
                    'mac_failover_enabled': settings.mac_failover_enabled,
                    'portal_failover_enabled': settings.portal_failover_enabled,
                    'stream_failover_enabled': settings.stream_failover_enabled,
                    'endpoint_failover_enabled': settings.endpoint_failover_enabled,
                    'useragent_failover_enabled': settings.useragent_failover_enabled,
                    'failover_priority': settings.failover_priority,
                },
            }
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {
                'test_channels': [],
                'statistics': {},
                'active_simulations': [],
                'recent_logs': [],
                'settings': {},
            }
    
    @database_sync_to_async
    def get_recent_logs(self, limit: int):
        """Get recent log entries."""
        try:
            from ..failover_test_service import get_failover_test_service
            service = get_failover_test_service()
            entries = service.get_log_entries(limit=limit)
            return [e.to_dict() for e in entries]
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []
    
    # Event Handlers for Group Messages
    async def failover_test_event(self, event):
        """Handle failover test event broadcast."""
        await self.send_json({
            'type': event.get('type', 'failover_event'),
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def failover_event(self, event):
        """Handle failover_event message type."""
        await self.send_json({
            'type': 'failover_event',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def simulation_started(self, event):
        """Handle simulation started event."""
        await self.send_json({
            'type': 'simulation_started',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def simulation_stopped(self, event):
        """Handle simulation stopped event."""
        await self.send_json({
            'type': 'simulation_stopped',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def simulation_completed(self, event):
        """Handle simulation completed event."""
        await self.send_json({
            'type': 'simulation_completed',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def log_entry(self, event):
        """Handle new log entry event."""
        await self.send_json({
            'type': 'log_entry',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def statistics_update(self, event):
        """Handle statistics update event."""
        await self.send_json({
            'type': 'statistics_update',
            'data': event.get('data', {}),
            'timestamp': timezone.now().isoformat(),
        })
