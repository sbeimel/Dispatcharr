/**
 * Failover Test Page - Klon der Channels-Seite mit Failover-Test-Funktionen
 * 
 * Features:
 * - Channels-Tabelle wie im Channels-Tab
 * - Vorschau-Funktion (Video Player)
 * - Kill FFmpeg Button - beendet den aktiven Stream
 * - Simulate Error Button - simuliert verschiedene Fehler
 * - Live Log für Failover-Events
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Title,
  Paper,
  Stack,
  Group,
  Button,
  Badge,
  Text,
  Table,
  ActionIcon,
  TextInput,
  Select,
  Pagination,
  ScrollArea,
  Tooltip,
  Modal,
  Alert,
  Loader,
  Switch,
  Center,
  Flex,
  NativeSelect,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconRefresh,
  IconPlayerStop,
  IconAlertTriangle,
  IconSearch,
  IconTrash,
  IconActivity,
  IconWifi,
  IconWifiOff,
  IconBolt,
  IconPlayerPlay,
  IconX,
  IconChevronDown,
  IconChevronRight,
} from '@tabler/icons-react';
import { CirclePlay, SquareMinus } from 'lucide-react';
import API from '../../api';
import useVideoStore from '../../store/useVideoStore';
import useSettingsStore from '../../store/settings';

const FailoverTestPage = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState([]);
  const [activeStreams, setActiveStreams] = useState({});
  const [logEntries, setLogEntries] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [wsConnected, setWsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [killingStream, setKillingStream] = useState(null);
  const [simulatingError, setSimulatingError] = useState(null);
  const [expandedChannels, setExpandedChannels] = useState(new Set());
  const [channelStreams, setChannelStreams] = useState({});

  // Video Store für Vorschau
  const showVideo = useVideoStore((s) => s.showVideo);
  const env_mode = useSettingsStore((s) => s.environment?.env_mode);

  // WebSocket für Live Logs
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/failover-test/`;
      
      try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          setWsConnected(true);
          addLogEntry('system', 'WebSocket verbunden - Live Logs aktiv');
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'log_entry' || data.type === 'failover_event') {
              setLogEntries(prev => [data.data, ...prev].slice(0, 500));
            } else if (data.type === 'stream_status') {
              setActiveStreams(prev => ({
                ...prev,
                [data.data.channel_id]: data.data,
              }));
            }
          } catch (e) {
            console.error('WebSocket parse error:', e);
          }
        };
        
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connect, 3000);
        };
        
        ws.onerror = () => ws.close();
      } catch (e) {
        console.log('WebSocket not available');
      }
    };

    connect();
    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Helper: Log Entry hinzufügen
  const addLogEntry = (type, message, extra = {}) => {
    setLogEntries(prev => [{
      id: Date.now(),
      timestamp: new Date().toISOString(),
      event_type: type,
      message,
      ...extra,
    }, ...prev].slice(0, 500));
  };

  // Channels laden
  const loadChannels = useCallback(async () => {
    setLoading(true);
    try {
      const response = await API.getChannels();
      setChannels(response || []);
      
      // Active Streams laden
      try {
        const host = import.meta.env.DEV ? `http://${window.location.hostname}:5656` : '';
        const streamsResponse = await fetch(`${host}/api/proxy/active-streams/`, {
          headers: { Authorization: `Bearer ${await API.getAuthToken()}` },
        });
        if (streamsResponse.ok) {
          const streams = await streamsResponse.json();
          const streamMap = {};
          (streams || []).forEach(s => {
            streamMap[s.channel_id] = s;
          });
          setActiveStreams(streamMap);
        }
      } catch (e) {
        console.log('Could not load active streams');
      }
    } catch (error) {
      notifications.show({ title: 'Fehler', message: 'Channels konnten nicht geladen werden', color: 'red' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadChannels(); }, [loadChannels]);

  // Filter & Pagination
  const filteredChannels = useMemo(() => {
    if (!search) return channels;
    const s = search.toLowerCase();
    return channels.filter(ch => 
      ch.name?.toLowerCase().includes(s) || ch.channel_number?.toString().includes(s)
    );
  }, [channels, search]);

  const paginatedChannels = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredChannels.slice(start, start + pageSize);
  }, [filteredChannels, page, pageSize]);

  const totalPages = Math.ceil(filteredChannels.length / pageSize);

  // Channel URL generieren
  const getChannelURL = (channel) => {
    if (!channel?.uuid) return '';
    const uri = `/proxy/ts/stream/${channel.uuid}`;
    const host = env_mode === 'dev' 
      ? `${window.location.protocol}//${window.location.hostname}:5656`
      : `${window.location.protocol}//${window.location.host}`;
    return `${host}${uri}`;
  };

  // Vorschau starten
  const handleWatchStream = (channel) => {
    const url = getChannelURL(channel);
    addLogEntry('preview', `Vorschau gestartet: ${channel.name}`, { channel_id: channel.id });
    showVideo(url);
  };


  // Kill FFmpeg - Stream beenden
  const killStream = async (channel) => {
    setKillingStream(channel.id);
    try {
      const host = import.meta.env.DEV ? `http://${window.location.hostname}:5656` : '';
      const response = await fetch(`${host}/api/proxy/kill-stream/${channel.id}/`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${await API.getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        addLogEntry('stream_killed', `FFmpeg beendet für: ${channel.name}`, { 
          channel_id: channel.id,
          success: true 
        });
        notifications.show({
          title: 'Stream beendet',
          message: `FFmpeg für "${channel.name}" wurde beendet. Failover sollte starten.`,
          color: 'orange',
        });
        setTimeout(loadChannels, 1000);
      } else {
        throw new Error('Kill failed');
      }
    } catch (error) {
      addLogEntry('error', `Fehler beim Beenden: ${channel.name}`, { channel_id: channel.id });
      notifications.show({ title: 'Fehler', message: 'Stream konnte nicht beendet werden', color: 'red' });
    } finally {
      setKillingStream(null);
    }
  };

  // Simulate Error - verschiedene Fehlertypen simulieren
  const simulateError = async (channel, errorType = 'timeout') => {
    setSimulatingError(channel.id);
    try {
      const host = import.meta.env.DEV ? `http://${window.location.hostname}:5656` : '';
      const response = await fetch(`${host}/api/proxy/simulate-error/${channel.id}/`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${await API.getAuthToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ error_type: errorType }),
      });
      
      if (response.ok) {
        const result = await response.json();
        addLogEntry('error_simulated', `Fehler simuliert (${errorType}): ${channel.name}`, { 
          channel_id: channel.id,
          error_type: errorType,
        });
        notifications.show({
          title: 'Fehler simuliert',
          message: `${errorType} Fehler für "${channel.name}" ausgelöst`,
          color: 'yellow',
        });
      } else {
        // Fallback: Lokale Simulation
        addLogEntry('error_simulated', `Fehler simuliert (lokal): ${channel.name}`, { 
          channel_id: channel.id,
          error_type: errorType,
        });
        notifications.show({
          title: 'Fehler simuliert (lokal)',
          message: `${errorType} Fehler für "${channel.name}" - API nicht verfügbar`,
          color: 'yellow',
        });
      }
    } catch (error) {
      // Lokale Simulation als Fallback
      addLogEntry('error_simulated', `Fehler simuliert (lokal): ${channel.name}`, { 
        channel_id: channel.id,
        error_type: errorType,
      });
    } finally {
      setSimulatingError(null);
    }
  };

  // Streams für Channel laden
  const toggleExpand = async (channelId) => {
    const isExpanded = expandedChannels.has(channelId);
    setExpandedChannels(prev => {
      const next = new Set(prev);
      isExpanded ? next.delete(channelId) : next.add(channelId);
      return next;
    });

    if (!isExpanded && !channelStreams[channelId]) {
      try {
        const streams = await API.getChannelStreams(channelId);
        setChannelStreams(prev => ({ ...prev, [channelId]: streams || [] }));
      } catch (e) {
        console.log('Could not load streams');
      }
    }
  };

  // Logs löschen
  const clearLogs = () => setLogEntries([]);

  // Zeit formatieren
  const formatTime = (ts) => ts ? new Date(ts).toLocaleTimeString('de-DE') : '';

  // Event Farbe
  const getEventColor = (entry) => {
    const colors = {
      failover_success: 'green',
      failover_failed: 'red',
      stream_killed: 'orange',
      error_simulated: 'yellow',
      reconnect: 'blue',
      preview: 'cyan',
      system: 'gray',
    };
    return colors[entry.event_type] || 'gray';
  };


  return (
    <Box p="md">
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Group>
          <Title order={2}>Failover Test</Title>
          <Badge color={wsConnected ? 'green' : 'red'} variant="dot" size="lg">
            {wsConnected ? 'Live' : 'Offline'}
          </Badge>
        </Group>
        <Button
          variant="outline"
          leftSection={<IconRefresh size={16} />}
          onClick={loadChannels}
          loading={loading}
        >
          Aktualisieren
        </Button>
      </Group>

      <Alert color="blue" mb="md" icon={<IconActivity size={16} />}>
        Wähle einen Kanal und nutze die Test-Buttons: <strong>Vorschau</strong> startet den Stream, 
        <strong> Kill FFmpeg</strong> beendet den aktiven Prozess, <strong>Fehler simulieren</strong> stoppt den Stream für Failover-Test.
        Beobachte das Live Log für Failover-Events.
      </Alert>

      <Box style={{ display: 'flex', gap: '16px', height: 'calc(100vh - 220px)' }}>
        {/* Links: Channels Tabelle */}
        <Paper shadow="xs" p="md" style={{ flex: 2, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Group justify="space-between" mb="md">
            <Text fw={600}>Channels ({filteredChannels.length})</Text>
            <TextInput
              placeholder="Suchen..."
              leftSection={<IconSearch size={14} />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 250 }}
            />
          </Group>

          <ScrollArea style={{ flex: 1 }}>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: 40 }}></Table.Th>
                  <Table.Th style={{ width: 60 }}>#</Table.Th>
                  <Table.Th>Name</Table.Th>
                  <Table.Th style={{ width: 100 }}>Status</Table.Th>
                  <Table.Th style={{ width: 200 }}>Aktionen</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {paginatedChannels.map(channel => {
                  const isActive = activeStreams[channel.id];
                  const isExpanded = expandedChannels.has(channel.id);
                  
                  return (
                    <React.Fragment key={channel.id}>
                      <Table.Tr>
                        <Table.Td>
                          <ActionIcon variant="subtle" size="sm" onClick={() => toggleExpand(channel.id)}>
                            {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                          </ActionIcon>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" c="dimmed">{channel.channel_number}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={500}>{channel.name}</Text>
                        </Table.Td>
                        <Table.Td>
                          {isActive ? (
                            <Badge color="green" leftSection={<IconWifi size={10} />}>Aktiv</Badge>
                          ) : (
                            <Badge color="gray" leftSection={<IconWifiOff size={10} />}>Idle</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {/* Vorschau Button */}
                            <Tooltip label="Vorschau starten">
                              <ActionIcon
                                color="green"
                                variant="light"
                                onClick={() => handleWatchStream(channel)}
                              >
                                <CirclePlay size={16} />
                              </ActionIcon>
                            </Tooltip>

                            {/* Kill FFmpeg Button */}
                            <Tooltip label="Kill FFmpeg (Stream beenden)">
                              <ActionIcon
                                color="red"
                                variant="light"
                                onClick={() => killStream(channel)}
                                loading={killingStream === channel.id}
                                disabled={!isActive}
                              >
                                <IconPlayerStop size={16} />
                              </ActionIcon>
                            </Tooltip>

                            {/* Simulate Error Button */}
                            <Tooltip label="Stream-Fehler simulieren">
                              <ActionIcon
                                color="orange"
                                variant="light"
                                loading={simulatingError === channel.id}
                                onClick={() => simulateError(channel)}
                              >
                                <IconBolt size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                      
                      {/* Expanded: Streams anzeigen */}
                      {isExpanded && (
                        <Table.Tr>
                          <Table.Td colSpan={5} style={{ background: 'var(--mantine-color-dark-7)', padding: '8px 16px' }}>
                            <Text size="xs" c="dimmed" mb="xs">Streams für diesen Kanal:</Text>
                            {channelStreams[channel.id]?.length > 0 ? (
                              <Stack gap="xs">
                                {channelStreams[channel.id].map((stream, idx) => (
                                  <Group key={stream.id || idx} gap="xs">
                                    <Badge size="xs" color={idx === 0 ? 'blue' : 'gray'}>
                                      {idx === 0 ? 'Primary' : `Backup ${idx}`}
                                    </Badge>
                                    <Text size="xs" ff="monospace" style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                      {stream.url || stream.m3u_account?.name || 'Unknown'}
                                    </Text>
                                  </Group>
                                ))}
                              </Stack>
                            ) : channelStreams[channel.id] === undefined ? (
                              <Loader size="xs" />
                            ) : (
                              <Text size="xs" c="dimmed">Keine Streams konfiguriert</Text>
                            )}
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          {/* Pagination */}
          <Group justify="space-between" mt="md">
            <NativeSelect
              value={pageSize.toString()}
              onChange={(e) => setPageSize(parseInt(e.target.value))}
              data={['25', '50', '100', '200']}
              style={{ width: 80 }}
              size="xs"
            />
            <Pagination total={totalPages} value={page} onChange={setPage} size="sm" />
          </Group>
        </Paper>

        {/* Rechts: Live Log */}
        <Paper shadow="xs" p="md" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Group justify="space-between" mb="md">
            <Text fw={600}>Live Log</Text>
            <Group gap="xs">
              <Switch label="Auto-scroll" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} size="xs" />
              <ActionIcon variant="subtle" onClick={clearLogs}><IconTrash size={14} /></ActionIcon>
            </Group>
          </Group>

          <ScrollArea style={{ flex: 1 }} viewportRef={(ref) => {
            if (ref && autoScroll && logEntries.length > 0) ref.scrollTop = 0;
          }}>
            <Stack gap="xs">
              {logEntries.length === 0 ? (
                <Text size="sm" c="dimmed" ta="center" py="xl">
                  Noch keine Events. Starte eine Vorschau oder beende einen Stream.
                </Text>
              ) : (
                logEntries.map((entry, idx) => (
                  <Paper key={entry.id || idx} p="xs" withBorder style={{ borderLeftWidth: 3, borderLeftColor: `var(--mantine-color-${getEventColor(entry)}-6)` }}>
                    <Group justify="space-between" mb={4}>
                      <Badge size="xs" color={getEventColor(entry)}>{entry.event_type}</Badge>
                      <Text size="xs" c="dimmed">{formatTime(entry.timestamp)}</Text>
                    </Group>
                    <Text size="xs">{entry.message}</Text>
                    {entry.channel_id && <Text size="xs" c="dimmed">Channel ID: {entry.channel_id}</Text>}
                    {entry.error_type && <Text size="xs" c="dimmed">Error Type: {entry.error_type}</Text>}
                  </Paper>
                ))
              )}
            </Stack>
          </ScrollArea>
        </Paper>
      </Box>
    </Box>
  );
};

export default FailoverTestPage;
