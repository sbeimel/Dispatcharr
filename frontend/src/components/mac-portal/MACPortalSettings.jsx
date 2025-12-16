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
  Stack,
  Group,
  Button,
  Text,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import API from '../../api';
import TimeoutRetryConfig from './TimeoutRetryConfig';
import CooldownConfig from './CooldownConfig';
import FeatureToggles from './FeatureToggles';

const MACPortalSettings = () => {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('general');

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
            <Tabs.Tab value="general">General</Tabs.Tab>
            <Tabs.Tab value="timeouts">Timeouts & Retries</Tabs.Tab>
            <Tabs.Tab value="cooldowns">Cooldowns</Tabs.Tab>
            <Tabs.Tab value="features">Features</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="general" pt="md">
            <Stack gap="md">
              <Text size="sm" c="dimmed">
                Configure general MAC Portal settings. These settings apply globally
                to all MAC/STB Portal accounts.
              </Text>
              
              <Paper withBorder p="md">
                <Title order={4} mb="sm">About MAC Portal Settings</Title>
                <Text size="sm" c="dimmed" mb="sm">
                  These global settings control how Dispatcharr connects to MAC/STB portals.
                  Changes here affect all MAC portal accounts.
                </Text>
                <Stack gap="xs">
                  <Text size="sm">• <strong>Timeouts & Retries:</strong> Connection and read timeouts, retry behavior</Text>
                  <Text size="sm">• <strong>Cooldowns:</strong> How long to wait after failures before retrying</Text>
                  <Text size="sm">• <strong>Features:</strong> Enable/disable VOD, Series, EPG, Cloudscraper, etc.</Text>
                  <Text size="sm">• <strong>Portal Engine:</strong> Select authentication strategy (Auto, Fastest, specific engines)</Text>
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>

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
        </Tabs>
      </Paper>
    </Box>
  );
};

export default MACPortalSettings;
