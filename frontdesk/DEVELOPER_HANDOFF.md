# J. Austin Front Desk Processing - Developer Handoff Document

**Last Updated:** January 29, 2026
**Application URL:** https://agent.opentruthai.com/frontdesk/
**Server:** 64.23.156.217 (DigitalOcean Droplet)
**Deployment Path:** `/opt/frontdesk`

---

## 1. Project Overview

J. Austin Front Desk Processing is a Django-based CRM system designed specifically for a **bullion and scrap metal dealer**. It handles:

- Customer management (buyers and sellers of precious metals)
- Buyer/seller matching for bullion transactions
- Appointment scheduling with integrated calendar
- Inventory needs tracking (what to buy/sell)
- SMS/Text messaging via Twilio
- Call logging integration with Front Desk AI
- Live precious metals pricing from Fortune Reserve (FizTrade/Dillon Gage)

---

## 2. Architecture & Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | Django 5.1 |
| Database | PostgreSQL 15 |
| Cache/Queue | Redis 7 |
| Task Queue | Celery |
| WSGI Server | Gunicorn |
| Reverse Proxy | Nginx (handles `/frontdesk` prefix) |

### Frontend
| Component | Technology |
|-----------|------------|
| CSS Framework | Bootstrap 5.3 |
| Icons | Bootstrap Icons |
| Forms | crispy-forms + crispy-bootstrap5 |
| Calendar | FullCalendar 6.x |
| JavaScript | Vanilla JS (no framework) |

### External Services
| Service | Purpose |
|---------|---------|
| Twilio | SMS send/receive |
| SendGrid | Email sending |
| Fortune Reserve API | Live metals pricing (FizTrade/Dillon Gage) |
| Front Desk AI | Call logging integration |

---

## 3. Data Models

### Core Models (`core/models.py`)

#### Customer
Primary record for all buyers and sellers.

```python
Fields:
- name (CharField)
- phone (CharField)
- email (EmailField)
- action (BUYING/SELLING)
- metal (GOLD/SILVER/PLATINUM/PALLADIUM)
- metal_form (BULLION/SCRAP/OTHER)
- bullion_amount (DecimalField - troy ounces)
- bullion_type (GOLD/SILVER/PLATINUM/PALLADIUM)
- price_per_oz (DecimalField)
- notes (TextField)
- status (PENDING/MATCHED/CLOSED/ACTIVE)
- source (WALK_IN/PHONE/TEXT/EMAIL/FRONTDESK_AI)
- created_at, updated_at
```

#### Match
Pairs buyers with sellers for bullion transactions.

```python
Fields:
- buyer (FK to Customer)
- seller (FK to Customer)
- amount (DecimalField - troy ounces)
- bullion_type (GOLD/SILVER/PLATINUM/PALLADIUM)
- status (PROPOSED/ACCEPTED/COMPLETED/CANCELED)
- profit_margin (DecimalField - dollars)
- notes (TextField)
- created_at
```

#### Appointment
Scheduled meetings with customers.

```python
Fields:
- customer (FK to Customer)
- match (FK to Match, optional)
- inventory_need (FK to InventoryNeed, optional)
- quantity (IntegerField - for inventory fulfillment)
- datetime (DateTimeField)
- end_datetime (DateTimeField, optional)
- purpose (CharField)
- location (CharField, default "J. Austin Office")
- status (SCHEDULED/CONFIRMED/COMPLETED/CANCELED/NO_SHOW)
- notes (TextField)
```

#### InventoryNeed
Tracks what the dealer needs to buy or sell.

```python
Fields:
- action (BUY/SELL)
- product (CharField - e.g., "Gold Eagle", "Silver Bar")
- metal (GOLD/SILVER/PLATINUM/PALLADIUM)
- size (CharField - e.g., "1 oz", "10 oz")
- quantity_needed (IntegerField)
- quantity_fulfilled (IntegerField)
- status (OPEN/PARTIAL/FILLED/CANCELED)
- notes (TextField)

Properties:
- quantity_pending: Calculated from scheduled/confirmed appointments
- quantity_remaining: needed - fulfilled - pending
```

#### DayNote
Calendar notes/reminders (not tied to appointments).

```python
Fields:
- date (DateField)
- time (TimeField, optional)
- content (TextField)
```

