/**
 * Test Channel Form Component
 * 
 * Form for creating/editing test channels.
 * Requirements: 2.1, 2.2, 2.3, 2.4
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Box,
  Stack,
  Group,
  Button,
  TextInput,
  Select,
  NumberInput,
  Text,
  Paper,
  ActionIcon,
  Divider,
  Switch,
  MultiSelect,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import {
  IconPlus,
  IconTrash,
  IconGripVertical,
} from '@tabler/icons-react';
import API from '../../api';

const TestChannelForm = ({ channel, onSave, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [availableAccounts, setAvailableAccounts] = useState([]);
  const [useMacPortal, setUseMacPortal] = useState(!!channel?.mac_portal_config);

  const form = useForm({
    initialValues: {
      name: channel?.name || '',
      primary_stream_url: channel?.primary_stream_url || '',
      backup_streams: channel?.backup_streams || [],
      mac_portal_config: channel?.mac_portal_config || null,
    },
    validate: {
      name: (value) => (!value ? 'Name is required' : null),
      primary_stream_url: (value) => {
        if (!value) return 'Primary URL is required';
        try {
          new URL(value);
          return null;
        } catch {
          return 'Invalid URL';
        }
      },
    },
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const accounts = await API.getM3UAccounts?.() || [];
      setAvailableAccounts(
        accounts
          .filter(a => a.account_type === 'MAC' || a.account_type === 'mac')
          .map(a => ({
            value: String(a.id),
            label: a.name,
            macs: a.macs || [],
          }))
      );
    } catch (error) {
      console.error('Failed to load accounts:', error);
    }
  };

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const data = {
        ...values,
        mac_portal_config: useMacPortal ? values.mac_portal_config : null,
      };
      await onSave(data);
    } finally {
      setLoading(false);
    }
  };

  const addBackupStream = () => {
    form.insertListItem('backup_streams', {
      url: '',
      priority: form.values.backup_streams.length,
      name: `Backup ${form.values.backup_streams.length + 1}`,
    });
  };

  const removeBackupStream = (index) => {
    form.removeListItem('backup_streams', index);
  };

  const handleAccountSelect = (accountId) => {
    const account = availableAccounts.find(a => a.value === accountId);
    if (account) {
      form.setFieldValue('mac_portal_config', {
        account_id: parseInt(accountId),
        portal_url: '',
        macs: account.macs?.map(m => m.address) || [],
        endpoints: ['/server/load.php', '/stalker_portal/server/load.php', '/portal.php'],
        user_agents: ['MAG250', 'MAG254', 'MAG322', 'MAG424'],
      });
    }
  };

  return (
    <Modal
      opened={true}
      onClose={onClose}
      title={channel ? 'Edit Test Channel' : 'New Test Channel'}
      size="lg"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Channel Name"
            placeholder="Test Channel 1"
            required
            {...form.getInputProps('name')}
          />

          <TextInput
            label="Primary Stream URL"
            placeholder="http://example.com/stream.m3u8"
            required
            {...form.getInputProps('primary_stream_url')}
          />

          <Divider label="Backup Streams" labelPosition="center" />

          <Stack gap="xs">
            {form.values.backup_streams.map((stream, index) => (
              <Paper key={index} withBorder p="xs">
                <Group wrap="nowrap">
                  <ActionIcon variant="subtle" size="sm">
                    <IconGripVertical size={14} />
                  </ActionIcon>
                  <TextInput
                    placeholder="Backup URL"
                    style={{ flex: 1 }}
                    {...form.getInputProps(`backup_streams.${index}.url`)}
                  />
                  <TextInput
                    placeholder="Name"
                    w={100}
                    {...form.getInputProps(`backup_streams.${index}.name`)}
                  />
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => removeBackupStream(index)}
                  >
                    <IconTrash size={14} />
                  </ActionIcon>
                </Group>
              </Paper>
            ))}

            <Button
              variant="outline"
              size="xs"
              leftSection={<IconPlus size={14} />}
              onClick={addBackupStream}
            >
              Add Backup Stream
            </Button>
          </Stack>

          <Divider label="MAC Portal Configuration" labelPosition="center" />

          <Switch
            label="Use MAC Portal"
            description="Configure MAC addresses and portal settings for testing"
            checked={useMacPortal}
            onChange={(e) => setUseMacPortal(e.currentTarget.checked)}
          />

          {useMacPortal && (
            <Paper withBorder p="md">
              <Stack gap="sm">
                <Select
                  label="MAC Portal Account"
                  placeholder="Select account"
                  data={availableAccounts}
                  onChange={handleAccountSelect}
                  value={form.values.mac_portal_config?.account_id?.toString()}
                />

                {form.values.mac_portal_config && (
                  <>
                    <TextInput
                      label="Portal URL"
                      placeholder="http://portal.example.com"
                      {...form.getInputProps('mac_portal_config.portal_url')}
                    />

                    <Text size="sm" fw={500}>
                      MACs ({form.values.mac_portal_config.macs?.length || 0})
                    </Text>
                    <Text size="xs" c="dimmed">
                      {form.values.mac_portal_config.macs?.join(', ') || 'No MACs configured'}
                    </Text>

                    <MultiSelect
                      label="Endpoints"
                      data={[
                        '/server/load.php',
                        '/stalker_portal/server/load.php',
                        '/portal.php',
                        '/c/portal.php',
                      ]}
                      value={form.values.mac_portal_config.endpoints || []}
                      onChange={(value) => form.setFieldValue('mac_portal_config.endpoints', value)}
                    />

                    <MultiSelect
                      label="User Agents"
                      data={['MAG250', 'MAG254', 'MAG322', 'MAG424']}
                      value={form.values.mac_portal_config.user_agents || []}
                      onChange={(value) => form.setFieldValue('mac_portal_config.user_agents', value)}
                    />
                  </>
                )}
              </Stack>
            </Paper>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              {channel ? 'Save Changes' : 'Create Channel'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default TestChannelForm;
