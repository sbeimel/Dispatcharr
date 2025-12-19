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
} from '@mantine/core';
import {
  IconRocket,
  IconBrandPython,
  IconDeviceTv,
  IconFlask,
  IconInfoCircle,
  IconCheck,
  IconTrash,
} from '@tabler/icons-react';
import API from '../../api';

const PORTAL_ENGINES = [
  {
    value: 'auto',
    label: 'Auto-Detect (Recommended)',
    description: 'Automatically detects and caches the working engine for this portal. Persists until manually cleared.',
    icon: IconRocket,
    color: 'green',
    badge: 'Recommended',
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
  
  // Engine Cache state
  const [cachedEngine, setCachedEngine] = useState(null);
  const [clearingCache, setClearingCache] = useState(false);
  
  // Load engine cache on mount
  useEffect(() => {
    if (accountId) {
      loadCachedEngine();
    }
  }, [accountId]);
  
  // Load cached engine from AUTO mode
  const loadCachedEngine = async () => {
    if (!accountId) return;
    try {
      // Get account details to extract portal URL
      const accountResponse = await API.get(`/api/m3u/accounts/${accountId}/`);
      const portalUrl = accountResponse.data.server_url;
      
      if (!portalUrl) return;
      
      // Get cached engine for this portal
      const response = await API.get(`/api/m3u/engine-cache/?portal_url=${encodeURIComponent(portalUrl)}`);
      
      if (response.data.success && response.data.cached) {
        setCachedEngine(response.data.engine);
      } else {
        setCachedEngine(null);
      }
    } catch (error) {
      console.error('Failed to load cached engine:', error);
      setCachedEngine(null);
    }
  };
  
  // Clear engine cache and trigger refresh
  const clearAndRefreshEngineCache = async () => {
    if (!accountId) return;
    
    setClearingCache(true);
    try {
      // Get account details to extract portal URL
      const accountResponse = await API.get(`/api/m3u/accounts/${accountId}/`);
      const portalUrl = accountResponse.data.server_url;
      
      if (!portalUrl) {
        alert('Portal URL not found');
        return;
      }
      
      // Clear cache and trigger refresh
      const response = await API.post('/api/m3u/engine-cache/clear/', {
        portal_url: portalUrl,
        account_id: accountId,
        trigger_refresh: true
      });
      
      if (response.data.success) {
        setCachedEngine(null);
        alert(response.data.message);
        
        // Reload after a short delay to show new engine
        setTimeout(() => {
          loadCachedEngine();
        }, 2000);
      } else {
        alert('Failed to clear cache: ' + (response.data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Failed to clear engine cache:', error);
      alert('Failed to clear cache: ' + (error.response?.data?.error || error.message));
    } finally {
      setClearingCache(false);
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
      
      {/* Engine Cache Section (AUTO Mode) */}
      {accountId && value === 'auto' && (
        <Paper withBorder p="md">
          <Group justify="space-between" mb="sm">
            <Group gap="xs">
              <ThemeIcon color="green" variant="light" size="lg">
                <IconRocket size={20} />
              </ThemeIcon>
              <div>
                <Text fw={500}>Cached Engine (AUTO Mode)</Text>
                <Text size="xs" c="dimmed">
                  The engine that worked for this portal (persists until manually cleared)
                </Text>
              </div>
            </Group>
            <Button
              size="xs"
              variant="light"
              color="orange"
              leftSection={clearingCache ? <Loader size={14} /> : <IconTrash size={14} />}
              onClick={clearAndRefreshEngineCache}
              disabled={clearingCache || !cachedEngine}
              loading={clearingCache}
            >
              {clearingCache ? 'Clearing...' : 'Clear & Refresh'}
            </Button>
          </Group>
          
          {cachedEngine ? (
            <Alert color="green" variant="light">
              <Group gap="xs">
                <IconCheck size={16} />
                <Text size="sm">
                  Cached engine: <strong>{cachedEngine.toUpperCase()}</strong>
                </Text>
              </Group>
              <Text size="xs" c="dimmed" mt="xs">
                This engine will be used for all connections until cache is cleared.
                Click "Clear & Refresh" to detect a new engine.
              </Text>
            </Alert>
          ) : (
            <Alert color="blue" variant="light">
              <Text size="sm">
                No cached engine yet. Will auto-detect on next connection.
              </Text>
            </Alert>
          )}
        </Paper>
      )}
      

      <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
        <Text size="sm">
          <strong>Engine Comparison:</strong>
        </Text>
        <Text size="xs" mt="xs">
          • <strong>Auto-Detect:</strong> Automatically detects working engine and caches it (recommended for most users)
        </Text>
        <Text size="xs">
          • <strong>AllinOne:</strong> Best-of-All - combines all techniques (prehash, signature, api_signature 263, UA rotation)
        </Text>
        <Text size="xs">
          • <strong>MacReplayXC:</strong> Standard strategy, works with most portals
        </Text>
        <Text size="xs">
          • <strong>EStalker:</strong> Enigma2 style with extended metrics (MAG254)
        </Text>
        <Text size="xs">
          • <strong>BoxPirate:</strong> Dreambox-style with signature authentication
        </Text>
        <Text size="xs">
          • <strong>OB2_2025:</strong> Extended checking logic with api_signature 263
        </Text>
        <Text size="xs">
          • <strong>iSTB:</strong> iOS Emulator style (api_signature 263, prehash, metrics)
        </Text>
        <Text size="xs">
          • <strong>MacAttack:</strong> X-Random header, api_sig 262, auth_second_step 1
        </Text>
      </Alert>
    </Stack>
  );
};

export default PortalEngineSelector;
