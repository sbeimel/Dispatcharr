/**
 * MAC Portal Page - Hauptseite mit allen MAC Portal Funktionen
 * 
 * Tabs:
 * 1. Overview - Portal-Übersicht mit Status
 * 2. Settings - Globale Einstellungen
 * 3. Failover - Failover-Konfiguration
 * 4. Health - MAC Health Dashboard
 * 5. Logs - Debug Logs
 */

import React, { useState } from 'react';
import { Box, Tabs, Title, Group, Text } from '@mantine/core';
import {
  IconDashboard,
  IconSettings,
  IconArrowsShuffle,
  IconHeartbeat,
  IconFileText,
  IconTestPipe,
  IconUsers,
  IconDownload,
} from '@tabler/icons-react';

// Import MAC Portal Components
import MACPortalOverview from '../components/mac-portal/MACPortalOverview';
import MACPortalSettings from '../components/mac-portal/MACPortalSettings';
import FailoverSettings from '../components/mac-portal/FailoverSettings';
import MACHealthDashboard from '../components/mac-portal/MACHealthDashboard';
import DebugLogViewer from '../components/mac-portal/DebugLogViewer';
import ConnectionTestWizard from '../components/mac-portal/ConnectionTestWizard';
import MACBatchOperations from '../components/mac-portal/MACBatchOperations';
import MACImportExport from '../components/mac-portal/MACImportExport';

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
            Settings
          </Tabs.Tab>
          <Tabs.Tab value="failover" leftSection={<IconArrowsShuffle size={16} />}>
            Failover
          </Tabs.Tab>
          <Tabs.Tab value="health" leftSection={<IconHeartbeat size={16} />}>
            Health
          </Tabs.Tab>
          <Tabs.Tab value="batch" leftSection={<IconUsers size={16} />}>
            Batch Ops
          </Tabs.Tab>
          <Tabs.Tab value="import-export" leftSection={<IconDownload size={16} />}>
            Import/Export
          </Tabs.Tab>
          <Tabs.Tab value="connection-test" leftSection={<IconTestPipe size={16} />}>
            Connection Test
          </Tabs.Tab>
          <Tabs.Tab value="logs" leftSection={<IconFileText size={16} />}>
            Debug Logs
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview">
          <MACPortalOverview />
        </Tabs.Panel>

        <Tabs.Panel value="settings">
          <MACPortalSettings />
        </Tabs.Panel>

        <Tabs.Panel value="failover">
          <FailoverSettings />
        </Tabs.Panel>

        <Tabs.Panel value="health">
          <MACHealthDashboard />
        </Tabs.Panel>

        <Tabs.Panel value="batch">
          <MACBatchOperations />
        </Tabs.Panel>

        <Tabs.Panel value="import-export">
          <MACImportExport />
        </Tabs.Panel>

        <Tabs.Panel value="connection-test">
          <ConnectionTestWizard />
        </Tabs.Panel>

        <Tabs.Panel value="logs">
          <DebugLogViewer />
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
};

export default MACPortalPage;
