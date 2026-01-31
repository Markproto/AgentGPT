# Calendar Sync Hub

Bidirectional calendar synchronization between:
- **AI Front Desk** (agent.opentruthai.com/frontdesk/calendar/)
- **Google Calendar**
- **External Frontdesk systems** (e.g., app.myaifrontdesk.cc)

## Privacy Filter

Customer data is protected when syncing to Google Calendar:

| Front Desk | Google Calendar |
|------------|-----------------|
| David Scott (555) 123-4567 | David 67 |
| Judith (555) 987-6543 | Judith 43 |

Only the **first name** and **last 2 digits of phone** are visible in Google Calendar.

## Quick Start

### 1. Install dependencies
```bash
cd calendar-sync
npm install
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Set up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the **Google Calendar API**
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:4200/api/auth/google/callback`
5. Copy Client ID and Secret to your `.env` file

### 4. Start the server
```bash
npm run dev
```

### 5. Connect Google Calendar
Open http://localhost:4200 and click "Connect Google Calendar"

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/google` | Start Google OAuth flow |
| GET | `/api/auth/google/callback` | OAuth callback (automatic) |
| GET | `/api/auth/status` | Check connection status |

### Sync Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sync/event` | Sync event to Google |
| PUT | `/api/sync/event/:id` | Update synced event |
| DELETE | `/api/sync/event/:id` | Delete from all calendars |
| GET | `/api/sync/mappings` | List all event mappings |
| POST | `/api/sync/full` | Full bidirectional sync |
| GET | `/api/sync/status` | Sync statistics |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhook/frontdesk` | Front Desk notifications |
| POST | `/api/webhook/google` | Google Calendar notifications |
| POST | `/api/webhook/google/setup` | Set up Google push notifications |
| POST | `/api/webhook/external` | External system notifications |

## Usage Examples

### Sync a new appointment

When an appointment is created in Front Desk, call:

```javascript
POST /api/sync/event
{
  "event": {
    "id": "apt-123",
    "customerName": "David Scott",
    "customerPhone": "(555) 123-4567",
    "startTime": "2026-02-02T14:00:00Z",
    "endTime": "2026-02-02T14:30:00Z",
    "purpose": "Selling 2 oz Gold",
    "action": "sell",
    "metal": "gold"
  }
}
```

Response:
```json
{
  "success": true,
  "mappingId": "uuid-here",
  "googleEventId": "google-event-id",
  "filteredTitle": "David 67"
}
```

### Webhook Integration

Configure Front Desk to send webhooks on appointment changes:

```javascript
POST /api/webhook/frontdesk
{
  "event": "event.created",
  "data": {
    "id": "apt-123",
    "customerName": "David Scott",
    "customerPhone": "(555) 123-4567",
    "startTime": "2026-02-02T14:00:00Z",
    "endTime": "2026-02-02T14:30:00Z"
  }
}
```

## Deployment

### On your Digital Ocean droplet

1. Clone to server:
```bash
cd /var/www
git clone <repo> calendar-sync
cd calendar-sync
npm install
```

2. Create `.env` with production credentials:
```bash
nano .env
```

3. Start with PM2:
```bash
pm2 start src/index.js --name calendar-sync
pm2 save
```

4. Add Nginx config:
```nginx
server {
    server_name sync.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:4200;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

5. Set up SSL:
```bash
certbot --nginx -d sync.yourdomain.com
```

6. Update Google OAuth redirect URI to production URL

## Data Flow

```
┌─────────────────────┐     ┌─────────────────────┐
│   Front Desk        │     │   Google Calendar   │
│   (Full Details)    │     │   (Privacy Filter)  │
│                     │     │                     │
│ David Scott         │────▶│ David 67            │
│ (555) 123-4567      │     │ 2:00 PM - 2:30 PM   │
│ Selling 2oz Gold    │     │                     │
│ 2:00 PM - 2:30 PM   │     │                     │
└─────────────────────┘     └─────────────────────┘
         │                           │
         │    ┌───────────────┐      │
         └───▶│  Sync Hub     │◀─────┘
              │  Port 4200    │
              │               │
              │ • Maps events │
              │ • Filters data│
              │ • Logs syncs  │
              └───────────────┘
```

## License

Private - J. Austin & Company
