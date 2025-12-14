"""
OB2_2025 Prüflogik Engine
Requirements: 76.1-90.4
"""

import hashlib
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class HandshakeType(Enum):
    """Supported handshake types in OB2_2025 mode."""
    STALKER1 = "stalker1"  # GET, hw_version=1.7-BD-00, api_signature=263
    STALKER2 = "stalker2"  # Extended metrics
    STALKER3 = "stalker3"  # do_auth with User/Pass
    STALKERC = "stalkerc"  # Async with Cloudflare bypass
    XTREAM1 = "xtream1"    # POST, hw_version=2.6-IB-00, api_signature=262
    XTREAM2 = "xtream2"    # Alternative POST
    XTREAMC = "xtreamc"    # Async
    XUI1 = "xui1"          # prehash=0
    XUI2 = "xui2"          # hw_version=2.17-IB-00 for MAG322
    MAGLOAD = "magload"    # /magLoad.php endpoint
    XUIONE = "xuione"      # /playlist/USER/PASS/m3u_plus


@dataclass
class DeviceMetrics:
    """Device metrics for authentication."""
    serial_number: str
    cut_serial_number: str
    device_id: str
    signature: str
    token: str
    hw_version: str
    api_signature: str
    stb_type: str


class OB2_2025Engine:
    """
    OB2_2025 checking logic engine.
    Requirements: 76.1, 76.2, 76.3, 76.4
    """
    
    # Handshake configurations
    HANDSHAKE_CONFIGS = {
        HandshakeType.STALKER1: {
            'method': 'GET',
            'endpoint': '/server/load.php',
            'hw_version': '1.7-BD-00',
            'api_signature': '263',
            'stb_type': 'MAG250',
        },
        HandshakeType.STALKER2: {
            'method': 'GET',
            'endpoint': '/server/load.php',
            'hw_version': '2.6-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG254',
        },
        HandshakeType.STALKER3: {
            'method': 'GET',
            'endpoint': '/stalker_portal/server/load.php',
            'hw_version': '1.7-BD-00',
            'api_signature': '263',
            'stb_type': 'MAG250',
            'requires_auth': True,
        },
        HandshakeType.XTREAM1: {
            'method': 'POST',
            'endpoint': '/server/load.php',
            'hw_version': '2.6-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG254',
        },
        HandshakeType.XTREAM2: {
            'method': 'POST',
            'endpoint': '/server/load.php',
            'hw_version': '2.17-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG322',
        },
        HandshakeType.XUI1: {
            'method': 'GET',
            'endpoint': '/server/load.php',
            'hw_version': '1.7-BD-00',
            'api_signature': '263',
            'stb_type': 'MAG250',
            'prehash': '0',
        },
        HandshakeType.XUI2: {
            'method': 'GET',
            'endpoint': '/server/load.php',
            'hw_version': '2.17-IB-00',
            'api_signature': '262',
            'stb_type': 'MAG322',
            'prehash': '0',
        },
        HandshakeType.MAGLOAD: {
            'method': 'POST',
            'endpoint': '/magLoad.php',
            'hw_version': '1.7-BD-00',
            'api_signature': '263',
            'stb_type': 'MAG250',
        },
    }
    
    # Expiry field mapping by portal type
    EXPIRY_FIELD_MAP = {
        'stalker': ['expire_billing_date', 'phone'],
        'xtream': ['exp_date', 'expire_billing_date'],
        'xui': ['phone'],
        'magload': ['date'],
    }
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._cached_handshake_type = {}
    
    def generate_device_metrics(self, mac: str, handshake_type: HandshakeType = HandshakeType.STALKER1) -> DeviceMetrics:
        """
        Generate device metrics for authentication.
        Requirements: 77.1, 77.2, 77.3, 77.4, 77.5
        """
        config = self.HANDSHAKE_CONFIGS.get(handshake_type, self.HANDSHAKE_CONFIGS[HandshakeType.STALKER1])
        mac_clean = mac.replace(':', '').upper()
        
        # Generate SerialNumber (SN)
        serial_number = f"SN{mac_clean}"
        
        # Generate CutSerialNumber (SNCUT)
        cut_serial_number = mac_clean[:8]
        
        # Generate DeviceID (DEVENC)
        device_id_input = f"{mac_clean}{config['stb_type']}"
        device_id = hashlib.md5(device_id_input.encode()).hexdigest()[:16].upper()
        
        # Generate Signature (SIGN)
        signature = hashlib.sha256(mac_clean.encode()).hexdigest()[:32]
        
        # Generate initial Token (TOKGEN)
        token_input = f"{mac_clean}{datetime.now().timestamp()}"
        token = hashlib.md5(token_input.encode()).hexdigest()
        
        return DeviceMetrics(
            serial_number=serial_number,
            cut_serial_number=cut_serial_number,
            device_id=device_id,
            signature=signature,
            token=token,
            hw_version=config['hw_version'],
            api_signature=config['api_signature'],
            stb_type=config['stb_type'],
        )
    
    def get_expiry_date(self, profile: Dict, portal_type: str = 'stalker') -> Optional[str]:
        """
        Extract expiry date from profile using portal-type-specific mapping.
        Requirements: 87.1, 87.2, 87.3, 87.4, 87.5
        """
        fields = self.EXPIRY_FIELD_MAP.get(portal_type, self.EXPIRY_FIELD_MAP['stalker'])
        
        for field in fields:
            value = profile.get(field)
            if value:
                return str(value)
        
        return None
    
    def build_handshake_params(self, mac: str, handshake_type: HandshakeType, token: str = '') -> Dict:
        """Build parameters for handshake request."""
        config = self.HANDSHAKE_CONFIGS.get(handshake_type, self.HANDSHAKE_CONFIGS[HandshakeType.STALKER1])
        
        params = {
            'type': 'stb',
            'action': 'handshake',
            'token': token,
            'JsHttpRequest': '1-xml',
        }
        
        # Add prehash for XUI types
        if config.get('prehash'):
            params['prehash'] = config['prehash']
        
        return params
    
    def build_headers(self, mac: str, handshake_type: HandshakeType, token: str = '') -> Dict:
        """Build headers for request."""
        config = self.HANDSHAKE_CONFIGS.get(handshake_type, self.HANDSHAKE_CONFIGS[HandshakeType.STALKER1])
        
        user_agent = f"Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: {config['stb_type'][3:]} Safari/533.3"
        
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cookie': f'mac={mac}; stb_lang=en; timezone=Europe/London',
        }
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def cache_successful_handshake(self, portal_url: str, handshake_type: HandshakeType):
        """Cache successful handshake type for a portal."""
        self._cached_handshake_type[portal_url] = handshake_type
    
    def get_cached_handshake_type(self, portal_url: str) -> Optional[HandshakeType]:
        """Get cached handshake type for a portal."""
        return self._cached_handshake_type.get(portal_url)
    
    def get_handshake_order(self, portal_url: str) -> List[HandshakeType]:
        """
        Get ordered list of handshake types to try.
        Requirements: 89.1, 89.2, 89.3, 89.4
        """
        # Check cache first
        cached = self.get_cached_handshake_type(portal_url)
        if cached:
            # Put cached type first
            order = [cached]
            for ht in HandshakeType:
                if ht != cached and ht != HandshakeType.XUIONE:
                    order.append(ht)
            return order
        
        # Default order
        return [
            HandshakeType.STALKER1,
            HandshakeType.XUI1,
            HandshakeType.XTREAM1,
            HandshakeType.STALKER2,
            HandshakeType.XUI2,
            HandshakeType.XTREAM2,
            HandshakeType.MAGLOAD,
            HandshakeType.STALKER3,
        ]


