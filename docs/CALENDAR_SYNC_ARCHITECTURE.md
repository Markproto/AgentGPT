# Bidirectional Calendar Sync API

## Overview

A privacy-preserving calendar synchronization system that connects:
1. **AI Front Desk Calendar** (agent.opentruthai.com/frontdesk/calendar/)
2. **Google Calendar**
3. **External Frontdesk systems**

## Privacy Model

Customer data is transformed before syncing to Google Calendar:
- **Full Data** (stored in main system): `John Smith, (555) 123-4567`
- **Synced Data** (sent to Google): `John 67` (first name + last 2 digits of phone)

This allows appointment visibility without exposing full customer details.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CALENDAR SYNC HUB                                │
│                    (Node.js Service on Port 4200)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   Privacy    │    │    Sync      │    │   Event Mapper           │  │
│  │   Filter     │    │    Engine    │    │   (normalize formats)    │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                                          │
└────────┬───────────────────┬───────────────────────┬────────────────────┘
         │                   │                       │
         ▼                   ▼                       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│  AI Front Desk  │  │ Google Calendar │  │  External Frontdesk API    │
│  Calendar API   │  │ API (OAuth2)    │  │  (webhook callbacks)       │
│                 │  │                 │  │                             │
│ POST /events    │  │ Push Notifs     │  │ POST /webhook/frontdesk    │
│ PUT /events/:id │  │ (via webhook)   │  │                             │
│ DELETE /events  │  │                 │  │                             │
└─────────────────┘  └─────────────────┘  └─────────────────────────────┘
```

## Data Flow

### Flow 1: New Appointment in AI Front Desk → Google Calendar

```
1. User books appointment in AI Front Desk
2. AI Front Desk calls: POST /api/sync/event
   {
     "source": "frontdesk",
     "event": {
       "customerName": "John Smith",
       "customerPhone": "5551234567",
       "startTime": "2026-02-01T10:00:00Z",
       "endTime": "2026-02-01T11:00:00Z",
       "service": "Consultation"
     }
   }
3. Sync Hub applies privacy filter:
   - Title becomes: "John 67 - Consultation"
4. Sync Hub creates event in Google Calendar
5. Sync Hub stores mapping: frontdesk_id <-> google_event_id
```

### Flow 2: New Event in Google Calendar → AI Front Desk

```
1. User manually adds event in Google Calendar
   Title: "Walk-in Customer"
2. Google sends push notification to webhook
3. Sync Hub receives: POST /api/webhook/google
4. Sync Hub fetches full event details from Google
5. Sync Hub calls AI Front Desk API to create slot:
   POST https://agent.opentruthai.com/api/calendar/events
   {
     "title": "Walk-in Customer",
     "startTime": "...",
     "endTime": "...",
     "source": "google",
     "googleEventId": "abc123"
   }
6. Sync Hub stores mapping for future updates
```

### Flow 3: Update/Delete Propagation

```
1. Event updated in any system
2. System notifies Sync Hub (webhook or API call)
3. Sync Hub looks up mapping to find linked events
4. Sync Hub propagates change to other systems
5. Privacy filter applied if syncing TO Google
```

## API Endpoints

### Sync Hub Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sync/event` | Create event and sync to all calendars |
| PUT | `/api/sync/event/:id` | Update event across all calendars |
| DELETE | `/api/sync/event/:id` | Delete event from all calendars |
| GET | `/api/sync/status` | Get sync status and health |
| POST | `/api/webhook/google` | Receive Google Calendar push notifications |
| POST | `/api/webhook/frontdesk` | Receive Frontdesk system notifications |

### AI Front Desk Required Endpoints

The AI Front Desk system needs these endpoints for the sync to work:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calendar/events` | List events (with date range filter) |
| POST | `/api/calendar/events` | Create new event |
| PUT | `/api/calendar/events/:id` | Update existing event |
| DELETE | `/api/calendar/events/:id` | Delete event |
| POST | `/api/calendar/webhook` | Register for change notifications |

## Privacy Filter Logic

```javascript
function applyPrivacyFilter(event) {
  // Extract first name only
  const firstName = event.customerName.split(' ')[0];

  // Get last 2 digits of phone (strip non-digits first)
  const digits = event.customerPhone.replace(/\D/g, '');
  const lastTwo = digits.slice(-2);

  return {
    title: `${firstName} ${lastTwo}`,
    // Or with service: `${firstName} ${lastTwo} - ${event.service}`
    startTime: event.startTime,
    endTime: event.endTime,
    // Store original ID for reverse lookup
    metadata: {
      syncSource: 'frontdesk',
      originalId: event.id
    }
  };
}
```

## Event Mapping Storage

SQLite database to track linked events across systems:

```sql
CREATE TABLE event_mappings (
  id TEXT PRIMARY KEY,
  frontdesk_event_id TEXT,
  google_event_id TEXT,
  external_event_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  sync_status TEXT DEFAULT 'synced',
  last_sync_error TEXT
);

CREATE INDEX idx_frontdesk ON event_mappings(frontdesk_event_id);
CREATE INDEX idx_google ON event_mappings(google_event_id);
```

## Google Calendar Setup

### 1. Create Google Cloud Project
- Go to: https://console.cloud.google.com
- Create new project: "Calendar Sync Hub"
- Enable Google Calendar API

### 2. Create OAuth2 Credentials
- Create OAuth 2.0 Client ID
- Application type: Web application
- Authorized redirect URI: `https://your-domain.com/api/auth/google/callback`

### 3. Set Up Push Notifications
- Register webhook: `https://your-domain.com/api/webhook/google`
- Google requires HTTPS with valid SSL
- Notifications sent for all calendar changes

### 4. Required Scopes
```
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/calendar.readonly
```

## Environment Variables

```env
# Google Calendar
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/auth/google/callback
GOOGLE_CALENDAR_ID=primary

# AI Front Desk
FRONTDESK_API_URL=https://agent.opentruthai.com/api
FRONTDESK_API_KEY=your-api-key

# Sync Hub
SYNC_HUB_PORT=4200
SYNC_HUB_SECRET=your-webhook-secret
DATABASE_URL=file:./sync.db
```

## Deployment Options

### Option A: Standalone Service (Recommended)
Deploy as separate service alongside existing systems:
- Run on port 4200
- Nginx proxy at `/sync/` path
- Own PM2 process

### Option B: Integrated into AgentGPT
Add as tRPC router to existing AgentGPT app:
- New Prisma models for event mappings
- New router: `calendarSyncRouter`
- Shared authentication

## Implementation Priority

1. **Phase 1**: Google Calendar OAuth + basic read/write
2. **Phase 2**: Privacy filter + one-way sync (Frontdesk → Google)
3. **Phase 3**: Webhook receiver for Google → Frontdesk
4. **Phase 4**: Full bidirectional sync with conflict resolution
5. **Phase 5**: External Frontdesk system integration
