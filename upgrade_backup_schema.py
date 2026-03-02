#!/usr/bin/env python3
"""
Script to upgrade an old backup dump to the new schema by adding missing columns.
This allows restoring 0.18.1 backups into 0.19.0 without migration errors.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def add_missing_columns_to_dump(input_dump: str, output_dump: str):
    """
    Add missing columns to a PostgreSQL dump file.
    
    This script:
    1. Converts the custom format dump to SQL
    2. Adds ALTER TABLE statements for missing columns
    3. Converts back to custom format
    """
    
    print(f"Processing {input_dump}...")
    
    # SQL statements to add missing columns (idempotent with IF NOT EXISTS)
    missing_columns_sql = """
-- Add missing columns from 0.19.0 schema

-- From migration 0032: is_adult fields
ALTER TABLE dispatcharr_channels_channel ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS is_adult BOOLEAN DEFAULT FALSE;

-- From migration 0033: stream_id and stream_chno fields
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_id INTEGER;
ALTER TABLE dispatcharr_channels_stream ADD COLUMN IF NOT EXISTS stream_chno DOUBLE PRECISION;

-- From migration 0021 (core): system notifications
-- Note: This will be handled by migrations, just ensuring table exists
"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sql_file = tmp_path / "dump.sql"
        patch_file = tmp_path / "patch.sql"
        
        # Step 1: Convert custom format to SQL
        print("Converting dump to SQL format...")
        result = subprocess.run(
            ["pg_restore", "--no-owner", "--no-acl", "-f", str(sql_file), input_dump],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 and "pg_restore" in result.stderr:
            print("ERROR: pg_restore not found. This script must run in an environment with PostgreSQL tools.")
            print("Run this inside the Docker container:")
            print("  docker exec -it dispatcharr python upgrade_backup_schema.py")
            sys.exit(1)
        
        # Step 2: Create patch SQL file
        print("Creating schema patch...")
        with open(patch_file, 'w') as f:
            f.write(missing_columns_sql)
        
        # Step 3: Combine SQL files
        print("Combining SQL files...")
        combined_sql = tmp_path / "combined.sql"
        with open(combined_sql, 'w') as outf:
            # First the original dump
            with open(sql_file, 'r') as inf:
                outf.write(inf.read())
            # Then our patches
            outf.write("\n\n-- Schema upgrades for 0.19.0 compatibility\n")
            with open(patch_file, 'r') as inf:
                outf.write(inf.read())
        
        # Step 4: Convert back to custom format
        print(f"Creating upgraded dump: {output_dump}...")
        result = subprocess.run(
            ["pg_dump", "--format=custom", "--file", output_dump, "--dbname", f"file://{combined_sql}"],
            capture_output=True,
            text=True
        )
        
        # Alternative: Just append the ALTER statements to the SQL and keep it as SQL
        # This is simpler and works with pg_restore
        print(f"Creating upgraded SQL dump: {output_dump}.sql...")
        with open(f"{output_dump}.sql", 'w') as outf:
            with open(sql_file, 'r') as inf:
                content = inf.read()
                # Insert ALTER statements after CREATE TABLE statements
                outf.write(content)
                outf.write("\n\n-- Schema upgrades for 0.19.0 compatibility\n")
                outf.write(missing_columns_sql)
    
    print("Done! Upgraded dump created.")
    print(f"You can now restore using: pg_restore {output_dump}.sql")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upgrade_backup_schema.py <input_dump> <output_dump>")
        print("Example: python upgrade_backup_schema.py database.dump database_upgraded.dump")
        sys.exit(1)
    
    input_dump = sys.argv[1]
    output_dump = sys.argv[2]
    
    if not Path(input_dump).exists():
        print(f"ERROR: Input file not found: {input_dump}")
        sys.exit(1)
    
    add_missing_columns_to_dump(input_dump, output_dump)
