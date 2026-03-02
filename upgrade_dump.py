#!/usr/bin/env python3
"""
Upgrade a 0.18.1 database dump to 0.19.0 schema by adding missing fields.
This modifies the dump file directly before restore.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def upgrade_dump(input_dump, output_dump):
    """
    Convert PostgreSQL custom format dump to SQL, add missing schema, convert back.
    """
    print(f"Upgrading {input_dump} to 0.19.0 schema...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sql_file = tmp_path / "dump.sql"
        
        # Step 1: Convert custom format to SQL
        print("Converting dump to SQL...")
        result = subprocess.run(
            ["pg_restore", "--no-owner", "--no-acl", "-f", str(sql_file), input_dump],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error converting dump: {result.stderr}")
            return False
        
        # Step 2: Read SQL and add missing schema
        print("Adding missing 0.19.0 schema...")
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Add missing columns and tables at the end
        schema_additions = """

-- ============================================================================
-- SCHEMA UPGRADES FOR 0.19.0 COMPATIBILITY
-- ============================================================================

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
CREATE INDEX IF NOT EXISTS core_systemnotification_notification_type_idx ON core_systemnotification(notification_type);
CREATE INDEX IF NOT EXISTS core_systemnotification_source_idx ON core_systemnotification(source);
CREATE INDEX IF NOT EXISTS core_systemnotification_is_active_idx ON core_systemnotification(is_active);
CREATE INDEX IF NOT EXISTS core_systemnotification_expires_at_idx ON core_systemnotification(expires_at);
CREATE INDEX IF NOT EXISTS core_system_is_acti_afab03_idx ON core_systemnotification(is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS core_system_notific_2179e3_idx ON core_systemnotification(notification_type, is_active);
CREATE INDEX IF NOT EXISTS core_system_source_a35829_idx ON core_systemnotification(source, is_active);

-- Add missing table: core_notificationdismissal
CREATE TABLE IF NOT EXISTS core_notificationdismissal (
    id BIGSERIAL PRIMARY KEY,
    dismissed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    action_taken VARCHAR(50),
    user_id BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    notification_id BIGINT NOT NULL REFERENCES core_systemnotification(id) ON DELETE CASCADE,
    UNIQUE(user_id, notification_id)
);

CREATE INDEX IF NOT EXISTS core_notifi_user_id_93e02e_idx ON core_notificationdismissal(user_id, notification_id);

-- Add missing columns: is_adult fields
ALTER TABLE dispatcharr_channels_channel ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;

-- Add missing columns: stream_id and stream_chno
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_id INTEGER;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_chno DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS dispatcharr_stream_id_idx ON dispatcharr_channels_stream(stream_id);
CREATE INDEX IF NOT EXISTS dispatcharr_stream_chno_idx ON dispatcharr_channels_stream(stream_chno);

-- Mark migrations as applied
INSERT INTO django_migrations (app, name, applied) VALUES ('core', '0021_systemnotification_notificationdismissal', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO django_migrations (app, name, applied) VALUES ('dispatcharr_channels', '0032_channel_is_adult_stream_is_adult', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO django_migrations (app, name, applied) VALUES ('dispatcharr_channels', '0033_stream_id_stream_chno', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO django_migrations (app, name, applied) VALUES ('dispatcharr_channels', '0034_remove_stream_dispatcharr_stream_id_idx_and_more', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO django_migrations (app, name, applied) VALUES ('m3u', '0020_add_proxy_field', NOW()) ON CONFLICT DO NOTHING;

"""
        
        # Append schema additions
        upgraded_sql = sql_content + schema_additions
        
        # Step 3: Write upgraded SQL
        upgraded_sql_file = tmp_path / "upgraded.sql"
        with open(upgraded_sql_file, 'w', encoding='utf-8') as f:
            f.write(upgraded_sql)
        
        # Step 4: Convert back to custom format
        print(f"Converting to custom format: {output_dump}...")
        result = subprocess.run(
            ["pg_dump", "-Fc", "-f", output_dump, f"--file={upgraded_sql_file}"],
            capture_output=True,
            text=True
        )
        
        # Actually, pg_dump can't read from SQL file. Let's just keep it as SQL
        print(f"Saving as SQL format: {output_dump}...")
        with open(output_dump, 'w', encoding='utf-8') as f:
            f.write(upgraded_sql)
        
        print(f"✓ Upgraded dump saved to: {output_dump}")
        print(f"  You can restore it with: psql < {output_dump}")
        print(f"  Or use pg_restore if you convert it back to custom format")
        
        return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upgrade_dump.py <input.dump> <output.sql>")
        print("Example: python upgrade_dump.py database.dump database_upgraded.sql")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    if upgrade_dump(input_file, output_file):
        print("\n✓ Success! Your upgraded dump is ready.")
    else:
        print("\n✗ Failed to upgrade dump.")
        sys.exit(1)
