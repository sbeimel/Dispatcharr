/**
 * VOD Browser Component
 * 
 * Browse VOD categories and items from MAC Portal.
 * Requirements: 4.1, 4.2
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Select,
  TextInput,
  Button,
  LoadingOverlay,
  Box,
  SimpleGrid,
  Card,
  Image,
  Badge,
  Pagination,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconSearch,
  IconRefresh,
  IconPlayerPlay,
  IconInfoCircle,
  IconFolder,
} from '@tabler/icons-react';
import API from '../../api';

const VODBrowser = ({ accountId, onSelectItem }) => {
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const itemsPerPage = 20;

  useEffect(() => {
    if (accountId) {
      fetchCategories();
    }
  }, [accountId]);

  useEffect(() => {
    if (selectedCategory) {
      fetchItems();
    }
  }, [selectedCategory, page]);

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const data = await API.getVODCategories(accountId);
      setCategories(data || []);
    } catch (error) {
      console.error('Failed to fetch VOD categories:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load VOD categories',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchItems = async () => {
    if (!selectedCategory) return;
    
    setLoading(true);
    try {
      const data = await API.getVODItems(accountId, selectedCategory, page);
      setItems(data.items || []);
      setTotalItems(data.total || 0);
    } catch (error) {
      console.error('Failed to fetch VOD items:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load VOD items',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!search.trim()) {
      fetchItems();
      return;
    }
    
    setLoading(true);
    try {
      const data = await API.searchVOD(accountId, search);
      setItems(data.items || []);
      setTotalItems(data.total || 0);
      setPage(1);
    } catch (error) {
      console.error('Failed to search VOD:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to search VOD',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (categoryId) => {
    setSelectedCategory(categoryId);
    setPage(1);
    setSearch('');
  };

  const handlePlayItem = async (item) => {
    try {
      const link = await API.getVODLink(accountId, item.cmd);
      if (link?.url) {
        window.open(link.url, '_blank');
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to get stream link',
        color: 'red',
      });
    }
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>VOD Browser</Title>
        <ActionIcon variant="light" onClick={fetchCategories}>
          <IconRefresh size={18} />
        </ActionIcon>
      </Group>

      <Paper withBorder p="md">
        <Group gap="md">
          <Select
            placeholder="Select category"
            value={selectedCategory}
            onChange={handleCategoryChange}
            data={categories.map(cat => ({
              value: cat.category_id || cat.id,
              label: `${cat.name} (${cat.item_count || 0})`,
            }))}
            searchable
            clearable
            style={{ flex: 1, maxWidth: 300 }}
            leftSection={<IconFolder size={16} />}
          />
          <TextInput
            placeholder="Search VOD..."
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            leftSection={<IconSearch size={16} />}
            style={{ flex: 1 }}
          />
          <Button onClick={handleSearch}>Search</Button>
        </Group>
      </Paper>

      <Box pos="relative" mih={400}>
        <LoadingOverlay visible={loading} />
        
        {!selectedCategory && !search ? (
          <Paper withBorder p="xl">
            <Stack align="center" gap="md">
              <IconFolder size={48} color="gray" />
              <Text c="dimmed">Select a category to browse VOD content</Text>
            </Stack>
          </Paper>
        ) : items.length === 0 ? (
          <Paper withBorder p="xl">
            <Text c="dimmed" ta="center">No VOD items found</Text>
          </Paper>
        ) : (
          <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 5 }} spacing="md">
            {items.map((item) => (
              <Card key={item.id || item.item_id} shadow="sm" padding="sm" withBorder>
                <Card.Section>
                  <Image
                    src={item.cover_url || item.cover || '/placeholder-movie.png'}
                    height={200}
                    alt={item.name}
                    fallbackSrc="/placeholder-movie.png"
                  />
                </Card.Section>

                <Stack gap="xs" mt="sm">
                  <Text fw={500} size="sm" lineClamp={2}>
                    {item.name}
                  </Text>
                  
                  <Group gap="xs">
                    {item.year && (
                      <Badge size="xs" variant="light">{item.year}</Badge>
                    )}
                    {item.rating && (
                      <Badge size="xs" variant="light" color="yellow">
                        ★ {item.rating}
                      </Badge>
                    )}
                  </Group>

                  <Group gap="xs" mt="auto">
                    <Tooltip label="Play">
                      <ActionIcon 
                        variant="filled" 
                        color="blue"
                        onClick={() => handlePlayItem(item)}
                      >
                        <IconPlayerPlay size={16} />
                      </ActionIcon>
                    </Tooltip>
                    {onSelectItem && (
                      <Tooltip label="Details">
                        <ActionIcon 
                          variant="light"
                          onClick={() => onSelectItem(item)}
                        >
                          <IconInfoCircle size={16} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                  </Group>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Box>

      {totalPages > 1 && (
        <Group justify="center">
          <Pagination 
            value={page} 
            onChange={setPage} 
            total={totalPages}
          />
        </Group>
      )}
    </Stack>
  );
};

export default VODBrowser;
