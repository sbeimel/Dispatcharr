"""
Stream Simulation Service.

Provides error simulation capabilities for testing failover mechanisms.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import logging
import uuid
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from django.utils import timezone

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors that can be simulated."""
    TIMEOUT = "timeout"
    CONNECTION_RESET = "connection_reset"
    HTTP_403 = "403"
    HTTP_404 = "404"
    HTTP_500 = "500"
    STREAM_ERROR = "stream_error"


@dataclass
class SimulationConfig:
    """Configuration for auto-simulation."""
    interval_ms: int = 5000
    error_types: list = None
    max_interruptions: int = 10
    
    def __post_init__(self):
        if self.error_types is None:
            self.error_types = [ErrorType.TIMEOUT]


@dataclass
class SimulationState:
    """State of an active simulation."""
    id: str
    channel_id: str
    config: SimulationConfig
    is_running: bool = True
    interruption_count: int = 0
    started_at: datetime = None
    last_interruption_at: datetime = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = timezone.now()


class SimulatedError(Exception):
    """Exception raised for simulated errors."""
    def __init__(self, error_type: ErrorType, message: str = ""):
        self.error_type = error_type
        self.message = message or f"Simulated {error_type.value} error"
        super().__init__(self.message)


class StreamSimulationService:
    """
    Service for simulating stream errors to test failover.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    def __init__(self):
        self._active_simulations: Dict[str, SimulationState] = {}
        self._simulation_threads: Dict[str, threading.Thread] = {}
        self._event_callback: Optional[Callable] = None
        self._lock = threading.Lock()
    
    def set_event_callback(self, callback: Callable[[dict], None]):
        """Set callback for simulation events."""
        self._event_callback = callback
    
    def simulate_error(self, channel_id: str, error_type: str) -> dict:
        """
        Simulate a specific error for a channel.
        
        Requirements: 3.1, 3.2, 3.3
        
        Args:
            channel_id: Test channel ID
            error_type: Type of error to simulate
            
        Returns:
            Result dict with event details
        """
        start_time = time.time()
        
        try:
            error_enum = ErrorType(error_type)
        except ValueError:
            error_enum = ErrorType.STREAM_ERROR
        
        # Failover test service removed - this functionality is deprecated
        # Use manual failover test (kill_stream) in proxy/views.py instead
        return {
            'success': False,
            'error': 'Failover test service removed - use manual failover test (kill_stream) instead',
        }
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Create log entry
        log_entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=timezone.now(),
            event_type=f"simulated_{error_type}",
            strategy=result.get('strategy', 'unknown'),
            original_value=result.get('original', ''),
            new_value=result.get('new', ''),
            reason=f"Simulated {error_type} error",
            success=result.get('success', False),
            duration_ms=duration_ms,
            details={
                'error_type': error_type,
                'channel_name': channel.name,
            }
        )
        
        service.add_log_entry(log_entry)
        
        # Broadcast event
        self._broadcast_event({
            'type': 'failover_event',
            'data': log_entry.to_dict(),
        })
        
        return {
            'success': True,
            'event': log_entry.to_dict(),
            'duration_ms': duration_ms,
        }
    
    def _execute_failover_test(self, channel, error_type: ErrorType) -> dict:
        """Execute a failover test for the channel.
        
        If the channel is imported from a real channel, use the real FailoverManager.
        Otherwise, use simulated failover for test channels.
        """
        result = {
            'success': False,
            'strategy': 'none',
            'original': channel.primary_stream_url,
            'new': '',
        }
        
        # If this is an imported real channel, use the real FailoverManager
        if channel.is_imported and channel.original_channel_id:
            return self._execute_real_failover(channel, error_type, result)
        
        # For test channels, use simulated failover
        return self._execute_simulated_failover(channel, result)
    
    def _execute_real_failover(self, channel, error_type: ErrorType, result: dict) -> dict:
        """Execute real failover using the actual FailoverManager."""
        try:
            from apps.channels.models import Channel as RealChannel
            from apps.proxy.ts_proxy.failover_utils import FailoverManager
            
            # Get the real channel
            real_channel = RealChannel.objects.get(id=channel.original_channel_id)
            channel_uuid = str(real_channel.uuid)
            
            # Create FailoverManager for this channel
            manager = FailoverManager(channel_uuid)
            
            # Try to get a failover stream
            new_url, profile_id, error = manager.get_stream_with_failover()
            
            if new_url:
                result['success'] = True
                result['strategy'] = 'mac' if profile_id else 'stream'
                result['original'] = channel.primary_stream_url
                result['new'] = new_url
                
                # Log the failover event
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Real MAC failover test successful for channel {channel.name}: {new_url[:50]}...")
            else:
                result['success'] = False
                result['strategy'] = 'none'
                result['error'] = error or 'Failover exhausted'
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Real failover test failed: {e}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _execute_simulated_failover(self, channel, result: dict) -> dict:
        """Execute simulated failover for test channels."""
        # If channel has MAC portal config, test MAC failover
        if channel.mac_portal_config:
            result['strategy'] = 'mac'
            
            # Simulate MAC rotation
            macs = channel.mac_portal_config.macs
            if len(macs) > 1:
                result['original'] = macs[0] if macs else ''
                result['new'] = macs[1] if len(macs) > 1 else macs[0]
                result['success'] = True
            else:
                # Try endpoint failover
                result['strategy'] = 'endpoint'
                endpoints = channel.mac_portal_config.endpoints
                if len(endpoints) > 1:
                    result['original'] = endpoints[0]
                    result['new'] = endpoints[1]
                    result['success'] = True
        
        # If no MAC config or MAC failover exhausted, try stream failover
        if not result['success'] and channel.backup_streams:
            result['strategy'] = 'stream'
            result['original'] = channel.primary_stream_url
            result['new'] = channel.backup_streams[0].url if channel.backup_streams else ''
            result['success'] = bool(channel.backup_streams)
        
        return result
    
    def start_auto_simulation(self, channel_id: str, config: dict) -> str:
        """
        Start automatic error simulation.
        
        Requirements: 3.4
        
        Args:
            channel_id: Test channel ID
            config: Simulation configuration
            
        Returns:
            Simulation ID
        """
        simulation_id = str(uuid.uuid4())
        
        sim_config = SimulationConfig(
            interval_ms=config.get('interval_ms', 5000),
            error_types=[ErrorType(et) for et in config.get('error_types', ['timeout'])],
            max_interruptions=config.get('max_interruptions', 10),
        )
        
        state = SimulationState(
            id=simulation_id,
            channel_id=channel_id,
            config=sim_config,
        )
        
        with self._lock:
            self._active_simulations[simulation_id] = state
        
        # Start simulation thread
        thread = threading.Thread(
            target=self._run_auto_simulation,
            args=(simulation_id,),
            daemon=True,
        )
        self._simulation_threads[simulation_id] = thread
        thread.start()
        
        logger.info(f"Started auto-simulation {simulation_id} for channel {channel_id}")
        
        self._broadcast_event({
            'type': 'simulation_started',
            'data': {
                'simulation_id': simulation_id,
                'channel_id': channel_id,
                'config': {
                    'interval_ms': sim_config.interval_ms,
                    'max_interruptions': sim_config.max_interruptions,
                },
            },
        })
        
        return simulation_id
    
    def _run_auto_simulation(self, simulation_id: str):
        """Run the auto-simulation loop."""
        import random
        
        while True:
            with self._lock:
                state = self._active_simulations.get(simulation_id)
                if not state or not state.is_running:
                    break
                
                if state.interruption_count >= state.config.max_interruptions:
                    state.is_running = False
                    break
            
            # Wait for interval
            time.sleep(state.config.interval_ms / 1000)
            
            with self._lock:
                state = self._active_simulations.get(simulation_id)
                if not state or not state.is_running:
                    break
            
            # Pick random error type
            error_type = random.choice(state.config.error_types)
            
            # Simulate error
            self.simulate_error(state.channel_id, error_type.value)
            
            with self._lock:
                if simulation_id in self._active_simulations:
                    self._active_simulations[simulation_id].interruption_count += 1
                    self._active_simulations[simulation_id].last_interruption_at = timezone.now()
        
        # Simulation completed
        self._broadcast_event({
            'type': 'simulation_completed',
            'data': {
                'simulation_id': simulation_id,
                'interruption_count': state.interruption_count if state else 0,
            },
        })
        
        logger.info(f"Auto-simulation {simulation_id} completed")
    
    def stop_simulation(self, simulation_id: str) -> bool:
        """
        Stop an active simulation.
        
        Requirements: 3.5
        
        Args:
            simulation_id: Simulation ID to stop
            
        Returns:
            True if stopped, False if not found
        """
        with self._lock:
            if simulation_id not in self._active_simulations:
                return False
            
            self._active_simulations[simulation_id].is_running = False
        
        logger.info(f"Stopped simulation {simulation_id}")
        
        self._broadcast_event({
            'type': 'simulation_stopped',
            'data': {
                'simulation_id': simulation_id,
            },
        })
        
        return True
    
    def stop_all_simulations(self, channel_id: str = None):
        """Stop all simulations, optionally filtered by channel."""
        with self._lock:
            for sim_id, state in list(self._active_simulations.items()):
                if channel_id is None or state.channel_id == channel_id:
                    state.is_running = False
        
        logger.info(f"Stopped all simulations" + (f" for channel {channel_id}" if channel_id else ""))
    
    def get_simulation_status(self, simulation_id: str) -> Optional[dict]:
        """Get status of a simulation."""
        with self._lock:
            state = self._active_simulations.get(simulation_id)
            if not state:
                return None
            
            return {
                'id': state.id,
                'channel_id': state.channel_id,
                'is_running': state.is_running,
                'interruption_count': state.interruption_count,
                'max_interruptions': state.config.max_interruptions,
                'started_at': state.started_at.isoformat() if state.started_at else None,
                'last_interruption_at': state.last_interruption_at.isoformat() if state.last_interruption_at else None,
            }
    
    def get_active_simulations(self) -> list:
        """Get all active simulations."""
        with self._lock:
            return [
                self.get_simulation_status(sim_id)
                for sim_id in self._active_simulations
                if self._active_simulations[sim_id].is_running
            ]
    
    def _broadcast_event(self, event: dict):
        """Broadcast an event to listeners."""
        if self._event_callback:
            try:
                self._event_callback(event)
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")
        
        # Also broadcast via WebSocket
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "failover_test",
                    {
                        'type': 'failover_test_event',
                        **event,
                    }
                )
        except Exception as e:
            logger.debug(f"Could not broadcast via WebSocket: {e}")


# Singleton instance
_simulation_service: Optional[StreamSimulationService] = None


def get_stream_simulation_service() -> StreamSimulationService:
    """Get the global StreamSimulationService instance."""
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = StreamSimulationService()
    return _simulation_service


def reset_stream_simulation_service():
    """Reset the global service instance (for testing)."""
    global _simulation_service
    if _simulation_service:
        _simulation_service.stop_all_simulations()
    _simulation_service = None
