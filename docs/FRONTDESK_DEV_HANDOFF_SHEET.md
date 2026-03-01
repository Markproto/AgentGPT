# Front Desk AI - Developer Handoff Sheet

**System:** J. Austin Front Desk Processing (Bullion/Scrap Metal CRM)
**Live URL:** https://agent.opentruthai.com/frontdesk/
**Server:** 64.23.156.217 (DigitalOcean Droplet)
**Deployment Path:** `/opt/frontdesk`
**Last Updated:** March 2026

---

## Quick Reference

| Item | Value |
|------|-------|
| Framework | Django 5.1 (Python 3.11) |
| Database | PostgreSQL 15 |
| Cache/Queue | Redis 7 + Celery |
| Frontend | Bootstrap 5.3, FullCalendar 6.x, Vanilla JS |
| WSGI | Gunicorn (port 8001) |
| Proxy | Nginx at `/frontdesk/` |
| Containers | `frontdesk-web`, `frontdesk-db`, `frontdesk-redis`, `frontdesk-celery` |
| Calendar Sync | Node.js service (port 4200) |
| Repo | `github.com/Markproto/AgentGPT` (under `/frontdesk/`) |

---

## 1. What It Does (Business Context)

A CRM for a precious metals dealer (J. Austin). Customers call or walk in wanting to **buy or sell** gold, silver, platinum, or palladium. The system:

1. Records customer intent (buying/selling, metal type, quantity, price expectations)
2. Schedules appointments via calendar
3. Matches buyers with sellers to facilitate transactions
4. Tracks inventory needs and fulfillment progress
5. Handles SMS communication via Twilio
6. Logs phone calls from the AI phone system (MyAIFrontDesk)
7. Shows live precious metals pricing (Fortune Reserve / FizTrade / Dillon Gage)
8. Syncs appointments bidirectionally with Google Calendar (privacy-filtered)
9. Provides a "High Command" alert system for cross-screen messages

---

## 2. Feature Inventory

### 2.1 Dashboard (`/frontdesk/`)
- At-a-glance stats: total customers, pending matches, today's appointments
- Volume breakdown by metal type (buy vs sell)
- Recent activity feed

### 2.2 Customer Management (`/frontdesk/customers/`)
- Full CRUD for customer records
- Fields: name, phone, email, action (buying/selling), metal preference, metal form, bullion amount, price per oz
- Source tracking: Walk-In, Phone, Text, Email, Front Desk AI
- Status workflow: Pending → Matched → Closed / Active
- Customer detail page with interaction history, appointments, matches
- Search/autocomplete across name, phone, email

### 2.3 Calendar & Appointments (`/frontdesk/calendar/`)
- **FullCalendar.js** interactive calendar (week/day/month views)
- Drag-and-drop appointment creation on time slots
- Click-to-edit existing appointments
- 15-minute time slots
- **Color coding by status:**
  - Blue = Scheduled
  - Green = Confirmed
  - Gray = Completed
  - Red = Canceled
  - Yellow = No Show
- **Day Notes**: Sticky notes on calendar dates (not appointments)
- **Auto-refresh**: Polls every 10 seconds, compares hash to detect changes
- Pauses polling when modal is open or page is hidden

### 2.4 Appointment Creation Form
- Customer selection (dropdown or type-to-create)
- **Buy/Sell toggle buttons** (updates the Customer record automatically)
- **Metal type buttons**: Gold, Silver, Platinum, Palladium
- **Metal form**: Bullion, Scrap, Other
- **Product selection** (from Spread/Product pricing table)
- **Quantity** (oz)
- **Inventory Need linking** (connects appointment to inventory fulfillment)
- Purpose, location, date/time, notes
- Duration (default 30 min)

### 2.5 Buyer/Seller Matching (`/frontdesk/matching/`)
- **Auto-match algorithm**: Finds complementary buy/sell needs by product, size, metal
- **Manual match**: Record consignment sales directly
- **Match workflow**: Proposed → Accepted → Completed (or Canceled)
- **Profit margin tracking** on each match
- Two-column layout: Buyers (left) vs Sellers (right)
- Balance sheet showing net position by metal type
- Live metals pricing ticker bar