#### Interaction
Record of all customer communications.

```python
Fields:
- customer (FK to Customer)
- type (CALL/TEXT/EMAIL)
- direction (INBOUND/OUTBOUND)
- summary (TextField)
- raw_data (JSONField)
- created_at
```

#### TextTemplate
Reusable SMS message templates.

```python
Fields:
- name (CharField)
- content (TextField)
- category (GENERAL/APPOINTMENT/PRICING/MATCHING)
- is_active (BooleanField)
```

#### CallLog
Phone call records from Front Desk AI.

```python
Fields:
- customer (FK to Customer, optional)
- phone_number (CharField)
- direction (INBOUND/OUTBOUND)
- duration (IntegerField - seconds)
- transcript (TextField)
- category_detected (CharField)
- frontdesk_ai_id (CharField)
```

---

## 4. URL Routes & API Endpoints

### Page Routes (HTML Views)

| URL | View | Description |
|-----|------|-------------|
| `/` | dashboard | Main dashboard with stats |
| `/login/` | login_view | Login page |
| `/logout/` | logout_view | Logout |
| `/customers/` | customer_list | Customer list/management |
| `/customers/<pk>/` | customer_detail | Single customer details |
| `/matching/` | matching_view | Buyer/seller matching interface |
| `/appointments/` | appointment_list | Appointment list |
| `/calendar/` | calendar_view | FullCalendar interface |
| `/texting/` | texting_view | SMS messaging interface |
| `/texting/templates/` | template_manage | Manage text templates |
| `/calls/` | call_log_view | Call log history |
| `/import/` | csv_import_view | CSV import interface |
| `/conversation/<pk>/` | conversation_view | Customer conversation thread |
| `/inventory/` | inventory_view | Inventory needs management |
| `/guide/` | integration_guide | Integration documentation |

### JSON API Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `/customers/api/` | GET/POST/PUT/DELETE | Customer CRUD |
| `/appointments/api/` | GET/POST/PUT/DELETE | Appointment CRUD |
| `/notes/api/` | GET/POST/PUT/DELETE | Day notes CRUD |
| `/inventory/api/` | GET/POST/PUT/DELETE | Inventory CRUD |
| `/inventory/for-appointment/` | GET | Get matching inventory for appointment |
| `/matching/generate/` | POST | Auto-generate buyer/seller matches |
| `/matching/manual/` | POST | Create manual match (consignment sale) |
| `/matching/<pk>/<action>/` | POST | Accept/complete/cancel match |
| `/texting/send/` | POST | Send SMS to customers |
| `/texting/templates/api/` | GET | Get text templates |
| `/api/prices/` | GET | Live metals pricing |
| `/api/dashboard/stats/` | GET | Dashboard statistics |
| `/api/customers/search/` | GET | Customer search |
| `/api/interactions/create/` | POST | Create interaction |

### Webhook Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `/calls/webhook/` | POST | Front Desk AI call webhook |
| `/sms/webhook/` | POST | Twilio inbound SMS webhook |

### Export Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `/export/calls/` | GET | Export call logs as CSV |
| `/export/texts/` | GET | Export text messages as CSV |

---

## 5. Key Features

### 5.1 Buyer/Seller Matching
- **Auto-match**: Analyzes customers to find compatible buyers and sellers
- **Manual match**: Record consignment sales directly (seller gives item, you find buyer)
- **Match workflow**: Proposed → Accepted → Completed
- **Balance sheet**: Shows net position by metal type

### 5.2 Calendar & Appointments
- **FullCalendar integration**: Drag-drop, resize, click-to-edit
- **Day notes**: Non-appointment reminders on calendar
- **Auto-refresh polling**: Calendar updates every 10 seconds across all screens
- **Inventory linking**: Appointments can fulfill inventory needs
- **Status tracking**: Scheduled → Confirmed → Completed

### 5.3 Inventory Management
- **Buy/Sell tracking**: What you need to acquire vs. sell
- **Progress tracking**:
  - `quantity_pending` = from scheduled appointments
  - `quantity_fulfilled` = actually completed
  - `quantity_remaining` = still needed
- **Auto-fulfillment**: When appointment completes, inventory updates
- **Stacked progress bars**: Visual showing pending (blue) + fulfilled (green)

