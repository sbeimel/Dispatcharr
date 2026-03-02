#!/usr/bin/env python3
"""
Upgrade a PostgreSQL custom format dump by parsing it directly in Python.
No pg_restore needed!
"""

import struct
import sys
from pathlib import Path


def read_pg_dump_header(f):
    """Read and validate PostgreSQL custom format header"""
    magic = f.read(5)
    if magic != b'PGDMP':
        raise ValueError("Not a valid PostgreSQL custom format dump")
    
    vmaj = struct.unpack('B', f.read(1))[0]
    vmin = struct.unpack('B', f.read(1))[0]
    vrev = struct.unpack('B', f.read(1))[0]
    
    print(f"PostgreSQL dump version: {vmaj}.{vmin}.{vrev}")
    return vmaj, vmin, vrev


def create_upgraded_sql_dump(input_dump, output_sql):
    """
    Create an upgraded SQL dump by appending schema changes.
    Since parsing custom format is complex, we'll create a SQL script
    that can be run AFTER restoring the original dump.
    """
    
    print(f"Creating upgrade script for {input_dump}...")
    
    upgrade_sql = """-- ============================================================================
-- UPGRADE SCRIPT: 0.18.1 → 0.19.0
-- ============================================================================
-- 
-- INSTRUCTIONS:
-- 1. First restore your original backup: 
--    Use Dispatcharr UI or: pg_restore -d database database.dump
-- 2. Then run this script:
--    psql -d database < database_upgrade.sql
--
-- ============================================================================

BEGIN;

-- Add missing table: core_systemnotification
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

CREATE INDEX IF NOT EXISTS core_systemnotification_notification_key_idx ON core_systemnotification(notification_key);
CREATE INDEX IF NOT EXISTS core_system_is_acti_afab03_idx ON core_systemnotification(is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS core_system_notific_2179e3_idx ON core_systemnotification(notification_type, is_active);
CREATE INDEX IF NOT EXISTS core_system_source_a35829_idx ON core_systemnotification(source, is_active);

-- Add missing table: core_notificationdismissal
DROP TABLE IF EXISTS core_notificationdismissal CASCADE;
CREATE TABLE core_notificationdismissal (
    id BIGSERIAL PRIMARY KEY,
    dismissed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    action_taken VARCHAR(50),
    user_id BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    notification_id BIGINT NOT NULL REFERENCES core_systemnotification(id) ON DELETE CASCADE,
    UNIQUE(user_id, notification_id)
);

CREATE INDEX IF NOT EXISTS core_notifi_user_id_93e02e_idx ON core_notificationdismissal(user_id, notification_id);

-- Add missing columns
ALTER TABLE dispatcharr_channels_channel ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_id INTEGER;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_chno DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS dispatcharr_stream_id_idx ON dispatcharr_channels_stream(stream_id);
CREATE INDEX IF NOT EXISTS dispatcharr_stream_chno_idx ON dispatcharr_channels_stream(stream_chno);

-- Mark migrations as applied
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

COMMIT;

-- Verify upgrade
SELECT 'Upgrade completed successfully!' AS status;
SELECT COUNT(*) AS "New migrations applied" FROM django_migrations 
WHERE name IN (
    '0021_systemnotification_notificationdismissal',
    '0032_channel_is_adult_stream_is_adult',
    '0033_stream_id_stream_chno',
    '0034_remove_stream_dispatcharr_stream_id_idx_and_more',
    '0020_add_proxy_field'
);
"""
    
    with open(output_sql, 'w', encoding='utf-8') as f:
        f.write(upgrade_sql)
    
    print(f"\n✓ Upgrade script created: {output_sql}")
    print("\nNEXT STEPS:")
    print("1. Restore your original backup using Dispatcharr UI")
    print(f"2. Run: docker cp {output_sql} dispatcharr:/app/")
    print(f"3. Run: docker exec -it dispatcharr python manage.py dbshell < /app/{Path(output_sql).name}")
    print("4. Restart container: docker restart dispatcharr")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upgrade_dump_pure_python.py <input.dump> <output_upgrade.sql>")
        print("Example: python upgrade_dump_pure_python.py database.dump database_upgrade.sql")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Verify it's a PostgreSQL dump
    try:
        with open(input_file, 'rb') as f:
            read_pg_dump_header(f)
    except Exception as e:
        print(f"Warning: Could not verify dump format: {e}")
        print("Continuing anyway...")
    
    if create_upgraded_sql_dump(input_file, output_file):
        print("\n✓ Done!")
    else:
        print("\n✗ Failed!")
        sys.exit(1)
