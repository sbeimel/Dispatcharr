/**
 * MAC Health Dashboard Component
 * 
 * Zeigt alle angelegten MAC/STB Portale mit ihren MACs an.
 * Liest die Portale aus der Datenbank und zeigt Status/Health.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Title,
  Paper,
  Table,
  Badge,
  Group,
  Button,
  Text,
  Progress,
  ActionIcon,
  Tooltip,
  LoadingOverlay,
  Stack,
  Card,
  SimpleGrid,
  Accordion,
  Alert,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconRefresh, 
  IconEye, 
  IconPlayerPlay, 
  IconServer,
  IconNetwork,
} from '@tabler/icons-react';
import API from '../../api';

const MACHealthDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [portals, setPortals] = useState([]);
  const [stats, setStats] = useState({
    total_portals: 0,
    online_portals: 0,
    offline_portals: 0,
    total_macs: 0,
    available_macs: 0,
    in_use_macs: 0,
    cooldown_macs: 0,
    expired_macs: 0,
  });

  useEffect(() => {
    fetchPortalHealth();
  }, []);

  const fetchPortalHealth = async () => {
    setLoading(true);
    try {
      const token = await API.getAuthToken();
      const response = await fetch('/api/mac-portal/overview/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPortals(data.portals || []);
        setStats(data.statistics || {
          total_portals: 0,
          online_portals: 0,
          offline_portals: 0,
          total_macs: 0,
          available_macs: 0,
          in_use_macs: 0,
          cooldown_macs: 0,
          expired_macs: 0,
        });
      } else {
        console.error('Failed to fetch portal overview:', response.status);
        setPortals([]);
      }
    } catch (error) {
      console.error('Failed to fetch portal health:', error);
      setPortals([]);
    } finally {
      setLoading(false);
    }
  };


  const handleResetCooldown = async (portalId, macId) => {
    try {
      const response = await fetch(`/api/mac-portal/${portalId}/macs/${macId}/reset-cooldown/`, {
        method: 'POST',
      });
      if (response.ok) {
        notifications.show({
          title: 'Erfolg',
          message: 'Cooldown zurückgesetzt',
          color: 'green',
        });
        fetchPortalHealth();
      }
    } catch (error) {
      notifications.show({
        title: 'Fehler',
        message: 'Cooldown konnte nicht zurückgesetzt werden',
        color: 'red',
      });
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
      case 'valid':
        return <Badge color="green">Aktiv</Badge>;
      case 'in_use':
        return <Badge color="blue">In Verwendung</Badge>;
      case 'cooldown':
        return <Badge color="yellow">Cooldown</Badge>;
      case 'expired':
        return <Badge color="red">Abgelaufen</Badge>;
      case 'error':
        return <Badge color="orange">Fehler</Badge>;
      default:
        return <Badge color="gray">Unbekannt</Badge>;
    }
  };

  const getPortalStatusBadge = (status) => {
    return status === 'online' 
      ? <Badge color="green" size="sm">Online</Badge>
      : <Badge color="red" size="sm">Offline</Badge>;
  };

  const getHealthColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  return (
    <Box pos="relative">
      <LoadingOverlay visible={loading} />
      
      <Group justify="space-between" mb="md">
        <Title order={3}>Portal & MAC Health</Title>
        <Button 
          leftSection={<IconRefresh size={16} />}
          variant="outline"
          onClick={fetchPortalHealth}
        >
          Aktualisieren
        </Button>
      </Group>

      {/* Statistik-Karten */}
      <SimpleGrid cols={{ base: 2, md: 4 }} mb="md">
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Portale</Text>
          <Group gap="xs">
            <Text size="xl" fw={700}>{stats.total_portals}</Text>
            <Text size="sm" c="green">({stats.online_portals} online)</Text>
          </Group>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">MACs Gesamt</Text>
          <Text size="xl" fw={700}>{stats.total_macs}</Text>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Verfügbar</Text>
          <Text size="xl" fw={700} c="green">{stats.available_macs}</Text>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Cooldown / Abgelaufen</Text>
          <Group gap="xs">
            <Text size="xl" fw={700} c="yellow">{stats.cooldown_macs}</Text>
            <Text size="xl" fw={700} c="red">/ {stats.expired_macs}</Text>
          </Group>
        </Card>
      </SimpleGrid>


      {/* Keine Portale angelegt */}
      {portals.length === 0 && !loading && (
        <Alert color="blue" title="Keine MAC/STB Portale angelegt" icon={<IconServer size={16} />}>
          Es sind noch keine MAC/STB Portal Accounts angelegt. 
          Erstelle zuerst einen Account unter "Accounts" mit dem Typ "MAC/STB Portal".
        </Alert>
      )}

      {/* Portal-Liste mit MACs */}
      {portals.length > 0 && (
        <Accordion variant="separated" defaultValue={portals[0]?.id?.toString()}>
          {portals.map((portal) => (
            <Accordion.Item key={portal.id} value={portal.id.toString()}>
              <Accordion.Control>
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="sm">
                    <IconNetwork size={20} />
                    <div>
                      <Text fw={500}>{portal.name}</Text>
                      <Text size="xs" c="dimmed">{portal.url}</Text>
                    </div>
                  </Group>
                  <Group gap="xs">
                    {getPortalStatusBadge(portal.status)}
                    <Badge variant="outline" size="sm">
                      {portal.mac_count} MAC{portal.mac_count !== 1 ? 's' : ''}
                    </Badge>
                  </Group>
                </Group>
              </Accordion.Control>
              <Accordion.Panel>
                {portal.macs && portal.macs.length > 0 ? (
                  <Paper withBorder>
                    <Table striped highlightOnHover>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>MAC Adresse</Table.Th>
                          <Table.Th>Status</Table.Th>
                          <Table.Th>Health Score</Table.Th>
                          <Table.Th>Ablaufdatum</Table.Th>
                          <Table.Th>Aktionen</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {portal.macs.map((mac) => (
                          <Table.Tr key={mac.id || mac.mac_address}>
                            <Table.Td>
                              <Text size="sm" ff="monospace">{mac.mac_address}</Text>
                            </Table.Td>
                            <Table.Td>{getStatusBadge(mac.status)}</Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                <Progress 
                                  value={mac.health_score ?? 0} 
                                  color={getHealthColor(mac.health_score ?? 0)}
                                  size="sm"
                                  w={60}
                                />
                                <Text size="xs">{mac.health_score ?? 0}%</Text>
                              </Group>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">
                                {mac.expiry_date 
                                  ? new Date(mac.expiry_date).toLocaleDateString('de-DE')
                                  : '-'}
                              </Text>
                              {mac.days_until_expiry !== null && mac.days_until_expiry < 7 && (
                                <Text size="xs" c="orange">
                                  ({mac.days_until_expiry} Tage)
                                </Text>
                              )}
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                <Tooltip label="Details anzeigen">
                                  <ActionIcon variant="subtle" color="blue">
                                    <IconEye size={16} />
                                  </ActionIcon>
                                </Tooltip>
                                {mac.status === 'cooldown' && (
                                  <Tooltip label="Cooldown zurücksetzen">
                                    <ActionIcon 
                                      variant="subtle" 
                                      color="yellow"
                                      onClick={() => handleResetCooldown(portal.id, mac.id)}
                                    >
                                      <IconPlayerPlay size={16} />
                                    </ActionIcon>
                                  </Tooltip>
                                )}
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Paper>
                ) : (
                  <Text c="dimmed" ta="center" py="md">
                    Keine MACs für dieses Portal konfiguriert
                  </Text>
                )}
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      )}
    </Box>
  );
};

export default MACHealthDashboard;