### 5.4 Live Metals Pricing
- **Source**: Fortune Reserve API (FizTrade/Dillon Gage)
- **Metals**: Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD)
- **Data**: Bid, Ask, Spot, Change, Change%
- **Caching**: 60-second cache to reduce API calls
- **Display**: Ticker bar on Matching and Inventory pages
- **Refresh**: Auto-refreshes every 60 seconds

### 5.5 SMS/Texting
- **Twilio integration**: Send and receive SMS
- **Template system**: Reusable message templates
- **Bulk send**: Send to multiple customers at once
- **Conversation view**: Thread-style message history

### 5.6 Call Integration
- **Front Desk AI webhook**: Auto-logs calls
- **Customer matching**: Matches phone numbers to customers
- **CSV import**: Import call logs from CSV

---

## 6. File Structure

```
frontdesk/
├── core/                      # Main Django app
│   ├── __init__.py
│   ├── admin.py              # Django admin config
│   ├── api_views.py          # JSON API views
│   ├── forms.py              # Django forms
│   ├── models.py             # Database models
│   ├── services.py           # External services (pricing)
│   ├── tasks.py              # Celery tasks
│   ├── urls.py               # URL routing
│   ├── views.py              # Main views (1900+ lines)
│   ├── migrations/           # Database migrations
│   └── templatetags/         # Custom template tags
│
├── frontdesk/                # Django project settings
│   ├── __init__.py
│   ├── celery.py             # Celery configuration
│   ├── settings.py           # Django settings
│   ├── urls.py               # Root URL config
│   └── wsgi.py               # WSGI application
│
├── templates/                # HTML templates
│   ├── base.html             # Base template with navbar
│   ├── dashboard.html        # Main dashboard
│   ├── customers.html        # Customer list
│   ├── customer_detail.html  # Customer detail page
│   ├── matching.html         # Buyer/seller matching
│   ├── calendar.html         # FullCalendar interface
│   ├── appointments.html     # Appointment list
│   ├── inventory.html        # Inventory management
│   ├── texting.html          # SMS interface
│   ├── call_log.html         # Call history
│   ├── conversation.html     # Message thread
│   ├── csv_import.html       # CSV import
│   ├── templates_manage.html # Text templates
│   ├── integration_guide.html # Integration docs
│   └── login.html            # Login page
│
├── static/                   # Static files (CSS, JS, images)
│   └── css/
│       └── style.css
│
├── staticfiles/              # Collected static files (production)
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker build file
├── docker-compose.yml        # Docker Compose config
├── .env.example              # Environment variables template
└── DEVELOPER_HANDOFF.md      # This document
```

---

## 7. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django
FRONTDESK_SECRET_KEY=<random-string>
FRONTDESK_DEBUG=False
FRONTDESK_ALLOWED_HOSTS=your-domain.com,localhost

# Database (PostgreSQL)
FRONTDESK_DB_NAME=frontdesk
FRONTDESK_DB_USER=frontdesk
FRONTDESK_DB_PASSWORD=<secure-password>
FRONTDESK_DB_HOST=frontdesk-db  # Docker service name
FRONTDESK_DB_PORT=5432

# Redis (Celery)
FRONTDESK_REDIS_URL=redis://frontdesk-redis:6379/1

# Twilio (SMS)
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_PHONE=+1XXXXXXXXXX

# SendGrid (Email)
SENDGRID_API_KEY=SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Front Desk AI
FRONTDESK_AI_API_KEY=<your-api-key>

# AI APIs (optional)
ANTHROPIC_API_KEY=<your-api-key>
GROK_API_KEY=<your-api-key>
```

---

## 8. Deployment

### Production Server Setup

The application runs on a DigitalOcean droplet at **64.23.156.217**.

**Server Path:** `/opt/frontdesk`

### Docker Deployment

```bash
# Start all services
cd /opt/frontdesk
docker compose up -d

# View logs
docker compose logs -f frontdesk-web

# Restart after code changes
docker compose restart frontdesk-web

# Run migrations
docker compose exec frontdesk-web python manage.py migrate

# Create superuser
docker compose exec frontdesk-web python manage.py createsuperuser

