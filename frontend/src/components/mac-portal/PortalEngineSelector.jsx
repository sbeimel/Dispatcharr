/**
 * Portal Engine Selector Component
 * 
 * Allows selection of the portal authentication engine.
 * Combines strategies from MacReplay, EStalker, BoxPirate, and OB2_2025.
 * 
 * Requirements: 100.1
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Text,
  Select,
  Paper,
  Badge,
  Group,
  Alert,
  ThemeIcon,
  Button,
  Loader,
  Table,
  Progress,
} from '@mantine/core';
import {
  IconRocket,
  IconBrandPython,
  IconDeviceTv,
  IconFlask,
  IconInfoCircle,
  IconPlayerPlay,
  IconCheck,
  IconX,
  IconBolt,
  IconTrash,
} from '@tabler/icons-react';
import API from '../../api';

const PORTAL_ENGINES = [
  {
    value: 'auto',
    label: 'Auto-Detect (Recommended)',
    description: 'Automatically tries all strategies and caches the first working one',
    icon: IconRocket,
    color: 'green',
    badge: 'Recommended',
  },
  {
    value: 'fastest',
    label: 'Fastest (Benchmarked)',
    description: 'Uses the fastest benchmarked engine per portal. Run benchmark first!',
    icon: IconBolt,
    color: 'yellow',
    badge: 'Benchmark',
  },
  {
    value: 'allinone',
    label: 'AllinOne Best-of-All',
    description: 'Combines the best techniques from all engines: prehash, signature, api_signature 263, User-Agent rotation',
    icon: IconRocket,
    color: 'teal',
    badge: 'Best-of-All',
  },
  {
    value: 'macreplay',
    label: 'MacReplayXC (Standard)',
    description: 'Standard GET/POST fallback strategy from MacReplayXC v2.2.1',
    icon: IconDeviceTv,
    color: 'cyan',
    badge: 'Standard',
  },
  {
    value: 'estalker',
    label: 'EStalker (Enigma2 Style)',
    description: 'Extended metrics with prehash support, MAG254 style',
    icon: IconBrandPython,
    color: 'violet',
    badge: null,
  },
  {
    value: 'boxpirate',
    label: 'BoxPirate (Dreambox Style)',
    description: 'Dreambox-style authentication with signature',
    icon: IconDeviceTv,
    color: 'orange',
    badge: null,
  },
  {
    value: 'ob2_2025',
    label: 'OB2_2025 (Extended Metrics)',
    description: 'Extended checking logic with api_signature 263',
    icon: IconFlask,
    color: 'yellow',
    badge: 'Experimental',
  },
  {
    value: 'istb',
    label: 'iSTB (iOS Emulator)',
    description: 'iOS STB Emulator style with prehash, metrics, hw_version_2, api_signature 263',
    icon: IconDeviceTv,
    color: 'pink',
    badge: 'New',
  },
  {
    value: 'macattack',
    label: 'MacAttack (X-Random)',
    description: 'MacAttack v4.7.6 style with X-Random header, api_sig 262, auth_second_step 1',
    icon: IconFlask,
    color: 'red',
    badge: 'New',
  },
];

const PortalEngineSelector = ({ value, onChange, disabled = false, accountId = null }) => {
  const selectedEngine = PORTAL_ENGINES.find(e => e.value === value) || PORTAL_ENGINES[0];
  const IconComponent = selectedEngine.icon;
  
  // Benchmark state
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkResults, setBenchmarkResults] = useState(null);
  const [cachedBenchmark, setCachedBenchmark] = useState(null);
  const [loadingCache, setLoadingCache] = useState(false);
  
  // Load cached benchmark on mount
  useEffect(() => {
    if (accountId) {
      loadCachedBenchmark();
    }
  }, [accountId]);
  
  const loadCachedBenchmark = async () => {
    if (!accountId) return;
    setLoadingCache(true);
    try {
      const response = await API.get(`/api/m3u/accounts/${accountId}/engine-benchmark/`);
      setCachedBenchmark(response.data);
    } catch (error) {
      console.error('Failed to load cached benchmark:', error);
    } finally {
      setLoadingCache(false);
    }
  };
  
  const runBenchmark = async () => {
    if (!accountId) {
      alert('Account ID required for benchmark');
      return;
    }
    
    setBenchmarkRunning(true);
    setBenchmarkResults(null);
    
    try {
      const response = await API.post(`/api/m3u/accounts/${accountId}/engine-benchmark/`);
      setBenchmarkResults(response.data);
      // Refresh cached data
      loadCachedBenchmark();
    } catch (error) {
      console.error('Benchmark failed:', error);
      setBenchmarkResults({ error: error.response?.data?.error || 'Benchmark failed' });
    } finally {
      setBenchmarkRunning(false);
    }
  };
  
  const clearBenchmark = async () => {
    if (!accountId) return;
    
    try {
      await API.delete(`/api/m3u/accounts/${accountId}/engine-benchmark/?action=all`);
      setCachedBenchmark(null);
      setBenchmarkResults(null);
    } catch (error) {
      console.error('Failed to clear benchmark:', error);
    }
  };
  
  const refreshAutoCache = async () => {
    if (!accountId) return;
    
    try {
      await API.delete(`/api/m3u/accounts/${accountId}/engine-benchmark/?action=auto`);
      // Refresh cached data to show updated state
      loadCachedBenchmark();
    } catch (error) {
      console.error('Failed to refresh auto cache:', error);
    }
  };

  return (
    <Stack gap="md">
      <Paper withBorder p="md">
        <Group gap="sm" mb="sm">
          <ThemeIcon color={selectedEngine.color} variant="light" size="lg">
            <IconComponent size={20} />
          </ThemeIcon>
          <div>
            <Group gap="xs">
              <Text fw={500}>Portal Authentication Engine</Text>
              {selectedEngine.badge && (
                <Badge size="xs" color={selectedEngine.color} variant="light">
                  {selectedEngine.badge}
                </Badge>
              )}
            </Group>
            <Text size="xs" c="dimmed">
              Select the authentication strategy for MAC/STB portals
            </Text>
          </div>
        </Group>

        <Select
          value={value}
          onChange={onChange}
          disabled={disabled}
          data={PORTAL_ENGINES.map(engine => ({
            value: engine.value,
            label: engine.label,
          }))}
          placeholder="Select engine"
        />

        <Text size="sm" c="dimmed" mt="sm">
          {selectedEngine.description}
        </Text>
      </Paper>
      
      {/* Benchmark Section */}
      {accountId && (
        <Paper withBorder p="md">
          <Group justify="space-between" mb="sm">
            <Group gap="xs">
              <ThemeIcon color="yellow" variant="light" size="lg">
                <IconBolt size={20} />
              </ThemeIcon>
              <div>
                <Text fw={500}>Engine Benchmark</Text>
                <Text size="xs" c="dimmed">
                  Test all engines and find the fastest one for this portal
                </Text>
              </div>
            </Group>
            <Group gap="xs">
              <Button
                size="xs"
                variant="light"
                color="red"
                leftSection={<IconTrash size={14} />}
                onClick={clearBenchmark}
                disabled={benchmarkRunning || (!cachedBenchmark?.has_benchmark && !benchmarkResults)}
              >
                Clear
              </Button>
              <Button
                size="xs"
                leftSection={benchmarkRunning ? <Loader size={14} /> : <IconPlayerPlay size={14} />}
                onClick={runBenchmark}
                disabled={benchmarkRunning}
                loading={benchmarkRunning}
              >
                {benchmarkRunning ? 'Running...' : 'Run Benchmark'}
              </Button>
            </Group>
          </Group>
          
          {/* Cached Auto Engine Info */}
          {cachedBenchmark?.cached_auto_engine && !benchmarkResults && (
            <Alert color="cyan" variant="light" mb="sm">
              <Group justify="space-between">
                <Group gap="xs">
                  <IconCheck size={16} />
                  <Text size="sm">
                    Auto-detected engine: <strong>{cachedBenchmark.cached_auto_engine}</strong>
                    {' '}(cached indefinitely until refresh)
                  </Text>
                </Group>
                <Button size="xs" variant="subtle" color="cyan" onClick={refreshAutoCache}>
                  Refresh
                </Button>
              </Group>
            </Alert>
          )}
          
          {/* Cached Benchmark Info */}
          {cachedBenchmark?.has_benchmark && !benchmarkResults && (
            <Alert color="green" variant="light" mb="sm">
              <Group gap="xs">
                <IconCheck size={16} />
                <Text size="sm">
                  Fastest engine (benchmark): <strong>{cachedBenchmark.fastest_engine?.engine}</strong>
                  {' '}({cachedBenchmark.fastest_engine?.time_ms}ms, {cachedBenchmark.fastest_engine?.channels} channels)
                  {cachedBenchmark.fastest_engine?.stream_link_ok && (
                    <Badge size="xs" color="green" ml="xs">Stream Link ✓</Badge>
                  )}
                </Text>
              </Group>
              <Text size="xs" c="dimmed" mt="xs">
                Tested: {new Date(cachedBenchmark.fastest_engine?.tested_at).toLocaleString()}
                {' '}(cached indefinitely until new benchmark)
              </Text>
            </Alert>
          )}
          
          {/* Benchmark Results */}
          {benchmarkResults && !benchmarkResults.error && (
            <Stack gap="sm">
              <Alert color="blue" variant="light">
                <Text size="sm">
                  <strong>Summary:</strong> {benchmarkResults.summary?.successful}/{benchmarkResults.summary?.total_tested} engines worked,
                  {' '}{benchmarkResults.summary?.with_stream_link || 0} with stream link
                  {benchmarkResults.fastest && (
                    <> — Fastest: <strong>{benchmarkResults.fastest}</strong> ({benchmarkResults.summary?.fastest_time_ms}ms)
                    {benchmarkResults.summary?.fastest_has_stream_link && (
                      <Badge size="xs" color="green" ml="xs">Stream Link ✓</Badge>
                    )}
                    </>
                  )}
                </Text>
                {benchmarkResults.portal_info && benchmarkResults.portal_info.portal_type !== 'unknown' && (
                  <Text size="sm" mt="xs">
                    <strong>Portal Type:</strong> {benchmarkResults.portal_info.portal_type.toUpperCase()}
                    {benchmarkResults.portal_info.portal_version && (
                      <> (v{benchmarkResults.portal_info.portal_version})</>
                    )}
                    {benchmarkResults.portal_info.detected_by && (
                      <Text size="xs" c="dimmed" component="span"> — detected by {benchmarkResults.portal_info.detected_by}</Text>
                    )}
                  </Text>
                )}
              </Alert>
              
              <Text size="xs" c="dimmed">
                Tests: Handshake → Genres → Channels → Stream Link → Portal Type Detection
              </Text>
              
              <Table striped highlightOnHover withTableBorder size="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Engine</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Stream Link</Table.Th>
                    <Table.Th>Time</Table.Th>
                    <Table.Th>Channels</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {benchmarkResults.results?.map((result) => (
                    <Table.Tr key={result.engine}>
                      <Table.Td>
                        <Group gap="xs">
                          {result.engine}
                          {result.engine === benchmarkResults.fastest && (
                            <Badge size="xs" color="yellow">Fastest</Badge>
                          )}
                          {result.full_success && (
                            <Badge size="xs" color="green">Full</Badge>
                          )}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        {result.success ? (
                          <Badge color="green" size="sm" leftSection={<IconCheck size={12} />}>
                            OK
                          </Badge>
                        ) : (
                          <Badge color="red" size="sm" leftSection={<IconX size={12} />}>
                            Failed
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {result.stream_link_ok ? (
                          <Badge color="green" size="sm" leftSection={<IconCheck size={12} />}>
                            OK
                          </Badge>
                        ) : result.success ? (
                          <Badge color="yellow" size="sm" leftSection={<IconX size={12} />}>
                            No
                          </Badge>
                        ) : (
                          <Text size="xs" c="dimmed">-</Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {result.success ? `${result.time_ms}ms` : '-'}
                      </Table.Td>
                      <Table.Td>
                        {result.success ? result.channels : (
                          <Text size="xs" c="dimmed">{result.error?.substring(0, 25)}</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Stack>
          )}
          
          {benchmarkResults?.error && (
            <Alert color="red" variant="light">
              <Text size="sm">Benchmark failed: {benchmarkResults.error}</Text>
            </Alert>
          )}
        </Paper>
      )}

      <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
        <Text size="sm">
          <strong>Engine Comparison:</strong>
        </Text>
        <Text size="xs" mt="xs">
          • <strong>Auto-Detect:</strong> Tries engines in order, stops at first working one
        </Text>
        <Text size="xs">
          • <strong>Fastest:</strong> Uses benchmarked fastest engine (run benchmark first!)
        </Text>
        <Text size="xs">
          • <strong>AllinOne:</strong> Best-of-All - combines prehash, signature, api_signature 263, UA rotation
        </Text>
        <Text size="xs">
          • <strong>MacReplayXC:</strong> Standard strategy, works with most portals
        </Text>
        <Text size="xs">
          • <strong>EStalker:</strong> Better for portals requiring extended metrics (MAG254)
        </Text>
        <Text size="xs">
          • <strong>BoxPirate:</strong> Dreambox-style, uses signature authentication
        </Text>
        <Text size="xs">
          • <strong>OB2_2025:</strong> Experimental, uses api_signature 263
        </Text>
        <Text size="xs">
          • <strong>iSTB:</strong> iOS Emulator style, api_signature 263, prehash, metrics
        </Text>
        <Text size="xs">
          • <strong>MacAttack:</strong> X-Random header, api_sig 262, auth_second_step 1
        </Text>
      </Alert>
    </Stack>
  );
};

export default PortalEngineSelector;
