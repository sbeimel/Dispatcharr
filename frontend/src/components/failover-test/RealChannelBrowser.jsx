/**
 * Real Channel Browser Component
 * 
 * Displays real channels and streams from the database for failover testing.
 * Similar to the Channels page but optimized for failover test selection.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Badge,
  Paper,
  Table,
  TextInput,
  Select,
  Checkbox,
  ActionIcon,
  Loader,
  Alert,
  Pagination,
  Collapse,
  ThemeIcon,
  ScrollArea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconSearch,
  IconRefresh,
  IconChevronDown,
  IconChevronUp,
  IconPlus,
  IconPlayerPlay,
  IconDeviceTv,
  IconList,
  IconAlertCircle,
} from '@tabler/icons-react';
import API from '../../api';

const RealChannelBrowser = ({ onImportChannel, onCreateTestFromChannel }) => {
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState([]);
  const [streams, setStreams] = useState([]);
  const [playlists, setPlaylists] = useState([]);
  const [channelGroups, setChannelGroups] = useState([]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlaylist, setSelectedPlaylist] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(25);
  
  // Selection
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [expandedChannel, setExpandedChannel] = useState(null);
  
  // View mode
  const [viewMode, setViewMode] = useState('channels'); // 'channels' or 'streams'

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (viewMode === 'channels') {
      loadChannels();
    } else {
      loadStreams();
    }
  }, [page, searchQuery, selectedPlaylist, selectedGroup, viewMode]);

  const loadInitialData = async () => {
    try {
      const [playlistsRes, groupsRes] = await Promise.all([
        API.getPlaylists(),
        API.getChannelGroups(),
      ]);
      setPlaylists(playlistsRes || []);
      setChannelGroups(groupsRes || []);
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const loadChannels = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      if (selectedGroup) {
        params.append('channel_group', selectedGroup);
      }
      
      const response = await API.queryChannels(params);
      setChannels(response?.results || response || []);
      setTotalPages(Math.ceil((response?.count || response?.length || 0) / pageSize));
    } catch (error) {
      console.error('Failed to load channels:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load channels',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadStreams = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      if (selectedPlaylist) {
        params.append('m3u_account', selectedPlaylist);
      }
      
      const response = await API.queryStreams(params);
      setStreams(response?.results || response || []);
      setTotalPages(Math.ceil((response?.count || response?.length || 0) / pageSize));
    } catch (error) {
      console.error('Failed to load streams:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load streams',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadChannelStreams = async (channelId) => {
    try {
      const streams = await API.getChannelStreams(channelId);
      return streams || [];
    } catch (error) {
      console.error('Failed to load channel streams:', error);
      return [];
    }
  };

  const handleExpandChannel = async (channelId) => {
    if (expandedChannel === channelId) {
      setExpandedChannel(null);
    } else {
      setExpandedChannel(channelId);
    }
  };

  const handleSelectChannel = (channelId) => {
    setSelectedChannels(prev => {
      if (prev.includes(channelId)) {
        return prev.filter(id => id !== channelId);
      }
      return [...prev, channelId];
    });
  };

  const handleSelectAll = () => {
    if (selectedChannels.length === channels.length) {
      setSelectedChannels([]);
    } else {
      setSelectedChannels(channels.map(c => c.id));
    }
  };

  const handleImportSelected = () => {
    if (selectedChannels.length === 0) {
      notifications.show({
        title: 'Warning',
        message: 'Please select at least one channel',
        color: 'yellow',
      });
      return;
    }
    
    const channelsToImport = channels.filter(c => selectedChannels.includes(c.id));
    onImportChannel?.(channelsToImport);
  };

  const handleCreateTest = (channel) => {
    onCreateTestFromChannel?.(channel);
  };

  const getPlaylistName = (accountId) => {
    const playlist = playlists.find(p => p.id === accountId);
    return playlist?.name || 'Unknown';
  };

  const getGroupName = (groupId) => {
    const group = channelGroups.find(g => g.id === groupId);
    return group?.name || 'Unknown';
  };

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Group>
          <Title order={4}>
            {viewMode === 'channels' ? 'Channels' : 'Streams'}
          </Title>
          <Badge>{viewMode === 'channels' ? channels.length : streams.length}</Badge>
        </Group>
        <Group>
          <Button.Group>
            <Button
              variant={viewMode === 'channels' ? 'filled' : 'outline'}
              size="xs"
              leftSection={<IconDeviceTv size={14} />}
              onClick={() => { setViewMode('channels'); setPage(1); }}
            >
              Channels
            </Button>
            <Button
              variant={viewMode === 'streams' ? 'filled' : 'outline'}
              size="xs"
              leftSection={<IconList size={14} />}
              onClick={() => { setViewMode('streams'); setPage(1); }}
            >
              Streams
            </Button>
          </Button.Group>
          <ActionIcon variant="subtle" onClick={viewMode === 'channels' ? loadChannels : loadStreams}>
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>
      </Group>

      {/* Filters */}
      <Paper withBorder p="sm" mb="md">
        <Group>
          <TextInput
            placeholder="Search..."
            leftSection={<IconSearch size={14} />}
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            style={{ flex: 1 }}
          />
          {viewMode === 'channels' ? (
            <Select
              placeholder="All Groups"
              data={[
                { value: '', label: 'All Groups' },
                ...channelGroups.map(g => ({ value: g.id.toString(), label: g.name }))
              ]}
              value={selectedGroup || ''}
              onChange={(val) => { setSelectedGroup(val || null); setPage(1); }}
              clearable
              w={200}
            />
          ) : (
            <Select
              placeholder="All Playlists"
              data={[
                { value: '', label: 'All Playlists' },
                ...playlists.map(p => ({ value: p.id.toString(), label: p.name }))
              ]}
              value={selectedPlaylist || ''}
              onChange={(val) => { setSelectedPlaylist(val || null); setPage(1); }}
              clearable
              w={200}
            />
          )}
        </Group>
      </Paper>

      {/* Selection Actions */}
      {viewMode === 'channels' && selectedChannels.length > 0 && (
        <Paper withBorder p="sm" mb="md" bg="blue.0">
          <Group justify="space-between">
            <Text size="sm">
              {selectedChannels.length} channel(s) selected
            </Text>
            <Button
              size="xs"
              leftSection={<IconPlus size={14} />}
              onClick={handleImportSelected}
            >
              Import to Failover Test
            </Button>
          </Group>
        </Paper>
      )}

      {/* Content */}
      {loading ? (
        <Paper withBorder p="xl" ta="center">
          <Loader size="lg" />
          <Text mt="md" c="dimmed">Loading...</Text>
        </Paper>
      ) : viewMode === 'channels' ? (
        <ChannelsList
          channels={channels}
          selectedChannels={selectedChannels}
          expandedChannel={expandedChannel}
          onSelectChannel={handleSelectChannel}
          onSelectAll={handleSelectAll}
          onExpandChannel={handleExpandChannel}
          onCreateTest={handleCreateTest}
          getGroupName={getGroupName}
          loadChannelStreams={loadChannelStreams}
        />
      ) : (
        <StreamsList
          streams={streams}
          getPlaylistName={getPlaylistName}
          onCreateTest={handleCreateTest}
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Group justify="center" mt="md">
          <Pagination
            value={page}
            onChange={setPage}
            total={totalPages}
            size="sm"
          />
        </Group>
      )}
    </Box>
  );
};

