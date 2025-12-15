/**
 * MAC Portal Page - Hauptseite mit allen MAC Portal Funktionen
 * 
 * Tabs:
 * 1. Overview - Portal-Übersicht mit Status (inkl. Health-Infos)
 * 2. MAC Portal Settings - Globale Einstellungen
 * 3. Failover - Failover-Konfiguration
 * 4. Batch Ops - Batch-Operationen für angelegte Portale/MACs
 * 5. Connection Test - Verbindungstest
 * 6. Debug Logs - Debug Logs
 */

import React, { useState } from 'react';
import { Box, Tabs, Title, Group, Text } from '@mantine/core';
import { 
  IconDashboard,
  IconSettings,
  IconArrowsShuffle,
  IconFileText,
  IconTestPipe,
  IconUsers,
} from '@tabler/icons-react';

// Import MAC Portal Components
import MACPortalOverview from '../components/mac-portal/MACPortalOverview';
import MACPortalSettings from '../components/mac-portal/MACPortalSettings';
import FailoverSettings from '../components/mac-portal/FailoverSettings';
import DebugLogViewer from '../components/mac-portal/DebugLogViewer';
import ConnectionTestWizard from '../components/mac-portal/ConnectionTestWizard';
import MACBatchOperations from '../components/mac-portal/MACBatchOperations';

const MACPortalPage = () => {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <Box p="md">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>MAC Portal Management</Title>
          <Text c="dimmed" size="sm">
            Verwalte MAC Portale, Failover-Einstellungen und Health-Monitoring
          </Text>
        </div>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="overview" leftSection={<IconDashboard size={16} />}>
            Overview
          </Tabs.Tab>
          <Tabs.Tab value="settings" leftSection={<IconSettings size={16} />}>
            MAC Portal Settings
          </Tabs.Tab>
          <Tabs.Tab value="failover" leftSection={<IconArrowsShuffle size={16} />}>
            Failover
          </Tabs.Tab>
          <Tabs.Tab value="batch" leftSection={<IconUsers size={16} />}>
            Batch Ops
          </Tabs.Tab>
          <Tabs.Tab value="connection-test" leftSection={<IconTestPipe size={16} />}>
            Connection Test
          </Tabs.Tab>
          <Tabs.Tab value="logs" leftSection={<IconFileText size={16} />}>
            Debug Logs
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

        <Tabs.Panel value="batch" pt="xs">
          <MACBatchOperations />
        </Tabs.Panel>

        <Tabs.Panel value="connection-test" pt="xs">
          <ConnectionTestWizard />
        </Tabs.Panel>

        <Tabs.Panel value="logs" pt="xs">
          <DebugLogViewer />
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
};

export default MACPortalPage;