### 2.6 Inventory Management (`/frontdesk/inventory/`)
- Track what the dealer needs to BUY or SELL
- Per-need tracking:
  - `quantity_needed` - total target
  - `quantity_fulfilled` - completed from appointments
  - `quantity_pending` - from scheduled/confirmed appointments
  - `quantity_remaining` - still outstanding
- **Stacked progress bars**: blue (pending) + green (fulfilled)
- Status: Open → Partial → Filled (auto-updates based on quantities)
- Links to appointments for fulfillment
- Live metals pricing ticker bar

### 2.7 Spread / Product Pricing (`/frontdesk/spread/`)
- Product catalog with pricing premiums relative to spot price
- Fields: name, metal, size, buy_premium, sell_premium
- Examples: "American Eagle 1 oz Gold" - buy premium $50, sell premium $80
- CRUD interface for managing products

### 2.8 Live Metals Pricing
- **Source**: Fortune Reserve API (FizTrade/Dillon Gage data)
- **Metals**: Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD)
- **Data points**: Bid, Ask, Spot (mid), Spread, Change, Change%
- **60-second cache** to reduce API calls
- **Auto-refresh**: Ticker bar refreshes every 60 seconds
- **Displayed on**: Matching page, Inventory page, via `/frontdesk/api/prices/`

### 2.9 SMS/Texting (`/frontdesk/texting/`)
- **Twilio integration** for send/receive SMS
- **Template system**: Reusable message templates with categories (General, Appointment, Pricing, Matching)
- **Bulk send**: Send to multiple customers at once
- **Conversation view** (`/frontdesk/conversation/<pk>/`): Thread-style message history per customer
- **Inbound SMS webhook**: `/frontdesk/sms/webhook/` (Twilio posts here)

### 2.10 Call Log (`/frontdesk/calls/`)
- Phone call records from Front Desk AI (MyAIFrontDesk)
- Fields: customer, phone, direction, duration, transcript, category
- **Webhook endpoint**: `/frontdesk/calls/webhook/` for incoming call data
- **Sync button**: `/frontdesk/calls/sync/` to pull latest calls
- **CSV import/export**: `/frontdesk/import/`, `/frontdesk/export/calls/`
- **Transcript viewer**: Modal with dialogue-formatted transcripts (assistant/user/system speakers)
- Customer auto-matching by phone number

### 2.11 Google Calendar Sync (Node.js service)
- **Bidirectional sync** between Front Desk calendar and Google Calendar
- **Privacy filtering**: Google Calendar only sees "FirstName XX" (first name + last 2 phone digits)
  - Example: "David Scott (555) 123-4567" → "David 67" in Google
- **Push notifications**: Google sends webhook on calendar changes
- **Event mapping**: SQLite DB tracks `frontdesk_event_id ↔ google_event_id`
- **OAuth2 flow** for Google Calendar authentication
- Runs as standalone Node.js Express service on port 4200

### 2.12 MyAIFrontDesk Integration (AI Phone System)
- **External webhook**: `POST /api/webhook/external` (via calendar-sync service)
- Accepts multiple payload formats (MyAIFrontDesk, standard, flat)
- **Auto-detection from call text**:
  - Action: "selling 2 oz gold" → `action=sell`
  - Metal: detects gold/silver/platinum/palladium
  - Quantity: extracts numeric + "oz"/"ounce"
  - Form: detects bullion/scrap/coins
- Creates appointments + call log entries automatically
- Syncs to Google Calendar with privacy filter

### 2.13 High Command Alert System (`/frontdesk/api/highcommand/`)
- Cross-screen alert banner system
- Send password-protected messages that flash across all screens
- Alert bar appears at top of every page
- Responders can acknowledge messages
- Status: Active → Acknowledged → Archived
- Polls every 5 seconds for new messages