// Channels List Sub-Component
const ChannelsList = ({
  channels,
  selectedChannels,
  expandedChannel,
  onSelectChannel,
  onSelectAll,
  onExpandChannel,
  onCreateTest,
  getGroupName,
  loadChannelStreams,
}) => {
  const [channelStreams, setChannelStreams] = useState({});

  const handleExpand = async (channelId) => {
    if (!channelStreams[channelId]) {
      const streams = await loadChannelStreams(channelId);
      setChannelStreams(prev => ({ ...prev, [channelId]: streams }));
    }
    onExpandChannel(channelId);
  };

  if (channels.length === 0) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="blue">
        No channels found. Try adjusting your filters.
      </Alert>
    );
  }

  return (
    <ScrollArea h={500}>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={40}>
              <Checkbox
                checked={selectedChannels.length === channels.length && channels.length > 0}
                indeterminate={selectedChannels.length > 0 && selectedChannels.length < channels.length}
                onChange={onSelectAll}
              />
            </Table.Th>
            <Table.Th w={40}></Table.Th>
            <Table.Th>Channel</Table.Th>
            <Table.Th>Group</Table.Th>
            <Table.Th>Streams</Table.Th>
            <Table.Th w={100}>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {channels.map((channel) => (
            <React.Fragment key={channel.id}>
              <Table.Tr>
                <Table.Td>
                  <Checkbox
                    checked={selectedChannels.includes(channel.id)}
                    onChange={() => onSelectChannel(channel.id)}
                  />
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    size="sm"
                    onClick={() => handleExpand(channel.id)}
                  >
                    {expandedChannel === channel.id ? (
                      <IconChevronUp size={14} />
                    ) : (
                      <IconChevronDown size={14} />
                    )}
                  </ActionIcon>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {channel.logo_url && (
                      <img
                        src={channel.logo_url}
                        alt=""
                        style={{ width: 24, height: 24, objectFit: 'contain' }}
                      />
                    )}
                    <div>
                      <Text size="sm" fw={500}>{channel.name}</Text>
                      {channel.channel_number && (
                        <Text size="xs" c="dimmed">#{channel.channel_number}</Text>
                      )}
                    </div>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="outline">
                    {getGroupName(channel.channel_group)}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" color="blue">
                    {channel.stream_count || 0}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<IconPlus size={12} />}
                    onClick={() => onCreateTest(channel)}
                  >
                    Test
                  </Button>
                </Table.Td>
              </Table.Tr>
              
              {/* Expanded Streams */}
              {expandedChannel === channel.id && (
                <Table.Tr>
                  <Table.Td colSpan={6} p={0}>
                    <Box bg="gray.0" p="sm">
                      <Text size="sm" fw={500} mb="xs">Streams:</Text>
                      {channelStreams[channel.id]?.length > 0 ? (
                        <Stack gap="xs">
                          {channelStreams[channel.id].map((stream, idx) => (
                            <Paper key={stream.id || idx} withBorder p="xs">
                              <Group justify="space-between">
                                <div>
                                  <Text size="sm">{stream.name || `Stream ${idx + 1}`}</Text>
                                  <Text size="xs" c="dimmed" truncate maw={400}>
                                    {stream.url}
                                  </Text>
                                </div>
                                <Badge size="xs" color={stream.is_active ? 'green' : 'gray'}>
                                  {stream.is_active ? 'Active' : 'Inactive'}
                                </Badge>
                              </Group>
                            </Paper>
                          ))}
                        </Stack>
                      ) : (
                        <Text size="sm" c="dimmed">No streams available</Text>
                      )}
                    </Box>
                  </Table.Td>
                </Table.Tr>
              )}
            </React.Fragment>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
};

// Streams List Sub-Component
const StreamsList = ({ streams, getPlaylistName, onCreateTest }) => {
  if (streams.length === 0) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="blue">
        No streams found. Try adjusting your filters.
      </Alert>
    );
  }

  return (
    <ScrollArea h={500}>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Stream</Table.Th>
            <Table.Th>Playlist</Table.Th>
            <Table.Th>Group</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th w={100}>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {streams.map((stream) => (
            <Table.Tr key={stream.id}>
              <Table.Td>
                <div>
                  <Text size="sm" fw={500}>{stream.name}</Text>
                  <Text size="xs" c="dimmed" truncate maw={300}>
                    {stream.url}
                  </Text>
                </div>
              </Table.Td>
              <Table.Td>
                <Badge size="sm" variant="outline">
                  {getPlaylistName(stream.m3u_account)}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{stream.group_title || '-'}</Text>
              </Table.Td>
              <Table.Td>
                <Badge size="sm" color={stream.is_active ? 'green' : 'gray'}>
                  {stream.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Button
                  size="xs"
                  variant="light"
                  leftSection={<IconPlus size={12} />}
                  onClick={() => onCreateTest({ 
                    name: stream.name, 
                    primary_stream_url: stream.url,
                    stream_id: stream.id,
                  })}
                >
                  Test
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
};

export default RealChannelBrowser;
