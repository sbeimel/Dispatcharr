# MAC/STB Portal Integration

This document describes the MAC/STB Portal integration features added to Dispatcharr.

## Overview

The MAC integration allows Dispatcharr to work with STB (Set-Top Box) portals that use MAC address authentication, commonly used by Stalker/MAG devices.

## Features

### MAC Account Type
- New account type "MAC / STB-Portal" in M3U account creation
- Support for multiple MAC addresses per account
- Priority-based failover between MAC addresses
- Status tracking (Valid, Expired, Error, Unknown)

### MAC Management UI
- Visual MAC address table with status indicators
- Priority management with up/down arrows
- Individual MAC deletion
- Bulk cleanup of expired MACs
- Real-time status updates via WebSocket
- Live connection status indicator

### API Endpoints

#### MAC Management
- `POST /api/m3u/accounts/{id}/delete-expired-macs/` - Delete expired MACs
- `DELETE /api/m3u/accounts/{id}/macs/{mac_id}/` - Delete single MAC
- `POST /api/m3u/accounts/{id}/reorder-macs/` - Reorder MAC priorities

### Basic Authentication
- HTTP Basic Auth protection for M3U and EPG endpoints
- Compatible with existing Django user accounts
- Maintains backward compatibility

### Failover System
- Multi-level failover: MAC → Profile → Stream
- Redis-based cooldown management
- Automatic recovery after cooldown periods
- Connection continuity during failover

## Configuration

### Creating a MAC Account
1. Go to M3U Accounts
2. Click "Add Account"
3. Select "MAC / STB-Portal" as account type
4. Enter Portal URL (e.g., `http://portal.example.com`)
5. Enter MAC address(es) in format `AA:BB:CC:DD:EE:FF`
6. Save the account

### MAC Address Management
- MAC addresses are automatically normalized to standard format
- Priority is assigned automatically (0 = highest priority)
- Status is updated automatically via portal communication
- Expired MACs can be cleaned up in bulk

### Basic Authentication Setup
Basic Auth is automatically enabled for M3U and EPG endpoints when configured.

## Technical Details

### Models
- `M3UAccount` - Extended with `mac_address` field and MAC account type
- `M3UAccountMac` - Individual MAC address management with status tracking

### MAC Portal Client
- Based on MacReplayXC implementation
- Handles STB portal communication
- Auto-discovery of portal endpoints
- Token-based authentication
- Session management with Redis caching

### WebSocket Integration
- Real-time MAC status updates
- Live connection status indicators
- Automatic UI updates when MAC status changes

## Backward Compatibility

All existing functionality remains unchanged:
- Standard M3U accounts continue to work
- Xtream Codes accounts are unaffected
- Existing API endpoints maintain the same response format
- Database migrations preserve all existing data

## Requirements Fulfilled

This implementation fulfills all requirements from the specification:
- ✅ MAC Account Type Support (Req 1)
- ✅ MAC Address Management (Req 2)  
- ✅ STB Portal Integration (Req 3)
- ✅ Multi-Level Failover System (Req 4)
- ✅ Basic Authentication Security (Req 5)
- ✅ Enhanced API Management (Req 6)
- ✅ Frontend MAC Management (Req 7)
- ✅ Performance and Reliability (Req 8)
- ✅ Backward Compatibility (Req 9)
- ✅ Comprehensive Logging and Monitoring (Req 10)