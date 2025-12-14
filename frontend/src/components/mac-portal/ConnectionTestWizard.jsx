/**
 * Connection Test Wizard Component
 * 
 * Step-by-step connection test for MAC Portal accounts.
 * Requirements: 52.1, 52.2, 52.3, 52.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Button,
  Stepper,
  LoadingOverlay,
  Box,
  Badge,
  Alert,
  Code,
  Collapse,
  ThemeIcon,
  List,
  Select,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconCheck, 
  IconX, 
  IconLoader,
  IconNetwork,
  IconKey,
  IconUser,
  IconPlayerPlay,
  IconAlertCircle,
  IconChevronDown,
  IconChevronUp,
} from '@tabler/icons-react';
import API from '../../api';

const TEST_STEPS = [
  { key: 'network', label: 'Network', description: 'Check portal reachability', icon: IconNetwork },
  { key: 'handshake', label: 'Handshake', description: 'Perform authentication', icon: IconKey },
  { key: 'profile', label: 'Profile', description: 'Fetch account profile', icon: IconUser },
  { key: 'channels', label: 'Channels', description: 'Load channel list', icon: IconPlayerPlay },
];

const ConnectionTestWizard = ({ accountId, mac, onClose }) => {
  const [testing, setTesting] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [results, setResults] = useState({});
  const [expandedStep, setExpandedStep] = useState(null);
  const [selectedPortal, setSelectedPortal] = useState(accountId || null);
  const [selectedMac, setSelectedMac] = useState(mac || null);
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(!accountId);

  // Fetch portals if not provided
  useEffect(() => {
    if (!accountId) {
      fetchPortals();
    }
  }, [accountId]);

  const fetchPortals = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/mac-portal/overview/');
      if (response.ok) {
        const data = await response.json();
        setPortals(data.portals || []);
        if (data.portals?.length > 0) {
          setSelectedPortal(data.portals[0].id);
          if (data.portals[0].macs?.length > 0) {
            setSelectedMac(data.portals[0].macs[0].mac_address);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch portals:', error);
    } finally {
      setLoading(false);
    }
  };

  const runTest = async () => {
    const testAccountId = accountId || selectedPortal;
    const testMac = mac || selectedMac;
    
    if (!testAccountId || !testMac) {
      notifications.show({
        title: 'Error',
        message: 'Please select a portal and MAC address',
        color: 'red',
      });
      return;
    }

    setTesting(true);
    setResults({});
    setCurrentStep(0);

    try {
      const response = await API.runConnectionTest(testAccountId, testMac);
      
      // Process results step by step with delays for visual feedback
      for (let i = 0; i < TEST_STEPS.length; i++) {
        setCurrentStep(i);
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const stepKey = TEST_STEPS[i].key;
        const stepResult = response.steps?.find(s => s.step === stepKey) || {
          step: stepKey,
          success: false,
          error: 'Step not executed',
        };
        
        setResults(prev => ({ ...prev, [stepKey]: stepResult }));
        
        if (!stepResult.success) {
          break;
        }
      }
      
      setCurrentStep(TEST_STEPS.length);
      
      if (response.success) {
        notifications.show({
          title: 'Connection Test Passed',
          message: 'All tests completed successfully',
          color: 'green',
        });
      } else {
        notifications.show({
          title: 'Connection Test Failed',
          message: response.error || 'One or more tests failed',
          color: 'red',
        });
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to run connection test',
        color: 'red',
      });
    } finally {
      setTesting(false);
    }
  };

  const getStepStatus = (index) => {
    const stepKey = TEST_STEPS[index].key;
    const result = results[stepKey];
    
    if (!result) {
      if (index === currentStep && testing) return 'loading';
      if (index < currentStep) return 'completed';
      return 'pending';
    }
    
    return result.success ? 'completed' : 'error';
  };

  const getStepIcon = (index) => {
    const status = getStepStatus(index);
    const StepIcon = TEST_STEPS[index].icon;
    
    switch (status) {
      case 'loading':
        return <IconLoader size={18} className="animate-spin" />;
      case 'completed':
        return <IconCheck size={18} />;
      case 'error':
        return <IconX size={18} />;
      default:
        return <StepIcon size={18} />;
    }
  };

  const getStepColor = (index) => {
    const status = getStepStatus(index);
    switch (status) {
      case 'completed': return 'green';
      case 'error': return 'red';
      case 'loading': return 'blue';
      default: return 'gray';
    }
  };

  const allPassed = TEST_STEPS.every(step => results[step.key]?.success);
  const anyFailed = TEST_STEPS.some(step => results[step.key]?.success === false);

  if (loading) {
    return (
      <Box pos="relative" h={200}>
        <LoadingOverlay visible={true} />
      </Box>
    );
  }

  const currentMac = mac || selectedMac;
  const availableMacs = !accountId && portals.length > 0 
    ? portals.find(p => p.id === selectedPortal)?.macs || []
    : [];

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={3}>Connection Test</Title>
          {currentMac ? (
            <Text size="sm" c="dimmed">
              Testing connection for MAC: <Code>{currentMac}</Code>
            </Text>
          ) : (
            <Text size="sm" c="dimmed">
              Select a portal and MAC address to test
            </Text>
          )}
        </div>
        <Button onClick={runTest} loading={testing} disabled={testing || !currentMac}>
          {Object.keys(results).length > 0 ? 'Run Again' : 'Start Test'}
        </Button>
      </Group>

      {!accountId && portals.length > 0 && (
        <Paper withBorder p="md">
          <Stack gap="sm">
            <Select
              label="Portal"
              placeholder="Select portal"
              value={selectedPortal?.toString()}
              onChange={(val) => {
                setSelectedPortal(val ? parseInt(val) : null);
                setSelectedMac(null);
              }}
              data={portals.map(p => ({ value: p.id.toString(), label: p.name }))}
            />
            {availableMacs.length > 0 && (
              <Select
                label="MAC Address"
                placeholder="Select MAC"
                value={selectedMac}
                onChange={setSelectedMac}
                data={availableMacs.map(m => ({ value: m.mac_address, label: m.mac_address }))}
              />
            )}
          </Stack>
        </Paper>
      )}

      {!accountId && portals.length === 0 && (
        <Alert color="blue">
          No MAC portals configured. Add a MAC/STB portal account first.
        </Alert>
      )}

      <Paper withBorder p="md">
        <Stepper 
          active={currentStep} 
          orientation="vertical"
          size="sm"
        >
          {TEST_STEPS.map((step, index) => {
            const result = results[step.key];
            const isExpanded = expandedStep === index;
            
            return (
              <Stepper.Step
                key={step.key}
                label={step.label}
                description={step.description}
                icon={getStepIcon(index)}
                color={getStepColor(index)}
                completedIcon={result?.success ? <IconCheck size={18} /> : <IconX size={18} />}
              >
                {result && (
                  <Box ml="xl" mt="xs">
                    <Group 
                      gap="xs" 
                      style={{ cursor: 'pointer' }}
                      onClick={() => setExpandedStep(isExpanded ? null : index)}
                    >
                      <Badge 
                        color={result.success ? 'green' : 'red'} 
                        variant="light"
                      >
                        {result.success ? 'Passed' : 'Failed'}
                      </Badge>
                      {result.duration_ms && (
                        <Text size="xs" c="dimmed">{result.duration_ms}ms</Text>
                      )}
                      {isExpanded ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
                    </Group>
                    
                    <Collapse in={isExpanded}>
                      <Paper withBorder p="sm" mt="xs" bg="gray.0">
                        {result.success ? (
                          <Stack gap="xs">
                            {result.data && Object.entries(result.data).map(([key, value]) => (
                              <Group key={key} gap="xs">
                                <Text size="xs" fw={500}>{key}:</Text>
                                <Text size="xs">{String(value)}</Text>
                              </Group>
                            ))}
                          </Stack>
                        ) : (
                          <Alert color="red" icon={<IconAlertCircle size={16} />}>
                            <Text size="sm">{result.error}</Text>
                            {result.details && (
                              <Code block mt="xs" style={{ fontSize: '11px' }}>
                                {JSON.stringify(result.details, null, 2)}
                              </Code>
                            )}
                          </Alert>
                        )}
                      </Paper>
                    </Collapse>
                  </Box>
                )}
              </Stepper.Step>
            );
          })}
        </Stepper>
      </Paper>

      {Object.keys(results).length > 0 && !testing && (
        <Paper withBorder p="md">
          <Title order={4} mb="md">Test Summary</Title>
          
          {allPassed ? (
            <Alert color="green" icon={<IconCheck size={16} />}>
              <Text fw={500}>All tests passed!</Text>
              <Text size="sm">The portal connection is working correctly.</Text>
            </Alert>
          ) : anyFailed ? (
            <Alert color="red" icon={<IconX size={16} />}>
              <Text fw={500}>Some tests failed</Text>
              <Text size="sm">Check the failed steps above for details.</Text>
              
              <Title order={5} mt="md" mb="xs">Troubleshooting Tips:</Title>
              <List size="sm">
                {results.network?.success === false && (
                  <List.Item>Check if the portal URL is correct and accessible</List.Item>
                )}
                {results.handshake?.success === false && (
                  <>
                    <List.Item>Verify the MAC address is valid and not blocked</List.Item>
                    <List.Item>Try a different User-Agent preset</List.Item>
                    <List.Item>Enable Cloudscraper if the portal uses Cloudflare</List.Item>
                  </>
                )}
                {results.profile?.success === false && (
                  <List.Item>The account may be expired or suspended</List.Item>
                )}
                {results.channels?.success === false && (
                  <List.Item>The portal may be experiencing issues</List.Item>
                )}
              </List>
            </Alert>
          ) : (
            <Alert color="blue" icon={<IconAlertCircle size={16} />}>
              <Text>Test incomplete. Click "Start Test" to run the full test.</Text>
            </Alert>
          )}
        </Paper>
      )}

      {onClose && (
        <Group justify="flex-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </Group>
      )}
    </Stack>
  );
};

export default ConnectionTestWizard;