class ErrorPatternRecognizer:
    """
    Recognizes error patterns from portal responses.
    Requirements: 83.1-83.7
    """
    
    class ErrorType(Enum):
        AUTH_FAILED = "auth_failed"
        DEVICE_NOT_ALLOWED = "device_not_allowed"
        DEVICE_CONFLICT = "device_conflict"
        SUBSCRIPTION_EXPIRED = "subscription_expired"
        ACCOUNT_BLOCKED = "account_blocked"
        RATE_LIMITED = "rate_limited"
        CAPTCHA_REQUIRED = "captcha_required"
        UNKNOWN = "unknown"
    
    PATTERNS = {
        ErrorType.AUTH_FAILED: [
            r'Authorization failed',
            r'Not valid MAC',
            r'Invalid MAC',
            r'MAC not found',
            r'auth.*failed',
            r'invalid.*credentials',
        ],
        ErrorType.DEVICE_NOT_ALLOWED: [
            r'Device auto add is disabled',
            r'device.*not.*allowed',
            r'auto.*add.*disabled',
            r'registration.*disabled',
        ],
        ErrorType.DEVICE_CONFLICT: [
            r'Device conflict',
            r'device.*conflict',
            r'already.*connected',
            r'max.*connections',
        ],
        ErrorType.SUBSCRIPTION_EXPIRED: [
            r'Your Subscription Expired',
            r'subscription.*expired',
            r'account.*expired',
            r'exp_date.*passed',
            r'trial.*ended',
        ],
        ErrorType.ACCOUNT_BLOCKED: [
            r'"status"\s*:\s*2',
            r'account.*blocked',
            r'user.*blocked',
            r'access.*denied',
            r'banned',
        ],
        ErrorType.RATE_LIMITED: [
            r'Too many attempts',
            r'rate.*limit',
            r'try.*again.*later',
            r'slow.*down',
        ],
        ErrorType.CAPTCHA_REQUIRED: [
            r'g-recaptcha',
            r'captcha',
            r'verify.*human',
            r'challenge',
        ],
    }
    
    @classmethod
    def recognize(cls, response_text: str, http_status: int = None) -> 'ErrorPatternRecognizer.ErrorType':
        """Recognize error type from response."""
        if http_status == 429:
            return cls.ErrorType.RATE_LIMITED
        
        for error_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    return error_type
        
        return cls.ErrorType.UNKNOWN
    
    @classmethod
    def get_failover_action(cls, error_type: 'ErrorPatternRecognizer.ErrorType') -> Dict:
        """
        Get recommended failover action for error type.
        Requirements: 88.1, 88.2, 88.3, 88.4
        """
        actions = {
            cls.ErrorType.AUTH_FAILED: {
                'action': 'mac_failover',
                'cooldown_minutes': 0,
                'retry': True,
            },
            cls.ErrorType.DEVICE_NOT_ALLOWED: {
                'action': 'show_error',
                'cooldown_minutes': 0,
                'retry': False,
            },
            cls.ErrorType.DEVICE_CONFLICT: {
                'action': 'mac_failover',
                'cooldown_minutes': 5,
                'retry': True,
            },
            cls.ErrorType.SUBSCRIPTION_EXPIRED: {
                'action': 'mark_expired',
                'cooldown_minutes': 0,
                'retry': False,
            },
            cls.ErrorType.ACCOUNT_BLOCKED: {
                'action': 'disable_mac',
                'cooldown_minutes': 0,
                'retry': False,
            },
            cls.ErrorType.RATE_LIMITED: {
                'action': 'cooldown_retry',
                'cooldown_minutes': 1,
                'retry': True,
            },
            cls.ErrorType.CAPTCHA_REQUIRED: {
                'action': 'show_error',
                'cooldown_minutes': 0,
                'retry': False,
            },
        }
        return actions.get(error_type, {
            'action': 'retry',
            'cooldown_minutes': 0,
            'retry': True,
        })


