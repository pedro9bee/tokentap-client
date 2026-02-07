# Device Tracking in Tokentap

Track LLM token usage per device with custom friendly names.

## Overview

Tokentap v0.5.0 introduces automatic device detection and tracking, allowing you to:
- See which devices consume the most tokens
- Name devices with friendly names (e.g., "Mac M1 Escritório", "Linux Server")
- Track costs per device
- Filter token-consuming events vs telemetry

## How It Works

### 1. Automatic Device Detection

Tokentap generates a unique `device_id` using multiple strategies:

**Priority order**:
1. **session_id** from raw_request (if available)
2. **device_id** from event_data (Claude Code telemetry)
3. **Fingerprint** from IP + OS + User-Agent hash

**Example device_id**: `device-a1b2c3d4e5f6`

### 2. Device Information Captured

Each event stores:
```json
{
  "device": {
    "id": "device-a1b2c3d4e5f6",
    "session_id": "abc-123-def-456",
    "os_type": "macOS",
    "os_version": "14.2",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "browser": "Chrome",
    "is_mobile": false,
    "is_bot": false
  },
  "device_id": "device-a1b2c3d4e5f6"
}
```

### 3. Device Registry

Devices are stored in MongoDB `devices` collection:
```json
{
  "_id": "device-a1b2c3d4e5f6",
  "name": "Mac M1 Escritório",
  "metadata": {},
  "first_seen": "2026-02-08T10:00:00Z",
  "last_updated": "2026-02-08T15:30:00Z"
}
```

## Using Device Tracking

### Web Dashboard

1. **Open dashboard**: `http://localhost:3000`
2. **Click "Devices" tab**
3. **View all devices** with auto-detected info
4. **Click device name** to rename (e.g., "Mac M1")
5. **See stats**: Tokens, requests, cost per device

### API Endpoints

**List devices**:
```bash
curl http://localhost:3000/api/devices
```

**Rename device**:
```bash
curl -X POST http://localhost:3000/api/devices/device-abc123/rename \
  -H "Content-Type: application/json" \
  -d '{"name": "Mac M1 Escritório"}'
```

**Device stats**:
```bash
curl http://localhost:3000/api/stats/by-device
```

**Filter by date**:
```bash
curl "http://localhost:3000/api/stats/by-device?date_from=2026-02-01&date_to=2026-02-08"
```

## Smart Token Detection

### is_token_consuming Flag

Not all events consume tokens. Tokentap automatically detects:

**Token-consuming events** (`is_token_consuming: true`):
- Has `messages` array (LLM conversation)
- Has `budget_tokens` field (thinking budget)
- Path matches `/v1/messages`, `/v1/chat/completions`, etc.

**Non-consuming events** (`is_token_consuming: false`):
- Telemetry (`/api/event_logging/batch`)
- Health checks (`/api/hello`)
- Auth requests (`/api/oauth/profile`)

### Filtering

Device stats **only count token-consuming events** by default.

To include all events:
```python
# In db.py
await db.usage_by_device({"is_token_consuming": None})
```

## Troubleshooting

### Device not detected

**Symptom**: `device_id` is null or generic

**Solution**:
- Check if User-Agent header is sent
- Verify IP address is captured (check `flow.client_conn.address`)
- For Claude Code: Ensure telemetry events include `session_id`

### Device ID changes

**Symptom**: Same device gets different IDs

**Reason**: Fingerprint is based on IP + OS + User-Agent. If any changes, ID changes.

**Solution**:
- Use session-based tracking (set `X-Tokentap-Session` header)
- Or accept that devices may get new IDs when network/UA changes

### Can't rename device

**Symptom**: Inline edit doesn't save

**Check**:
1. Browser console for errors
2. API endpoint responds: `curl -X POST http://localhost:3000/api/devices/XXX/rename -d '{"name":"test"}'`
3. MongoDB connection working

## Future Enhancements (v0.6.0)

- **Rule-based filtering**: "Capture only if is_token_consuming = true"
- **Device tags**: Tag devices (personal, work, testing)
- **Device groups**: Group by team/project
- **Cost alerts**: Alert when device exceeds budget
