/**
 * MAC Batch Operations Component
 * 
 * Multi-select and batch actions for MAC addresses.
 * Requirements: 50.1, 50.2, 50.3, 50.4
 */

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Table,
  Checkbox,
  Group,
  Button,
  Text,
  Badge,
  Menu,
  ActionIcon,
  Progress,
  Modal,
  Stack,
  LoadingOverlay,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconDotsVertical, 
  IconPlayerPlay, 
  IconPlayerPause,
  IconTrash,
  IconRefresh,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import API from '../../api';

const MACBatchOperations = ({ accountId, macs, onRefresh }) => {
  const [selectedMacs, setSelectedMacs] = useState([]);
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState([]);
  const [showResults, setShowResults] = useState(false);

  const toggleSelectAll = () => {
    if (selectedMacs.length === macs.length) {
      setSelectedMacs([]);
    } else {
      setSelectedMacs(macs.map(m => m.id));
    }
  };

  const toggleSelect = (macId) => {
    if (selectedMacs.includes(macId)) {
      setSelectedMacs(selectedMacs.filter(id => id !== macId));
    } else {
      setSelectedMacs([...selectedMacs, macId]);
    }
  };

  const handleBatchTest = async () => {
    if (selectedMacs.length === 0) {
      notifications.show({
        title: 'Warning',
        message: 'Please select at least one MAC address',
        color: 'yellow',
      });
      return;
    }

    setTesting(true);
    setTestResults([]);
    setShowResults(true);

    try {
      const results = await API.batchTestMACs(accountId, selectedMacs);
      setTestResults(results.results || []);
      
      const successCount = results.results?.filter(r => r.success).length || 0;
      notifications.show({
        title: 'Test Complete',
        message: `${successCount}/${results.results?.length || 0} MACs passed`,
        color: successCount === results.results?.length ? 'green' : 'yellow',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Batch test failed',
        color: 'red',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleBatchEnable = async () => {
    if (selectedMacs.length === 0) return;

    try {
      await API.batchEnableMACs(accountId, selectedMacs);
      notifications.show({
        title: 'Success',
        message: `${selectedMacs.length} MACs enabled`,
        color: 'green',
      });
      onRefresh?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to enable MACs',
        color: 'red',
      });
    }
  };

  const handleBatchDisable = async () => {
    if (selectedMacs.length === 0) return;

    try {
      await API.batchDisableMACs(accountId, selectedMacs);
      notifications.show({
        title: 'Success',
        message: `${selectedMacs.length} MACs disabled`,
        color: 'green',
      });
      onRefresh?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to disable MACs',
        color: 'red',
      });
    }
  };

  const handleBatchResetCooldown = async () => {
    if (selectedMacs.length === 0) return;

    try {
      for (const macId of selectedMacs) {
        await API.resetMACCooldown(accountId, macId);
      }
      notifications.show({
        title: 'Success',
        message: `Cooldown reset for ${selectedMacs.length} MACs`,
        color: 'green',
      });
      onRefresh?.();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to reset cooldowns',
        color: 'red',
      });
    }
  };

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {selectedMacs.length} of {macs.length} selected
          </Text>
        </Group>
        <Group gap="xs">
          <Button 
            size="xs" 
            variant="outline"
            onClick={handleBatchTest}
            disabled={selectedMacs.length === 0}
            loading={testing}
          >
            Test Selected
          </Button>
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <Button 
                size="xs" 
                variant="outline"
                disabled={selectedMacs.length === 0}
              >
                Batch Actions
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item 
                leftSection={<IconPlayerPlay size={14} />}
                onClick={handleBatchEnable}
              >
                Enable Selected
              </Menu.Item>
              <Menu.Item 
                leftSection={<IconPlayerPause size={14} />}
                onClick={handleBatchDisable}
              >
                Disable Selected
              </Menu.Item>
              <Menu.Item 
                leftSection={<IconRefresh size={14} />}
                onClick={handleBatchResetCooldown}
              >
                Reset Cooldowns
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      <Paper withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={40}>
                <Checkbox
                  checked={selectedMacs.length === macs.length && macs.length > 0}
                  indeterminate={selectedMacs.length > 0 && selectedMacs.length < macs.length}
                  onChange={toggleSelectAll}
                />
              </Table.Th>
              <Table.Th>MAC Address</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Health</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {macs.map((mac) => (
              <Table.Tr key={mac.id}>
                <Table.Td>
                  <Checkbox
                    checked={selectedMacs.includes(mac.id)}
                    onChange={() => toggleSelect(mac.id)}
                  />
                </Table.Td>
                <Table.Td>
                  <Text size="sm" ff="monospace">{mac.address}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge 
                    color={mac.status === 'valid' ? 'green' : mac.status === 'expired' ? 'red' : 'gray'}
                    size="sm"
                  >
                    {mac.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Progress 
                    value={mac.health_score || 50} 
                    size="sm" 
                    w={60}
                    color={mac.health_score >= 80 ? 'green' : mac.health_score >= 50 ? 'yellow' : 'red'}
                  />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={showResults}
        onClose={() => setShowResults(false)}
        title="Batch Test Results"
        size="lg"
      >
        <Box pos="relative" mih={200}>
          <LoadingOverlay visible={testing} />
          
          {testResults.length > 0 && (
            <Stack gap="xs">
              {testResults.map((result, index) => (
                <Paper key={index} withBorder p="sm">
                  <Group justify="space-between">
                    <Group gap="xs">
                      {result.success ? (
                        <IconCheck size={16} color="green" />
                      ) : (
                        <IconX size={16} color="red" />
                      )}
                      <Text size="sm" ff="monospace">{result.address}</Text>
                    </Group>
                    <Group gap="xs">
                      {result.duration_ms && (
                        <Text size="xs" c="dimmed">{result.duration_ms}ms</Text>
                      )}
                      <Badge color={result.success ? 'green' : 'red'} size="sm">
                        {result.success ? 'Pass' : 'Fail'}
                      </Badge>
                    </Group>
                  </Group>
                  {result.error && (
                    <Text size="xs" c="red" mt="xs">{result.error}</Text>
                  )}
                </Paper>
              ))}
            </Stack>
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default MACBatchOperations;
