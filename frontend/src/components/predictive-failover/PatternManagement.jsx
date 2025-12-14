/**
 * Pattern Management Component
 * 
 * Manages failure patterns for predictive failover.
 * 
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Table,
  Paper,
  ActionIcon,
  Badge,
  Button,
  Modal,
  Slider,
  Alert,
  Tooltip,
  Switch,
  Group,
  Stack,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconTrash,
  IconThumbDown,
  IconCircleCheck,
  IconRefresh,
  IconClearAll,
} from '@tabler/icons-react';
import API from '../../api';

const PatternManagement = () => {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, pattern: null });
  const [confidenceDialog, setConfidenceDialog] = useState({ open: false, pattern: null, value: 50 });

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/predictive-failover/patterns/');
      setPatterns(response.data);
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to load patterns', color: 'red' });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const markFalsePositive = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/mark_false_positive/`);
      notifications.show({ title: 'Success', message: 'Pattern marked as false positive', color: 'green' });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to mark pattern', color: 'red' });
      console.error(err);
    }
  };

  const markConfirmed = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/mark_confirmed/`);
      notifications.show({ title: 'Success', message: 'Pattern marked as confirmed', color: 'green' });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to confirm pattern', color: 'red' });
      console.error(err);
    }
  };

  const toggleStatus = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/toggle_status/`);
      notifications.show({ title: 'Success', message: 'Pattern status toggled', color: 'green' });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to toggle pattern status', color: 'red' });
      console.error(err);
    }
  };

  const deletePattern = async () => {
    if (!deleteDialog.pattern) return;
    try {
      await API.delete(`/api/predictive-failover/patterns/${deleteDialog.pattern.id}/`);
      notifications.show({ title: 'Success', message: 'Pattern deleted', color: 'green' });
      setDeleteDialog({ open: false, pattern: null });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to delete pattern', color: 'red' });
      console.error(err);
    }
  };

  const updateConfidence = async () => {
    if (!confidenceDialog.pattern) return;
    try {
      await API.patch(`/api/predictive-failover/patterns/${confidenceDialog.pattern.id}/`, {
        confidence: confidenceDialog.value
      });
      notifications.show({ title: 'Success', message: 'Confidence updated', color: 'green' });
      setConfidenceDialog({ open: false, pattern: null, value: 50 });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to update confidence', color: 'red' });
      console.error(err);
    }
  };

  const cleanupPatterns = async () => {
    try {
      const response = await API.post('/api/predictive-failover/patterns/cleanup/', { threshold: 30 });
      notifications.show({ title: 'Success', message: `Cleaned up ${response.data.deleted} low-confidence patterns`, color: 'green' });
      loadPatterns();
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to cleanup patterns', color: 'red' });
      console.error(err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'green';
      case 'confirmed': return 'blue';
      case 'disabled': return 'gray';
      case 'false_positive': return 'red';
      default: return 'gray';
    }
  };

  const getTypeLabel = (type) => {
    const labels = {
      response_time: 'Response Time',
      buffer_underrun: 'Buffer Underrun',
      bitrate_drop: 'Bitrate Drop',
      connection_reset: 'Connection Reset',
      time_window: 'Time Window',
      correlation: 'Correlation',
      composite: 'Composite',
    };
    return labels[type] || type;
  };

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Title order={4}>Failure Patterns</Title>
        <Group>
          <Button
            variant="outline"
            leftSection={<IconClearAll size={16} />}
            onClick={cleanupPatterns}
          >
            Cleanup Low Confidence
          </Button>
          <ActionIcon variant="subtle" onClick={loadPatterns}>
            <IconRefresh size={18} />
          </ActionIcon>
        </Group>
      </Group>

      <Paper withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Confidence</Table.Th>
              <Table.Th>Hits</Table.Th>
              <Table.Th>Success Rate</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {patterns.map((pattern) => (
              <Table.Tr key={pattern.id}>
                <Table.Td>{pattern.name}</Table.Td>
                <Table.Td>
                  <Badge variant="outline" size="sm">{getTypeLabel(pattern.pattern_type)}</Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    variant="subtle"
                    size="xs"
                    onClick={() => setConfidenceDialog({ open: true, pattern, value: pattern.confidence })}
                  >
                    {pattern.confidence}%
                  </Button>
                </Table.Td>
                <Table.Td>{pattern.hit_count}</Table.Td>
                <Table.Td>{pattern.success_rate?.toFixed(1) || 0}%</Table.Td>
                <Table.Td>
                  <Badge color={getStatusColor(pattern.status)} size="sm">
                    {pattern.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <Tooltip label="Toggle Active/Disabled">
                      <Switch
                        size="xs"
                        checked={pattern.status === 'active' || pattern.status === 'confirmed'}
                        onChange={() => toggleStatus(pattern)}
                        disabled={pattern.status === 'false_positive'}
                      />
                    </Tooltip>
                    <Tooltip label="Mark as False Positive">
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="yellow"
                        onClick={() => markFalsePositive(pattern)}
                      >
                        <IconThumbDown size={14} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Mark as Confirmed">
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="green"
                        onClick={() => markConfirmed(pattern)}
                      >
                        <IconCircleCheck size={14} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Delete">
                      <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="red"
                        onClick={() => setDeleteDialog({ open: true, pattern })}
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {patterns.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed">No patterns found</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Modal
        opened={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, pattern: null })}
        title="Delete Pattern"
      >
        <Text mb="md">
          Are you sure you want to delete pattern "{deleteDialog.pattern?.name}"?
        </Text>
        <Group justify="flex-end">
          <Button variant="outline" onClick={() => setDeleteDialog({ open: false, pattern: null })}>
            Cancel
          </Button>
          <Button color="red" onClick={deletePattern}>
            Delete
          </Button>
        </Group>
      </Modal>

      {/* Confidence Adjustment Dialog */}
      <Modal
        opened={confidenceDialog.open}
        onClose={() => setConfidenceDialog({ open: false, pattern: null, value: 50 })}
        title="Adjust Confidence"
      >
        <Stack>
          <Text size="sm">Confidence: {confidenceDialog.value}%</Text>
          <Slider
            value={confidenceDialog.value}
            onChange={(v) => setConfidenceDialog(prev => ({ ...prev, value: v }))}
            min={0}
            max={100}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="outline" onClick={() => setConfidenceDialog({ open: false, pattern: null, value: 50 })}>
              Cancel
            </Button>
            <Button onClick={updateConfidence}>Save</Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  );
};

export default PatternManagement;
