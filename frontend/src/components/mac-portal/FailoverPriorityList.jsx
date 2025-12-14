/**
 * Failover Priority List Component
 * 
 * Drag-and-drop interface for configuring failover strategy priority.
 * Requirements: 60.1, 60.2, 60.3, 60.4
 */

import React from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  ActionIcon,
  Box,
  Badge,
  ThemeIcon,
  Alert,
} from '@mantine/core';
import { 
  IconGripVertical, 
  IconNetwork, 
  IconRouter, 
  IconPlayerPlay,
  IconUser,
  IconInfoCircle,
} from '@tabler/icons-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const STRATEGY_INFO = {
  mac: { name: 'MAC Failover', description: 'Try different MAC addresses', icon: IconNetwork, color: 'blue' },
  portal: { name: 'Portal Failover', description: 'Switch to backup portal URLs', icon: IconRouter, color: 'green' },
  endpoint: { name: 'Endpoint Failover', description: 'Try different API endpoints', icon: IconRouter, color: 'teal' },
  stream: { name: 'Stream Failover', description: 'Retry with alternative streams', icon: IconPlayerPlay, color: 'orange' },
  useragent: { name: 'User-Agent Failover', description: 'Rotate User-Agent strings', icon: IconUser, color: 'violet' },
};

const SortableItem = ({ id, index }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const info = STRATEGY_INFO[id] || { name: id, description: 'Unknown strategy', icon: IconNetwork, color: 'gray' };
  const Icon = info.icon;

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Paper ref={setNodeRef} style={style} shadow={isDragging ? 'md' : 'xs'} mb="sm" p="md">
      <Group>
        <ActionIcon variant="subtle" {...attributes} {...listeners} style={{ cursor: 'grab' }}>
          <IconGripVertical size={20} />
        </ActionIcon>
        <Badge size="lg" variant="filled" color={info.color} circle>{index + 1}</Badge>
        <ThemeIcon size="lg" variant="light" color={info.color}><Icon size={20} /></ThemeIcon>
        <div style={{ flex: 1 }}>
          <Text fw={500}>{info.name}</Text>
          <Text size="xs" c="dimmed">{info.description}</Text>
        </div>
      </Group>
    </Paper>
  );
};

const FailoverPriorityList = ({ priority, onPriorityChange }) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = priority.indexOf(active.id);
      const newIndex = priority.indexOf(over.id);
      onPriorityChange(arrayMove(priority, oldIndex, newIndex));
    }
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure the order in which failover strategies are tried. When an error occurs, the system will try each strategy in order until one succeeds.
      </Text>
      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Drag strategies to reorder. The first strategy is tried first, then the second, and so on.
      </Alert>
      <Paper withBorder p="md">
        <Title order={4} mb="md">Failover Priority Order</Title>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={priority} strategy={verticalListSortingStrategy}>
            {priority.map((strategyKey, index) => (
              <SortableItem key={strategyKey} id={strategyKey} index={index} />
            ))}
          </SortableContext>
        </DndContext>
      </Paper>
      <Paper withBorder p="md">
        <Title order={5} mb="sm">How Failover Works</Title>
        <Stack gap="xs">
          <Text size="sm">1. When an error occurs, the system checks the first strategy in the list.</Text>
          <Text size="sm">2. If that strategy is enabled and has available alternatives, it tries them.</Text>
          <Text size="sm">3. If all alternatives for that strategy fail, it moves to the next strategy.</Text>
          <Text size="sm">4. This continues until either a request succeeds or all strategies are exhausted.</Text>
        </Stack>
      </Paper>
    </Stack>
  );
};

export default FailoverPriorityList;
