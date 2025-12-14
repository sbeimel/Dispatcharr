/**
 * User-Agent Failover Configuration Component
 * 
 * Configures User-Agent rotation and failover settings.
 * Requirements: 59.1, 59.2, 59.3, 59.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Switch,
  Group,
  Button,
  Divider,
  ActionIcon,
  Box,
  Badge,
} from '@mantine/core';
import { IconDeviceFloppy, IconGripVertical } from '@tabler/icons-react';
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

const DEFAULT_USER_AGENTS = [
  { id: 'MAG250', name: 'MAG250', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3' },
  { id: 'MAG254', name: 'MAG254', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 254 Safari/533.3' },
  { id: 'MAG322', name: 'MAG322', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 322 Safari/533.3' },
  { id: 'MAG424', name: 'MAG424', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 424 Safari/533.3' },
];

const SortableUserAgent = ({ id, index, isEnabled }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const uaInfo = DEFAULT_USER_AGENTS.find(ua => ua.id === id) || { id, name: id, ua: 'Unknown' };
  
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
      <div style={{ flex: 1 }}>
        <Group gap="xs">
          <Text size="sm" fw={500}>{uaInfo.name}</Text>
          {index === 0 && <Badge size="xs" color="yellow">Default</Badge>}
        </Group>
        <Text size="xs" c="dimmed" lineClamp={1}>{uaInfo.ua.substring(0, 60)}...</Text>
      </div>
    </Group>
  );
};

const UserAgentFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    useragent_failover_enabled: false,
    useragent_rotation_order: DEFAULT_USER_AGENTS.map(ua => ua.id),
    useragent_rotate_on_auth_failure: true,
    useragent_rotate_on_403: true,
    useragent_rotate_on_cloudflare: true,
    useragent_remember_successful: true,
  });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        useragent_failover_enabled: settings.useragent_failover_enabled ?? false,
        useragent_rotation_order: settings.useragent_rotation_order?.length > 0 ? settings.useragent_rotation_order : DEFAULT_USER_AGENTS.map(ua => ua.id),
        useragent_rotate_on_auth_failure: settings.useragent_rotate_on_auth_failure ?? true,
        useragent_rotate_on_403: settings.useragent_rotate_on_403 ?? true,
        useragent_rotate_on_cloudflare: settings.useragent_rotate_on_cloudflare ?? true,
        useragent_remember_successful: settings.useragent_remember_successful ?? true,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => setLocalSettings(prev => ({ ...prev, [field]: value }));
  const handleSave = () => onSave({ ...settings, ...localSettings });

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = localSettings.useragent_rotation_order.indexOf(active.id);
      const newIndex = localSettings.useragent_rotation_order.indexOf(over.id);
      handleChange('useragent_rotation_order', arrayMove(localSettings.useragent_rotation_order, oldIndex, newIndex));
    }
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">Configure User-Agent rotation. The system can try different User-Agent strings when specific errors occur.</Text>

      <Paper withBorder p="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={4}>Enable User-Agent Failover</Title>
            <Text size="xs" c="dimmed">Rotate User-Agent strings on specific errors</Text>
          </div>
          <Switch checked={localSettings.useragent_failover_enabled} onChange={(e) => handleChange('useragent_failover_enabled', e.currentTarget.checked)} />
        </Group>

        <Divider my="md" />

        <Stack gap="md" opacity={localSettings.useragent_failover_enabled ? 1 : 0.5}>
          <Title order={5}>Rotation Triggers</Title>
          
          <Group justify="space-between">
            <div><Text fw={500}>On Authentication Failure</Text><Text size="xs" c="dimmed">Rotate when portal returns auth error</Text></div>
            <Switch checked={localSettings.useragent_rotate_on_auth_failure} onChange={(e) => handleChange('useragent_rotate_on_auth_failure', e.currentTarget.checked)} disabled={!localSettings.useragent_failover_enabled} />
          </Group>

          <Group justify="space-between">
            <div><Text fw={500}>On HTTP 403 Forbidden</Text><Text size="xs" c="dimmed">Rotate when server returns 403 error</Text></div>
            <Switch checked={localSettings.useragent_rotate_on_403} onChange={(e) => handleChange('useragent_rotate_on_403', e.currentTarget.checked)} disabled={!localSettings.useragent_failover_enabled} />
          </Group>

          <Group justify="space-between">
            <div><Text fw={500}>On Cloudflare Challenge</Text><Text size="xs" c="dimmed">Rotate when Cloudflare protection is detected</Text></div>
            <Switch checked={localSettings.useragent_rotate_on_cloudflare} onChange={(e) => handleChange('useragent_rotate_on_cloudflare', e.currentTarget.checked)} disabled={!localSettings.useragent_failover_enabled} />
          </Group>

          <Group justify="space-between">
            <div><Text fw={500}>Remember Successful User-Agent</Text><Text size="xs" c="dimmed">Cache which User-Agent worked for each portal</Text></div>
            <Switch checked={localSettings.useragent_remember_successful} onChange={(e) => handleChange('useragent_remember_successful', e.currentTarget.checked)} disabled={!localSettings.useragent_failover_enabled} />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="md" opacity={localSettings.useragent_failover_enabled ? 1 : 0.5}>
        <Title order={4} mb="md">User-Agent Priority</Title>
        <Text size="xs" c="dimmed" mb="md">Drag to reorder. User-Agents are tried in order from top to bottom.</Text>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={localSettings.useragent_rotation_order} strategy={verticalListSortingStrategy}>
            {localSettings.useragent_rotation_order.map((uaId, index) => (
              <SortableUserAgent key={uaId} id={uaId} index={index} isEnabled={localSettings.useragent_failover_enabled} />
            ))}
          </SortableContext>
        </DndContext>
      </Paper>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>Save User-Agent Failover Settings</Button>
      </Group>
    </Stack>
  );
};

export default UserAgentFailoverConfig;
