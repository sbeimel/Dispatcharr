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
import { IconDeviceFloppy, IconGripVertical, IconStar, IconStarFilled } from '@tabler/icons-react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

const DEFAULT_USER_AGENTS = [
  { id: 'MAG250', name: 'MAG250', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3' },
  { id: 'MAG254', name: 'MAG254', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 254 Safari/533.3' },
  { id: 'MAG322', name: 'MAG322', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 322 Safari/533.3' },
  { id: 'MAG424', name: 'MAG424', ua: 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 424 Safari/533.3' },
];

const UserAgentFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    useragent_failover_enabled: false,
    useragent_rotation_order: DEFAULT_USER_AGENTS.map(ua => ua.id),
    useragent_rotate_on_auth_failure: true,
    useragent_rotate_on_403: true,
    useragent_rotate_on_cloudflare: true,
    useragent_remember_successful: true,
  });

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        useragent_failover_enabled: settings.useragent_failover_enabled ?? false,
        useragent_rotation_order: settings.useragent_rotation_order?.length > 0 
          ? settings.useragent_rotation_order 
          : DEFAULT_USER_AGENTS.map(ua => ua.id),
        useragent_rotate_on_auth_failure: settings.useragent_rotate_on_auth_failure ?? true,
        useragent_rotate_on_403: settings.useragent_rotate_on_403 ?? true,
        useragent_rotate_on_cloudflare: settings.useragent_rotate_on_cloudflare ?? true,
        useragent_remember_successful: settings.useragent_remember_successful ?? true,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave({ ...settings, ...localSettings });
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const items = Array.from(localSettings.useragent_rotation_order);
    const [reordered] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reordered);
    
    handleChange('useragent_rotation_order', items);
  };

  const getUserAgentInfo = (id) => {
    return DEFAULT_USER_AGENTS.find(ua => ua.id === id) || { id, name: id, ua: 'Unknown' };
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure User-Agent rotation. The system can try different User-Agent
        strings when specific errors occur.
      </Text>

      <Paper withBorder p="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={4}>Enable User-Agent Failover</Title>
            <Text size="xs" c="dimmed">
              Rotate User-Agent strings on specific errors
            </Text>
          </div>
          <Switch
            checked={localSettings.useragent_failover_enabled}
            onChange={(e) => handleChange('useragent_failover_enabled', e.currentTarget.checked)}
          />
        </Group>

        <Divider my="md" />

        <Stack gap="md" opacity={localSettings.useragent_failover_enabled ? 1 : 0.5}>
          <Title order={5}>Rotation Triggers</Title>
          
          <Group justify="space-between">
            <div>
              <Text fw={500}>On Authentication Failure</Text>
              <Text size="xs" c="dimmed">
                Rotate when portal returns auth error
              </Text>
            </div>
            <Switch
              checked={localSettings.useragent_rotate_on_auth_failure}
              onChange={(e) => handleChange('useragent_rotate_on_auth_failure', e.currentTarget.checked)}
              disabled={!localSettings.useragent_failover_enabled}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text fw={500}>On HTTP 403 Forbidden</Text>
              <Text size="xs" c="dimmed">
                Rotate when server returns 403 error
              </Text>
            </div>
            <Switch
              checked={localSettings.useragent_rotate_on_403}
              onChange={(e) => handleChange('useragent_rotate_on_403', e.currentTarget.checked)}
              disabled={!localSettings.useragent_failover_enabled}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text fw={500}>On Cloudflare Challenge</Text>
              <Text size="xs" c="dimmed">
                Rotate when Cloudflare protection is detected
              </Text>
            </div>
            <Switch
              checked={localSettings.useragent_rotate_on_cloudflare}
              onChange={(e) => handleChange('useragent_rotate_on_cloudflare', e.currentTarget.checked)}
              disabled={!localSettings.useragent_failover_enabled}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text fw={500}>Remember Successful User-Agent</Text>
              <Text size="xs" c="dimmed">
                Cache which User-Agent worked for each portal
              </Text>
            </div>
            <Switch
              checked={localSettings.useragent_remember_successful}
              onChange={(e) => handleChange('useragent_remember_successful', e.currentTarget.checked)}
              disabled={!localSettings.useragent_failover_enabled}
            />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="md" opacity={localSettings.useragent_failover_enabled ? 1 : 0.5}>
        <Title order={4} mb="md">User-Agent Priority</Title>
        <Text size="xs" c="dimmed" mb="md">
          Drag to reorder. User-Agents are tried in order from top to bottom.
        </Text>

        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="useragents">
            {(provided) => (
              <Box {...provided.droppableProps} ref={provided.innerRef}>
                {localSettings.useragent_rotation_order.map((uaId, index) => {
                  const uaInfo = getUserAgentInfo(uaId);
                  return (
                    <Draggable key={uaId} draggableId={uaId} index={index}>
                      {(provided, snapshot) => (
                        <Group
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          mb="xs"
                          p="xs"
                          style={{
                            backgroundColor: snapshot.isDragging 
                              ? 'var(--mantine-color-blue-light)' 
                              : 'var(--mantine-color-gray-light)',
                            borderRadius: 'var(--mantine-radius-sm)',
                            ...provided.draggableProps.style,
                          }}
                        >
                          <ActionIcon 
                            variant="subtle" 
                            {...provided.dragHandleProps}
                            disabled={!localSettings.useragent_failover_enabled}
                          >
                            <IconGripVertical size={16} />
                          </ActionIcon>
                          <div style={{ flex: 1 }}>
                            <Group gap="xs">
                              <Text size="sm" fw={500}>{uaInfo.name}</Text>
                              {index === 0 && (
                                <Badge size="xs" color="yellow">Default</Badge>
                              )}
                            </Group>
                            <Text size="xs" c="dimmed" lineClamp={1}>
                              {uaInfo.ua.substring(0, 60)}...
                            </Text>
                          </div>
                        </Group>
                      )}
                    </Draggable>
                  );
                })}
                {provided.placeholder}
              </Box>
            )}
          </Droppable>
        </DragDropContext>
      </Paper>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>
          Save User-Agent Failover Settings
        </Button>
      </Group>
    </Stack>
  );
};

export default UserAgentFailoverConfig;
