/**
 * Portal/Endpoint Failover Configuration Component
 * 
 * Configures portal and endpoint failover settings.
 * Requirements: 57.1, 57.2, 57.3, 57.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  NumberInput,
  Switch,
  Group,
  Button,
  TextInput,
  ActionIcon,
  Box,
} from '@mantine/core';
import { IconDeviceFloppy, IconPlus, IconTrash, IconGripVertical } from '@tabler/icons-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const DEFAULT_ENDPOINTS = [
  '/server/load.php',
  '/portal.php',
  '/stalker_portal/server/load.php',
  '/c/server/load.php',
];

const SortableEndpoint = ({ id, onRemove, isEnabled, canRemove }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    backgroundColor: isDragging ? 'var(--mantine-color-blue-light)' : 'var(--mantine-color-gray-light)',
    borderRadius: 'var(--mantine-radius-sm)',
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Group ref={setNodeRef} style={style} mb="xs" p="xs">
      <ActionIcon variant="subtle" {...attributes} {...listeners} disabled={!isEnabled}>
        <IconGripVertical size={16} />
      </ActionIcon>
      <Text size="sm" style={{ flex: 1 }}>{id}</Text>
      <ActionIcon variant="subtle" color="red" onClick={() => onRemove(id)} disabled={!isEnabled || !canRemove}>
        <IconTrash size={16} />
      </ActionIcon>
    </Group>
  );
};

const PortalFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    portal_failover_enabled: true,
    endpoint_failover_enabled: true,
    endpoint_priority: DEFAULT_ENDPOINTS,
    endpoint_timeout: 10,
    endpoint_cache_enabled: true,
  });
  const [newEndpoint, setNewEndpoint] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        portal_failover_enabled: settings.portal_failover_enabled ?? true,
        endpoint_failover_enabled: settings.endpoint_failover_enabled ?? true,
        endpoint_priority: settings.endpoint_priority?.length > 0 ? settings.endpoint_priority : DEFAULT_ENDPOINTS,
        endpoint_timeout: settings.endpoint_timeout ?? 10,
        endpoint_cache_enabled: settings.endpoint_cache_enabled ?? true,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => onSave({ ...settings, ...localSettings });

  const handleAddEndpoint = () => {
    if (newEndpoint && !localSettings.endpoint_priority.includes(newEndpoint)) {
      handleChange('endpoint_priority', [...localSettings.endpoint_priority, newEndpoint]);
      setNewEndpoint('');
    }
  };

  const handleRemoveEndpoint = (endpoint) => {
    handleChange('endpoint_priority', localSettings.endpoint_priority.filter(e => e !== endpoint));
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = localSettings.endpoint_priority.indexOf(active.id);
      const newIndex = localSettings.endpoint_priority.indexOf(over.id);
      handleChange('endpoint_priority', arrayMove(localSettings.endpoint_priority, oldIndex, newIndex));
    }
  };

  const isEnabled = localSettings.portal_failover_enabled || localSettings.endpoint_failover_enabled;

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure portal and endpoint failover. The system will try different API endpoints when connection errors occur.
      </Text>

      <Paper withBorder p="md">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={4}>Enable Portal Failover</Title>
              <Text size="xs" c="dimmed">Switch to backup portal URLs on connection errors</Text>
            </div>
            <Switch checked={localSettings.portal_failover_enabled} onChange={(e) => handleChange('portal_failover_enabled', e.currentTarget.checked)} />
          </Group>
          <Group justify="space-between">
            <div>
              <Title order={4}>Enable Endpoint Failover</Title>
              <Text size="xs" c="dimmed">Try different API endpoints on failure</Text>
            </div>
            <Switch checked={localSettings.endpoint_failover_enabled} onChange={(e) => handleChange('endpoint_failover_enabled', e.currentTarget.checked)} />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="md" opacity={isEnabled ? 1 : 0.5}>
        <Title order={4} mb="md">Endpoint Priority</Title>
        <Text size="xs" c="dimmed" mb="md">Drag to reorder. Endpoints are tried in order from top to bottom.</Text>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={localSettings.endpoint_priority} strategy={verticalListSortingStrategy}>
            {localSettings.endpoint_priority.map((endpoint) => (
              <SortableEndpoint
                key={endpoint}
                id={endpoint}
                onRemove={handleRemoveEndpoint}
                isEnabled={isEnabled}
                canRemove={localSettings.endpoint_priority.length > 1}
              />
            ))}
          </SortableContext>
        </DndContext>

        <Group mt="md">
          <TextInput placeholder="/custom/endpoint.php" value={newEndpoint} onChange={(e) => setNewEndpoint(e.currentTarget.value)} style={{ flex: 1 }} disabled={!isEnabled} />
          <Button leftSection={<IconPlus size={16} />} onClick={handleAddEndpoint} disabled={!isEnabled || !newEndpoint}>Add</Button>
        </Group>
      </Paper>

      <Paper withBorder p="md" opacity={isEnabled ? 1 : 0.5}>
        <Title order={4} mb="md">Endpoint Settings</Title>
        <Stack gap="md">
          <NumberInput label="Endpoint Timeout (seconds)" description="Time to wait for each endpoint before trying the next" value={localSettings.endpoint_timeout} onChange={(val) => handleChange('endpoint_timeout', val)} min={5} max={60} disabled={!isEnabled} />
          <Group justify="space-between">
            <div>
              <Text fw={500}>Cache Successful Endpoint</Text>
              <Text size="xs" c="dimmed">Remember which endpoint worked and try it first next time</Text>
            </div>
            <Switch checked={localSettings.endpoint_cache_enabled} onChange={(e) => handleChange('endpoint_cache_enabled', e.currentTarget.checked)} disabled={!isEnabled} />
          </Group>
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>Save Portal Failover Settings</Button>
      </Group>
    </Stack>
  );
};

export default PortalFailoverConfig;
