/**
 * Predictive Failover Page - Hauptseite mit allen Predictive Failover Funktionen
 * 
 * Tabs:
 * 1. Dashboard - Echtzeit-Übersicht
 * 2. Settings - Konfiguration
 * 3. Patterns - Pattern-Analyse
 * 4. Provider Health - Provider-Status
 * 5. Analytics - Statistiken
 */

import React, { useState } from 'react';
import { Box, Tabs, Title, Group, Text } from '@mantine/core';
import {
  IconDashboard,
  IconSettings,
  IconChartLine,
  IconHeartbeat,
  IconBrain,
  IconActivity,
} from '@tabler/icons-react';

// Import Predictive Failover Components
import PredictiveFailoverDashboard from '../components/predictive-failover/PredictiveFailoverDashboard';
import PredictiveFailoverSettings from '../components/predictive-failover/PredictiveFailoverSettings';
import PatternManagement from '../components/predictive-failover/PatternManagement';
import ProviderHealthDashboard from '../components/predictive-failover/ProviderHealthDashboard';
import AnalyticsDashboard from '../components/predictive-failover/AnalyticsDashboard';
import StreamPredictiveSettings from '../components/predictive-failover/StreamPredictiveSettings';

const PredictiveFailoverPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <Box p="md">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Predictive Failover</Title>
          <Text c="dimmed" size="sm">
            KI-gestütztes vorausschauendes Failover mit Pattern-Analyse
          </Text>
        </div>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="dashboard" leftSection={<IconDashboard size={16} />}>
            Dashboard
          </Tabs.Tab>
          <Tabs.Tab value="settings" leftSection={<IconSettings size={16} />}>
            Settings
          </Tabs.Tab>
          <Tabs.Tab value="patterns" leftSection={<IconBrain size={16} />}>
            Patterns
          </Tabs.Tab>
          <Tabs.Tab value="provider-health" leftSection={<IconHeartbeat size={16} />}>
            Provider Health
          </Tabs.Tab>
          <Tabs.Tab value="stream-settings" leftSection={<IconActivity size={16} />}>
            Stream Settings
          </Tabs.Tab>
          <Tabs.Tab value="analytics" leftSection={<IconChartLine size={16} />}>
            Analytics
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="dashboard">
          <PredictiveFailoverDashboard />
        </Tabs.Panel>

        <Tabs.Panel value="settings">
          <PredictiveFailoverSettings />
        </Tabs.Panel>

        <Tabs.Panel value="patterns">
          <PatternManagement />
        </Tabs.Panel>

        <Tabs.Panel value="provider-health">
          <ProviderHealthDashboard />
        </Tabs.Panel>

        <Tabs.Panel value="stream-settings">
          <StreamPredictiveSettings />
        </Tabs.Panel>

        <Tabs.Panel value="analytics">
          <AnalyticsDashboard />
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
};

export default PredictiveFailoverPage;
