"""
Portal Type Detection System
Requirements: 62.1-62.6, 63.1-63.4, 68.1-68.7
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


class PortalType(Enum):
    """Supported portal types with their characteristics."""
    STALKER = "stalker"
    XTREAM = "xtream"
    XUI = "xui"
    MAGLOAD = "magload"
    XUIONE = "xuione"
    STALKER_USERPASS = "stalker_userpass"
    UNKNOWN = "unknown"


class ErrorPattern(Enum):
    """Error patterns for classification."""
    AUTH_FAILED = "auth_failed"
    DEVICE_NOT_ALLOWED = "device_not_allowed"
    DEVICE_CONFLICT = "device_conflict"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    ACCOUNT_BLOCKED = "account_blocked"
    RATE_LIMITED = "rate_limited"
    CAPTCHA_REQUIRED = "captcha_required"
    XUI_DEBUG = "xui_debug"
    XUI_ADMIN = "xui_admin"
    UNKNOWN = "unknown"


class XUIAdminStatus(Enum):
    """XUI Admin Panel detection status. Requirements: 71.1-71.4"""
    NOT_DETECTED = "not_detected"
    XUI_ADMIN = "xui_admin"
    XUI_DEBUG_MODE = "xui_debug_mode"
    CAPTCHA_PROTECTED = "captcha_protected"


@dataclass
class DetectionEvidence:
    """Evidence for portal type detection."""
    source: str
    pattern: str
    description: str
    confidence: float


@dataclass
class DetectionResult:
    """Result of portal type detection."""
    portal_type: PortalType
    confidence: float
    evidence: List[DetectionEvidence]
    detected_endpoint: Optional[str] = None
    requires_userpass: bool = False


class PortalTypeDetector:
    """
    Automatically detects portal type based on response patterns.
    Requirements: 62.1, 62.2, 62.3, 62.4, 62.5, 62.6
    """
    
    # Detection patterns for each portal type
    DETECTION_PATTERNS = {
        PortalType.XUI: [
            ('profile', 'phone', 'expiry in phone field', 0.8),
            ('handshake', 'prehash', 'accepts prehash parameter', 0.7),
            ('response', 'XUI.one', 'XUI.one in response', 0.9),
        ],
        PortalType.XTREAM: [
            ('stream_url', r'/live/[^/]+/[^/]+/', 'stream URL contains /live/USER/PASS/', 0.9),
            ('endpoint', 'player_api.php', 'has player_api.php', 0.8),
            ('response', 'user_info', 'has user_info in response', 0.7),
        ],
        PortalType.MAGLOAD: [
            ('endpoint', '/magLoad.php', 'uses magLoad endpoint', 0.95),
            ('params', 'deviceSn', 'uses deviceSn parameter', 0.8),
        ],
        PortalType.XUIONE: [
            ('endpoint', '/playlist/', 'uses /playlist/USER/PASS/ format', 0.95),
            ('url', r'/playlist/[^/]+/[^/]+/m3u', 'playlist URL pattern', 0.9),
        ],
        PortalType.STALKER: [
            ('profile', 'expire_billing_date', 'has expire_billing_date field', 0.7),
            ('endpoint', '/server/load.php', 'uses standard stalker endpoint', 0.5),
            ('response', 'stb_type', 'has stb_type in response', 0.6),
        ],
        PortalType.STALKER_USERPASS: [
            ('auth', 'do_auth', 'uses do_auth action', 0.9),
            ('params', 'login', 'requires login parameter', 0.8),
        ],
    }
    
    # Error patterns for classification
    ERROR_PATTERNS = {
        ErrorPattern.AUTH_FAILED: [
            r'Authorization failed',
            r'Not valid MAC',
            r'Invalid MAC',
            r'MAC not found',
            r'auth.*failed',
        ],
        ErrorPattern.DEVICE_NOT_ALLOWED: [
            r'Device auto add is disabled',
            r'device.*not.*allowed',
            r'auto.*add.*disabled',
        ],
        ErrorPattern.DEVICE_CONFLICT: [
            r'Device conflict',
            r'device.*conflict',
            r'already.*connected',
        ],
        ErrorPattern.SUBSCRIPTION_EXPIRED: [
            r'Your Subscription Expired',
            r'subscription.*expired',
            r'account.*expired',
            r'exp_date.*passed',
        ],
        ErrorPattern.ACCOUNT_BLOCKED: [
            r'"status"\s*:\s*2',
            r'account.*blocked',
            r'user.*blocked',
            r'access.*denied',
        ],
        ErrorPattern.RATE_LIMITED: [
            r'Too many attempts',
            r'rate.*limit',
            r'try.*again.*later',
        ],
        ErrorPattern.CAPTCHA_REQUIRED: [
            r'g-recaptcha',
            r'captcha',
            r'verify.*human',
        ],
        ErrorPattern.XUI_DEBUG: [
            r'XUI\.one.*Debug Mode',
            r'debug.*mode.*enabled',
        ],
    }
    
    def __init__(self, portal_url: str, mac: str = None):
        self.portal_url = portal_url
        self.mac = mac
        self.detected_type = PortalType.UNKNOWN
        self.detection_evidence: List[DetectionEvidence] = []
        self.confidence = 0.0
    
    def detect_from_response(self, response_data: Dict, endpoint: str = None) -> DetectionResult:
        """Detect portal type from API response."""
        evidence = []
        type_scores = {pt: 0.0 for pt in PortalType}
        
        response_str = str(response_data)
        
        for portal_type, patterns in self.DETECTION_PATTERNS.items():
            for source, pattern, description, confidence in patterns:
                matched = False
                
                if source == 'response':
                    if re.search(pattern, response_str, re.IGNORECASE):
                        matched = True
                elif source == 'profile' and isinstance(response_data, dict):
                    if pattern in response_data or pattern in response_data.get('js', {}):
                        matched = True
                elif source == 'endpoint' and endpoint:
                    if pattern in endpoint:
                        matched = True
                elif source == 'stream_url':
                    # Check for stream URL patterns in response
                    cmd = response_data.get('cmd', response_data.get('js', {}).get('cmd', ''))
                    if re.search(pattern, cmd):
                        matched = True
                
                if matched:
                    evidence.append(DetectionEvidence(
                        source=source,
                        pattern=pattern,
                        description=description,
                        confidence=confidence
                    ))
                    type_scores[portal_type] += confidence
        
        # Find best match
        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]
        
        if best_score < 0.5:
            best_type = PortalType.UNKNOWN
        
        self.detected_type = best_type
        self.detection_evidence = evidence
        self.confidence = min(best_score, 1.0)
        
        return DetectionResult(
            portal_type=best_type,
            confidence=self.confidence,
            evidence=evidence,
            detected_endpoint=endpoint,
            requires_userpass=best_type == PortalType.STALKER_USERPASS
        )
    
    def detect_from_url(self) -> DetectionResult:
        """Detect portal type from URL patterns."""
        evidence = []
        
        url_lower = self.portal_url.lower()
        
        # Check for specific URL patterns
        if '/magload.php' in url_lower:
            evidence.append(DetectionEvidence('url', 'magLoad.php', 'MagLoad endpoint in URL', 0.95))
            return DetectionResult(PortalType.MAGLOAD, 0.95, evidence)
        
        if '/playlist/' in url_lower and '/m3u' in url_lower:
            evidence.append(DetectionEvidence('url', '/playlist/', 'XUIONE playlist URL', 0.95))
            return DetectionResult(PortalType.XUIONE, 0.95, evidence)
        
        if 'player_api.php' in url_lower:
            evidence.append(DetectionEvidence('url', 'player_api.php', 'Xtream API in URL', 0.9))
            return DetectionResult(PortalType.XTREAM, 0.9, evidence)
        
        # Default to unknown, will need response analysis
        return DetectionResult(PortalType.UNKNOWN, 0.0, evidence)
    
    @classmethod
    def classify_error(cls, response_text: str, http_status: int = None) -> ErrorPattern:
        """Classify error from response text."""
        if http_status == 429:
            return ErrorPattern.RATE_LIMITED
        
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    return error_type
        
        return ErrorPattern.UNKNOWN
    
    @classmethod
    def get_recommended_action(cls, error: ErrorPattern) -> Dict:
        """Get recommended action for an error pattern."""
        actions = {
            ErrorPattern.AUTH_FAILED: {
                'action': 'mac_failover',
                'cooldown_minutes': 0,
                'message': 'Try different MAC address',
            },
            ErrorPattern.DEVICE_NOT_ALLOWED: {
                'action': 'show_error',
                'cooldown_minutes': 0,
                'message': 'Device auto-add is disabled on this portal',
            },
            ErrorPattern.DEVICE_CONFLICT: {
                'action': 'mac_failover',
                'cooldown_minutes': 5,
                'message': 'Device conflict - applying cooldown',
            },
            ErrorPattern.SUBSCRIPTION_EXPIRED: {
                'action': 'mark_expired',
                'cooldown_minutes': 0,
                'message': 'Subscription has expired',
            },
            ErrorPattern.ACCOUNT_BLOCKED: {
                'action': 'disable_mac',
                'cooldown_minutes': 0,
                'message': 'Account is blocked',
            },
            ErrorPattern.RATE_LIMITED: {
                'action': 'cooldown_retry',
                'cooldown_minutes': 1,
                'message': 'Rate limited - waiting before retry',
            },
            ErrorPattern.CAPTCHA_REQUIRED: {
                'action': 'show_error',
                'cooldown_minutes': 0,
                'message': 'CAPTCHA required - manual intervention needed',
            },
            ErrorPattern.XUI_DEBUG: {
                'action': 'mark_xui',
                'cooldown_minutes': 0,
                'message': 'Detected XUI portal in debug mode',
            },
        }
        return actions.get(error, {
            'action': 'retry',
            'cooldown_minutes': 0,
            'message': 'Unknown error',
        })


class DeviceMetricsGenerator:
    """
    Generates device metrics for different STB types.
    Requirements: 69.1, 69.2, 69.3, 69.4, 77.1-77.5
    """
    
    DEVICE_PROFILES = {
        'MAG250': {
            'hw_version': '1.7-BD-00',
            'api_signature': '263',
            'stb_type': 'MAG250',
            'device_id_prefix': 'HW',
            'sn_prefix': 'SN',
        },
        'MAG254': {
            'hw_version': '2.6-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG254',
            'device_id_prefix': 'HW',
            'sn_prefix': 'SN',
        },
        'MAG322': {
            'hw_version': '2.17-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG322',
            'device_id_prefix': 'HW',
            'sn_prefix': 'SN',
        },
        'MAG424': {
            'hw_version': '2.18-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG424',
            'device_id_prefix': 'HW',
            'sn_prefix': 'SN',
        },
    }
    
    @classmethod
    def generate_serial_number(cls, mac: str, profile: str = 'MAG250') -> str:
        """Generate serial number from MAC address."""
        mac_clean = mac.replace(':', '').upper()
        prefix = cls.DEVICE_PROFILES.get(profile, {}).get('sn_prefix', 'SN')
        return f"{prefix}{mac_clean}"
    
    @classmethod
    def generate_device_id(cls, mac: str, profile: str = 'MAG250') -> str:
        """Generate device ID from MAC address."""
        import hashlib
        mac_clean = mac.replace(':', '').upper()
        hash_input = f"{mac_clean}{profile}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:16].upper()
        prefix = cls.DEVICE_PROFILES.get(profile, {}).get('device_id_prefix', 'HW')
        return f"{prefix}{hash_value}"
    
    @classmethod
    def generate_signature(cls, mac: str, token: str = '') -> str:
        """Generate authentication signature."""
        import hashlib
        mac_clean = mac.replace(':', '').upper()
        sig_input = f"{mac_clean}{token}"
        return hashlib.sha256(sig_input.encode()).hexdigest()[:32]
    
    @classmethod
    def get_metrics(cls, mac: str, profile: str = 'MAG250') -> Dict:
        """Get complete device metrics for a profile."""
        profile_data = cls.DEVICE_PROFILES.get(profile, cls.DEVICE_PROFILES['MAG250'])
        
        return {
            'sn': cls.generate_serial_number(mac, profile),
            'device_id': cls.generate_device_id(mac, profile),
            'device_id2': cls.generate_device_id(mac, profile),
            'signature': cls.generate_signature(mac),
            'hw_version': profile_data['hw_version'],
            'stb_type': profile_data['stb_type'],
            'api_signature': profile_data['api_signature'],
        }


class XUIAdminDetector:
    """
    Detects XUI Admin Panel presence.
    Requirements: 71.1, 71.2, 71.3, 71.4
    """
    
    # XUI Admin Panel detection patterns
    XUI_LOGIN_PATTERNS = [
        r'<form.*action=["\'].*login\.php["\']',
        r'XUI\.one',
        r'xui-login',
        r'xtream-ui',
        r'panel.*login',
    ]
    
    XUI_DEBUG_PATTERNS = [
        r'XUI\.one.*Debug Mode',
        r'debug.*mode.*enabled',
        r'DEBUG_MODE\s*=\s*true',
    ]
    
    CAPTCHA_PATTERNS = [
        r'g-recaptcha',
        r'h-captcha',
        r'captcha.*required',
        r'verify.*human',
    ]
    
    @classmethod
    def detect_from_login_page(cls, html_content: str) -> XUIAdminStatus:
        """
        Detect XUI Admin Panel from /login.php response.
        Requirements: 71.1, 71.2
        """
        if not html_content:
            return XUIAdminStatus.NOT_DETECTED
        
        # Check for captcha first (highest priority)
        for pattern in cls.CAPTCHA_PATTERNS:
            if re.search(pattern, html_content, re.IGNORECASE):
                return XUIAdminStatus.CAPTCHA_PROTECTED
        
        # Check for debug mode
        for pattern in cls.XUI_DEBUG_PATTERNS:
            if re.search(pattern, html_content, re.IGNORECASE):
                return XUIAdminStatus.XUI_DEBUG_MODE
        
        # Check for XUI login form
        for pattern in cls.XUI_LOGIN_PATTERNS:
            if re.search(pattern, html_content, re.IGNORECASE):
                return XUIAdminStatus.XUI_ADMIN
        
        return XUIAdminStatus.NOT_DETECTED
    
    @classmethod
    def check_login_endpoint(cls, base_url: str, session=None) -> dict:
        """
        Check /login.php endpoint for XUI Admin Panel.
        Requirements: 71.3, 71.4
        
        Returns:
            Dict with status, detected_type, and evidence
        """
        import requests
        
        result = {
            'status': XUIAdminStatus.NOT_DETECTED,
            'detected': False,
            'evidence': [],
            'url_checked': None,
        }
        
        # Normalize URL
        base_url = base_url.rstrip('/')
        login_url = f"{base_url}/login.php"
        result['url_checked'] = login_url
        
        try:
            sess = session or requests.Session()
            response = sess.get(login_url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                status = cls.detect_from_login_page(response.text)
                result['status'] = status
                result['detected'] = status != XUIAdminStatus.NOT_DETECTED
                
                if status == XUIAdminStatus.XUI_ADMIN:
                    result['evidence'].append('XUI login form detected')
                elif status == XUIAdminStatus.XUI_DEBUG_MODE:
                    result['evidence'].append('XUI debug mode enabled')
                elif status == XUIAdminStatus.CAPTCHA_PROTECTED:
                    result['evidence'].append('CAPTCHA protection detected')
            
            elif response.status_code == 404:
                result['evidence'].append('login.php not found')
            
            elif response.status_code == 403:
                result['evidence'].append('Access forbidden')
                
        except Exception as e:
            result['evidence'].append(f'Error: {str(e)}')
        
        return result


class XtreamCredentialExtractor:
    """
    Extracts Xtream credentials from stream URLs.
    Requirements: 64.1, 64.2, 64.3, 64.4, 64.5, 84.1-84.5
    """
    
    # Pattern: /live/USERNAME/PASSWORD/stream_id.ts
    LIVE_PATTERN = re.compile(r'/live/([^/]+)/([^/]+)/(\d+)')
    # Pattern: /movie/USERNAME/PASSWORD/stream_id.extension
    MOVIE_PATTERN = re.compile(r'/movie/([^/]+)/([^/]+)/(\d+)')
    # Pattern: /series/USERNAME/PASSWORD/stream_id.extension
    SERIES_PATTERN = re.compile(r'/series/([^/]+)/([^/]+)/(\d+)')
    
    @classmethod
    def extract_credentials(cls, stream_url: str) -> Optional[Dict]:
        """Extract username and password from stream URL."""
        for pattern in [cls.LIVE_PATTERN, cls.MOVIE_PATTERN, cls.SERIES_PATTERN]:
            match = pattern.search(stream_url)
            if match:
                return {
                    'username': match.group(1),
                    'password': match.group(2),
                    'stream_id': match.group(3),
                }
        return None
    
    @classmethod
    def generate_m3u_url(cls, base_url: str, username: str, password: str) -> str:
        """Generate M3U playlist URL from credentials."""
        # Remove trailing slash
        base_url = base_url.rstrip('/')
        return f"{base_url}/get.php?username={username}&password={password}&type=m3u_plus"
    
    @classmethod
    def generate_player_api_url(cls, base_url: str, username: str, password: str) -> str:
        """Generate player_api.php URL from credentials."""
        base_url = base_url.rstrip('/')
        return f"{base_url}/player_api.php?username={username}&password={password}"
    
    @classmethod
    def generate_xmltv_url(cls, base_url: str, username: str, password: str) -> str:
        """Generate XMLTV EPG URL from credentials."""
        base_url = base_url.rstrip('/')
        return f"{base_url}/xmltv.php?username={username}&password={password}"
