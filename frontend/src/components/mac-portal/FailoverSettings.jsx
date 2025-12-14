/**
 * Failover Settings Component
 * 
 * Main page for configuring failover strategies.
 * Requirements: 55.1, 55.2, 55.3, 55.4
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Title,
  Tabs,
  LoadingOverlay,
  Paper,
  Stack,
  Group,
  Button,
  Text,
  Switch,
  Alert,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertCircle, IconRefresh } from '@tabler/icons-react';
import API from '../../api';
import MACFailoverConfig from './MACFailoverConfig';
import PortalFailoverConfig from './PortalFailoverConfig';
import StreamFailoverConfig from './StreamFailoverConfig';
import UserAgentFailoverConfig from './UserAgentFailoverConfig';
import FailoverPriorityList from './FailoverPriorityList';

const FailoverSettings = () => {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await API.getFailoverSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to fetch failover settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load failover settings',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (updatedSettings) => {
    try {
      const data = await API.updateFailoverSettings(updatedSettings);
      setSettings(data);
      notifications.show({
        title: 'Success',
        message: 'Failover settings saved successfully',
        color: 'green',
      });
    } catch (error) {
      console.error('Failed to save failover settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to save failover settings',
        color: 'red',
      });
    }
  };

  const handleToggleStrategy = async (strategy, enabled) => {
    const fieldMap = {
      mac: 'mac_failover_enabled',
      portal: 'portal_failover_enabled',
      stream: 'stream_failover_enabled',
      endpoint: 'endpoint_failover_enabled',
      useragent: 'useragent_failover_enabled',
    };
    
    const field = fieldMap[strategy];
    if (field) {
      await handleSaveSettings({ ...settings, [field]: enabled });
    }
  };

  const handlePriorityChange = async (newPriority) => {
    await handleSaveSettings({ ...settings, failover_priority: newPriority });
  };

  const handleResetSettings = async () => {
    try {
      const data = await API.resetFailoverSettings();
      setSettings(data);
      notifications.show({
        title: 'Success',
        message: 'Failover settings reset to defaults',
        color: 'blue',
      });
    } catch (error) {
      console.error('Failed to reset failover settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to reset failover settings',
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

  const strategies = [
    { key: 'mac', label: 'MAC Failover', enabled: settings?.mac_failover_enabled },
    { key: 'portal', label: 'Portal Failover', enabled: settings?.portal_failover_enabled },
    { key: 'stream', label: 'Stream Failover', enabled: settings?.stream_failover_enabled },
    { key: 'endpoint', label: 'Endpoint Failover', enabled: settings?.endpoint_failover_enabled },
    { key: 'useragent', label: 'User-Agent Failover', enabled: settings?.useragent_failover_enabled },
  ];

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Title order={2}>Failover Configuration</Title>
        <Group>
          <Button 
            variant="outline" 
            leftSection={<IconRefresh size={16} />}
            onClick={fetchSettings}
          >
            Refresh
          </Button>
          <Button variant="outline" color="gray" onClick={handleResetSettings}>
            Reset to Defaults
          </Button>
        </Group>
      </Group>

      <Alert icon={<IconAlertCircle size={16} />} color="blue" mb="md">
        Failover strategies help maintain stream availability by automatically
        trying alternative configurations when errors occur.
      </Alert>

      <Paper shadow="xs" p="md">
        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="overview">Overview</Tabs.Tab>
            <Tabs.Tab value="mac">MAC</Tabs.Tab>
            <Tabs.Tab value="portal">Portal/Endpoint</Tabs.Tab>
            <Tabs.Tab value="stream">Stream</Tabs.Tab>
            <Tabs.Tab value="useragent">User-Agent</Tabs.Tab>
            <Tabs.Tab value="priority">Priority</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="md">
            <Stack gap="md">
              <Text size="sm" c="dimmed">
                Enable or disable individual failover strategies. When a strategy
                is enabled, the system will automatically try alternatives when
                errors occur.
              </Text>
              
              <Paper withBorder p="md">
                <Title order={4} mb="md">Failover Strategies</Title>
                <Stack gap="sm">
                  {strategies.map((strategy) => (
                    <Group key={strategy.key} justify="space-between">
                      <div>
                        <Text fw={500}>{strategy.label}</Text>
                        <Text size="xs" c="dimmed">
                          {getStrategyDescription(strategy.key)}
                        </Text>
                      </div>
                      <Switch
                        checked={strategy.enabled}
                        onChange={(e) => handleToggleStrategy(strategy.key, e.currentTarget.checked)}
                      />
                    </Group>
                  ))}
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="mac" pt="md">
            <MACFailoverConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="portal" pt="md">
            <PortalFailoverConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="stream" pt="md">
            <StreamFailoverConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="useragent" pt="md">
            <UserAgentFailoverConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="priority" pt="md">
            <FailoverPriorityList 
              priority={settings?.failover_priority || ['mac', 'useragent', 'endpoint', 'stream']}
              onPriorityChange={handlePriorityChange}
            />
          </Tabs.Panel>
        </Tabs>
      </Paper>
    </Box>
  );
};

const getStrategyDescription = (key) => {
  const descriptions = {
    mac: 'Try different MAC addresses when authentication fails',
    portal: 'Switch to backup portal URLs on connection errors',
    stream: 'Validate streams and retry with alternatives on failure',
    endpoint: 'Try different API endpoints (/server/load.php, /portal.php, etc.)',
    useragent: 'Rotate User-Agent strings on specific errors',
  };
  return descriptions[key] || '';
};

export default FailoverSettings;