class PlayerApiClient:
    """
    Client for player_api.php integration.
    Requirements: 85.1, 85.2, 85.3, 85.4
    """
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
    
    def get_api_url(self, action: str = '') -> str:
        """Get player_api.php URL."""
        url = f"{self.base_url}/player_api.php?username={self.username}&password={self.password}"
        if action:
            url += f"&action={action}"
        return url
    
    def get_account_info(self, session) -> Optional[Dict]:
        """Get account info from player_api.php."""
        try:
            url = self.get_api_url()
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return {
                    'username': data.get('user_info', {}).get('username'),
                    'status': data.get('user_info', {}).get('status'),
                    'exp_date': data.get('user_info', {}).get('exp_date'),
                    'active_cons': data.get('user_info', {}).get('active_cons'),
                    'max_connections': data.get('user_info', {}).get('max_connections'),
                    'is_trial': data.get('user_info', {}).get('is_trial'),
                }
        except Exception:
            pass
        return None
    
    def get_expiry_date(self, session) -> Optional[str]:
        """Extract expiry date from player_api.php."""
        info = self.get_account_info(session)
        if info and info.get('exp_date'):
            try:
                timestamp = int(info['exp_date'])
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            except Exception:
                return str(info['exp_date'])
        return None


class GeoIPLookup:
    """
    GEO-IP lookup service.
    Requirements: 90.1, 90.2, 90.3, 90.4
    """
    
    API_URL = "http://ip-api.com/json/"
    
    @classmethod
    def lookup(cls, ip: str = None, session = None) -> Optional[Dict]:
        """Lookup GEO information for IP."""
        try:
            import requests
            sess = session or requests.Session()
            
            url = cls.API_URL
            if ip:
                url += ip
            
            response = sess.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'ip': data.get('query'),
                        'country': data.get('country'),
                        'country_code': data.get('countryCode'),
                        'region': data.get('regionName'),
                        'city': data.get('city'),
                        'isp': data.get('isp'),
                        'timezone': data.get('timezone'),
                    }
        except Exception:
            pass
        return None
