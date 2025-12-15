/**
 * MAC Import/Export Component
 * 
 * Import and export MAC addresses.
 * Requirements: 51.1, 51.2, 51.3, 51.4
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Modal,
  Tabs,
  Textarea,
  Button,
  Group,
  Text,
  Stack,
  Paper,
  Checkbox,
  Code,
  CopyButton,
  ActionIcon,
  Tooltip,
  Alert,
  Select,
  LoadingOverlay,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconUpload, IconDownload, IconCopy, IconCheck, IconAlertCircle } from '@tabler/icons-react';
import API from '../../api';

const MACImportExport = ({ accountId, opened = true, onClose, onImportComplete }) => {
  const [activeTab, setActiveTab] = useState('import');
  const [importText, setImportText] = useState('');
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportData, setExportData] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [portals, setPortals] = useState([]);
  const [selectedPortal, setSelectedPortal] = useState(accountId || null);
  const [loading, setLoading] = useState(!accountId);

  // Fetch portals if not provided
  useEffect(() => {
    if (!accountId) {
      fetchPortals();
    }
  }, [accountId]);

  const fetchPortals = async () => {
    setLoading(true);
    try {
      const token = await API.getAuthToken();
      const response = await fetch('/api/mac-portal/overview/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPortals(data.portals || []);
        if (data.portals?.length > 0) {
          setSelectedPortal(data.portals[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch portals:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentAccountId = accountId || selectedPortal;

  const handleImport = async () => {
    if (!currentAccountId) {
      notifications.show({
        title: 'Warning',
        message: 'Please select a portal first',
        color: 'yellow',
      });
      return;
    }

    if (!importText.trim()) {
      notifications.show({
        title: 'Warning',
        message: 'Please enter MAC addresses to import',
        color: 'yellow',
      });
      return;
    }

    setImporting(true);
    setImportResult(null);

    try {
      // Parse MAC addresses from text (one per line or comma-separated)
      const lines = importText.split(/[\n,]/).map(l => l.trim()).filter(l => l);
      const macs = lines.map(address => ({ address }));

      const result = await API.importMACs(currentAccountId, macs, replaceExisting);
      setImportResult(result);

      notifications.show({
        title: 'Import Complete',
        message: `Imported ${result.imported} MAC addresses`,
        color: result.errors?.length > 0 ? 'yellow' : 'green',
      });

      if (result.imported > 0) {
        onImportComplete?.();
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to import MAC addresses',
        color: 'red',
      });
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async () => {
    if (!currentAccountId) {
      notifications.show({
        title: 'Warning',
        message: 'Please select a portal first',
        color: 'yellow',
      });
      return;
    }

    setExporting(true);

    try {
      const data = await API.exportMACs(currentAccountId);
      setExportData(data);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to export MAC addresses',
        color: 'red',
      });
    } finally {
      setExporting(false);
    }
  };

  const getExportText = () => {
    if (!exportData?.macs) return '';
    return exportData.macs.map(m => m.address).join('\n');
  };

  const getExportJSON = () => {
    if (!exportData) return '';
    return JSON.stringify(exportData, null, 2);
  };

  const handleDownload = (format) => {
    if (!exportData) return;

    let content, filename, type;
    if (format === 'txt') {
      content = getExportText();
      filename = `macs_${currentAccountId}.txt`;
      type = 'text/plain';
    } else {
      content = getExportJSON();
      filename = `macs_${currentAccountId}.json`;
      type = 'application/json';
    }

    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  // If used as standalone component (not in modal)
  const content = (
    <Box pos="relative">
      <LoadingOverlay visible={loading} />
      
      {!accountId && portals.length > 0 && (
        <Select
          label="Select Portal"
          placeholder="Choose a portal"
          value={selectedPortal?.toString()}
          onChange={(val) => setSelectedPortal(val ? parseInt(val) : null)}
          data={portals.map(p => ({ value: p.id.toString(), label: p.name }))}
          mb="md"
        />
      )}

      {!accountId && portals.length === 0 && !loading && (
        <Alert color="blue" mb="md">
          No MAC portals configured. Add a MAC/STB portal account first.
        </Alert>
      )}

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="import" leftSection={<IconUpload size={14} />}>
            Import
          </Tabs.Tab>
          <Tabs.Tab value="export" leftSection={<IconDownload size={14} />}>
            Export
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="import" pt="md">
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Enter MAC addresses, one per line or comma-separated.
            </Text>

            <Textarea
              placeholder="00:1A:79:XX:XX:XX&#10;00:1A:79:YY:YY:YY&#10;..."
              minRows={8}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />

            <Checkbox
              label="Replace existing MAC addresses"
              description="If checked, all existing MACs will be removed before import"
              checked={replaceExisting}
              onChange={(e) => setReplaceExisting(e.currentTarget.checked)}
            />

            {importResult && (
              <Alert 
                color={importResult.errors?.length > 0 ? 'yellow' : 'green'}
                icon={importResult.errors?.length > 0 ? <IconAlertCircle /> : <IconCheck />}
              >
                <Text size="sm">
                  Imported: {importResult.imported} MAC addresses
                </Text>
                {importResult.errors?.length > 0 && (
                  <Text size="xs" c="dimmed" mt="xs">
                    Errors: {importResult.errors.map(e => e.address).join(', ')}
                  </Text>
                )}
              </Alert>
            )}

            <Group justify="flex-end">
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button 
                onClick={handleImport} 
                loading={importing}
                leftSection={<IconUpload size={16} />}
              >
                Import
              </Button>
            </Group>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="export" pt="md">
          <Stack gap="md">
            {!exportData ? (
              <>
                <Text size="sm" c="dimmed">
                  Export all MAC addresses from this account.
                </Text>
                <Button 
                  onClick={handleExport} 
                  loading={exporting}
                  leftSection={<IconDownload size={16} />}
                >
                  Load Export Data
                </Button>
              </>
            ) : (
              <>
                <Paper withBorder p="sm">
                  <Group justify="space-between" mb="xs">
                    <Text size="sm" fw={500}>
                      {exportData.mac_count} MAC addresses
                    </Text>
                    <Group gap="xs">
                      <CopyButton value={getExportText()}>
                        {({ copied, copy }) => (
                          <Tooltip label={copied ? 'Copied' : 'Copy'}>
                            <ActionIcon 
                              color={copied ? 'green' : 'gray'} 
                              variant="subtle"
                              onClick={copy}
                            >
                              {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                            </ActionIcon>
                          </Tooltip>
                        )}
                      </CopyButton>
                    </Group>
                  </Group>
                  <Code block mah={200} style={{ overflow: 'auto' }}>
                    {getExportText()}
                  </Code>
                </Paper>

                <Group justify="flex-end">
                  <Button 
                    variant="outline" 
                    onClick={() => handleDownload('txt')}
                    leftSection={<IconDownload size={16} />}
                  >
                    Download TXT
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => handleDownload('json')}
                    leftSection={<IconDownload size={16} />}
                  >
                    Download JSON
                  </Button>
                </Group>
              </>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Box>
  );

  // If opened prop is provided, wrap in Modal
  if (typeof opened !== 'undefined' && onClose) {
    return (
      <Modal
        opened={opened}
        onClose={onClose}
        title="Import / Export MAC Addresses"
        size="lg"
      >
        {content}
      </Modal>
    );
  }

  // Otherwise render as standalone component
  return content;
};

export default MACImportExport;
