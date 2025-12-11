// Modal.js
import React, { useState, useEffect } from 'react';
import API from '../../api';
import useUserAgentsStore from '../../store/userAgents';
import M3UProfiles from './M3UProfiles';
import {
  LoadingOverlay,
  TextInput,
  Button,
  Checkbox,
  Modal,
  Flex,
  Select,
  FileInput,
  useMantineTheme,
  NumberInput,
  Divider,
  Stack,
  Group,
  Switch,
  Box,
  PasswordInput,
  Table,
  Badge,
  ActionIcon,
} from '@mantine/core';
import M3UGroupFilter from './M3UGroupFilter';
import useChannelsStore from '../../store/channels';
import { notifications } from '@mantine/notifications';
import { isNotEmpty, useForm } from '@mantine/form';
import useEPGsStore from '../../store/epgs';
import useVODStore from '../../store/useVODStore';
import M3UFilters from './M3UFilters';
import { useWebSocket } from '../../WebSocket';

const M3U = ({
  m3uAccount = null,
  isOpen,
  onClose,
  playlistCreated = false,
}) => {
  const theme = useMantineTheme();

  const userAgents = useUserAgentsStore((s) => s.userAgents);
  const fetchChannelGroups = useChannelsStore((s) => s.fetchChannelGroups);
  const fetchEPGs = useEPGsStore((s) => s.fetchEPGs);
  const fetchCategories = useVODStore((s) => s.fetchCategories);

  const [playlist, setPlaylist] = useState(null);
  const [file, setFile] = useState(null);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [groupFilterModalOpen, setGroupFilterModalOpen] = useState(false);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [showCredentialFields, setShowCredentialFields] = useState(false);

  // WebSocket for real-time updates
  const [isWebSocketReady, , webSocketValue] = useWebSocket();

  const form = useForm({
    mode: 'uncontrolled',
    initialValues: {
      name: '',
      server_url: '',
      user_agent: '0',
      is_active: true,
      max_streams: 0,
      refresh_interval: 24,
      account_type: 'XC',
      create_epg: false,
      username: '',
      password: '',
      stale_stream_days: 7,
      priority: 0,
      enable_vod: false,
      mac_address: '',
      proxy: '',
    },

    validate: {
      name: isNotEmpty('Please select a name'),
      user_agent: isNotEmpty('Please select a user-agent'),
      refresh_interval: isNotEmpty('Please specify a refresh interval'),
    },
  });

  useEffect(() => {
    console.log(m3uAccount);
    if (m3uAccount) {
      setPlaylist(m3uAccount);
      form.setValues({
        name: m3uAccount.name,
        server_url: m3uAccount.server_url,
        max_streams: m3uAccount.max_streams,
        user_agent: m3uAccount.user_agent ? `${m3uAccount.user_agent}` : '0',
        is_active: m3uAccount.is_active,
        refresh_interval: m3uAccount.refresh_interval,
        account_type: m3uAccount.account_type,
        username: m3uAccount.username ?? '',
        password: '',
        stale_stream_days:
          m3uAccount.stale_stream_days !== undefined &&
          m3uAccount.stale_stream_days !== null
            ? m3uAccount.stale_stream_days
            : 7,
        priority:
          m3uAccount.priority !== undefined && m3uAccount.priority !== null
            ? m3uAccount.priority
            : 0,
        enable_vod: m3uAccount.enable_vod || false,
        mac_address: m3uAccount.mac_address ?? '',
        proxy: m3uAccount.proxy ?? '',
      });

      if (m3uAccount.account_type == 'XC') {
        setShowCredentialFields(true);
      } else {
        setShowCredentialFields(false);
      }
    } else {
      setPlaylist(null);
      form.reset();
    }
  }, [m3uAccount]);

  useEffect(() => {
    if (form.values.account_type == 'XC') {
      setShowCredentialFields(true);
    }
  }, [form.values.account_type]);

  // Listen for WebSocket updates for this playlist
  useEffect(() => {
    if (webSocketValue && playlist?.id) {
      try {
        const parsedEvent = JSON.parse(webSocketValue);
        
        // Check if this is a playlist update for our current playlist
        if (parsedEvent.type === 'playlist_updated' && 
            parsedEvent.data?.account === playlist.id) {
          
          // Update the playlist with new data (including MAC status updates)
          const updatedPlaylist = parsedEvent.data;
          setPlaylist(updatedPlaylist);
          
          // Update form field if MAC addresses changed
          if (updatedPlaylist.mac_address !== undefined) {
            form.setFieldValue('mac_address', updatedPlaylist.mac_address ?? '');
          }
          
          // Show notification for MAC status changes
          if (updatedPlaylist.macs && updatedPlaylist.macs.length > 0) {
            const hasStatusChanges = updatedPlaylist.macs.some(mac => 
              mac.status === 'valid' || mac.status === 'expired' || mac.status === 'error'
            );
            
            if (hasStatusChanges) {
              notifications.show({
                title: 'MAC Status Updated',
                message: 'MAC address status has been updated automatically.',
                color: 'blue',
              });
            }
          }
        }
      } catch (e) {
        // Ignore parsing errors for non-JSON WebSocket messages
      }
    }
  }, [webSocketValue, playlist?.id, form]);

  const onSubmit = async () => {
    const { create_epg, ...values } = form.getValues();

    if (values.account_type == 'XC' && values.password == '') {
      // If account XC and no password input, assuming no password change
      // from previously stored value.
      delete values.password;
    }

    // Validation for MAC accounts
    if (values.account_type === 'MAC') {
      if (!values.server_url) {
        notifications.show({
          title: 'Validation Error',
          message: 'Portal URL is required for MAC accounts',
          color: 'red',
        });
        return;
      }
      if (!values.mac_address) {
        notifications.show({
          title: 'Validation Error', 
          message: 'MAC address is required for MAC accounts',
          color: 'red',
        });
        return;
      }
    }

    if (values.user_agent == '0') {
      values.user_agent = null;
    }

    let newPlaylist;
    if (playlist?.id) {
      await API.updatePlaylist({
        id: playlist.id,
        ...values,
        file,
      });
    } else {
      newPlaylist = await API.addPlaylist({
        ...values,
        file,
      });

      if (create_epg) {
        API.addEPG({
          name: values.name,
          source_type: 'xmltv',
          url: `${values.server_url}/xmltv.php?username=${values.username}&password=${values.password}`,
          api_key: '',
          is_active: true,
          refresh_interval: 24,
        });
      }

      if (values.account_type != 'XC' && values.account_type != 'MAC') {
        notifications.show({
          title: 'Fetching M3U Groups',
          message:
            'Configure group filters and auto sync settings once complete.',
        });
      } else if (values.account_type === 'MAC') {
        notifications.show({
          title: 'Connecting to MAC Portal',
          message:
            'Testing MAC portal connection and fetching channels...',
        });

        // Don't prompt for group filters, but keeping this here
        // in case we want to revive it
        newPlaylist = null;
        close();
        return;
      }

      // Fetch the updated playlist details (this also updates the store via API)
      const updatedPlaylist = await API.getPlaylist(newPlaylist.id);

      // Note: We don't call fetchPlaylists() here because API.addPlaylist()
      // already added the playlist to the store. Calling fetchPlaylists() creates
      // a race condition where the store is temporarily cleared/replaced while
      // websocket updates for the new playlist's refresh task are arriving.
      await Promise.all([fetchChannelGroups(), fetchEPGs()]);

      // If this is an XC account with VOD enabled, also fetch VOD categories
      if (values.account_type === 'XC' && values.enable_vod) {
        fetchCategories();
      }

      console.log('opening group options');
      setPlaylist(updatedPlaylist);
      setGroupFilterModalOpen(true);
      return;
    }

    form.reset();
    setFile(null);
    onClose(newPlaylist);
  };

  const close = () => {
    form.reset();
    setFile(null);
    setPlaylist(null);
    onClose();
  };

  const closeGroupFilter = () => {
    setGroupFilterModalOpen(false);
    // After group filter setup for a new account, reset everything
    form.reset();
    setFile(null);
    setPlaylist(null);
    onClose();
  };

  const closeFilter = () => {
    setFilterModalOpen(false);
  };

  useEffect(() => {
    if (playlistCreated) {
      setGroupFilterModalOpen(true);
    }
  }, [playlist, playlistCreated]);

  // MAC Management Handlers
  const handleDeleteExpiredMacs = async () => {
    if (!playlist?.id) {
      return;
    }
    try {
      const res = await API.deleteExpiredMacs(playlist.id);
      const account = res.account || res;

      setPlaylist(account);
      form.setFieldValue('mac_address', account.mac_address ?? '');

      const deleted = res.deleted ?? 0;
      notifications.show({
        title: 'MACs updated',
        message: `${deleted} expired MAC(s) deleted.`,
      });
    } catch (e) {
      console.error(e);
      notifications.show({
        color: 'red',
        title: 'Error',
        message: 'Could not delete expired MACs.',
      });
    }
  };

  const handleDeleteMac = async (macId) => {
    if (!playlist?.id) return;

    try {
      const res = await API.deleteAccountMac(playlist.id, macId);
      const account = res.account || res;

      setPlaylist(account);
      form.setFieldValue('mac_address', account.mac_address ?? '');
      
      notifications.show({
        title: 'MAC deleted',
        message: 'MAC address has been removed.',
      });
    } catch (e) {
      console.error(e);
      notifications.show({
        color: 'red',
        title: 'Error',
        message: 'Could not delete MAC address.',
      });
    }
  };

  const handleMoveMac = async (macId, direction) => {
    if (!playlist?.id) return;

    const macs = playlist?.macs || [];
    const ids = macs.map((m) => m.id);
    const index = ids.indexOf(macId);
    if (index === -1) return;

    if (direction === 'up' && index > 0) {
      [ids[index - 1], ids[index]] = [ids[index], ids[index - 1]];
    } else if (direction === 'down' && index < ids.length - 1) {
      [ids[index + 1], ids[index]] = [ids[index], ids[index + 1]];
    } else {
      return;
    }

    try {
      const res = await API.reorderAccountMacs(playlist.id, ids);
      const account = res.account || res;

      setPlaylist(account);
      form.setFieldValue('mac_address', account.mac_address ?? '');
      
      notifications.show({
        title: 'MAC order updated',
        message: 'MAC priority order has been updated.',
      });
    } catch (e) {
      console.error(e);
      notifications.show({
        color: 'red',
        title: 'Error',
        message: 'Could not update MAC order.',
      });
    }
  };

  const handleRefreshMacStatus = async () => {
    if (!playlist?.id) return;

    try {
      // Trigger actual MAC status check via API
      await API.refreshMacStatus(playlist.id);
      
      // Wait a moment for the check to complete, then refresh playlist
      setTimeout(async () => {
        try {
          const updatedPlaylist = await API.getPlaylist(playlist.id);
          setPlaylist(updatedPlaylist);
        } catch (e) {
          console.error('Error refreshing playlist after MAC check:', e);
        }
      }, 2000);
      
      notifications.show({
        title: 'MAC status check initiated',
        message: 'Checking MAC address status...',
      });
    } catch (e) {
      console.error(e);
      notifications.show({
        color: 'red',
        title: 'Error',
        message: 'Could not refresh MAC status.',
      });
    }
  };

  const macs = playlist?.macs || [];

  if (!isOpen) {
    return <></>;
  }

  return (
    <>
      <Modal
        size={900}
        opened={isOpen}
        onClose={close}
        title="M3U Account"
        scrollAreaComponent={Modal.NativeScrollArea}
        lockScroll={false}
        withinPortal={true}
        trapFocus={false}
        yOffset="2vh"
      >
        <LoadingOverlay
          visible={form.submitting}
          overlayBlur={2}
          loaderProps={loadingText ? { children: loadingText } : {}}
        />

        <form onSubmit={form.onSubmit(onSubmit)}>
          <Group justify="space-between" align="top">
            <Stack gap="5" style={{ flex: 1 }}>
              <TextInput
                style={{ width: '100%' }}
                id="name"
                name="name"
                label="Name"
                description="Unique identifier for this M3U account"
                {...form.getInputProps('name')}
                key={form.key('name')}
              />
              <TextInput
                style={{ width: '100%' }}
                id="server_url"
                name="server_url"
                label="URL"
                description="Direct URL to the M3U playlist or server"
                {...form.getInputProps('server_url')}
                key={form.key('server_url')}
              />

              <Select
                id="account_type"
                name="account_type"
                label="Account Type"
                description={
                  <>
                    Standard for direct M3U URLs, <br />
                    Xtream Codes for panel-based services
                  </>
                }
                data={[
                  {
                    value: 'STD',
                    label: 'Standard',
                  },
                  {
                    value: 'XC',
                    label: 'Xtream Codes',
                  },
                  {
                    value: 'MAC',
                    label: 'MAC / STB-Portal',
                  },
                ]}
                key={form.key('account_type')}
                {...form.getInputProps('account_type')}
              />

              {form.getValues().account_type == 'XC' && (
                <Box>
                  {!m3uAccount && (
                    <Group justify="space-between">
                      <Box>Create EPG</Box>
                      <Switch
                        id="create_epg"
                        name="create_epg"
                        description="Automatically create matching EPG source for this Xtream account"
                        key={form.key('create_epg')}
                        {...form.getInputProps('create_epg', {
                          type: 'checkbox',
                        })}
                      />
                    </Group>
                  )}

                  <Group justify="space-between">
                    <Box>Enable VOD Scanning</Box>
                    <Switch
                      id="enable_vod"
                      name="enable_vod"
                      description="Scan and import VOD content (movies/series) from this Xtream account"
                      key={form.key('enable_vod')}
                      {...form.getInputProps('enable_vod', {
                        type: 'checkbox',
                      })}
                    />
                  </Group>

                  <TextInput
                    id="username"
                    name="username"
                    label="Username"
                    description="Username for Xtream Codes authentication"
                    {...form.getInputProps('username')}
                  />

                  <PasswordInput
                    id="password"
                    name="password"
                    label="Password"
                    description="Password for Xtream Codes authentication (leave empty to keep existing)"
                    {...form.getInputProps('password')}
                  />
                </Box>
              )}

              {form.getValues().account_type === 'MAC' && (
                <Box>
                  <TextInput
                    id="mac_address"
                    name="mac_address"
                    label="MAC Address(es)"
                    description="One or more MAC addresses (e.g. AA:BB:CC:DD:EE:FF, 11:22:33:44:55:66 or each MAC on a new line)"
                    {...form.getInputProps('mac_address')}
                    key={form.key('mac_address')}
                  />
                  
                  <TextInput
                    id="proxy"
                    name="proxy"
                    label="Proxy Server (Optional)"
                    description="Proxy server for portal connections (e.g. http://proxy:8080 or socks5://proxy:1080)"
                    {...form.getInputProps('proxy')}
                    key={form.key('proxy')}
                  />
                  
                  {macs.length > 0 && (
                    <Box mt="sm">
                      <Group justify="space-between" align="center" mb={4}>
                        <Group gap="xs" align="center">
                          <Box fw={500}>MAC Status</Box>
                          {isWebSocketReady && (
                            <Badge size="xs" color="green" variant="dot">
                              Live Updates
                            </Badge>
                          )}
                          {!isWebSocketReady && (
                            <Badge size="xs" color="gray" variant="dot">
                              Offline
                            </Badge>
                          )}
                        </Group>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="outline"
                            color="blue"
                            onClick={handleRefreshMacStatus}
                          >
                            Refresh Status
                          </Button>
                          <Button
                            size="xs"
                            variant="outline"
                            color="red"
                            onClick={handleDeleteExpiredMacs}
                          >
                            Delete Expired MACs
                          </Button>
                        </Group>
                      </Group>
                      <Table striped highlightOnHover withTableBorder withColumnBorders>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>#</Table.Th>
                            <Table.Th>MAC</Table.Th>
                            <Table.Th>Status</Table.Th>
                            <Table.Th>Valid Until</Table.Th>
                            <Table.Th>Actions</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {macs.map((mac, idx) => {
                            let color = 'gray';
                            if (mac.status === 'valid') color = 'green';
                            if (mac.status === 'expired') color = 'red';
                            if (mac.status === 'error') color = 'orange';

                            return (
                              <Table.Tr
                                key={mac.id || idx}
                                style={
                                  mac.status === 'expired'
                                    ? { color: theme.colors.red[6] }
                                    : undefined
                                }
                              >
                                <Table.Td>{mac.priority + 1}</Table.Td>
                                <Table.Td>{mac.address}</Table.Td>
                                <Table.Td>
                                  <Badge color={color} size="sm">
                                    {mac.status}
                                  </Badge>
                                </Table.Td>
                                <Table.Td>
                                  {mac.expires_text ||
                                    mac.expires_at ||
                                    'unknown'}
                                </Table.Td>
                                <Table.Td>
                                  <Group gap="xs" justify="flex-end">
                                    <ActionIcon
                                      color="red"
                                      variant="subtle"
                                      onClick={() => handleDeleteMac(mac.id)}
                                      title="Delete MAC"
                                    >
                                      ❌
                                    </ActionIcon>
                                    <ActionIcon
                                      variant="subtle"
                                      onClick={() => handleMoveMac(mac.id, 'up')}
                                      disabled={idx === 0}
                                      title="Move Up"
                                    >
                                      ↑
                                    </ActionIcon>
                                    <ActionIcon
                                      variant="subtle"
                                      onClick={() => handleMoveMac(mac.id, 'down')}
                                      disabled={idx === macs.length - 1}
                                      title="Move Down"
                                    >
                                      ↓
                                    </ActionIcon>
                                  </Group>
                                </Table.Td>
                              </Table.Tr>
                            );
                          })}
                        </Table.Tbody>
                      </Table>
                    </Box>
                  )}
                </Box>
              )}

              {form.getValues().account_type != 'XC' && form.getValues().account_type != 'MAC' && (
                <FileInput
                  id="file"
                  label="Upload files"
                  placeholder="Upload files"
                  description="Upload a local M3U file instead of using URL"
                  onChange={setFile}
                />
              )}
            </Stack>

            <Divider size="sm" orientation="vertical" />

            <Stack gap="5" style={{ flex: 1 }}>
              <TextInput
                style={{ width: '100%' }}
                id="max_streams"
                name="max_streams"
                label="Max Streams"
                placeholder="0 = Unlimited"
                description="Maximum number of concurrent streams (0 for unlimited)"
                {...form.getInputProps('max_streams')}
                key={form.key('max_streams')}
              />

              <Select
                id="user_agent"
                name="user_agent"
                label="User-Agent"
                description="User-Agent header to use when accessing this M3U source"
                {...form.getInputProps('user_agent')}
                key={form.key('user_agent')}
                data={[{ value: '0', label: '(Use Default)' }].concat(
                  userAgents.map((ua) => ({
                    label: ua.name,
                    value: `${ua.id}`,
                  }))
                )}
              />

              <NumberInput
                label="Refresh Interval (hours)"
                description={
                  <>
                    How often to automatically refresh M3U data
                    <br />
                    (0 to disable automatic refreshes)
                  </>
                }
                {...form.getInputProps('refresh_interval')}
                key={form.key('refresh_interval')}
              />

              <NumberInput
                min={0}
                max={365}
                label="Stale Stream Retention (days)"
                description="Streams not seen for this many days will be removed"
                {...form.getInputProps('stale_stream_days')}
              />

              <NumberInput
                min={0}
                max={999}
                label="VOD Priority"
                description="Priority for VOD provider selection (higher numbers = higher priority). Used when multiple providers offer the same content."
                {...form.getInputProps('priority')}
                key={form.key('priority')}
              />

              <Checkbox
                label="Is Active"
                description="Enable or disable this M3U account"
                {...form.getInputProps('is_active', { type: 'checkbox' })}
                key={form.key('is_active')}
              />
            </Stack>
          </Group>

          <Flex mih={50} gap="xs" justify="flex-end" align="flex-end">
            {playlist && (
              <>
                <Button
                  variant="filled"
                  size="sm"
                  onClick={() => setFilterModalOpen(true)}
                >
                  Filters
                </Button>
                <Button
                  variant="filled"
                  // color={theme.custom.colors.buttonPrimary}
                  size="sm"
                  onClick={() => {
                    // If this is an XC account with VOD enabled, fetch VOD categories
                    if (
                      m3uAccount?.account_type === 'XC' &&
                      m3uAccount?.enable_vod
                    ) {
                      fetchCategories();
                    }
                    setGroupFilterModalOpen(true);
                  }}
                >
                  Groups
                </Button>
                <Button
                  variant="filled"
                  // color={theme.custom.colors.buttonPrimary}
                  size="sm"
                  onClick={() => setProfileModalOpen(true)}
                >
                  Profiles
                </Button>
              </>
            )}

            <Button
              type="submit"
              variant="filled"
              disabled={form.submitting}
              size="sm"
            >
              Save
            </Button>
          </Flex>
        </form>
      </Modal>
      {playlist && (
        <>
          <M3UProfiles
            playlist={playlist}
            isOpen={profileModalOpen}
            onClose={() => setProfileModalOpen(false)}
          />
          <M3UGroupFilter
            isOpen={groupFilterModalOpen}
            playlist={playlist}
            onClose={closeGroupFilter}
          />
          <M3UFilters
            isOpen={filterModalOpen}
            playlist={playlist}
            onClose={closeFilter}
          />
        </>
      )}
    </>
  );
};

export default M3U;
