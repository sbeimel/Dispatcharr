"""
Failover Test Service.

Provides test channel management and failover testing capabilities
for the Failover Test Page.

Requirements: 2.1, 2.3, 2.5, 8.2, 8.3, 8.4
"""

import logging
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class BackupStream:
    """A backup stream configuration."""
    id: str
    url: str
    priority: int
    name: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'url': self.url,
            'priority': self.priority,
            'name': self.name,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BackupStream':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            url=data['url'],
            priority=data.get('priority', 0),
            name=data.get('name', ''),
        )


@dataclass
class MACPortalConfig:
    """MAC Portal configuration for a test channel."""
    account_id: int
    portal_url: str
    macs: List[str]
    endpoints: List[str]
    user_agents: List[str]
    
    def to_dict(self) -> dict:
        return {
            'account_id': self.account_id,
            'portal_url': self.portal_url,
            'macs': self.macs,
            'endpoints': self.endpoints,
            'user_agents': self.user_agents,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MACPortalConfig':
        return cls(
            account_id=data['account_id'],
            portal_url=data.get('portal_url', ''),
            macs=data.get('macs', []),
            endpoints=data.get('endpoints', []),
            user_agents=data.get('user_agents', []),
        )


@dataclass
class TestChannel:
    """A temporary test channel."""
    id: str
    name: str
    primary_stream_url: str
    backup_streams: List[BackupStream]
    mac_portal_config: Optional[MACPortalConfig] = None
    is_imported: bool = False
    original_channel_id: Optional[int] = None
    created_at: datetime = field(default_factory=timezone.now)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'primary_stream_url': self.primary_stream_url,
            'backup_streams': [bs.to_dict() for bs in self.backup_streams],
            'mac_portal_config': self.mac_portal_config.to_dict() if self.mac_portal_config else None,
            'is_imported': self.is_imported,
            'original_channel_id': self.original_channel_id,
            'created_at': self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TestChannel':
        backup_streams = [BackupStream.from_dict(bs) for bs in data.get('backup_streams', [])]
        mac_config = None
        if data.get('mac_portal_config'):
            mac_config = MACPortalConfig.from_dict(data['mac_portal_config'])
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data['name'],
            primary_stream_url=data['primary_stream_url'],
            backup_streams=backup_streams,
            mac_portal_config=mac_config,
            is_imported=data.get('is_imported', False),
            original_channel_id=data.get('original_channel_id'),
        )


@dataclass
class LogEntry:
    """A log entry for failover events."""
    id: str
    timestamp: datetime
    event_type: str
    strategy: str
    original_value: str
    new_value: str
    reason: str
    success: bool
    duration_ms: int
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'strategy': self.strategy,
            'original_value': self.original_value,
            'new_value': self.new_value,
            'reason': self.reason,
            'success': self.success,
            'duration_ms': self.duration_ms,
            'details': self.details,
        }


@dataclass
class StrategyStats:
    """Statistics for a single failover strategy."""
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    total_time_ms: int = 0
    
    @property
    def avg_time_ms(self) -> float:
        if self.attempts == 0:
            return 0
        return self.total_time_ms / self.attempts
    
    def to_dict(self) -> dict:
        return {
            'attempts': self.attempts,
            'successes': self.successes,
            'failures': self.failures,
            'avg_time_ms': self.avg_time_ms,
        }


@dataclass
class TestStatistics:
    """Statistics for failover tests."""
    total_tests: int = 0
    successful_failovers: int = 0
    failed_failovers: int = 0
    total_time_ms: int = 0
    strategy_stats: Dict[str, StrategyStats] = field(default_factory=dict)
    
    @property
    def average_failover_time_ms(self) -> float:
        if self.total_tests == 0:
            return 0
        return self.total_time_ms / self.total_tests
    
    def to_dict(self) -> dict:
        return {
            'total_tests': self.total_tests,
            'successful_failovers': self.successful_failovers,
            'failed_failovers': self.failed_failovers,
            'average_failover_time_ms': self.average_failover_time_ms,
            'strategy_stats': {k: v.to_dict() for k, v in self.strategy_stats.items()},
        }
    
    def record_event(self, strategy: str, success: bool, duration_ms: int):
        """Record a failover event in statistics."""
        self.total_tests += 1
        self.total_time_ms += duration_ms
        
        if success:
            self.successful_failovers += 1
        else:
            self.failed_failovers += 1
        
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = StrategyStats()
        
        stats = self.strategy_stats[strategy]
        stats.attempts += 1
        stats.total_time_ms += duration_ms
        if success:
            stats.successes += 1
        else:
            stats.failures += 1
    
    def reset(self):
        """Reset all statistics."""
        self.total_tests = 0
        self.successful_failovers = 0
        self.failed_failovers = 0
        self.total_time_ms = 0
        self.strategy_stats.clear()