### 2.14 CSV Import/Export (`/frontdesk/import/`)
- Import call logs and customer data from CSV files
- Export call logs: `/frontdesk/export/calls/`
- Export text messages: `/frontdesk/export/texts/`

### 2.15 Integration Guide (`/frontdesk/guide/`)
- Built-in documentation page for webhook integration
- Shows payload formats and API usage

---

## 3. Data Models

### Customer
| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | |
| phone | CharField(20) | |
| email | EmailField | |
| action | CharField(10) | BUYING / SELLING |
| metal | CharField(10) | GOLD / SILVER / PLATINUM / PALLADIUM |
| metal_form | CharField(10) | BULLION / SCRAP / OTHER |
| category | CharField(20) | Legacy: BUY_BULLION / SELL_BULLION / BUY_SCRAP_GOLD / BUY_SCRAP_SILVER |
| bullion_amount | Decimal(12,4) | Troy ounces |
| bullion_type | CharField(10) | GOLD / SILVER / PLATINUM / PALLADIUM |
| price_per_oz | Decimal(10,2) | Desired price per troy oz |
| notes | TextField | |
| status | CharField(10) | PENDING / MATCHED / CLOSED / ACTIVE |
| source | CharField(15) | WALK_IN / PHONE / TEXT / EMAIL / FRONTDESK_AI |

### Appointment
| Field | Type | Notes |
|-------|------|-------|
| customer | FK→Customer | |
| match | FK→Match | Optional |
| inventory_need | FK→InventoryNeed | Optional - links to fulfillment |
| quantity | Decimal(10,4) | Oz for this appointment |
| datetime | DateTimeField | Start time |
| end_datetime | DateTimeField | Optional |
| purpose | CharField(255) | |
| location | CharField(255) | Default: "J. Austin Office" |
| status | CharField(10) | SCHEDULED / CONFIRMED / COMPLETED / CANCELED / NO_SHOW |

### Match
| Field | Type | Notes |
|-------|------|-------|
| buyer | FK→Customer | |
| seller | FK→Customer | |
| amount | Decimal(12,4) | Troy ounces |
| bullion_type | CharField(10) | |
| status | CharField(10) | PROPOSED / ACCEPTED / COMPLETED / CANCELED |
| profit_margin | Decimal(10,2) | Dollars |

### InventoryNeed
| Field | Type | Notes |
|-------|------|-------|
| action | CharField(4) | BUY / SELL |
| product | CharField(100) | e.g., "Gold Eagle" |
| metal | CharField(10) | |
| size | CharField(50) | e.g., "1 oz" |
| quantity_needed | Decimal(10,4) | |
| quantity_fulfilled | Decimal(10,4) | |
| status | CharField(10) | OPEN / PARTIAL / FILLED / CANCELED |
| **quantity_pending** | Property | Sum from scheduled/confirmed appointments |
| **quantity_remaining** | Property | needed - fulfilled - pending |

### Product (Spread Pricing)
| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | e.g., "American Eagle" |
| metal | CharField(10) | GOLD / SILVER / PLATINUM / PALLADIUM |
| size | CharField(50) | e.g., "1 oz" |
| buy_premium | Decimal(10,2) | Premium when buying from customer |
| sell_premium | Decimal(10,2) | Premium when selling to customer |
| is_active | Boolean | |

### CallLog
| Field | Type | Notes |
|-------|------|-------|
| customer | FK→Customer | Optional |
| phone_number | CharField(20) | |
| direction | CharField(10) | INBOUND / OUTBOUND |
| duration | Integer | Seconds |
| transcript | TextField | Full call transcript |
| category_detected | CharField(50) | |
| frontdesk_ai_id | CharField(255) | External ID from MyAIFrontDesk |

### HighCommandMessage
| Field | Type | Notes |
|-------|------|-------|
| message | TextField | Alert message text |
| sender_name | CharField(100) | Who sent it |
| status | CharField(12) | ACTIVE / ACKNOWLEDGED / ARCHIVED |
| response | TextField | Response text |
| responder_name | CharField(100) | Who responded |
| responded_at | DateTimeField | |

