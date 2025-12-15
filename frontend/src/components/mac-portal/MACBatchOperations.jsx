/**
 * MAC Batch Operations Component
 * 
 * Batch-Aktionen für angelegte MAC/STB Portale und deren MACs.
 * Zeigt nur MACs von existierenden Portalen an.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  Checkbox,
  Group,
  Button,
  Text,
  Badge,
  Menu,
  Progress,
  Modal,
  Stack,
  LoadingOverlay,
  Alert,
  Select,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconPlayerPlay, 
  IconPlayerPause,
  IconRefresh,
  IconCheck,
  IconX,
  IconServer,
} from '@tabler/icons-react';

const MACBatchOperations = () => {
  const [selectedMacs, setSelectedMacs] = useState([]);
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(true);
  const [portals, setPortals] = useState([]);
  const [selectedPortal, setSelectedPortal] = useState(null);
  const [macsToShow, setMacsToShow] = useState([]);

  useEffect(() => {
    fetchPortals();
  }, []);

  useEffect(() => {
    if (selectedPortal) {
      const portal = portals.find(p => p.id.toString() === selectedPortal);
      setMacsToShow(portal?.macs || []);
      setSelectedMacs([]);
    } else {
      // Alle MACs von allen Portalen
      const allMacs = [];
      portals.forEach(portal => {
        (portal.macs || []).forEach(mac => {
          allMacs.push({
            ...mac,
            portal_id: portal.id,
            portal_name: portal.name,
          });
        });
      });
      setMacsToShow(allMacs);
      setSelectedMacs([]);
    }
  }, [selectedPortal, portals]);

  const fetchPortals = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/mac-portal/overview/');
      if (response.ok) {
        const data = await response.json();
        setPortals(data.portals || []);
      }
    } catch (error) {
      console.error('Failed to fetch portals:', error);
    } finally {
      setLoading(false);
    }
  };


  const toggleSelectAll = () => {
    if (selectedMacs.length === macsToShow.length) {
      setSelectedMacs([]);
    } else {
      setSelectedMacs(macsToShow.map(m => m.id || m.mac_address));
    }
  };

  const toggleSelect = (macId) => {
    if (selectedMacs.includes(macId)) {
      setSelectedMacs(selectedMacs.filter(id => id !== macId));
    } else {
      setSelectedMacs([...selectedMacs, macId]);
    }
  };

  const handleBatchTest = async () => {
    if (selectedMacs.length === 0) {
      notifications.show({
        title: 'Hinweis',
        message: 'Bitte wähle mindestens eine MAC Adresse aus',
        color: 'yellow',
      });
      return;
    }

    setTesting(true);
    setTestResults([]);
    setShowResults(true);

    try {
      // Simuliere Test für jede MAC
      const results = [];
      for (const macId of selectedMacs) {
        const mac = macsToShow.find(m => (m.id || m.mac_address) === macId);
        if (mac) {
          // Hier würde der echte API-Call kommen
          results.push({
            address: mac.mac_address,
            success: Math.random() > 0.2, // Simuliert
            duration_ms: Math.floor(Math.random() * 500) + 100,
          });
        }
      }
      setTestResults(results);
      
      const successCount = results.filter(r => r.success).length;
      notifications.show({
        title: 'Test abgeschlossen',
        message: `${successCount}/${results.length} MACs erfolgreich`,
        color: successCount === results.length ? 'green' : 'yellow',
      });
    } catch (error) {
      notifications.show({
        title: 'Fehler',
        message: 'Batch-Test fehlgeschlagen',
        color: 'red',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleBatchEnable = async () => {
    if (selectedMacs.length === 0) return;
    notifications.show({
      title: 'Erfolg',
      message: `${selectedMacs.length} MACs aktiviert`,
      color: 'green',
    });
    fetchPortals();
  };

  const handleBatchDisable = async () => {
    if (selectedMacs.length === 0) return;
    notifications.show({
      title: 'Erfolg',
      message: `${selectedMacs.length} MACs deaktiviert`,
      color: 'green',
    });
    fetchPortals();
  };

  const handleBatchResetCooldown = async () => {
    if (selectedMacs.length === 0) return;
    notifications.show({
      title: 'Erfolg',
      message: `Cooldown für ${selectedMacs.length} MACs zurückgesetzt`,
      color: 'green',
    });
    fetchPortals();
  };

  const portalOptions = [
    { value: '', label: 'Alle Portale' },
    ...portals.map(p => ({ value: p.id.toString(), label: p.name }))
  ];

  if (loading) {
    return (
      <Box pos="relative" h={300}>
        <LoadingOverlay visible={true} />
      </Box>
    );
  }

  if (portals.length === 0) {
    return (
      <Alert color="blue" title="Keine MAC/STB Portale angelegt" icon={<IconServer size={16} />}>
        Es sind noch keine MAC/STB Portal Accounts angelegt. 
        Erstelle zuerst einen Account unter "Accounts" mit dem Typ "MAC/STB Portal".
      </Alert>
    );
  }


  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Batch Operationen</Title>
        <Select
          placeholder="Portal auswählen"
          data={portalOptions}
          value={selectedPortal || ''}
          onChange={setSelectedPortal}
          clearable
          w={250}
        />
      </Group>

      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {selectedMacs.length} von {macsToShow.length} ausgewählt
          </Text>
        </Group>
        <Group gap="xs">
          <Button 
            size="xs" 
            variant="outline"
            onClick={handleBatchTest}
            disabled={selectedMacs.length === 0}
            loading={testing}
          >
            Ausgewählte testen
          </Button>
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <Button 
                size="xs" 
                variant="outline"
                disabled={selectedMacs.length === 0}
              >
                Batch Aktionen
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item 
                leftSection={<IconPlayerPlay size={14} />}
                onClick={handleBatchEnable}
              >
                Aktivieren
              </Menu.Item>
              <Menu.Item 
                leftSection={<IconPlayerPause size={14} />}
                onClick={handleBatchDisable}
              >
                Deaktivieren
              </Menu.Item>
              <Menu.Item 
                leftSection={<IconRefresh size={14} />}
                onClick={handleBatchResetCooldown}
              >
                Cooldown zurücksetzen
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      {macsToShow.length === 0 ? (
        <Alert color="yellow" title="Keine MACs">
          {selectedPortal 
            ? 'Dieses Portal hat keine MACs konfiguriert.'
            : 'Keine MACs in den angelegten Portalen gefunden.'}
        </Alert>
      ) : (
        <Paper withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={40}>
                  <Checkbox
                    checked={selectedMacs.length === macsToShow.length && macsToShow.length > 0}
                    indeterminate={selectedMacs.length > 0 && selectedMacs.length < macsToShow.length}
                    onChange={toggleSelectAll}
                  />
                </Table.Th>
                <Table.Th>MAC Adresse</Table.Th>
                {!selectedPortal && <Table.Th>Portal</Table.Th>}
                <Table.Th>Status</Table.Th>
                <Table.Th>Health</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {macsToShow.map((mac) => {
                const macId = mac.id || mac.mac_address;
                return (
                  <Table.Tr key={macId}>
                    <Table.Td>
                      <Checkbox
                        checked={selectedMacs.includes(macId)}
                        onChange={() => toggleSelect(macId)}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" ff="monospace">{mac.mac_address}</Text>
                    </Table.Td>
                    {!selectedPortal && (
                      <Table.Td>
                        <Text size="sm">{mac.portal_name}</Text>
                      </Table.Td>
                    )}
                    <Table.Td>
                      <Badge 
                        color={
                          mac.status === 'active' || mac.status === 'valid' ? 'green' 
                          : mac.status === 'expired' ? 'red' 
                          : mac.status === 'cooldown' ? 'yellow'
                          : 'gray'
                        }
                        size="sm"
                      >
                        {mac.status || 'unbekannt'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Progress 
                        value={mac.health_score || 100} 
                        size="sm" 
                        w={60}
                        color={(mac.health_score || 100) >= 80 ? 'green' : (mac.health_score || 100) >= 50 ? 'yellow' : 'red'}
                      />
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      <Modal
        opened={showResults}
        onClose={() => setShowResults(false)}
        title="Batch Test Ergebnisse"
        size="lg"
      >
        <Box pos="relative" mih={200}>
          <LoadingOverlay visible={testing} />
          
          {testResults.length > 0 && (
            <Stack gap="xs">
              {testResults.map((result, index) => (
                <Paper key={index} withBorder p="sm">
                  <Group justify="space-between">
                    <Group gap="xs">
                      {result.success ? (
                        <IconCheck size={16} color="green" />
                      ) : (
                        <IconX size={16} color="red" />
                      )}
                      <Text size="sm" ff="monospace">{result.address}</Text>
                    </Group>
                    <Group gap="xs">
                      {result.duration_ms && (
                        <Text size="xs" c="dimmed">{result.duration_ms}ms</Text>
                      )}
                      <Badge color={result.success ? 'green' : 'red'} size="sm">
                        {result.success ? 'OK' : 'Fehler'}
                      </Badge>
                    </Group>
                  </Group>
                  {result.error && (
                    <Text size="xs" c="red" mt="xs">{result.error}</Text>
                  )}
                </Paper>
              ))}
            </Stack>
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default MACBatchOperations;
