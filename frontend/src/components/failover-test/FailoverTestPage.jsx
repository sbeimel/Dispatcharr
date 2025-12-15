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
  Tabs,
  Modal,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconRefresh,
  IconPlus,
  IconAlertCircle,
  IconDeviceTv,
  IconList,
  IconTestPipe,
} from '@tabler/icons-react';
import failoverTestApi from '../../api/failoverTestApi';
import TestChannelList from './TestChannelList';
import TestChannelForm from './TestChannelForm';
import StreamSimulator from './StreamSimulator';
import LiveLogViewer from './LiveLogViewer';
import TestStatistics from './TestStatistics';
import RealChannelBrowser from './RealChannelBrowser';
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
  const [activeTab, setActiveTab] = useState('test');
  const [showBrowserModal, setShowBrowserModal] = useState(false);

  // Handle WebSocket events - use useCallback to prevent reconnection loops
  const handleWebSocketEvent = React.useCallback((event) => {
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
  }, []);

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

  // Handle importing channels from the browser
  const handleImportFromBrowser = async (channelsToImport) => {
    try {
      for (const channel of channelsToImport) {
        await failoverTestApi.importChannelForTest(channel.id);
      }
      notifications.show({
        title: 'Success',
        message: `Imported ${channelsToImport.length} channel(s)`,
        color: 'green',
      });
      loadData();
      setShowBrowserModal(false);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to import channels',
        color: 'red',
      });
    }
  };

  // Handle creating test from channel/stream
  const handleCreateTestFromChannel = async (channelData) => {
    setEditingChannel(null);
    // Pre-fill the form with channel data
    const prefillData = {
      name: channelData.name,
      primary_stream_url: channelData.primary_stream_url || channelData.url || '',
      original_channel_id: channelData.id,
    };
    setEditingChannel(prefillData);
    setShowChannelForm(true);
    setShowBrowserModal(false);
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
            variant="outline"
            leftSection={<IconDeviceTv size={16} />}
            onClick={() => setShowBrowserModal(true)}
          >
            Browse Channels
          </Button>
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={() => setShowChannelForm(true)}
          >
            New Test Channel
          </Button>
        </Group>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab} mb="md">
        <Tabs.List>
          <Tabs.Tab value="test" leftSection={<IconTestPipe size={14} />}>
            Test Environment
          </Tabs.Tab>
          <Tabs.Tab value="channels" leftSection={<IconDeviceTv size={14} />}>
            Real Channels & Streams
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="test" pt="md">
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
        </Tabs.Panel>

        <Tabs.Panel value="channels" pt="md">
          <Paper shadow="xs" p="md">
            <RealChannelBrowser
              onImportChannel={handleImportFromBrowser}
              onCreateTestFromChannel={handleCreateTestFromChannel}
            />
          </Paper>
        </Tabs.Panel>
      </Tabs>

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

      {/* Channel Browser Modal */}
      <Modal
        opened={showBrowserModal}
        onClose={() => setShowBrowserModal(false)}
        title="Browse Channels & Streams"
        size="xl"
      >
        <RealChannelBrowser
          onImportChannel={handleImportFromBrowser}
          onCreateTestFromChannel={handleCreateTestFromChannel}
        />
      </Modal>
    </Box>
  );
};

export default FailoverTestPage;
