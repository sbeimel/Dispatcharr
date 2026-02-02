#!/bin/bash

echo "Applying Dispatcharr Stream Timeout Fixes..."

# Fix 1: Increase grace period from 5 to 30 seconds
echo "1. Increasing channel_init_grace_period from 5 to 30 seconds..."
sed -i 's/"channel_init_grace_period": 5,/"channel_init_grace_period": 30,/g' apps/proxy/config.py

# Fix 2: Add connection attempt time reset in update_url method
echo "2. Adding connection attempt time reset to stream switching..."

# Check if the fix is already applied
if ! grep -q "Reset connection attempt time in Redis" apps/proxy/ts_proxy/stream_manager.py; then
    # Find the line with "self.url_switch_start_time = time.time()" and add our fix after it
    sed -i '/self\.url_switch_start_time = time\.time()/a\\n        # Reset connection attempt time in Redis to restart grace period\n        try:\n            from .redis_keys import RedisKeys\n            from core.utils import RedisClient\n            redis_client = RedisClient.get_client()\n            if redis_client:\n                attempt_key = RedisKeys.connection_attempt(self.channel_id)\n                redis_client.setex(attempt_key, 60, str(time.time()))\n                logger.debug(f"Reset connection attempt time for channel {self.channel_id} during stream switch")\n        except Exception as e:\n            logger.warning(f"Could not reset connection attempt time for channel {self.channel_id}: {e}")' apps/proxy/ts_proxy/stream_manager.py
fi

echo "3. Fixes applied successfully!"
echo ""
echo "To apply these fixes:"
echo "1. Run this script: bash fix_stream_timeout.sh"
echo "2. Rebuild your Docker image: docker build -t sbeimel/dispatcharr:0.18.1-fixed -f docker/Dockerfile ."
echo "3. Restart your container with the new image"
echo ""
echo "These fixes address:"
echo "- Streams getting stuck in 'connecting' state"
echo "- 5-second timeout being too short for stream switching"
echo "- Grace period not resetting when switching streams"