# Collect static files
docker compose exec frontdesk-web python manage.py collectstatic --noinput
```

### Services Running
- **frontdesk-web**: Django application (port 8001)
- **frontdesk-db**: PostgreSQL database (port 5433 external, 5432 internal)
- **frontdesk-redis**: Redis for Celery (port 6380 external, 6379 internal)
- **frontdesk-celery**: Celery worker for async tasks

### Nginx Configuration

Nginx proxies `/frontdesk/` to the Django app:

```nginx
location /frontdesk/ {
    proxy_pass http://127.0.0.1:8001/frontdesk/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Manual Deployment Steps

When updating code on the server:

```bash
# SSH to server
ssh root@64.23.156.217

# Navigate to deployment directory
cd /opt/frontdesk

# Copy updated files (from local machine or pull from repo)
# Files to update: core/, templates/, static/

# Restart the web service
docker compose restart frontdesk-web

# If models changed, run migrations
docker compose exec frontdesk-web python manage.py migrate
```

---

## 9. Pricing API Integration

### Fortune Reserve API

**Endpoint:** `https://fortunereserve.com/wp-json/fortune-reserve/v1/spot-prices`

**Response Format:**
```json
{
  "success": true,
  "timestamp": "Thursday, Jan 29 10:30:00 AM",
  "source": "FizTrade via Fortune Reserve",
  "data": {
    "gold": {
      "name": "Gold",
      "symbol": "XAU",
      "bid": 2650.80,
      "ask": 2652.40,
      "change": -12.50,
      "changePercent": -0.47
    },
    "silver": { ... },
    "platinum": { ... },
    "palladium": { ... }
  }
}
```

**Frontend API:** `/frontdesk/api/prices/`

Returns transformed data with:
- Calculated spot price (avg of bid/ask)
- Spread (ask - bid)
- 60-second caching

---

## 10. Key JavaScript Patterns

### CSRF Token (all pages)
```javascript
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1];
```

### Bootstrap Modal Instance Pattern
To prevent backdrop stacking issues:
```javascript
// Store modal instance (don't create new ones)
let myModal = null;

document.addEventListener('DOMContentLoaded', function() {
    myModal = new bootstrap.Modal(document.getElementById('myModal'));
});

function showModal() {
    // Only show if not already visible
    const modalEl = document.getElementById('myModal');
    if (!modalEl.classList.contains('show')) {
        myModal.show();
    }
}
```

### Calendar Polling (10-second refresh)
```javascript
let pollInterval = null;
let lastEventHash = '';

function startCalendarPolling() {
    pollInterval = setInterval(checkForUpdates, 10000);
}

function checkForUpdates() {
    fetch('/frontdesk/appointments/api/?start=...&end=...')
        .then(r => r.json())
        .then(data => {
            const hash = JSON.stringify(data);
            if (hash !== lastEventHash) {
                lastEventHash = hash;
                calendar.refetchEvents();
            }
        });
}
```

---

## 11. Recent Changes (January 2026)

1. **Inventory Management System**
   - Added InventoryNeed model with BUY/SELL actions
   - Track quantity_pending from scheduled appointments
   - Auto-fulfillment when appointments complete

2. **Calendar Auto-Refresh**
   - 10-second polling interval
   - Hash comparison to detect changes
   - Pauses when modals open or page hidden

3. **Modal Backdrop Bug Fix**
   - Store modal instances as variables
   - Only show if not already visible

4. **Manual Match Feature**
   - Record consignment sales
   - Optional buyer/seller fields (defaults to "Unknown")
   - Goes directly to COMPLETED status

5. **Live Metals Pricing**
   - Fortune Reserve API integration
   - Bid/Ask/Spot/Change display
   - 60-second cache and refresh
   - Ticker bar on Matching and Inventory pages

---

## 12. Known Issues & TODOs

### Current Issues
- None critical

### Future Enhancements
- [ ] SMS auto-responder integration
- [ ] Price alerts when metals hit target prices
- [ ] Report generation (daily/weekly summaries)
- [ ] Customer portal for self-service appointments
- [ ] Mobile-responsive improvements
- [ ] Push notifications for new matches

---

## 13. Support & Contact

For questions about this application, contact the development team or refer to:
- **Integration Guide:** `/frontdesk/guide/`
- **GitHub Issues:** Report bugs and feature requests

---

*Document generated by Claude Code - January 29, 2026*
