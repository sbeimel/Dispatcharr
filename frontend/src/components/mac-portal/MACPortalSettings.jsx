/**
 * MAC Portal Settings Component
 * 
 * Main settings page for MAC Portal configuration.
 * Requirements: 44.1, 44.2
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Title,
  Tabs,
  LoadingOverlay,
  Paper,
  Group,
  Button,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import API from '../../api';
import TimeoutRetryConfig from './TimeoutRetryConfig';
import CooldownConfig from './CooldownConfig';
import FeatureToggles from './FeatureToggles';
import StreamPerformanceSettings from './StreamPerformanceSettings';

const MACPortalSettings = () => {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('features');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await API.getMACPortalSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to fetch MAC Portal settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load MAC Portal settings',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (updatedSettings) => {
    try {
      const data = await API.updateMACPortalSettings(updatedSettings);
      setSettings(data);
      notifications.show({
        title: 'Success',
        message: 'Settings saved successfully',
        color: 'green',
      });
    } catch (error) {
      console.error('Failed to save settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to save settings',
        color: 'red',
      });
    }
  };

  const handleResetSettings = async () => {
    try {
      const data = await API.resetMACPortalSettings();
      setSettings(data);
      notifications.show({
        title: 'Success',
        message: 'Settings reset to defaults',
        color: 'blue',
      });
    } catch (error) {
      console.error('Failed to reset settings:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to reset settings',
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
        <Title order={2}>MAC Portal Settings</Title>
        <Button variant="outline" color="gray" onClick={handleResetSettings}>
          Reset to Defaults
        </Button>
      </Group>

      <Paper shadow="xs" p="md">
        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="features">Features & Engine</Tabs.Tab>
            <Tabs.Tab value="performance">Stream Performance</Tabs.Tab>
            <Tabs.Tab value="timeouts">Timeouts & Retries</Tabs.Tab>
            <Tabs.Tab value="cooldowns">Cooldowns</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="timeouts" pt="md">
            <TimeoutRetryConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="cooldowns" pt="md">
            <CooldownConfig 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="features" pt="md">
            <FeatureToggles 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>

          <Tabs.Panel value="performance" pt="md">
            <StreamPerformanceSettings 
              settings={settings} 
              onSave={handleSaveSettings} 
            />
          </Tabs.Panel>
        </Tabs>
      </Paper>
    </Box>
  );
};

export default MACPortalSettings;