@dataclass
class TestSession:
    """A test session containing channels, logs, and statistics."""
    id: str
    created_at: datetime
    test_channels: Dict[str, TestChannel] = field(default_factory=dict)
    log_entries: List[LogEntry] = field(default_factory=list)
    statistics: TestStatistics = field(default_factory=TestStatistics)
    active_simulations: Dict[str, dict] = field(default_factory=dict)


class FailoverTestService:
    """
    Service for managing failover tests.
    
    Requirements: 2.1, 2.3, 2.5, 8.2, 8.3, 8.4
    """
    
    def __init__(self):
        self._sessions: Dict[str, TestSession] = {}
        self._default_session_id = "default"
    
    def _get_or_create_session(self, session_id: str = None) -> TestSession:
        """Get or create a test session."""
        sid = session_id or self._default_session_id
        if sid not in self._sessions:
            self._sessions[sid] = TestSession(
                id=sid,
                created_at=timezone.now(),
            )
        return self._sessions[sid]
    
    def create_test_channel(self, config: dict, session_id: str = None) -> TestChannel:
        """
        Create a new test channel.
        
        Requirements: 2.1, 2.3
        
        Args:
            config: Channel configuration dict
            session_id: Optional session ID
            
        Returns:
            Created TestChannel
        """
        session = self._get_or_create_session(session_id)
        
        # Validate required fields
        if not config.get('name'):
            raise ValueError("Channel name is required")
        if not config.get('primary_stream_url'):
            raise ValueError("Primary stream URL is required")
        
        # Create channel
        channel_id = str(uuid.uuid4())
        backup_streams = []
        for i, bs_data in enumerate(config.get('backup_streams', [])):
            bs_data['priority'] = bs_data.get('priority', i)
            backup_streams.append(BackupStream.from_dict(bs_data))
        
        mac_config = None
        if config.get('mac_portal_config'):
            mac_config = MACPortalConfig.from_dict(config['mac_portal_config'])
        
        channel = TestChannel(
            id=channel_id,
            name=config['name'],
            primary_stream_url=config['primary_stream_url'],
            backup_streams=backup_streams,
            mac_portal_config=mac_config,
            is_imported=False,
        )
        
        session.test_channels[channel_id] = channel
        logger.info(f"Created test channel: {channel.name} ({channel_id})")
        
        return channel
    
    def get_test_channel(self, channel_id: str, session_id: str = None) -> Optional[TestChannel]:
        """Get a test channel by ID."""
        session = self._get_or_create_session(session_id)
        return session.test_channels.get(channel_id)
    
    def get_all_test_channels(self, session_id: str = None) -> List[TestChannel]:
        """Get all test channels."""
        session = self._get_or_create_session(session_id)
        return list(session.test_channels.values())
    
    def delete_test_channel(self, channel_id: str, session_id: str = None) -> bool:
        """
        Delete a test channel.
        
        Requirements: 2.5
        
        Args:
            channel_id: Channel ID to delete
            session_id: Optional session ID
            
        Returns:
            True if deleted, False if not found
        """
        session = self._get_or_create_session(session_id)
        
        if channel_id not in session.test_channels:
            return False
        
        # Stop any active simulations for this channel
        if channel_id in session.active_simulations:
            del session.active_simulations[channel_id]
        
        del session.test_channels[channel_id]
        logger.info(f"Deleted test channel: {channel_id}")
        
        return True
    
    def import_channel(self, channel_id: int, session_id: str = None) -> TestChannel:
        """
        Import an existing channel as a test copy.
        
        Requirements: 8.2, 8.3, 8.4
        
        Args:
            channel_id: Database channel ID to import
            session_id: Optional session ID
            
        Returns:
            Created TestChannel copy
        """
        from apps.channels.models import Channel, ChannelStream
        from apps.m3u.models import M3UAccount
        
        # Get original channel
        try:
            original = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist:
            raise ValueError(f"Channel {channel_id} not found")
        
        # Get streams for this channel
        streams = ChannelStream.objects.filter(channel=original).order_by('priority')
        
        # Build backup streams list
        backup_streams = []
        primary_url = ""
        
        for i, stream in enumerate(streams):
            url = stream.url or ""
            if i == 0:
                primary_url = url
            else:
                backup_streams.append(BackupStream(
                    id=str(uuid.uuid4()),
                    url=url,
                    priority=i,
                    name=f"Backup {i}",
                ))
        
        # Check for MAC portal config
        mac_config = None
        if streams.exists():
            first_stream = streams.first()
            if first_stream and first_stream.m3u_account:
                account = first_stream.m3u_account
                if account.account_type == 'mac':
                    macs = list(account.macs.values_list('address', flat=True))
                    mac_config = MACPortalConfig(
                        account_id=account.id,
                        portal_url=account.server_url or "",
                        macs=macs,
                        endpoints=[
                            "/server/load.php",
                            "/stalker_portal/server/load.php",
                            "/portal.php",
                        ],
                        user_agents=["MAG250", "MAG254", "MAG322", "MAG424"],
                    )
        
        # Create test channel
        config = {
            'name': f"[TEST] {original.name}",
            'primary_stream_url': primary_url,
            'backup_streams': [bs.to_dict() for bs in backup_streams],
            'mac_portal_config': mac_config.to_dict() if mac_config else None,
        }
        
        channel = self.create_test_channel(config, session_id)
        channel.is_imported = True
        channel.original_channel_id = channel_id
        
        logger.info(f"Imported channel {original.name} as test channel {channel.id}")
        
        return channel
    
    def get_available_channels(self) -> List[dict]:
        """
        Get list of available channels for import.
        
        Requirements: 8.1
        """
        from apps.channels.models import Channel
        
        channels = Channel.objects.all().order_by('name')[:100]
        return [
            {
                'id': ch.id,
                'name': ch.name,
                'channel_number': ch.channel_number,
            }
            for ch in channels
        ]
    
    def add_log_entry(self, entry: LogEntry, session_id: str = None):
        """Add a log entry to the session."""
        session = self._get_or_create_session(session_id)
        session.log_entries.append(entry)
        
        # Update statistics
        session.statistics.record_event(
            strategy=entry.strategy,
            success=entry.success,
            duration_ms=entry.duration_ms,
        )
    
    def get_log_entries(self, session_id: str = None, limit: int = 100) -> List[LogEntry]:
        """Get log entries."""
        session = self._get_or_create_session(session_id)
        return session.log_entries[-limit:]
    
    def get_statistics(self, session_id: str = None) -> TestStatistics:
        """Get test statistics."""
        session = self._get_or_create_session(session_id)
        return session.statistics
    
    def reset_statistics(self, session_id: str = None):
        """Reset test statistics."""
        session = self._get_or_create_session(session_id)
        session.statistics.reset()
        session.log_entries.clear()
        logger.info(f"Reset statistics for session {session.id}")
    
    def export_logs_json(self, session_id: str = None) -> List[dict]:
        """Export logs as JSON-serializable list."""
        session = self._get_or_create_session(session_id)
        return [entry.to_dict() for entry in session.log_entries]
    
    def export_statistics_csv(self, session_id: str = None) -> str:
        """Export statistics as CSV string."""
        session = self._get_or_create_session(session_id)
        stats = session.statistics
        
        lines = ["strategy,attempts,successes,failures,avg_time_ms"]
        for strategy, s in stats.strategy_stats.items():
            lines.append(f"{strategy},{s.attempts},{s.successes},{s.failures},{s.avg_time_ms:.2f}")
        
        lines.append("")
        lines.append(f"total,{stats.total_tests},{stats.successful_failovers},{stats.failed_failovers},{stats.average_failover_time_ms:.2f}")
        
        return "\n".join(lines)
    
    def cleanup_session(self, session_id: str = None):
        """Clean up a test session."""
        sid = session_id or self._default_session_id
        if sid in self._sessions:
            session = self._sessions[sid]
            session.active_simulations.clear()
            session.test_channels.clear()
            del self._sessions[sid]
            logger.info(f"Cleaned up session {sid}")


# Singleton instance
_service_instance: Optional[FailoverTestService] = None


def get_failover_test_service() -> FailoverTestService:
    """Get the global FailoverTestService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FailoverTestService()
    return _service_instance


def reset_failover_test_service():
    """Reset the global service instance (for testing)."""
    global _service_instance
    _service_instance = None
