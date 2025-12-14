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
  Divider,
  TextInput,
  ActionIcon,
  Box,
} from '@mantine/core';
import { IconDeviceFloppy, IconPlus, IconTrash, IconGripVertical } from '@tabler/icons-react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

const DEFAULT_ENDPOINTS = [
  '/server/load.php',
  '/portal.php',
  '/stalker_portal/server/load.php',
  '/c/server/load.php',
];

const PortalFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    portal_failover_enabled: true,
    endpoint_failover_enabled: true,
    endpoint_priority: DEFAULT_ENDPOINTS,
    endpoint_timeout: 10,
    endpoint_cache_enabled: true,
  });
  const [newEndpoint, setNewEndpoint] = useState('');

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        portal_failover_enabled: settings.portal_failover_enabled ?? true,
        endpoint_failover_enabled: settings.endpoint_failover_enabled ?? true,
        endpoint_priority: settings.endpoint_priority?.length > 0 
          ? settings.endpoint_priority 
          : DEFAULT_ENDPOINTS,
        endpoint_timeout: settings.endpoint_timeout ?? 10,
        endpoint_cache_enabled: settings.endpoint_cache_enabled ?? true,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave({ ...settings, ...localSettings });
  };

  const handleAddEndpoint = () => {
    if (newEndpoint && !localSettings.endpoint_priority.includes(newEndpoint)) {
      handleChange('endpoint_priority', [...localSettings.endpoint_priority, newEndpoint]);
      setNewEndpoint('');
    }
  };

  const handleRemoveEndpoint = (index) => {
    const updated = localSettings.endpoint_priority.filter((_, i) => i !== index);
    handleChange('endpoint_priority', updated);
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const items = Array.from(localSettings.endpoint_priority);
    const [reordered] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reordered);
    
    handleChange('endpoint_priority', items);
  };

  const isEnabled = localSettings.portal_failover_enabled || localSettings.endpoint_failover_enabled;

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure portal and endpoint failover. The system will try different
        API endpoints when connection errors occur.
      </Text>

      <Paper withBorder p="md">
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={4}>Enable Portal Failover</Title>
              <Text size="xs" c="dimmed">
                Switch to backup portal URLs on connection errors
              </Text>
            </div>
            <Switch
              checked={localSettings.portal_failover_enabled}
              onChange={(e) => handleChange('portal_failover_enabled', e.currentTarget.checked)}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Title order={4}>Enable Endpoint Failover</Title>
              <Text size="xs" c="dimmed">
                Try different API endpoints on failure
              </Text>
            </div>
            <Switch
              checked={localSettings.endpoint_failover_enabled}
              onChange={(e) => handleChange('endpoint_failover_enabled', e.currentTarget.checked)}
            />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="md" opacity={isEnabled ? 1 : 0.5}>
        <Title order={4} mb="md">Endpoint Priority</Title>
        <Text size="xs" c="dimmed" mb="md">
          Drag to reorder. Endpoints are tried in order from top to bottom.
        </Text>

        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="endpoints">
            {(provided) => (
              <Box {...provided.droppableProps} ref={provided.innerRef}>
                {localSettings.endpoint_priority.map((endpoint, index) => (
                  <Draggable key={endpoint} draggableId={endpoint} index={index}>
                    {(provided, snapshot) => (
                      <Group
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        mb="xs"
                        p="xs"
                        style={{
                          backgroundColor: snapshot.isDragging ? 'var(--mantine-color-blue-light)' : 'var(--mantine-color-gray-light)',
                          borderRadius: 'var(--mantine-radius-sm)',
                          ...provided.draggableProps.style,
                        }}
                      >
                        <ActionIcon 
                          variant="subtle" 
                          {...provided.dragHandleProps}
                          disabled={!isEnabled}
                        >
                          <IconGripVertical size={16} />
                        </ActionIcon>
                        <Text size="sm" style={{ flex: 1 }}>{endpoint}</Text>
                        <ActionIcon 
                          variant="subtle" 
                          color="red"
                          onClick={() => handleRemoveEndpoint(index)}
                          disabled={!isEnabled || localSettings.endpoint_priority.length <= 1}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Group>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </Box>
            )}
          </Droppable>
        </DragDropContext>

        <Group mt="md">
          <TextInput
            placeholder="/custom/endpoint.php"
            value={newEndpoint}
            onChange={(e) => setNewEndpoint(e.currentTarget.value)}
            style={{ flex: 1 }}
            disabled={!isEnabled}
          />
          <Button 
            leftSection={<IconPlus size={16} />}
            onClick={handleAddEndpoint}
            disabled={!isEnabled || !newEndpoint}
          >
            Add
          </Button>
        </Group>
      </Paper>

      <Paper withBorder p="md" opacity={isEnabled ? 1 : 0.5}>
        <Title order={4} mb="md">Endpoint Settings</Title>
        
        <Stack gap="md">
          <NumberInput
            label="Endpoint Timeout (seconds)"
            description="Time to wait for each endpoint before trying the next"
            value={localSettings.endpoint_timeout}
            onChange={(val) => handleChange('endpoint_timeout', val)}
            min={5}
            max={60}
            disabled={!isEnabled}
          />

          <Group justify="space-between">
            <div>
              <Text fw={500}>Cache Successful Endpoint</Text>
              <Text size="xs" c="dimmed">
                Remember which endpoint worked and try it first next time
              </Text>
            </div>
            <Switch
              checked={localSettings.endpoint_cache_enabled}
              onChange={(e) => handleChange('endpoint_cache_enabled', e.currentTarget.checked)}
              disabled={!isEnabled}
            />
          </Group>
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>
          Save Portal Failover Settings
        </Button>
      </Group>
    </Stack>
  );
};

export default PortalFailoverConfig;
