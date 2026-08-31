import { PROXY_SETTINGS_OPTIONS } from '../../../constants.js';

export const getProxySettingsFormInitialValues = () => {
  return Object.keys(PROXY_SETTINGS_OPTIONS).reduce((acc, key) => {
    acc[key] = '';
    return acc;
  }, {});
};

export const getProxySettingDefaults = () => {
  return {
    buffering_timeout: 15,
    buffering_speed: 1.0,
    redis_chunk_ttl: 60,
    channel_shutdown_delay: 0,
    channel_init_grace_period: 5,
    new_client_behind_seconds: 5,
    stream_cooldown_enabled: false,
    stream_cooldown_minutes: 10,
    connection_timeout: 10,
    max_retries: 3,
    url_switch_timeout: 10,
    max_stream_switches: 5,
    failover_rotation_cooldown: 60,
    retry_wait_interval: 2,
    failover_grace_period: 3,
    chunk_timeout: 10,
    client_wait_timeout: 10,
    stream_timeout: 30,
    retry_window_seconds: 60,
    stable_connection_threshold: 30,
  };
};
