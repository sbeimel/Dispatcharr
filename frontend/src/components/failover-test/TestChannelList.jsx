/**
 * Test Channel List Component
 * 
 * Displays and manages test channels.
 * Requirements: 2.5, 8.1
 */

import React from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Badge,
  Paper,
  ActionIcon,
  Menu,
} from '@mantine/core';
import {
  IconDotsVertical,
  IconTrash,
  IconEdit,
  IconPlayerPlay,
  IconDownload,
} from '@tabler/icons-react';

const TestChannelList = ({
  channels = [],
  selectedChannel,
  onSelect,
  onDelete,
  onEdit,
  onImport,
}) => {
  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={4}>Test Channels</Title>
        <Badge>{channels.length}</Badge>
      </Group>

      <Stack gap="xs">
        {channels.length === 0 ? (
          <Paper withBorder p="md" ta="center">
            <Text c="dimmed" size="sm">
              Keine Test-Channels. Erstelle einen neuen Channel oder importiere einen existierenden.
            </Text>
          </Paper>
        ) : (
          channels.map((channel) => (
            <ChannelItem
              key={channel.id}
              channel={channel}
              isSelected={selectedChannel?.id === channel.id}
              onSelect={() => onSelect(channel)}
              onDelete={() => onDelete(channel.id)}
              onEdit={() => onEdit(channel)}
            />
          ))
        )}
      </Stack>
    </Box>
  );
};

const ChannelItem = ({ channel, isSelected, onSelect, onDelete, onEdit }) => {
  const backupCount = channel.backup_streams?.length || 0;
  const hasMacConfig = !!channel.mac_portal_config;

  return (
    <Paper
      withBorder
      p="sm"
      style={{
        cursor: 'pointer',
        backgroundColor: isSelected ? 'var(--mantine-color-blue-0)' : undefined,
        borderColor: isSelected ? 'var(--mantine-color-blue-4)' : undefined,
      }}
      onClick={onSelect}
    >
      <Group justify="space-between" wrap="nowrap">
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs" wrap="nowrap">
            <Text fw={500} truncate>
              {channel.name}
            </Text>
            {channel.is_imported && (
              <Badge size="xs" color="gray" variant="outline">
                Imported
              </Badge>
            )}
          </Group>
          
          <Text size="xs" c="dimmed" truncate>
            {channel.primary_stream_url}
          </Text>
          
          <Group gap="xs" mt={4}>
            {backupCount > 0 && (
              <Badge size="xs" variant="light">
                {backupCount} Backup{backupCount !== 1 ? 's' : ''}
              </Badge>
            )}
            {hasMacConfig && (
              <Badge size="xs" variant="light" color="violet">
                MAC Portal
              </Badge>
            )}
            {hasMacConfig && channel.mac_portal_config.macs?.length > 0 && (
              <Badge size="xs" variant="light" color="grape">
                {channel.mac_portal_config.macs.length} MACs
              </Badge>
            )}
          </Group>
        </Box>

        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <ActionIcon
              variant="subtle"
              onClick={(e) => e.stopPropagation()}
            >
              <IconDotsVertical size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              leftSection={<IconEdit size={14} />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
            >
              Edit
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </Paper>
  );
};

export default TestChannelList;
