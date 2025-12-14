/**
 * Series Detail View Component
 * 
 * Displays series with seasons and episodes.
 * Requirements: 13.3, 39.1, 39.2
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
  Tabs,
  List,
  ActionIcon,
  Tooltip,
  Progress,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconPlayerPlay,
  IconBookmark,
  IconBookmarkFilled,
  IconCalendar,
  IconStar,
  IconArrowLeft,
  IconCheck,
} from '@tabler/icons-react';
import API from '../../api';

const SeriesDetailView = ({ accountId, series, onBack, onPlay }) => {
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [watchedEpisodes, setWatchedEpisodes] = useState({});
  const [isFavorite, setIsFavorite] = useState(false);

  useEffect(() => {
    if (series) {
      fetchDetails();
    }
  }, [series]);

  const fetchDetails = async () => {
    setLoading(true);
    try {
      const data = await API.getSeriesInfo(accountId, series.id || series.series_id);
      setDetails(data);
      setIsFavorite(data?.is_favorite || false);
      
      // Set first season as default
      if (data?.seasons?.length > 0) {
        setSelectedSeason(data.seasons[0].season_number || data.seasons[0].id);
      }
      
      // Fetch watched status
      const watched = await API.getSeriesWatchedStatus(accountId, series.id || series.series_id);
      setWatchedEpisodes(watched || {});
    } catch (error) {
      console.error('Failed to fetch series details:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load series details',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePlayEpisode = async (episode) => {
    try {
      const link = await API.getSeriesLink(
        accountId, 
        episode.cmd,
        series.id || series.series_id,
        selectedSeason,
        episode.id || episode.episode_id
      );
      
      if (link?.url) {
        if (onPlay) {
          onPlay(link.url, episode, series);
        } else {
          window.open(link.url, '_blank');
        }
        
        // Mark as watched
        markEpisodeWatched(episode);
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to get stream link',
        color: 'red',
      });
    }
  };

  const markEpisodeWatched = async (episode) => {
    try {
      await API.markEpisodeWatched(
        accountId,
        series.id || series.series_id,
        selectedSeason,
        episode.id || episode.episode_id
      );
      setWatchedEpisodes(prev => ({
        ...prev,
        [`${selectedSeason}-${episode.id || episode.episode_id}`]: true,
      }));
    } catch (error) {
      // Silent fail for watched status
    }
  };

  const handleToggleFavorite = async () => {
    try {
      if (isFavorite) {
        await API.removeSeriesFavorite(accountId, series.id || series.series_id);
      } else {
        await API.addSeriesFavorite(accountId, series.id || series.series_id);
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

  const isEpisodeWatched = (episode) => {
    return watchedEpisodes[`${selectedSeason}-${episode.id || episode.episode_id}`];
  };

  const currentSeason = details?.seasons?.find(
    s => (s.season_number || s.id) === selectedSeason
  );
  
  const episodes = currentSeason?.episodes || details?.episodes?.filter(
    e => e.season === selectedSeason || e.season_number === selectedSeason
  ) || [];

  const watchedCount = episodes.filter(e => isEpisodeWatched(e)).length;
  const progressPercent = episodes.length > 0 ? (watchedCount / episodes.length) * 100 : 0;

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
                src={series?.cover_url || series?.cover || '/placeholder-series.png'}
                alt={series?.name}
                radius="md"
                fallbackSrc="/placeholder-series.png"
              />
              
              {episodes.length > 0 && (
                <Box mt="sm">
                  <Group justify="space-between" mb="xs">
                    <Text size="xs" c="dimmed">Progress</Text>
                    <Text size="xs" c="dimmed">
                      {watchedCount} / {episodes.length} episodes
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
                    <Title order={2}>{series?.name}</Title>
                    {series?.original_name && series.original_name !== series.name && (
                      <Text size="sm" c="dimmed">{series.original_name}</Text>
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
                  {series?.year && (
                    <Badge leftSection={<IconCalendar size={12} />} variant="light">
                      {series.year}
                    </Badge>
                  )}
                  {series?.rating && (
                    <Badge leftSection={<IconStar size={12} />} variant="light" color="yellow">
                      {series.rating}
                    </Badge>
                  )}
                  {details?.seasons && (
                    <Badge variant="light" color="blue">
                      {details.seasons.length} Seasons
                    </Badge>
                  )}
                </Group>

                {(series?.description || details?.description) && (
                  <>
                    <Divider />
                    <div>
                      <Text fw={500} mb="xs">Description</Text>
                      <Text size="sm" c="dimmed">
                        {details?.description || series?.description}
                      </Text>
                    </div>
                  </>
                )}
              </Stack>
            </Grid.Col>
          </Grid>
        </Paper>

        {details?.seasons && details.seasons.length > 0 && (
          <Paper withBorder p="md">
            <Tabs value={selectedSeason?.toString()} onChange={(val) => setSelectedSeason(val)}>
              <Tabs.List>
                {details.seasons.map((season) => (
                  <Tabs.Tab 
                    key={season.season_number || season.id} 
                    value={(season.season_number || season.id).toString()}
                  >
                    Season {season.season_number || season.name}
                  </Tabs.Tab>
                ))}
              </Tabs.List>

              {details.seasons.map((season) => (
                <Tabs.Panel 
                  key={season.season_number || season.id} 
                  value={(season.season_number || season.id).toString()}
                  pt="md"
                >
                  <List spacing="xs">
                    {episodes.map((episode) => (
                      <List.Item
                        key={episode.id || episode.episode_id}
                        icon={
                          isEpisodeWatched(episode) ? (
                            <IconCheck size={16} color="green" />
                          ) : null
                        }
                      >
                        <Group justify="space-between">
                          <div>
                            <Text size="sm" fw={500}>
                              E{episode.episode_number || episode.episode_num}: {episode.name || episode.title}
                            </Text>
                            {episode.plot && (
                              <Text size="xs" c="dimmed" lineClamp={1}>
                                {episode.plot}
                              </Text>
                            )}
                          </div>
                          <Group gap="xs">
                            {episode.duration && (
                              <Text size="xs" c="dimmed">{episode.duration}</Text>
                            )}
                            <Tooltip label="Play Episode">
                              <ActionIcon 
                                variant="filled" 
                                color="blue"
                                onClick={() => handlePlayEpisode(episode)}
                              >
                                <IconPlayerPlay size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Group>
                      </List.Item>
                    ))}
                  </List>
                </Tabs.Panel>
              ))}
            </Tabs>
          </Paper>
        )}
      </Stack>
    </Box>
  );
};

export default SeriesDetailView;
