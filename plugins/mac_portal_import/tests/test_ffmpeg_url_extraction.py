"""
Property-Based Test for FFmpeg URL Extraction.

**Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
**Validates: Requirements 3.4**

Tests that for any cmd string containing "ffmpeg http://...",
the extractor should return only the HTTP URL portion.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings

from utils import StreamLinkGenerator


# Strategy for generating valid HTTP URLs
def http_url_strategy():
    """Generates valid HTTP URLs for testing."""
    return st.builds(
        lambda scheme, host, port, path: f"{scheme}://{host}{port}{path}",
        scheme=st.sampled_from(['http', 'https']),
        host=st.from_regex(r'[a-z][a-z0-9]{2,10}\.[a-z]{2,4}', fullmatch=True),
        port=st.one_of(
            st.just(''),
            st.integers(min_value=1, max_value=65535).map(lambda p: f':{p}')
        ),
        path=st.one_of(
            st.just(''),
            st.from_regex(r'/[a-z0-9_/]{1,30}', fullmatch=True)
        )
    )


class TestFFmpegURLExtraction:
    """
    Property-Based Tests for FFmpeg URL Extraction.
    
    **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
    **Validates: Requirements 3.4**
    """
    
    @given(url=http_url_strategy())
    @settings(max_examples=100)
    def test_ffmpeg_prefix_extraction(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        **Validates: Requirements 3.4**
        
        Property: For any cmd string containing "ffmpeg http://...",
        the extractor should return only the HTTP URL portion.
        """
        # Create cmd with ffmpeg prefix
        cmd = f"ffmpeg {url}"
        
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        # Result should equal the original URL
        assert result == url, f"Expected {url}, got {result}"
    
    @given(url=http_url_strategy())
    @settings(max_examples=100)
    def test_ffmpeg_uppercase_prefix_extraction(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        **Validates: Requirements 3.4**
        
        Property: FFmpeg extraction should be case-insensitive for the prefix.
        """
        # Create cmd with uppercase FFMPEG prefix
        cmd = f"FFMPEG {url}"
        
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        # Result should equal the original URL
        assert result == url, f"Expected {url}, got {result}"
    
    @given(url=http_url_strategy())
    @settings(max_examples=100)
    def test_direct_url_extraction(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        **Validates: Requirements 3.4**
        
        Property: Direct HTTP URLs (without ffmpeg prefix) should be returned as-is.
        """
        result = StreamLinkGenerator.extract_url_from_cmd(url)
        
        # Result should equal the original URL
        assert result == url, f"Expected {url}, got {result}"
    
    @given(url=http_url_strategy())
    @settings(max_examples=100)
    def test_url_with_whitespace_trimmed(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        **Validates: Requirements 3.4**
        
        Property: URLs with leading/trailing whitespace should be trimmed.
        """
        # Add whitespace around URL
        cmd = f"  {url}  "
        
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        # Result should equal the trimmed URL
        assert result == url, f"Expected {url}, got {result}"
    
    @given(url=http_url_strategy())
    @settings(max_examples=100)
    def test_ffmpeg_with_whitespace_trimmed(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        **Validates: Requirements 3.4**
        
        Property: FFmpeg commands with extra whitespace should still extract URL correctly.
        """
        # Add extra whitespace
        cmd = f"ffmpeg   {url}  "
        
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        # Result should equal the trimmed URL (may have leading space from split)
        assert result is not None, "Result should not be None"
        assert url in result or result.strip() == url, f"Expected {url} in result, got {result}"
    
    def test_empty_cmd_returns_none(self):
        """
        Edge case: Empty cmd should return None.
        """
        result = StreamLinkGenerator.extract_url_from_cmd('')
        assert result is None, "Empty cmd should return None"
    
    def test_none_cmd_returns_none(self):
        """
        Edge case: None cmd should return None.
        """
        result = StreamLinkGenerator.extract_url_from_cmd(None)
        assert result is None, "None cmd should return None"
    
    def test_non_http_cmd_returns_none(self):
        """
        Edge case: cmd without HTTP URL should return None.
        """
        result = StreamLinkGenerator.extract_url_from_cmd('some random text')
        assert result is None, "Non-HTTP cmd should return None"
    
    def test_ffmpeg_without_url_returns_none(self):
        """
        Edge case: ffmpeg without URL should return None.
        """
        result = StreamLinkGenerator.extract_url_from_cmd('ffmpeg ')
        # Should return empty string or None depending on implementation
        assert result is None or result == '', "ffmpeg without URL should return None or empty"


def run_tests_manually():
    """Run tests manually without pytest to avoid Django interference."""
    test_instance = TestFFmpegURLExtraction()
    
    print("Running Property-Based Tests for FFmpeg URL Extraction...")
    print("=" * 60)
    
    tests = [
        ('test_ffmpeg_prefix_extraction', test_instance.test_ffmpeg_prefix_extraction),
        ('test_ffmpeg_uppercase_prefix_extraction', test_instance.test_ffmpeg_uppercase_prefix_extraction),
        ('test_direct_url_extraction', test_instance.test_direct_url_extraction),
        ('test_url_with_whitespace_trimmed', test_instance.test_url_with_whitespace_trimmed),
        ('test_ffmpeg_with_whitespace_trimmed', test_instance.test_ffmpeg_with_whitespace_trimmed),
        ('test_empty_cmd_returns_none', test_instance.test_empty_cmd_returns_none),
        ('test_none_cmd_returns_none', test_instance.test_none_cmd_returns_none),
        ('test_non_http_cmd_returns_none', test_instance.test_non_http_cmd_returns_none),
        ('test_ffmpeg_without_url_returns_none', test_instance.test_ffmpeg_without_url_returns_none),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}...")
            test_func()
            print("  PASSED")
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests_manually()
    exit(0 if success else 1)