### Other Models
- **Interaction**: Customer communication log (type, direction, summary, raw_data)
- **TextTemplate**: Reusable SMS templates (name, content, category)
- **DayNote**: Calendar notes not tied to appointments (date, time, content)

---

## 4. API Endpoints Reference

### Page Routes (require login)

| Path | View | Description |
|------|------|-------------|
| `/` | dashboard | Dashboard with stats |
| `/login/` | login_view | Login page |
| `/customers/` | customer_list | Customer list |
| `/customers/<pk>/` | customer_detail | Customer detail |
| `/matching/` | matching_view | Matching interface |
| `/calendar/` | calendar_view | FullCalendar |
| `/appointments/` | appointment_list | Appointment list |
| `/inventory/` | inventory_view | Inventory management |
| `/spread/` | spread_view | Product pricing |
| `/texting/` | texting_view | SMS interface |
| `/texting/templates/` | template_manage | Manage templates |
| `/calls/` | call_log_view | Call log |
| `/conversation/<pk>/` | conversation_view | Message thread |
| `/import/` | csv_import_view | CSV import |
| `/guide/` | integration_guide | Integration docs |

### JSON API Endpoints (require login + CSRF)

| Path | Methods | Description |
|------|---------|-------------|
| `/customers/api/` | GET/POST/PUT/DELETE | Customer CRUD |
| `/appointments/api/` | GET/PUT/DELETE | Appointment read/update/delete |
| `/appointments/create/` | POST | Create appointment |
| `/notes/api/` | GET/POST/PUT/DELETE | Day notes CRUD |
| `/inventory/api/` | GET/POST/PUT/DELETE | Inventory needs CRUD |
| `/inventory/for-appointment/` | GET | Get inventory needs for appointment form |
| `/matching/generate/` | POST | Run auto-match algorithm |
| `/matching/manual/` | POST | Create manual match |
| `/matching/<pk>/<action>/` | POST | accept/complete/cancel match |
| `/texting/send/` | POST | Send SMS |
| `/texting/templates/api/` | GET | List templates |
| `/spread/api/` | GET/POST/PUT/DELETE | Product pricing CRUD |
| `/api/prices/` | GET | Live metals pricing |
| `/api/dashboard/stats/` | GET | Dashboard statistics |
| `/api/customers/search/` | GET | Customer autocomplete |
| `/api/interactions/create/` | POST | Create interaction record |
| `/api/highcommand/` | GET/POST | High Command alerts (GET=check, POST=send/respond) |

### Webhook Endpoints (no auth required)

| Path | Method | Description |
|------|--------|-------------|
| `/calls/webhook/` | POST | Front Desk AI call data |
| `/sms/webhook/` | POST | Twilio inbound SMS |

### Export Endpoints (require login)

| Path | Method | Description |
|------|--------|-------------|
| `/export/calls/` | GET | Export call logs as CSV |
| `/export/texts/` | GET | Export text messages as CSV |

### Calendar Sync Service Endpoints (port 4200)

| Path | Method | Description |
|------|--------|-------------|
| `/api/sync/event` | POST | Sync event to all calendars |
| `/api/sync/status` | GET | Sync health status |
| `/api/webhook/frontdesk` | POST | Receive Front Desk changes |
| `/api/webhook/google` | POST | Receive Google Calendar push notifications |
| `/api/webhook/google/setup` | POST | Configure Google push notifications |
| `/api/webhook/external` | POST | MyAIFrontDesk webhook (creates appointments) |
| `/api/auth/google` | GET | Start Google OAuth flow |
| `/api/auth/google/callback` | GET | OAuth callback |

---

## 5. Architecture

