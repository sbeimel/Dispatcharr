/**
 * Channel Import Modal Component
 * 
 * Modal for importing existing channels as test copies.
 * Requirements: 8.1, 8.2, 8.4
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Box,
  Stack,
  Group,
  Button,
  Text,
  TextInput,
  Paper,
  ScrollArea,
  LoadingOverlay,
  Badge,
} from '@mantine/core';
import { IconSearch, IconDownload } from '@tabler/icons-react';
import failoverTestApi from '../../api/failoverTestApi';

const ChannelImportModal = ({ opened, onClose, onImport }) => {
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [channels, setChannels] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedChannel, setSelectedChannel] = useState(null);

  useEffect(() => {
    if (opened) {
      loadChannels();
    }
  }, [opened]);

  const loadChannels = async () => {
    setLoading(true);
    try {
      const data = await failoverTestApi.getAvailableChannelsForImport();
      setChannels(data || []);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!selectedChannel) return;

    setImporting(true);
    try {
      const imported = await failoverTestApi.importChannelForTest(selectedChannel.id);
      onImport(imported);
      onClose();
    } catch (error) {
      console.error('Failed to import channel:', error);
    } finally {
      setImporting(false);
    }
  };

  const filteredChannels = channels.filter(ch =>
    ch.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Import Channel for Testing"
      size="lg"
    >
      <Box pos="relative">
        <LoadingOverlay visible={loading} />

        <Stack gap="md">
          <TextInput
            placeholder="Search channels..."
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
          />

          <Text size="sm" c="dimmed">
            Select a channel to import as a test copy. The original channel will not be modified.
          </Text>

          <ScrollArea h={300}>
            <Stack gap="xs">
              {filteredChannels.length === 0 ? (
                <Paper withBorder p="md" ta="center">
                  <Text c="dimmed" size="sm">
                    {loading ? 'Loading...' : 'No channels found'}
                  </Text>
                </Paper>
              ) : (
                filteredChannels.map((channel) => (
                  <Paper
                    key={channel.id}
                    withBorder
                    p="sm"
                    style={{
                      cursor: 'pointer',
                      backgroundColor: selectedChannel?.id === channel.id
                        ? 'var(--mantine-color-blue-0)'
                        : undefined,
                      borderColor: selectedChannel?.id === channel.id
                        ? 'var(--mantine-color-blue-4)'
                        : undefined,
                    }}
                    onClick={() => setSelectedChannel(channel)}
                  >
                    <Group justify="space-between">
                      <Box>
                        <Text fw={500}>{channel.name}</Text>
                        {channel.channel_number && (
                          <Text size="xs" c="dimmed">
                            Channel #{channel.channel_number}
                          </Text>
                        )}
                      </Box>
                      {selectedChannel?.id === channel.id && (
                        <Badge color="blue">Selected</Badge>
                      )}
                    </Group>
                  </Paper>
                ))
              )}
            </Stack>
          </ScrollArea>

          <Group justify="flex-end">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              leftSection={<IconDownload size={16} />}
              onClick={handleImport}
              loading={importing}
              disabled={!selectedChannel}
            >
              Import Channel
            </Button>
          </Group>
        </Stack>
      </Box>
    </Modal>
  );
};

export default ChannelImportModal;
