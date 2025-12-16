"""
HTTP Stream Reader - Thread-based HTTP stream reader that writes to a pipe.
This allows us to use the same fetch_chunk() path for both transcode and HTTP streams.
"""

import threading
import os
import requests
from requests.adapters import HTTPAdapter
from .utils import get_logger

logger = get_logger()


class HTTPStreamReader:
    """Thread-based HTTP stream reader that writes to a pipe"""

    def __init__(self, url, user_agent=None, chunk_size=8192):
        self.url = url
        self.user_agent = user_agent
        self.chunk_size = chunk_size
        self.session = None
        self.response = None
        self.thread = None
        self.pipe_read = None
        self.pipe_write = None
        self.running = False
        # Stream metrics
        self.response_time_ms = None  # Time to first byte in milliseconds
        self.connection_error = None  # Error message if connection failed

    def start(self):
        """Start the HTTP stream reader thread"""
        # Create a pipe (works on Windows and Unix)
        self.pipe_read, self.pipe_write = os.pipe()

        # Start the reader thread
        self.running = True
        self.thread = threading.Thread(target=self._read_stream, daemon=True)
        self.thread.start()

        logger.info(f"Started HTTP stream reader thread for {self.url}")
        return self.pipe_read

    def _read_stream(self):
        """Thread worker that reads HTTP stream and writes to pipe"""
        import time as time_module
        try:
            # Build headers
            headers = {}
            if self.user_agent:
                headers['User-Agent'] = self.user_agent

            logger.info(f"HTTP reader connecting to {self.url}")

            # Create session
            self.session = requests.Session()

            # Disable retries for faster failure detection
            adapter = HTTPAdapter(max_retries=0, pool_connections=1, pool_maxsize=1)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)

            # Track response time (time to first byte)
            request_start_time = time_module.time()

            # Stream the URL
            self.response = self.session.get(
                self.url,
                headers=headers,
                stream=True,
                timeout=(5, 30)  # 5s connect, 30s read
            )

            # Calculate response time in milliseconds
            self.response_time_ms = (time_module.time() - request_start_time) * 1000

            if self.response.status_code != 200:
                self.connection_error = f"HTTP {self.response.status_code}"
                logger.error(f"HTTP {self.response.status_code} from {self.url}")
                return

            logger.info(f"HTTP reader connected successfully (response time: {self.response_time_ms:.0f}ms), streaming data...")

            # Stream chunks to pipe
            chunk_count = 0
            for chunk in self.response.iter_content(chunk_size=self.chunk_size):
                if not self.running:
                    break

                if chunk:
                    try:
                        # Write binary data to pipe
                        os.write(self.pipe_write, chunk)
                        chunk_count += 1

                        # Log progress periodically
                        if chunk_count % 1000 == 0:
                            logger.debug(f"HTTP reader streamed {chunk_count} chunks")
                    except OSError as e:
                        logger.error(f"Pipe write error: {e}")
                        break

            logger.info("HTTP stream ended")

        except requests.exceptions.RequestException as e:
            self.connection_error = str(e)
            logger.error(f"HTTP reader request error: {e}")
        except Exception as e:
            self.connection_error = str(e)
            logger.error(f"HTTP reader unexpected error: {e}", exc_info=True)
        finally:
            self.running = False
            # Close write end of pipe to signal EOF
            try:
                if self.pipe_write is not None:
                    os.close(self.pipe_write)
                    self.pipe_write = None
            except OSError:
                pass

    def stop(self):
        """Stop the HTTP stream reader"""
        logger.info("Stopping HTTP stream reader")
        self.running = False

        # Close response
        if self.response:
            try:
                self.response.close()
            except Exception:
                pass

        # Close session
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass

        # Close write end of pipe
        if self.pipe_write is not None:
            try:
                os.close(self.pipe_write)
                self.pipe_write = None
            except OSError:
                pass

        # Wait for thread
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
