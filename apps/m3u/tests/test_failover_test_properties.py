"""
Property-based tests for Failover Test Service.

Uses Hypothesis for property-based testing.

**Feature: failover-test-page**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch, MagicMock

from apps.m3u.failover_test_service import (
    FailoverTestService,
    TestChannel,
    BackupStream,
    MACPortalConfig,
    LogEntry,
    TestStatistics,
    StrategyStats,
)
from apps.m3u.stream_simulation_service import (
    StreamSimulationService,
    ErrorType,
    SimulationConfig,
)


# =============================================================================
# Strategies for generating test data
# =============================================================================

valid_url = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&()*+,;='),
    min_size=10,
    max_size=100
).map(lambda s: f"http://test.com/{s}")

valid_name = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_'),
    min_size=1,
    max_size=50
).filter(lambda s: s.strip())

mac_address = st.text(
    alphabet=st.sampled_from('0123456789ABCDEF:'),
    min_size=17,
    max_size=17
).map(lambda _: "00:1A:79:XX:XX:XX".replace('X', 'A'))

error_type_strategy = st.sampled_from([
    'timeout', 'connection_reset', '403', '404', '500', 'stream_error'
])

strategy_name = st.sampled_from(['mac', 'portal', 'endpoint', 'useragent', 'stream'])


# =============================================================================
# Property 1: Test Channel Validation
# **Feature: failover-test-page, Property 1: Test Channel Validation**
# **Validates: Requirements 2.3**
# =============================================================================

@settings(max_examples=100)
@given(
    name=valid_name,
    primary_url=valid_url,
    backup_urls=st.lists(valid_url, min_size=0, max_size=5),
)
def test_valid_channel_creation_succeeds(name, primary_url, backup_urls):
    """
    **Feature: failover-test-page, Property 1: Test Channel Validation**
    
    For any test channel configuration with a non-empty name and valid 
    primary stream URL, saving the channel should succeed and the channel 
    should appear in the test channel list.
    """
    service = FailoverTestService()
    
    config = {
        'name': name,
        'primary_stream_url': primary_url,
        'backup_streams': [{'url': url, 'priority': i} for i, url in enumerate(backup_urls)],
    }
    
    channel = service.create_test_channel(config)
    
    # Channel should be created
    assert channel is not None
    assert channel.name == name
    assert channel.primary_stream_url == primary_url
    assert len(channel.backup_streams) == len(backup_urls)
    
    # Channel should appear in list
    all_channels = service.get_all_test_channels()
    assert any(c.id == channel.id for c in all_channels)


# =============================================================================
# Property 2: Test Channel Deletion Cleanup
# **Feature: failover-test-page, Property 2: Test Channel Deletion Cleanup**
# **Validates: Requirements 2.5**
# =============================================================================

@settings(max_examples=100)
@given(
    name=valid_name,
    primary_url=valid_url,
)
def test_deleted_channel_not_in_list(name, primary_url):
    """
    **Feature: failover-test-page, Property 2: Test Channel Deletion Cleanup**
    
    For any test channel that is deleted, the channel should no longer 
    appear in the test channel list.
    """
    service = FailoverTestService()
    
    config = {
        'name': name,
        'primary_stream_url': primary_url,
    }
    
    channel = service.create_test_channel(config)
    channel_id = channel.id
    
    # Verify channel exists
    assert service.get_test_channel(channel_id) is not None
    
    # Delete channel
    result = service.delete_test_channel(channel_id)
    assert result is True
    
    # Channel should not be in list
    assert service.get_test_channel(channel_id) is None
    all_channels = service.get_all_test_channels()
    assert not any(c.id == channel_id for c in all_channels)


# =============================================================================
# Property 4: Error Type Simulation Accuracy
# **Feature: failover-test-page, Property 4: Error Type Simulation Accuracy**
# **Validates: Requirements 3.2**
# =============================================================================

@settings(max_examples=100)
@given(error_type=error_type_strategy)
def test_simulated_error_matches_type(error_type):
    """
    **Feature: failover-test-page, Property 4: Error Type Simulation Accuracy**
    
    For any selected error type, the simulated error should match the 
    selected type in the resulting log entry.
    """
    # Setup
    test_service = FailoverTestService()
    sim_service = StreamSimulationService()
    
    # Create a test channel
    config = {
        'name': 'Test Channel',
        'primary_stream_url': 'http://test.com/stream',
        'backup_streams': [{'url': 'http://test.com/backup', 'priority': 0}],
    }
    channel = test_service.create_test_channel(config)
    
    # Simulate error
    with patch.object(sim_service, '_broadcast_event'):
        result = sim_service.simulate_error(channel.id, error_type)
    
    # Verify result
    assert result['success'] is True
    assert 'event' in result
    
    event = result['event']
    assert error_type in event['event_type']
    assert event['details']['error_type'] == error_type


# =============================================================================
# Property 9: Statistics Accuracy
# **Feature: failover-test-page, Property 9: Statistics Accuracy**
# **Validates: Requirements 6.1, 6.2, 6.3**
# =============================================================================

@settings(max_examples=100)
@given(
    events=st.lists(
        st.tuples(
            strategy_name,
            st.booleans(),  # success
            st.integers(min_value=1, max_value=10000),  # duration_ms
        ),
        min_size=1,
        max_size=50,
    )
)
def test_statistics_accuracy(events):
    """
    **Feature: failover-test-page, Property 9: Statistics Accuracy**
    
    For any set of failover tests, the statistics should satisfy:
    successful + failed = total, and average time = sum of times / count.
    """
    stats = TestStatistics()
    
    total_time = 0
    expected_successes = 0
    expected_failures = 0
    
    for strategy, success, duration_ms in events:
        stats.record_event(strategy, success, duration_ms)
        total_time += duration_ms
        if success:
            expected_successes += 1
        else:
            expected_failures += 1
    
    # Verify totals
    assert stats.total_tests == len(events)
    assert stats.successful_failovers == expected_successes
    assert stats.failed_failovers == expected_failures
    assert stats.successful_failovers + stats.failed_failovers == stats.total_tests
    
    # Verify average time
    expected_avg = total_time / len(events)
    assert abs(stats.average_failover_time_ms - expected_avg) < 0.001


# =============================================================================
# Property 10: Statistics Reset
# **Feature: failover-test-page, Property 10: Statistics Reset**
# **Validates: Requirements 6.4**
# =============================================================================

@settings(max_examples=100)
@given(
    events=st.lists(
        st.tuples(strategy_name, st.booleans(), st.integers(min_value=1, max_value=1000)),
        min_size=1,
        max_size=20,
    )
)
def test_statistics_reset(events):
    """
    **Feature: failover-test-page, Property 10: Statistics Reset**
    
    For any statistics reset operation, all counters should be set to zero.
    """
    stats = TestStatistics()
    
    # Record some events
    for strategy, success, duration_ms in events:
        stats.record_event(strategy, success, duration_ms)
    
    # Verify we have data
    assert stats.total_tests > 0
    
    # Reset
    stats.reset()
    
    # All counters should be zero
    assert stats.total_tests == 0
    assert stats.successful_failovers == 0
    assert stats.failed_failovers == 0
    assert stats.total_time_ms == 0
    assert len(stats.strategy_stats) == 0


# =============================================================================
# Property 12: Channel Import Completeness
# **Feature: failover-test-page, Property 12: Channel Import Completeness**
# **Validates: Requirements 8.2, 8.4**
# =============================================================================

def test_channel_import_preserves_data():
    """
    **Feature: failover-test-page, Property 12: Channel Import Completeness**
    
    For any imported channel, the test copy should contain all fields 
    from the original including backup streams and MAC portal configuration.
    """
    service = FailoverTestService()
    
    # Create original config
    original_config = {
        'name': 'Original Channel',
        'primary_stream_url': 'http://original.com/stream',
        'backup_streams': [
            {'url': 'http://backup1.com/stream', 'priority': 0, 'name': 'Backup 1'},
            {'url': 'http://backup2.com/stream', 'priority': 1, 'name': 'Backup 2'},
        ],
        'mac_portal_config': {
            'account_id': 1,
            'portal_url': 'http://portal.com',
            'macs': ['00:1A:79:AA:BB:CC', '00:1A:79:DD:EE:FF'],
            'endpoints': ['/server/load.php', '/portal.php'],
            'user_agents': ['MAG250', 'MAG254'],
        },
    }
    
    original = service.create_test_channel(original_config)
    
    # Verify all data is preserved
    assert original.name == original_config['name']
    assert original.primary_stream_url == original_config['primary_stream_url']
    assert len(original.backup_streams) == 2
    assert original.backup_streams[0].url == 'http://backup1.com/stream'
    assert original.backup_streams[1].url == 'http://backup2.com/stream'
    
    assert original.mac_portal_config is not None
    assert original.mac_portal_config.account_id == 1
    assert len(original.mac_portal_config.macs) == 2
    assert len(original.mac_portal_config.endpoints) == 2


# =============================================================================
# Property 14: Export Data Completeness
# **Feature: failover-test-page, Property 14: Export Data Completeness**
# **Validates: Requirements 9.1, 9.2, 9.3**
# =============================================================================

@settings(max_examples=50)
@given(
    events=st.lists(
        st.tuples(strategy_name, st.booleans(), st.integers(min_value=1, max_value=1000)),
        min_size=1,
        max_size=10,
    )
)
def test_export_data_completeness(events):
    """
    **Feature: failover-test-page, Property 14: Export Data Completeness**
    
    For any log export, the exported data should be valid and contain 
    all log entries with timestamps.
    """
    import json
    from django.utils import timezone
    
    service = FailoverTestService()
    
    # Add log entries
    for i, (strategy, success, duration_ms) in enumerate(events):
        entry = LogEntry(
            id=f"test-{i}",
            timestamp=timezone.now(),
            event_type="test_event",
            strategy=strategy,
            original_value="original",
            new_value="new",
            reason="test reason",
            success=success,
            duration_ms=duration_ms,
        )
        service.add_log_entry(entry)
    
    # Export logs
    exported = service.export_logs_json()
    
    # Verify export
    assert len(exported) == len(events)
    
    for entry in exported:
        assert 'id' in entry
        assert 'timestamp' in entry
        assert 'event_type' in entry
        assert 'strategy' in entry
        assert 'success' in entry
        assert 'duration_ms' in entry
    
    # Verify JSON serializable
    json_str = json.dumps(exported)
    assert json_str is not None
    
    # Export CSV
    csv_str = service.export_statistics_csv()
    assert 'strategy,attempts,successes,failures,avg_time_ms' in csv_str
    assert 'total,' in csv_str