```
                                 ┌─────────────────┐
                                 │  MyAIFrontDesk  │
                                 │  (AI Phone)     │
                                 └────────┬────────┘
                                          │ webhook POST
                                          ▼
┌──────────┐     ┌──────────┐     ┌─────────────────┐     ┌──────────────┐
│ Browser  │────▶│  Nginx   │────▶│ calendar-sync   │────▶│   Google     │
│          │     │ (proxy)  │     │ (Node.js:4200)  │     │  Calendar    │
└──────────┘     └────┬─────┘     └────────┬────────┘     └──────────────┘
                      │                     │
                      ▼                     ▼
               ┌──────────────┐     ┌──────────────┐
               │ frontdesk-web│     │   sync.db    │
               │ (Django:8001)│     │  (SQLite)    │
               └──────┬───────┘     └──────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌───────────┐ ┌─────────┐ ┌────────┐
   │PostgreSQL │ │  Redis  │ │ Celery │
   │  (5433)   │ │ (6380)  │ │ worker │
   └───────────┘ └─────────┘ └────────┘
```

### Docker Services (docker-compose.yml)

| Service | Container | Port (ext:int) | Image |
|---------|-----------|----------------|-------|
| frontdesk-web | frontdesk-web | 8001:8001 | Custom (Dockerfile) |
| frontdesk-db | frontdesk-db | 5433:5432 | postgres:15-alpine |
| frontdesk-redis | frontdesk-redis | 6380:6379 | redis:7-alpine |
| frontdesk-celery | frontdesk-celery | none | Same as web |

---

## 6. File Structure

```
frontdesk/
├── core/                        # Main Django app
│   ├── models.py               # 11 models (462 lines)
│   ├── views.py                # All views + APIs (1900+ lines)
│   ├── api_views.py            # Additional JSON APIs
│   ├── services.py             # Fortune Reserve pricing API
│   ├── forms.py                # Django forms
│   ├── urls.py                 # 66 URL patterns
│   ├── admin.py                # Django admin config
│   ├── tasks.py                # Celery async tasks
│   ├── templatetags/           # Custom template tags
│   └── migrations/             # Database migrations
├── frontdesk/                   # Django project config
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL config
│   ├── celery.py               # Celery configuration
│   └── wsgi.py                 # WSGI entry point
├── templates/                   # 16 HTML templates
│   ├── base.html               # Base template + navbar + High Command
│   ├── dashboard.html
│   ├── calendar.html           # FullCalendar interface
│   ├── customers.html
│   ├── customer_detail.html
│   ├── matching.html
│   ├── inventory.html
│   ├── spread.html
│   ├── texting.html
│   ├── call_log.html
│   ├── conversation.html
│   ├── appointments.html
│   ├── csv_import.html
│   ├── templates_manage.html
│   ├── integration_guide.html
│   └── login.html
├── static/css/style.css         # Custom CSS
├── Dockerfile                   # Python 3.11-slim + gunicorn
├── docker-compose.yml           # 4 services
├── requirements.txt             # 13 Python packages
├── manage.py
└── DEVELOPER_HANDOFF.md
```

---

## 7. External Services & Integrations

| Service | Purpose | Config |
|---------|---------|--------|
| **Twilio** | SMS send/receive | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE` |
| **SendGrid** | Email sending | `SENDGRID_API_KEY` |
| **Fortune Reserve** | Live metals pricing | No auth required (public API) |
| **MyAIFrontDesk** | AI phone system → webhooks | Webhook URL configured in their dashboard |
| **Google Calendar** | Calendar sync | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| **Anthropic** | AI features (optional) | `ANTHROPIC_API_KEY` |

---

## 8. Environment Variables

```bash
# Django
FRONTDESK_SECRET_KEY=<random-string>
FRONTDESK_DEBUG=False
FRONTDESK_ALLOWED_HOSTS=agent.opentruthai.com,localhost

# Database (PostgreSQL)
FRONTDESK_DB_NAME=frontdesk
FRONTDESK_DB_USER=frontdesk
FRONTDESK_DB_PASSWORD=<secure-password>
FRONTDESK_DB_HOST=frontdesk-db
FRONTDESK_DB_PORT=5432

# Redis
FRONTDESK_REDIS_URL=redis://frontdesk-redis:6379/1

