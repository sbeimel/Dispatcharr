/**
 * MAC Portal Page - Hauptseite mit allen MAC Portal Funktionen
 * 
 * Tabs:
 * 1. Overview - Portal-Übersicht mit Status (inkl. Health-Infos, Benchmark)
 * 2. MAC Portal Settings - Globale Einstellungen
 * 3. Failover - Failover-Konfiguration
 */

import React, { useState } from 'react';
import { Box, Tabs, Title, Group, Text } from '@mantine/core';
import { 
  IconDashboard,
  IconSettings,
  IconArrowsShuffle,
} from '@tabler/icons-react';

// Import MAC Portal Components
import MACPortalOverview from '../components/mac-portal/MACPortalOverview';
import MACPortalSettings from '../components/mac-portal/MACPortalSettings';
import FailoverSettings from '../components/mac-portal/FailoverSettings';

const MACPortalPage = () => {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <Box p="md">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Advanced Settings</Title>
          <Text c="dimmed" size="sm">
            Configure MAC Portal settings, failover behavior, and performance tuning
          </Text>
        </div>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="overview" leftSection={<IconDashboard size={16} />}>
            Overview
          </Tabs.Tab>
          <Tabs.Tab value="settings" leftSection={<IconSettings size={16} />}>
            Settings
          </Tabs.Tab>
          <Tabs.Tab value="failover" leftSection={<IconArrowsShuffle size={16} />}>
            Failover
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview" pt="xs">
          <MACPortalOverview />
        </Tabs.Panel>

        <Tabs.Panel value="settings" pt="xs">
          <MACPortalSettings />
        </Tabs.Panel>

        <Tabs.Panel value="failover" pt="xs">
          <FailoverSettings />
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
};

export default MACPortalPage;
