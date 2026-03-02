-- SQL script to fix a restored 0.18.1 backup for 0.19.0 compatibility
-- Run this AFTER restoring an old backup: python manage.py dbshell < fix_restored_backup.sql

-- Clean up any partially created tables from previous failed attempts
DROP TABLE IF EXISTS core_notificationdismissal CASCADE;

-- Add missing table from core migration 0021 (SystemNotification)
CREATE TABLE IF NOT EXISTS core_systemnotification (
    id BIGSERIAL PRIMARY KEY,
    notification_key VARCHAR(255) UNIQUE NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'info' NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal' NOT NULL,
    source VARCHAR(20) DEFAULT 'system' NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    action_data JSONB DEFAULT '{}' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    admin_only BOOLEAN DEFAULT FALSE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS core_systemnotification_notification_key_idx 
ON core_systemnotification(notification_key);

CREATE INDEX IF NOT EXISTS core_systemnotification_notification_type_idx 
ON core_systemnotification(notification_type);

CREATE INDEX IF NOT EXISTS core_systemnotification_source_idx 
ON core_systemnotification(source);

CREATE INDEX IF NOT EXISTS core_systemnotification_is_active_idx 
ON core_systemnotification(is_active);

CREATE INDEX IF NOT EXISTS core_systemnotification_expires_at_idx 
ON core_systemnotification(expires_at);

CREATE INDEX IF NOT EXISTS core_system_is_acti_afab03_idx 
ON core_systemnotification(is_active, created_at DESC);

CREATE INDEX IF NOT EXISTS core_system_notific_2179e3_idx 
ON core_systemnotification(notification_type, is_active);

CREATE INDEX IF NOT EXISTS core_system_source_a35829_idx 
ON core_systemnotification(source, is_active);

-- Add NotificationDismissal table
CREATE TABLE IF NOT EXISTS core_notificationdismissal (
    id BIGSERIAL PRIMARY KEY,
    dismissed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    action_taken VARCHAR(50),
    user_id BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    notification_id BIGINT NOT NULL REFERENCES core_systemnotification(id) ON DELETE CASCADE,
    UNIQUE(user_id, notification_id)
);

CREATE INDEX IF NOT EXISTS core_notifi_user_id_93e02e_idx 
ON core_notificationdismissal(user_id, notification_id);

-- Add missing columns from migration 0032 (is_adult fields)
ALTER TABLE dispatcharr_channels_channel 
ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;

ALTER TABLE dispatcharr_channels_stream 
ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;

-- Add missing columns from migration 0033 (stream_id and stream_chno)
ALTER TABLE dispatcharr_channels_stream 
ADD COLUMN IF NOT EXISTS stream_id INTEGER;

ALTER TABLE dispatcharr_channels_stream 
ADD COLUMN IF NOT EXISTS stream_chno DOUBLE PRECISION;

-- Add indexes if they don't exist
CREATE INDEX IF NOT EXISTS dispatcharr_stream_id_idx 
ON dispatcharr_channels_stream(stream_id);

CREATE INDEX IF NOT EXISTS dispatcharr_stream_chno_idx 
ON dispatcharr_channels_stream(stream_chno);

-- Update django_migrations table to mark migrations as applied
INSERT INTO django_migrations (app, name, applied)
VALUES ('core', '0021_systemnotification_notificationdismissal', NOW())
ON CONFLICT DO NOTHING;

INSERT INTO django_migrations (app, name, applied)
VALUES ('dispatcharr_channels', '0032_channel_is_adult_stream_is_adult', NOW())
ON CONFLICT DO NOTHING;

INSERT INTO django_migrations (app, name, applied)
VALUES ('dispatcharr_channels', '0033_stream_id_stream_chno', NOW())
ON CONFLICT DO NOTHING;

INSERT INTO django_migrations (app, name, applied)
VALUES ('dispatcharr_channels', '0034_remove_stream_dispatcharr_stream_id_idx_and_more', NOW())
ON CONFLICT DO NOTHING;

INSERT INTO django_migrations (app, name, applied)
VALUES ('m3u', '0020_add_proxy_field', NOW())
ON CONFLICT DO NOTHING;

-- Note: Migration 0033 includes a data migration that populates stream_id and stream_chno
-- from custom_properties. You may want to run: python manage.py migrate --run-syncdb
-- to properly execute the data migration logic.

SELECT 'Backup schema upgraded successfully!' AS status;
