/**
 * Failover Test Page
 * 
 * Main page for testing failover mechanisms.
 * Requirements: 1.1, 1.2, 1.3
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Title,
  Grid,
  Paper,
  Stack,
  Group,
  Button,
  Badge,
  Alert,
  LoadingOverlay,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconRefresh,
  IconPlus,
  IconAlertCircle,
} from '@tabler/icons-react';
import failoverTestApi from '../../api/failoverTestApi';
import TestChannelList from './TestChannelList';
import TestChannelForm from './TestChannelForm';
import StreamSimulator from './StreamSimulator';
import LiveLogViewer from './LiveLogViewer';
import TestStatistics from './TestStatistics';
import useFailoverTestWebSocket from './hooks/useFailoverTestWebSocket';

const FailoverTestPage = () => {
  const [loading, setLoading] = useState(true);
  const [testChannels, setTestChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [showChannelForm, setShowChannelForm] = useState(false);
  const [editingChannel, setEditingChannel] = useState(null);
  const [logEntries, setLogEntries] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [settings, setSettings] = useState(null);
  const [activeSimulations, setActiveSimulations] = useState([]);

  // WebSocket connection
  const { connected } = useFailoverTestWebSocket({
    onEvent: handleWebSocketEvent,
  });

  // Load initial data
  useEffect(() => {
    loadData();
    return () => {
      // Cleanup on unmount - stop all simulations
      failoverTestApi.stopAllSimulations?.().catch(() => {});
    };
  }, []);

  // Handle WebSocket events
  function handleWebSocketEvent(event) {
    if (event.type === 'initial_state') {
      setTestChannels(event.data.test_channels || []);
      setStatistics(event.data.statistics);
      setLogEntries(event.data.recent_logs || []);
      setActiveSimulations(event.data.active_simulations || []);
      setSettings(event.data.settings);
    } else if (event.type === 'log_entry' || event.type === 'failover_event') {
      setLogEntries(prev => [event.data, ...prev].slice(0, 100));
    } else if (event.type === 'statistics_update') {
      setStatistics(event.data);
    } else if (event.type === 'simulation_started') {
      setActiveSimulations(prev => [...prev, event.data]);
    } else if (event.type === 'simulation_stopped' || event.type === 'simulation_completed') {
      setActiveSimulations(prev => 
        prev.filter(s => s.simulation_id !== event.data.simulation_id)
      );
    }
  }

  const loadData = async () => {
    setLoading(true);
    try {
      const [channelsRes, statsRes, logsRes, settingsRes] = await Promise.all([
        failoverTestApi.getFailoverTestChannels(),
        failoverTestApi.getFailoverTestStatistics(),
        failoverTestApi.getFailoverTestLogs(),
        failoverTestApi.getFailoverTestSettings(),
      ]);
      
      setTestChannels(channelsRes || []);
      setStatistics(statsRes);
      setLogEntries(logsRes || []);
      setSettings(settingsRes);
    } catch (error) {
      console.error('Failed to load data:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load failover test data',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChannel = async (channelData) => {
    try {
      const channel = await failoverTestApi.createFailoverTestChannel(channelData);
      setTestChannels(prev => [...prev, channel]);
      setShowChannelForm(false);
      notifications.show({
        title: 'Success',
        message: 'Test channel created',
        color: 'green',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to create test channel',
        color: 'red',
      });
    }
  };

  const handleDeleteChannel = async (channelId) => {
    try {
      await failoverTestApi.deleteFailoverTestChannel(channelId);
      setTestChannels(prev => prev.filter(c => c.id !== channelId));
      if (selectedChannel?.id === channelId) {
        setSelectedChannel(null);
      }
      notifications.show({
        title: 'Success',
        message: 'Test channel deleted',
        color: 'green',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete test channel',
        color: 'red',
      });
    }
  };

  const handleInterrupt = async (channelId, errorType) => {
    try {
      const result = await failoverTestApi.simulateFailoverInterrupt(channelId, errorType);
      if (result.event) {
        setLogEntries(prev => [result.event, ...prev].slice(0, 100));
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to simulate interruption',
        color: 'red',
      });
    }
  };

  const handleStartAutoSimulation = async (channelId, config) => {
    try {
      await failoverTestApi.startFailoverAutoSimulation(channelId, config);
      notifications.show({
        title: 'Started',
        message: 'Auto-simulation started',
        color: 'blue',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to start auto-simulation',
        color: 'red',
      });
    }
  };

  const handleStopSimulation = async (simulationId) => {
    try {
      await failoverTestApi.stopFailoverSimulation(simulationId);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to stop simulation',
        color: 'red',
      });
    }
  };

  const handleResetStatistics = async () => {
    try {
      await failoverTestApi.resetFailoverTestStatistics();
      setStatistics({
        total_tests: 0,
        successful_failovers: 0,
        failed_failovers: 0,
        average_failover_time_ms: 0,
        strategy_stats: {},
      });
      setLogEntries([]);
      notifications.show({
        title: 'Reset',
        message: 'Statistics reset',
        color: 'blue',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to reset statistics',
        color: 'red',
      });
    }
  };

  const handleExportLogs = async () => {
    try {
      const blob = await failoverTestApi.exportFailoverTestLogs();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'failover_test_logs.json';
      a.click();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to export logs',
        color: 'red',
      });
    }
  };

  const handleExportStatistics = async () => {
    try {
      const blob = await failoverTestApi.exportFailoverTestStatistics();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'failover_test_statistics.csv';
      a.click();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to export statistics',
        color: 'red',
      });
    }
  };

  if (loading) {
    return (
      <Box pos="relative" h={400}>
        <LoadingOverlay visible={true} />
      </Box>
    );
  }

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Group>
          <Title order={2}>Failover Test</Title>
          <Badge color={connected ? 'green' : 'red'} variant="dot">
            {connected ? 'Connected' : 'Disconnected'}
          </Badge>
        </Group>
        <Group>
          <Button
            variant="outline"
            leftSection={<IconRefresh size={16} />}
            onClick={loadData}
          >
            Refresh
          </Button>
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={() => setShowChannelForm(true)}
          >
            New Test Channel
          </Button>
        </Group>
      </Group>

      <Alert icon={<IconAlertCircle size={16} />} color="blue" mb="md">
        Test your failover configuration by creating test channels and simulating
        stream interruptions. Watch the live log to see failover events in real-time.
      </Alert>

      <Grid>
        {/* Left Column - Channels and Simulator */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Stack gap="md">
            <Paper shadow="xs" p="md">
              <TestChannelList
                channels={testChannels}
                selectedChannel={selectedChannel}
                onSelect={setSelectedChannel}
                onDelete={handleDeleteChannel}
                onEdit={(ch) => {
                  setEditingChannel(ch);
                  setShowChannelForm(true);
                }}
              />
            </Paper>

            {selectedChannel && (
              <Paper shadow="xs" p="md">
                <StreamSimulator
                  channel={selectedChannel}
                  activeSimulations={activeSimulations}
                  onInterrupt={handleInterrupt}
                  onStartAuto={handleStartAutoSimulation}
                  onStop={handleStopSimulation}
                />
              </Paper>
            )}

            <Paper shadow="xs" p="md">
              <TestStatistics
                statistics={statistics}
                onReset={handleResetStatistics}
                onExport={handleExportStatistics}
              />
            </Paper>
          </Stack>
        </Grid.Col>

        {/* Right Column - Live Log */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper shadow="xs" p="md" h="100%">
            <LiveLogViewer
              entries={logEntries}
              onExport={handleExportLogs}
            />
          </Paper>
        </Grid.Col>
      </Grid>

      {/* Channel Form Modal */}
      {showChannelForm && (
        <TestChannelForm
          channel={editingChannel}
          onSave={handleCreateChannel}
          onClose={() => {
            setShowChannelForm(false);
            setEditingChannel(null);
          }}
        />
      )}
    </Box>
  );
};

export default FailoverTestPage;
