/**
 * VOD Detail View Component
 * 
 * Displays detailed VOD information with metadata.
 * Requirements: 38.1, 38.2, 38.3, 38.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Button,
  LoadingOverlay,
  Box,
  Image,
  Badge,
  Grid,
  Divider,
  Progress,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconPlayerPlay,
  IconBookmark,
  IconBookmarkFilled,
  IconClock,
  IconCalendar,
  IconStar,
  IconMovie,
  IconArrowLeft,
} from '@tabler/icons-react';
import API from '../../api';

const VODDetailView = ({ accountId, item, onBack, onPlay }) => {
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState(null);
  const [resumePoint, setResumePoint] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);

  useEffect(() => {
    if (item) {
      fetchDetails();
      fetchResumePoint();
    }
  }, [item]);

  const fetchDetails = async () => {
    setLoading(true);
    try {
      const data = await API.getVODInfo(accountId, item.id || item.item_id);
      setDetails(data);
      setIsFavorite(data?.is_favorite || false);
    } catch (error) {
      console.error('Failed to fetch VOD details:', error);
      // Use item data as fallback
      setDetails(item);
    } finally {
      setLoading(false);
    }
  };

  const fetchResumePoint = async () => {
    try {
      const data = await API.getVODResumePoint(accountId, item.id || item.item_id);
      setResumePoint(data);
    } catch (error) {
      // Resume point not found is not an error
    }
  };

  const handlePlay = async (fromStart = false) => {
    try {
      const link = await API.getVODLink(accountId, item.cmd);
      if (link?.url) {
        const url = fromStart || !resumePoint 
          ? link.url 
          : `${link.url}#t=${resumePoint.position_seconds}`;
        
        if (onPlay) {
          onPlay(url, item);
        } else {
          window.open(url, '_blank');
        }
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to get stream link',
        color: 'red',
      });
    }
  };

  const handleToggleFavorite = async () => {
    try {
      if (isFavorite) {
        await API.removeVODFavorite(accountId, item.id || item.item_id);
      } else {
        await API.addVODFavorite(accountId, item.id || item.item_id);
      }
      setIsFavorite(!isFavorite);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to update favorite',
        color: 'red',
      });
    }
  };

  const data = details || item;
  const progressPercent = resumePoint && data?.duration_seconds
    ? (resumePoint.position_seconds / data.duration_seconds) * 100
    : 0;

  const formatDuration = (seconds) => {
    if (!seconds) return null;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  };

  return (
    <Box pos="relative">
      <LoadingOverlay visible={loading} />
      
      <Stack gap="md">
        {onBack && (
          <Button 
            variant="subtle" 
            leftSection={<IconArrowLeft size={16} />}
            onClick={onBack}
            w="fit-content"
          >
            Back to Browser
          </Button>
        )}

        <Paper withBorder p="md">
          <Grid>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Image
                src={data?.cover_url || data?.cover || '/placeholder-movie.png'}
                alt={data?.name}
                radius="md"
                fallbackSrc="/placeholder-movie.png"
              />
              
              {resumePoint && (
                <Box mt="sm">
                  <Group justify="space-between" mb="xs">
                    <Text size="xs" c="dimmed">Continue watching</Text>
                    <Text size="xs" c="dimmed">
                      {formatDuration(resumePoint.position_seconds)} / {formatDuration(data?.duration_seconds)}
                    </Text>
                  </Group>
                  <Progress value={progressPercent} size="sm" />
                </Box>
              )}
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 8 }}>
              <Stack gap="md">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Title order={2}>{data?.name}</Title>
                    {data?.original_name && data.original_name !== data.name && (
                      <Text size="sm" c="dimmed">{data.original_name}</Text>
                    )}
                  </div>
                  <Tooltip label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}>
                    <ActionIcon 
                      variant="light" 
                      color="yellow"
                      size="lg"
                      onClick={handleToggleFavorite}
                    >
                      {isFavorite ? <IconBookmarkFilled size={20} /> : <IconBookmark size={20} />}
                    </ActionIcon>
                  </Tooltip>
                </Group>

                <Group gap="md">
                  {data?.year && (
                    <Badge leftSection={<IconCalendar size={12} />} variant="light">
                      {data.year}
                    </Badge>
                  )}
                  {data?.rating && (
                    <Badge leftSection={<IconStar size={12} />} variant="light" color="yellow">
                      {data.rating}
                    </Badge>
                  )}
                  {data?.duration_seconds && (
                    <Badge leftSection={<IconClock size={12} />} variant="light">
                      {formatDuration(data.duration_seconds)}
                    </Badge>
                  )}
                  {data?.genre && (
                    <Badge leftSection={<IconMovie size={12} />} variant="light">
                      {data.genre}
                    </Badge>
                  )}
                </Group>

                <Divider />

                {data?.description && (
                  <div>
                    <Text fw={500} mb="xs">Description</Text>
                    <Text size="sm" c="dimmed">{data.description}</Text>
                  </div>
                )}

                {(data?.director || data?.cast) && (
                  <>
                    <Divider />
                    <Grid>
                      {data?.director && (
                        <Grid.Col span={6}>
                          <Text fw={500} size="sm">Director</Text>
                          <Text size="sm" c="dimmed">{data.director}</Text>
                        </Grid.Col>
                      )}
                      {data?.cast && (
                        <Grid.Col span={6}>
                          <Text fw={500} size="sm">Cast</Text>
                          <Text size="sm" c="dimmed">{data.cast}</Text>
                        </Grid.Col>
                      )}
                    </Grid>
                  </>
                )}

                <Divider />

                <Group>
                  {resumePoint ? (
                    <>
                      <Button 
                        leftSection={<IconPlayerPlay size={16} />}
                        onClick={() => handlePlay(false)}
                      >
                        Continue Watching
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => handlePlay(true)}
                      >
                        Start from Beginning
                      </Button>
                    </>
                  ) : (
                    <Button 
                      leftSection={<IconPlayerPlay size={16} />}
                      onClick={() => handlePlay(true)}
                    >
                      Play
                    </Button>
                  )}
                </Group>
              </Stack>
            </Grid.Col>
          </Grid>
        </Paper>
      </Stack>
    </Box>
  );
};

export default VODDetailView;
