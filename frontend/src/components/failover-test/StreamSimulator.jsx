/**
 * Stream Simulator Component
 * 
 * Controls for simulating stream interruptions and errors.
 * Requirements: 3.1, 3.2, 3.4, 3.5
 */

import React, { useState } from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Select,
  NumberInput,
  Switch,
  Text,
  Badge,
  Paper,
  Divider,
} from '@mantine/core';
import {
  IconPlayerStop,
  IconBolt,
  IconRepeat,
  IconAlertTriangle,
} from '@tabler/icons-react';

const ERROR_TYPES = [
  { value: 'timeout', label: 'Timeout' },
  { value: 'connection_reset', label: 'Connection Reset' },
  { value: '403', label: 'HTTP 403 Forbidden' },
  { value: '404', label: 'HTTP 404 Not Found' },
  { value: '500', label: 'HTTP 500 Server Error' },
  { value: 'stream_error', label: 'Stream Error' },
];

const StreamSimulator = ({
  channel,
  activeSimulations = [],
  onInterrupt,
  onStartAuto,
  onStop,
}) => {
  const [errorType, setErrorType] = useState('timeout');
  const [autoMode, setAutoMode] = useState(false);
  const [intervalSec, setIntervalSec] = useState(5);
  const [maxInterruptions, setMaxInterruptions] = useState(10);
  const [isSimulating, setIsSimulating] = useState(false);

  // Check if this channel has an active simulation
  const activeSimulation = activeSimulations.find(
    s => s.channel_id === channel?.id
  );

  const handleInterrupt = () => {
    if (channel) {
      onInterrupt(channel.id, errorType);
    }
  };

  const handleStartAuto = () => {
    if (channel) {
      setIsSimulating(true);
      onStartAuto(channel.id, {
        interval_ms: intervalSec * 1000,
        error_types: [errorType],
        max_interruptions: maxInterruptions,
      });
    }
  };

  const handleStop = () => {
    if (activeSimulation) {
      onStop(activeSimulation.simulation_id);
    }
    setIsSimulating(false);
  };

  if (!channel) {
    return (
      <Box>
        <Title order={4} mb="md">Stream Simulation</Title>
        <Text c="dimmed" size="sm">
          Select a test channel to simulate stream interruptions.
        </Text>
      </Box>
    );
  }

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={4}>Stream Simulation</Title>
        {activeSimulation && (
          <Badge color="orange" variant="dot">
            Simulating ({activeSimulation.interruption_count || 0}/{maxInterruptions})
          </Badge>
        )}
      </Group>

      <Text size="sm" c="dimmed" mb="md">
        Channel: <strong>{channel.name}</strong>
      </Text>

      <Stack gap="md">
        {/* Error Type Selection */}
        <Select
          label="Error Type"
          description="Type of error to simulate"
          data={ERROR_TYPES}
          value={errorType}
          onChange={setErrorType}
          disabled={!!activeSimulation}
        />

        {/* Manual Interrupt Button */}
        <Button
          color="red"
          size="lg"
          fullWidth
          leftSection={<IconBolt size={20} />}
          onClick={handleInterrupt}
          disabled={!!activeSimulation}
        >
          🔴 STREAM UNTERBRECHEN
        </Button>

        <Divider label="Auto-Simulation" labelPosition="center" />

        {/* Auto Mode Settings */}
        <Paper withBorder p="sm">
          <Stack gap="sm">
            <Switch
              label="Auto-Modus"
              description="Automatische wiederholte Unterbrechungen"
              checked={autoMode}
              onChange={(e) => setAutoMode(e.currentTarget.checked)}
              disabled={!!activeSimulation}
            />

            {autoMode && (
              <>
                <NumberInput
                  label="Intervall (Sekunden)"
                  description="Zeit zwischen Unterbrechungen"
                  value={intervalSec}
                  onChange={setIntervalSec}
                  min={1}
                  max={60}
                  disabled={!!activeSimulation}
                />

                <NumberInput
                  label="Max. Unterbrechungen"
                  description="Anzahl der Unterbrechungen"
                  value={maxInterruptions}
                  onChange={setMaxInterruptions}
                  min={1}
                  max={100}
                  disabled={!!activeSimulation}
                />
              </>
            )}
          </Stack>
        </Paper>

        {/* Auto Simulation Controls */}
        <Group grow>
          {!activeSimulation ? (
            <Button
              color="blue"
              leftSection={<IconRepeat size={16} />}
              onClick={handleStartAuto}
              disabled={!autoMode}
            >
              Auto-Simulation starten
            </Button>
          ) : (
            <Button
              color="gray"
              leftSection={<IconPlayerStop size={16} />}
              onClick={handleStop}
            >
              ⏹ STOP
            </Button>
          )}
        </Group>

        {/* Active Simulation Info */}
        {activeSimulation && (
          <Paper withBorder p="sm" bg="orange.0">
            <Group gap="xs">
              <IconAlertTriangle size={16} color="orange" />
              <Text size="sm">
                Simulation läuft: {activeSimulation.interruption_count || 0} von{' '}
                {activeSimulation.max_interruptions || maxInterruptions} Unterbrechungen
              </Text>
            </Group>
          </Paper>
        )}
      </Stack>
    </Box>
  );
};

export default StreamSimulator;
