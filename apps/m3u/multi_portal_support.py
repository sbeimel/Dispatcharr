"""
Multi-Portal Support System
Requirements: 65.1-67.4, 72.1-75.4
"""

import re
import hashlib
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class HandshakeResult:
    """Result of a handshake attempt."""
    success: bool
    token: str = ''
    token_random: str = ''
    play_token: str = ''
    profile: Dict = None
    error: str = ''
    portal_type: str = ''


class BaseHandshakeStrategy(ABC):
    """Base class for handshake strategies."""
    
    def __init__(self, portal_url: str, mac: str, user_agent: str = None):
        self.portal_url = portal_url.rstrip('/')
        self.mac = mac
        self.user_agent = user_agent or self.get_default_user_agent()
    
    @abstractmethod
    def get_default_user_agent(self) -> str:
        pass
    
    @abstractmethod
    def perform_handshake(self, session) -> HandshakeResult:
        pass
    
    @abstractmethod
    def get_profile(self, session, token: str) -> Dict:
        pass
    
    def get_headers(self, token: str = None) -> Dict:
        """Get common headers for requests."""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers


class StalkerHandshake(BaseHandshakeStrategy):
    """
    Standard Stalker/Ministra handshake.
    Requirements: 65.1, 65.2, 65.3, 65.4
    """
    
    ENDPOINTS = [
        '/server/load.php',
        '/portal.php',
        '/stalker_portal/server/load.php',
        '/c/server/load.php',
    ]
    
    def get_default_user_agent(self) -> str:
        return 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3'
    
    def perform_handshake(self, session) -> HandshakeResult:
        """Perform Stalker handshake."""
        for endpoint in self.ENDPOINTS:
            try:
                url = f"{self.portal_url}{endpoint}"
                params = {
                    'type': 'stb',
                    'action': 'handshake',
                    'prehash': '0',
                    'token': '',
                    'JsHttpRequest': '1-xml',
                }
                
                headers = self.get_headers()
                headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
                
                response = session.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get('js', {})
                    
                    if js.get('token'):
                        return HandshakeResult(
                            success=True,
                            token=js.get('token', ''),
                            token_random=js.get('random', ''),
                            portal_type='stalker'
                        )
            except Exception as e:
                continue
        
        return HandshakeResult(success=False, error='All endpoints failed')
    
    def get_profile(self, session, token: str) -> Dict:
        """Get account profile."""
        for endpoint in self.ENDPOINTS:
            try:
                url = f"{self.portal_url}{endpoint}"
                params = {
                    'type': 'stb',
                    'action': 'get_profile',
                    'JsHttpRequest': '1-xml',
                }
                
                headers = self.get_headers()
                headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
                headers['Authorization'] = f'Bearer {token}'
                
                response = session.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('js', {})
            except Exception:
                continue
        
        return {}


