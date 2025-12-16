/**
 * Failover Settings Component
 * 
 * Simplified failover configuration - MAC and Stream failover only.
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
  Badge,
  ThemeIcon,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconAlertCircle, 
  IconRefresh, 
  IconNetwork, 
  IconPlayerPlay,
  IconArrowRight,
} from '@tabler/icons-react';
import API from '../../api';
import MACFailoverConfig from './MACFailoverConfig';
import StreamFailoverConfig from './StreamFailoverConfig';

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
      stream: 'stream_failover_enabled',
    };
    
    const field = fieldMap[strategy];
    if (field) {
      await handleSaveSettings({ ...settings, [field]: enabled });
    }
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
        Failover automatically tries alternative configurations when errors occur.
        MAC failover is tried first, then stream failover if all MACs fail.
      </Alert>

      <Paper shadow="xs" p="md">
        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="overview">Overview</Tabs.Tab>
            <Tabs.Tab value="mac">MAC Failover</Tabs.Tab>
            <Tabs.Tab value="stream">Stream Failover</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="md">
            <Stack gap="md">
              {/* Failover Flow Visualization */}
              <Paper withBorder p="md">
                <Title order={4} mb="md">Failover Flow</Title>
                <Group gap="xs" align="center" wrap="nowrap">
                  <Paper withBorder p="sm" style={{ textAlign: 'center' }}>
                    <ThemeIcon size="lg" variant="light" color="blue" mb="xs">
                      <IconNetwork size={20} />
                    </ThemeIcon>
                    <Text size="sm" fw={500}>1. MAC Failover</Text>
                    <Text size="xs" c="dimmed">Try next MAC</Text>
                  </Paper>
                  <IconArrowRight size={20} color="gray" />
                  <Paper withBorder p="sm" style={{ textAlign: 'center' }}>
                    <ThemeIcon size="lg" variant="light" color="orange" mb="xs">
                      <IconPlayerPlay size={20} />
                    </ThemeIcon>
                    <Text size="sm" fw={500}>2. Stream Failover</Text>
                    <Text size="xs" c="dimmed">Try alt stream</Text>
                  </Paper>
                </Group>
              </Paper>

              {/* Strategy Toggles */}
              <Paper withBorder p="md">
                <Title order={4} mb="md">Failover Strategies</Title>
                <Stack gap="md">
                  <Group justify="space-between">
                    <Group>
                      <ThemeIcon size="lg" variant="light" color="blue">
                        <IconNetwork size={20} />
                      </ThemeIcon>
                      <div>
                        <Text fw={500}>MAC Failover</Text>
                        <Text size="xs" c="dimmed">
                          When a MAC fails, automatically try the next available MAC address
                        </Text>
                      </div>
                    </Group>
                    <Switch
                      checked={settings?.mac_failover_enabled}
                      onChange={(e) => handleToggleStrategy('mac', e.currentTarget.checked)}
                    />
                  </Group>

                  <Group justify="space-between">
                    <Group>
                      <ThemeIcon size="lg" variant="light" color="orange">
                        <IconPlayerPlay size={20} />
                      </ThemeIcon>
                      <div>
                        <Text fw={500}>Stream Failover</Text>
                        <Text size="xs" c="dimmed">
                          When all MACs fail, try alternative stream sources
                        </Text>
                      </div>
                    </Group>
                    <Switch
                      checked={settings?.stream_failover_enabled}
                      onChange={(e) => handleToggleStrategy('stream', e.currentTarget.checked)}
                    />
                  </Group>
                </Stack>
              </Paper>

              {/* How it works */}
              <Paper withBorder p="md">
                <Title order={4} mb="md">How Failover Works</Title>
                <Stack gap="xs">
                  <Text size="sm">
                    <Badge color="blue" size="sm" mr="xs">1</Badge>
                    When a stream request fails, the system first tries the next available MAC address.
                  </Text>
                  <Text size="sm">
                    <Badge color="blue" size="sm" mr="xs">2</Badge>
                    MACs are rotated based on health score - healthier MACs are tried first.
                  </Text>
                  <Text size="sm">
                    <Badge color="orange" size="sm" mr="xs">3</Badge>
                    If all MACs are exhausted or in cooldown, stream failover kicks in.
                  </Text>
                  <Text size="sm">
                    <Badge color="orange" size="sm" mr="xs">4</Badge>
                    Stream failover tries alternative stream sources from other providers.
                  </Text>
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

          <Tabs.Panel value="stream" pt="md">
            <StreamFailoverConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>
        </Tabs>
      </Paper>
    </Box>
  );
};

export default FailoverSettings;