# Twilio (SMS)
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_PHONE=+1XXXXXXXXXX

# SendGrid (Email)
SENDGRID_API_KEY=SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Google Calendar (calendar-sync service)
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
GOOGLE_REDIRECT_URI=<redirect-uri>
GOOGLE_CALENDAR_ID=primary

# Front Desk AI / Webhook
FRONTDESK_API_URL=<frontdesk-api-url>
FRONTDESK_API_KEY=<api-key>
WEBHOOK_SECRET=<hmac-secret>

# AI APIs (optional)
ANTHROPIC_API_KEY=<key>
GROK_API_KEY=<key>
```

---

## 9. Deployment & Operations

### Start / Stop
```bash
cd /opt/frontdesk
docker compose up -d          # Start all services
docker compose down           # Stop all services
docker compose restart frontdesk-web  # Restart web only
```

### View Logs
```bash
docker compose logs -f frontdesk-web     # Django logs
docker compose logs -f frontdesk-celery  # Celery worker logs
```

### Database Operations
```bash
# Run migrations
docker compose exec frontdesk-web python manage.py migrate

# Create superuser
docker compose exec frontdesk-web python manage.py createsuperuser

# Django shell
docker compose exec -it frontdesk-web python manage.py shell

# Direct DB access
docker compose exec frontdesk-db psql -U frontdesk -d frontdesk
```

### Static Files
```bash
docker compose exec frontdesk-web python manage.py collectstatic --noinput
```

### Nginx Config
Location: `/etc/nginx/sites-enabled/agentgpt.conf`
```nginx
location /frontdesk/ {
    proxy_pass http://127.0.0.1:8001/frontdesk/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

## 10. Security Notes

- **Authentication**: Session-based login required for all views (except webhooks)
- **CSRF**: All POST/PUT/DELETE require `X-CSRFToken` header
- **Webhook endpoints** (`/calls/webhook/`, `/sms/webhook/`): Exempt from CSRF and auth (controlled by Nginx)
- **Calendar sync webhook**: HMAC-SHA256 signature verification
- **Privacy filtering**: Google Calendar only shows first name + last 2 phone digits
- **High Command**: Password-protected message sending

---

## 11. Key Dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.1 | Web framework |
| psycopg2-binary | 2.9.9 | PostgreSQL adapter |
| gunicorn | 22.0.0 | WSGI server |
| celery | 5.4.0 | Async task queue |
| redis | 5.0.0 | Redis client |
| twilio | 9.0.0 | SMS integration |
| sendgrid | 6.11.0 | Email integration |
| anthropic | 0.39.0 | AI features |
| requests | 2.31.0 | HTTP client (pricing API) |
| django-crispy-forms | 2.3 | Form rendering |
| crispy-bootstrap5 | 2024.10 | Bootstrap 5 form templates |
| django-cors-headers | 4.3.1 | CORS headers |
| python-dateutil | 2.8.2 | Date parsing |

---

## 12. Privacy Model (Calendar Sync)

When events sync from Front Desk to Google Calendar:

| Stored in Front Desk | Shown in Google Calendar |
|---------------------|-------------------------|
| David Scott | David 67 |
| (555) 123-4567 | (last 2 digits only) |
| Selling 2oz Gold Eagles | (purpose in description) |

This prevents full customer data from appearing in shared Google Calendar views.

---

## 13. Recent Additions (Feb-Mar 2026)

1. **High Command Alert System** - Cross-screen password-protected alert banner
2. **Product/Spread Pricing** - Product catalog with buy/sell premiums
3. **Inventory Need linking to Appointments** - Track fulfillment per appointment
4. **MyAIFrontDesk auto-detection** - Parse buy/sell/metal/quantity from call transcripts
5. **Call log transcript dialogue formatting** - Renders assistant/user/system as chat bubbles
6. **Google Calendar bidirectional sync** - Full push notification support
7. **Live metals pricing ticker** - Fortune Reserve API with 60s cache

---

*Generated March 2026*