class XUIHandshake(BaseHandshakeStrategy):
    """
    XUI.ONE specific handshake.
    Requirements: 66.1, 66.2, 66.3, 66.4
    """
    
    def get_default_user_agent(self) -> str:
        return 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 322 Safari/533.3'
    
    def perform_handshake(self, session) -> HandshakeResult:
        """Perform XUI handshake with prehash."""
        url = f"{self.portal_url}/server/load.php"
        
        # XUI requires prehash=0 for initial handshake
        params = {
            'type': 'stb',
            'action': 'handshake',
            'prehash': '0',
            'token': '',
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                js = data.get('js', {})
                
                if js.get('token'):
                    # XUI may require auth_second_step
                    token = js.get('token', '')
                    
                    if js.get('auth_second_step'):
                        # Perform second step authentication
                        token = self._auth_second_step(session, token)
                    
                    return HandshakeResult(
                        success=True,
                        token=token,
                        token_random=js.get('random', ''),
                        portal_type='xui'
                    )
        except Exception as e:
            return HandshakeResult(success=False, error=str(e))
        
        return HandshakeResult(success=False, error='XUI handshake failed')
    
    def _auth_second_step(self, session, token: str) -> str:
        """Perform XUI auth_second_step."""
        url = f"{self.portal_url}/server/load.php"
        
        # Generate hw_version_2 hash
        hw_version_2 = hashlib.md5(f"{self.mac}{token}".encode()).hexdigest()
        
        params = {
            'type': 'stb',
            'action': 'handshake',
            'token': token,
            'hw_version_2': hw_version_2,
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get('js', {}).get('token', token)
        except Exception:
            pass
        
        return token
    
    def get_profile(self, session, token: str) -> Dict:
        """Get XUI account profile."""
        url = f"{self.portal_url}/server/load.php"
        
        params = {
            'type': 'stb',
            'action': 'get_profile',
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                profile = data.get('js', {})
                
                # XUI stores expiry in 'phone' field
                if 'phone' in profile and not profile.get('expire_billing_date'):
                    profile['expire_billing_date'] = profile['phone']
                
                return profile
        except Exception:
            pass
        
        return {}


class MagLoadHandshake(BaseHandshakeStrategy):
    """
    MagLoad portal handshake.
    Requirements: 65.1, 65.2, 65.3, 65.4 (MagLoad variant)
    """
    
    def get_default_user_agent(self) -> str:
        return 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3'
    
    def perform_handshake(self, session) -> HandshakeResult:
        """Perform MagLoad handshake."""
        url = f"{self.portal_url}/magLoad.php"
        
        mac_clean = self.mac.replace(':', '')
        
        data = {
            'deviceMac': self.mac,
            'deviceSn': f'SN{mac_clean}',
            'deviceType': 'MAG250',
            'action': 'handshake',
        }
        
        headers = self.get_headers()
        
        try:
            response = session.post(url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('token') or result.get('success'):
                    return HandshakeResult(
                        success=True,
                        token=result.get('token', ''),
                        portal_type='magload'
                    )
        except Exception as e:
            return HandshakeResult(success=False, error=str(e))
        
        return HandshakeResult(success=False, error='MagLoad handshake failed')
    
    def get_profile(self, session, token: str) -> Dict:
        """Get MagLoad account profile."""
        url = f"{self.portal_url}/magLoad.php"
        
        mac_clean = self.mac.replace(':', '')
        
        data = {
            'deviceMac': self.mac,
            'deviceSn': f'SN{mac_clean}',
            'deviceType': 'MAG250',
            'action': 'get_profile',
            'token': token,
        }
        
        headers = self.get_headers()
        
        try:
            response = session.post(url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        
        return {}


class StalkerUserPassHandshake(BaseHandshakeStrategy):
    """
    Stalker with username/password authentication.
    Requirements: 67.1, 67.2, 67.3, 67.4
    """
    
    def __init__(self, portal_url: str, mac: str, username: str, password: str, user_agent: str = None):
        super().__init__(portal_url, mac, user_agent)
        self.username = username
        self.password = password
    
    def get_default_user_agent(self) -> str:
        return 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3'
    
    def perform_handshake(self, session) -> HandshakeResult:
        """Perform Stalker handshake with do_auth."""
        url = f"{self.portal_url}/stalker_portal/server/load.php"
        
        # First, get initial token
        params = {
            'type': 'stb',
            'action': 'handshake',
            'prehash': '0',
            'token': '',
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('js', {}).get('token', '')
                
                if token:
                    # Now perform do_auth
                    auth_result = self._do_auth(session, token)
                    if auth_result.success:
                        return auth_result
        except Exception as e:
            return HandshakeResult(success=False, error=str(e))
        
        return HandshakeResult(success=False, error='User/Pass handshake failed')
    
    def _do_auth(self, session, token: str) -> HandshakeResult:
        """Perform do_auth action."""
        url = f"{self.portal_url}/stalker_portal/server/load.php"
        
        params = {
            'type': 'stb',
            'action': 'do_auth',
            'login': self.username,
            'password': self.password,
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                js = data.get('js', {})
                
                if js.get('token') or js.get('success'):
                    return HandshakeResult(
                        success=True,
                        token=js.get('token', token),
                        portal_type='stalker_userpass'
                    )
        except Exception as e:
            return HandshakeResult(success=False, error=str(e))
        
        return HandshakeResult(success=False, error='do_auth failed')
    
    def get_profile(self, session, token: str) -> Dict:
        """Get account profile."""
        url = f"{self.portal_url}/stalker_portal/server/load.php"
        
        params = {
            'type': 'stb',
            'action': 'get_profile',
            'JsHttpRequest': '1-xml',
        }
        
        headers = self.get_headers()
        headers['Cookie'] = f'mac={self.mac}; stb_lang=en; timezone=Europe/London'
        headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json().get('js', {})
        except Exception:
            pass
        
        return {}


class XUIONEPlaylistHandler:
    """
    XUIONE playlist format handler.
    Requirements: 72.1, 72.2, 72.3, 72.4
    """
    
    @staticmethod
    def generate_playlist_url(base_url: str, username: str, password: str, output_type: str = 'm3u_plus') -> str:
        """Generate XUIONE playlist URL."""
        base_url = base_url.rstrip('/')
        return f"{base_url}/playlist/{username}/{password}/{output_type}"
    
    @staticmethod
    def parse_playlist_url(url: str) -> Optional[Dict]:
        """Parse XUIONE playlist URL to extract credentials."""
        pattern = r'/playlist/([^/]+)/([^/]+)/([^/]+)'
        match = re.search(pattern, url)
        
        if match:
            return {
                'username': match.group(1),
                'password': match.group(2),
                'output_type': match.group(3),
            }
        return None


class HandshakeStrategySelector:
    """
    Selects appropriate handshake strategy based on portal type.
    Requirements: 89.1, 89.2, 89.3, 89.4
    """
    
    STRATEGIES = {
        'stalker': StalkerHandshake,
        'xui': XUIHandshake,
        'magload': MagLoadHandshake,
        'stalker_userpass': StalkerUserPassHandshake,
    }
    
    @classmethod
    def get_strategy(cls, portal_type: str, portal_url: str, mac: str, **kwargs) -> BaseHandshakeStrategy:
        """Get appropriate handshake strategy."""
        strategy_class = cls.STRATEGIES.get(portal_type, StalkerHandshake)
        return strategy_class(portal_url, mac, **kwargs)
    
    @classmethod
    def auto_detect_and_handshake(cls, portal_url: str, mac: str, session) -> Tuple[HandshakeResult, str]:
        """Try all strategies and return the first successful one."""
        strategies_to_try = ['stalker', 'xui', 'magload']
        
        for strategy_type in strategies_to_try:
            strategy = cls.get_strategy(strategy_type, portal_url, mac)
            result = strategy.perform_handshake(session)
            
            if result.success:
                return result, strategy_type
        
        return HandshakeResult(success=False, error='All strategies failed'), 'unknown'
