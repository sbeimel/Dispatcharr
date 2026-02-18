#!/bin/bash

# Fix stream_manager.py IndentationError
# This script removes duplicate code blocks that were accidentally left in

echo "Fixing stream_manager.py syntax error..."

cd ~/Dispatcharr

# Create backup
cp apps/proxy/ts_proxy/stream_manager.py apps/proxy/ts_proxy/stream_manager.py.backup

# Remove lines 1741-1767 (duplicate code block)
sed -i '1741,1767d' apps/proxy/ts_proxy/stream_manager.py

echo "✅ Fixed! Backup saved as stream_manager.py.backup"
echo ""
echo "Now rebuild the Docker image:"
echo "docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile ."
