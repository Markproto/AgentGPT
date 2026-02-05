# Front Desk - Developer Handoff Documentation

**OpenTruth AI Front Desk System**
**Last Updated:** February 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Deployment](#deployment)
4. [Data Models](#data-models)
5. [Calendar & Scheduling](#calendar--scheduling)
6. [Inventory & Matching System](#inventory--matching-system)
7. [External Integrations](#external-integrations)
8. [API Reference](#api-reference)
9. [Webhooks](#webhooks)
10. [Frontend Templates](#frontend-templates)
11. [Common Operations](#common-operations)

---

## System Overview

Front Desk is a customer relationship and appointment management system for a precious metals business. It handles:

- **Customer Management** - Track customers, their buy/sell preferences, contact info
- **Appointment Scheduling** - Calendar-based appointment booking with Google Calendar sync
- **Inventory Matching** - Match buyers with sellers for gold, silver, platinum, palladium
- **Spread Pricing** - Product pricing with buy/sell premiums
- **Communication** - SMS texting via Twilio, call logging
- **External Integration** - MyAIFrontDesk webhook for automated appointment creation

### Business Context

Customers call or walk in wanting to buy or sell precious metals (bullion). The system:
1. Records customer intent (buying/selling, metal type, quantity)
2. Schedules appointments
3. Matches buyers with sellers
4. Tracks inventory needs and fulfillment

---

## Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 4.x (Python 3.11) |
| Database | SQLite (containerized) |
| Frontend | Bootstrap 5, FullCalendar.js, Vanilla JS |
| Container | Docker |
| Reverse Proxy | Nginx |
| Calendar Sync | Node.js service (calendar-sync) |
| SMS | Twilio API |
| AI Phone | MyAIFrontDesk |

### System Diagram

```
                                    ┌─────────────────┐
                                    │  MyAIFrontDesk  │
                                    │  (AI Phone)     │
                                    └────────┬────────┘
                                             │ webhook
                                             ▼
┌─────────────┐     ┌─────────────┐    ┌─────────────────┐
│   Browser   │────▶│    Nginx    │───▶│  calendar-sync  │
│             │     │  (proxy)    │    │  (Node.js)      │
└─────────────┘     └──────┬──────┘    └────────┬────────┘
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐       ┌─────────────┐
                    │  Front Desk │       │   Google    │
                    │  (Django)   │◀─────▶│  Calendar   │
                    └──────┬──────┘       └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   SQLite    │
                    │   Database  │
                    └─────────────┘
```

### File Structure

```
/app/                          # Django application root
├── core/
│   ├── models.py              # Data models
│   ├── views.py               # View functions
│   ├── api_views.py           # API endpoints
│   ├── urls.py                # URL routing
│   └── admin.py               # Django admin config
├── templates/
│   ├── base.html              # Base template
│   ├── calendar.html          # Calendar view
│   ├── matching.html          # Matching page
│   ├── inventory.html         # Inventory management
│   ├── spread.html            # Product pricing
│   └── ...
└── static/                    # CSS, JS assets

/home/user/AgentGPT/calendar-sync/   # Calendar sync service
├── src/
│   ├── index.js               # Express server
│   ├── routes/
│   │   └── webhooks.js        # Webhook handlers
│   └── services/
│       ├── syncEngine.js      # Bidirectional sync logic
│       ├── googleCalendar.js  # Google Calendar API
│       ├── frontdeskClient.js # Front Desk API client
│       └── privacyFilter.js   # Name/phone privacy filtering
└── data/
    └── sync.db                # SQLite for sync mappings
```

---

## Deployment

### Docker Container

The Front Desk Django app runs in a Docker container named `frontdesk-web`.

```bash
# View container status
docker ps | grep frontdesk

# View logs
docker logs frontdesk-web --tail 100

# Restart container
docker restart frontdesk-web

# Execute commands in container
docker exec frontdesk-web <command>

# Access Django shell
docker exec -it frontdesk-web python manage.py shell
```

### Nginx Configuration

Located at `/etc/nginx/sites-enabled/agentgpt.conf`

Key routes:
- `/frontdesk/` - Proxied to Django container (port 8001)
- `/frontdesk/api/external-appointment/` - Public webhook endpoint (no auth)

### Environment Variables

```bash
# Django settings
SECRET_KEY=<django-secret-key>
DEBUG=False
ALLOWED_HOSTS=agent.opentruthai.com

# Twilio (SMS)
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
TWILIO_PHONE_NUMBER=<phone>

# Google Calendar (in calendar-sync)
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
GOOGLE_REDIRECT_URI=<redirect-uri>
```

---

## Data Models

### Customer

The central entity - represents a person who buys/sells precious metals.

```python
class Customer(models.Model):
    class Action(models.TextChoices):
        BUYING = "BUYING", "Buying"
        SELLING = "SELLING", "Selling"

    class Metal(models.TextChoices):
        GOLD = "GOLD", "Gold"
        SILVER = "SILVER", "Silver"
        PLATINUM = "PLATINUM", "Platinum"
        PALLADIUM = "PALLADIUM", "Palladium"

    class MetalForm(models.TextChoices):
        COIN = "COIN", "Coin"
        BAR = "BAR", "Bar"
        SCRAP = "SCRAP", "Scrap"
        ROUND = "ROUND", "Round"

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Buy/Sell preferences (used for matching)
    action = models.CharField(choices=Action.choices, blank=True)
    metal = models.CharField(choices=Metal.choices, blank=True)
    metal_form = models.CharField(choices=MetalForm.choices, blank=True)

    source = models.CharField(choices=Source.choices)  # WALK_IN, PHONE, WEB, etc.
    status = models.CharField(choices=Status.choices)  # ACTIVE, INACTIVE, etc.

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Appointment

A scheduled meeting with a customer.

```python
class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"
        NO_SHOW = "NO_SHOW", "No Show"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)

    purpose = models.CharField(max_length=200)  # e.g., "Selling 2oz Gold"
    location = models.CharField(max_length=200, default="J. Austin")
    status = models.CharField(choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)

    # Matching/Inventory link
    inventory_need = models.ForeignKey(
        'InventoryNeed',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Quantity in oz for this appointment"
    )

    # Product link (from Spread pricing)
    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments'
    )

    created_at = models.DateTimeField(auto_now_add=True)
```

### Product (Spread Pricing)

Products with buy/sell premiums for pricing.

```python
class Product(models.Model):
    class Metal(models.TextChoices):
        GOLD = "GOLD", "Gold"
        SILVER = "SILVER", "Silver"
        PLATINUM = "PLATINUM", "Platinum"
        PALLADIUM = "PALLADIUM", "Palladium"

    name = models.CharField(max_length=200)  # e.g., "American Eagle"
    metal = models.CharField(choices=Metal.choices)
    size = models.CharField(max_length=50)  # e.g., "1 oz", "1/2 oz", "100 oz"

    buy_premium = models.DecimalField(max_digits=10, decimal_places=2)   # Premium when WE BUY
    sell_premium = models.DecimalField(max_digits=10, decimal_places=2)  # Premium when WE SELL

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### InventoryNeed (Matching)

Represents a customer's need to buy or sell a specific product.

```python
class InventoryNeed(models.Model):
    class Action(models.TextChoices):
        BUY = "BUY", "Buy"      # Customer wants to BUY (we need to SELL)
        SELL = "SELL", "Sell"  # Customer wants to SELL (we need to BUY)

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIAL = "PARTIAL", "Partial"
        FILLED = "FILLED", "Filled"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    action = models.CharField(choices=Action.choices)

    product = models.CharField(max_length=200)  # Product name
    size = models.CharField(max_length=50)      # Size (1 oz, etc.)
    metal = models.CharField(max_length=20)     # Metal type

    quantity_needed = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    quantity_fulfilled = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    status = models.CharField(choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def quantity_pending(self):
        """Quantity from scheduled/confirmed appointments."""
        pending_statuses = [Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED]
        result = self.appointments.filter(status__in=pending_statuses).aggregate(
            total=Sum('quantity')
        )
        return result['total'] or 0

    @property
    def quantity_remaining(self):
        """Remaining = needed - fulfilled - pending"""
        return max(0, self.quantity_needed - self.quantity_fulfilled - self.quantity_pending)
```

### Match

A potential match between a buyer and seller.

```python
class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONTACTED = "CONTACTED", "Contacted"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    buyer = models.ForeignKey(Customer, related_name='matches_as_buyer')
    seller = models.ForeignKey(Customer, related_name='matches_as_seller')

    product = models.CharField(max_length=200)
    size = models.CharField(max_length=50)
    metal = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=4)

    buyer_need = models.ForeignKey(InventoryNeed, related_name='matches_as_buyer_need')
    seller_need = models.ForeignKey(InventoryNeed, related_name='matches_as_seller_need')

    status = models.CharField(choices=Status.choices, default=Status.PENDING)
    match_score = models.FloatField(default=0)  # Algorithm-generated score

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## Calendar & Scheduling

### Calendar View (`/frontdesk/calendar/`)

The main scheduling interface uses FullCalendar.js.

**Features:**
- Week/day/month views
- Drag-and-drop appointment creation
- Click to edit existing appointments
- Color-coded by status (blue=scheduled, green=confirmed, gray=completed, red=canceled)
- 15-minute time slots

### Appointment Creation Flow

1. User clicks on calendar time slot or "New Appointment" button
2. Modal opens with form fields:
   - Customer (dropdown or type new name)
   - Phone number
   - Action (Buying/Selling) - **updates Customer record**
   - Metal type (Gold/Silver/etc.) - **updates Customer record**
   - Metal form (Coin/Bar/Scrap) - **updates Customer record**
   - Inventory Need (dropdown) - **links to matching system**
   - Quantity (oz)
   - Purpose/notes
   - Date/time
3. POST to `/frontdesk/appointments/create/`
4. Appointment created, synced to Google Calendar

### Calendar Form Fields

```html
<!-- Matching Section (at top of form) -->
<div class="row mb-3 p-2 bg-info bg-opacity-10 rounded border border-info">
    <div class="col-12 mb-2">
        <strong class="text-info"><i class="bi bi-shuffle"></i> Matching</strong>
    </div>
    <div class="col-md-8">
        <label class="form-label">Product</label>
        <select id="apptProduct" class="form-select">
            <option value="">-- Select Product --</option>
            {% for p in products %}
            <option value="{{ p.id }}">{{ p.name }} ({{ p.get_metal_display }}) - {{ p.size }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-md-4">
        <label class="form-label">Qty (oz)</label>
        <input type="number" id="apptQuantity" class="form-control" step="0.0001" min="0">
    </div>
</div>

<!-- Customer Section -->
<div class="mb-3">
    <label class="form-label">Customer</label>
    <select id="apptCustomer" class="form-select">...</select>
</div>

<!-- Buy/Sell Action Buttons -->
<div class="row mb-3">
    <div class="col-md-6">
        <button type="button" class="btn btn-success w-100" id="btnBuying">
            <i class="bi bi-cart-plus"></i> Customer Buying
        </button>
    </div>
    <div class="col-md-6">
        <button type="button" class="btn btn-warning w-100" id="btnSelling">
            <i class="bi bi-cash-coin"></i> Customer Selling
        </button>
    </div>
</div>

<!-- Metal Type Selection -->
<div class="row mb-3" id="metalSection">
    <div class="col-md-3"><button class="btn btn-outline-warning w-100" data-metal="GOLD">Gold</button></div>
    <div class="col-md-3"><button class="btn btn-outline-secondary w-100" data-metal="SILVER">Silver</button></div>
    <div class="col-md-3"><button class="btn btn-outline-info w-100" data-metal="PLATINUM">Platinum</button></div>
    <div class="col-md-3"><button class="btn btn-outline-primary w-100" data-metal="PALLADIUM">Palladium</button></div>
</div>
```

### Google Calendar Sync

The `calendar-sync` Node.js service handles bidirectional sync:

**Front Desk → Google:**
- Privacy filtering: Only syncs "FirstName XX" (first name + last 2 digits of phone)
- Triggered on appointment create/update/delete

**Google → Front Desk:**
- Push notifications via webhook
- Creates appointments from Google events

```javascript
// Privacy-filtered title for Google Calendar
function createGoogleTitle(event) {
    const firstName = privacyFilter.extractFirstName(event.customerName);
    const lastTwo = privacyFilter.extractLastTwoDigits(event.customerPhone);
    return `${firstName} ${lastTwo}`;  // e.g., "David 67"
}
```

---

## Inventory & Matching System

### How Matching Works

1. **Record Customer Need**: When a customer wants to buy/sell, create an InventoryNeed
2. **Generate Matches**: System finds complementary needs (buyer ↔ seller)
3. **Review Matches**: Staff reviews potential matches
4. **Schedule Appointments**: Link appointments to inventory needs
5. **Track Fulfillment**: Mark quantities as fulfilled when transactions complete

### Matching Algorithm

```python
def generate_matches(request):
    """Find potential buyer-seller matches."""
    # Get all open/partial inventory needs
    buyers = InventoryNeed.objects.filter(
        action='BUY',
        status__in=['OPEN', 'PARTIAL']
    )
    sellers = InventoryNeed.objects.filter(
        action='SELL',
        status__in=['OPEN', 'PARTIAL']
    )

    matches = []
    for buyer in buyers:
        for seller in sellers:
            # Match on product, size, metal
            if (buyer.product == seller.product and
                buyer.size == seller.size and
                buyer.metal == seller.metal):

                # Calculate match quantity
                qty = min(buyer.quantity_remaining, seller.quantity_remaining)
                if qty > 0:
                    matches.append({
                        'buyer': buyer,
                        'seller': seller,
                        'quantity': qty,
                        'score': calculate_match_score(buyer, seller)
                    })

    return matches
```

### Inventory Need Lifecycle

```
OPEN → PARTIAL → FILLED
  │       │
  └───────┴── Appointments scheduled/completed update quantities
```

### Matching Page (`/frontdesk/matching/`)

Two-column layout showing:
- **Left**: Buyers (customers wanting to buy)
- **Right**: Sellers (customers wanting to sell)

Each need shows:
- Customer name
- Product/size/metal
- Quantity needed/fulfilled/remaining
- Linked appointments

---

## External Integrations

### MyAIFrontDesk (AI Phone System)

Automated phone system that books appointments via webhook.

**Webhook Endpoint:** `POST /frontdesk/api/external-appointment/`
(Proxied through calendar-sync at `/api/webhook/external`)

**Payload Formats Supported:**

```javascript
// MyAIFrontDesk format
{
    "call_id": "call-123",
    "caller_name": "John Smith",
    "caller_number": "+15551234567",
    "appointment_time": "2026-02-10T14:00:00",
    "reason": "Selling 2 oz Gold Eagles",
    "transcript": "Customer wants to sell gold coins..."
}

// Standard format
{
    "event": "appointment.created",
    "data": {
        "id": "apt-123",
        "customerName": "John Smith",
        "customerPhone": "(555) 123-4567",
        "startTime": "2026-02-10T14:00:00",
        "purpose": "Selling 2 oz Gold",
        "action": "sell",
        "metal": "gold"
    }
}
```

**Auto-Detection:**
The webhook automatically detects buy/sell intent and metal type from the purpose/reason text:

```javascript
// Detects: "Selling 2 oz Gold Eagles" → action=sell, metal=gold, quantity=2
function detectActionFromText(text) {
    if (text.includes('sell') || text.includes('selling')) return 'sell';
    if (text.includes('buy') || text.includes('buying')) return 'buy';
    return null;
}

function detectMetalFromText(text) {
    if (text.includes('gold')) return 'gold';
    if (text.includes('silver')) return 'silver';
    // ...
}

function detectQuantityFromText(text) {
    const match = text.match(/(\d+(?:\.\d+)?)\s*(?:oz|ounce)/i);
    return match ? parseFloat(match[1]) : null;
}
```

### Twilio (SMS)

Used for customer communication.

**Endpoints:**
- `POST /frontdesk/texting/send/` - Send SMS
- `POST /frontdesk/sms/webhook/` - Receive inbound SMS

---

## API Reference

**Base URL:** `https://agent.opentruthai.com/frontdesk`

**Authentication:** All endpoints require login (session-based) except webhooks.

**CSRF:** All POST/PUT/DELETE requests require `X-CSRFToken` header.

---

### Appointments API

#### List Appointments
```
GET /appointments/api/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | ISO datetime | Filter appointments after this date |
| `end` | ISO datetime | Filter appointments before this date |

**Response:**
```json
[
    {
        "id": 123,
        "title": "John Smith - Selling Gold",
        "start": "2026-02-10T14:00:00-08:00",
        "end": "2026-02-10T14:30:00-08:00",
        "color": "#0d6efd",
        "extendedProps": {
            "customer_id": 45,
            "customer_name": "John Smith",
            "phone": "(555) 123-4567",
            "action": "SELLING",
            "metal": "GOLD",
            "metal_form": "COIN",
            "purpose": "Selling Gold",
            "location": "J. Austin",
            "status": "SCHEDULED",
            "notes": "",
            "duration_minutes": 30,
            "inventory_need_id": 12,
            "quantity": 2.5
        }
    }
]
```

**Status Color Map:**
| Status | Color |
|--------|-------|
| SCHEDULED | `#0d6efd` (blue) |
| CONFIRMED | `#198754` (green) |
| COMPLETED | `#6c757d` (gray) |
| CANCELED | `#dc3545` (red) |
| NO_SHOW | `#ffc107` (yellow) |

---

#### Create Appointment
```
POST /appointments/create/
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer` | integer | No | Existing customer ID |
| `customer_name` | string | No | Name for new customer (if no customer ID) |
| `phone` | string | No | Customer phone number |
| `action` | string | No | `BUYING` or `SELLING` (updates customer) |
| `metal` | string | No | `GOLD`, `SILVER`, `PLATINUM`, `PALLADIUM` |
| `metal_form` | string | No | `COIN`, `BAR`, `SCRAP`, `ROUND` |
| `iso_datetime` | ISO datetime | Yes* | Appointment start time (UTC) |
| `appt_date` | date | Yes* | Date (if not using iso_datetime) |
| `appt_time` | time | Yes* | Time (if not using iso_datetime) |
| `iso_end_datetime` | ISO datetime | No | End time (defaults to start + duration) |
| `duration` | integer | No | Duration in minutes (default: 30) |
| `purpose` | string | Yes | Appointment purpose/description |
| `inventory_need_id` | integer | No | Link to inventory need for matching |
| `quantity` | decimal | No | Quantity in oz for this appointment |

*Either `iso_datetime` OR (`appt_date` + `appt_time`) required

**Success Response (201):**
```json
{
    "status": "created",
    "id": 123,
    "title": "John Smith - Selling Gold"
}
```

**Error Response (400):**
```json
{
    "errors": {
        "customer": ["Select or type a customer name."],
        "form": ["Purpose is required."],
        "datetime": ["Invalid date or time."]
    }
}
```

---

#### Update Appointment
```
PUT /appointments/api/?id=123
Content-Type: application/json
```

**Request Body:**
```json
{
    "datetime": "2026-02-10T15:00:00Z",
    "end_datetime": "2026-02-10T15:30:00Z",
    "purpose": "Updated purpose",
    "status": "CONFIRMED",
    "notes": "Customer confirmed via phone"
}
```

**Response:**
```json
{
    "status": "updated",
    "id": 123
}
```

---

#### Delete Appointment
```
DELETE /appointments/api/?id=123
```

**Response:**
```json
{
    "status": "deleted",
    "id": 123
}
```

---

### Customers API

#### List/Search Customers
```
GET /customers/api/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search by name or phone |
| `action` | string | Filter by `BUYING` or `SELLING` |
| `metal` | string | Filter by metal type |

**Response:**
```json
[
    {
        "id": 45,
        "name": "John Smith",
        "phone": "(555) 123-4567",
        "email": "john@example.com",
        "action": "SELLING",
        "metal": "GOLD",
        "metal_form": "COIN",
        "source": "PHONE",
        "status": "ACTIVE",
        "created_at": "2026-01-15T10:30:00Z"
    }
]
```

---

#### Create Customer
```
POST /customers/api/
Content-Type: application/json
```

**Request Body:**
```json
{
    "name": "Jane Doe",
    "phone": "(555) 987-6543",
    "email": "jane@example.com",
    "action": "BUYING",
    "metal": "SILVER",
    "metal_form": "BAR",
    "source": "WEB",
    "notes": "Interested in 100oz bars"
}
```

**Response:**
```json
{
    "status": "created",
    "id": 46
}
```

---

#### Customer Search (Autocomplete)
```
GET /api/customers/search/?q=john
```

**Response:**
```json
[
    {"id": 45, "name": "John Smith", "phone": "(555) 123-4567"},
    {"id": 52, "name": "Johnny Appleseed", "phone": "(555) 222-3333"}
]
```

---

### Inventory API

#### List Inventory Needs
```
GET /inventory/api/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `OPEN`, `PARTIAL`, `FILLED` |
| `action` | string | `BUY` or `SELL` |
| `metal` | string | Metal type filter |

**Response:**
```json
[
    {
        "id": 12,
        "customer_id": 45,
        "customer_name": "John Smith",
        "action": "SELL",
        "product": "American Eagle",
        "size": "1 oz",
        "metal": "GOLD",
        "quantity_needed": 5.0,
        "quantity_fulfilled": 2.0,
        "quantity_pending": 1.0,
        "quantity_remaining": 2.0,
        "status": "PARTIAL",
        "created_at": "2026-02-01T09:00:00Z"
    }
]
```

---

#### Create Inventory Need
```
POST /inventory/api/
Content-Type: application/json
```

**Request Body:**
```json
{
    "customer_id": 45,
    "action": "SELL",
    "product": "American Eagle",
    "size": "1 oz",
    "metal": "GOLD",
    "quantity_needed": 5.0,
    "notes": "Customer has 5 coins to sell"
}
```

---

#### Get Inventory for Appointment Form
```
GET /inventory/for-appointment/
```

Returns inventory needs filtered for appointment dropdown.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `customer_action` | string | `BUYING` or `SELLING` |
| `metal` | string | Metal type filter |

**Response:**
```json
[
    {
        "id": 12,
        "label": "SELL 5x American Eagle 1 oz (Gold) - John Smith",
        "customer_id": 45,
        "action": "SELL",
        "product": "American Eagle",
        "quantity_remaining": 2.0
    }
]
```

---

### Products/Spread API

#### List Products
```
GET /spread/api/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `metal` | string | Filter by metal type |
| `active` | boolean | Filter by active status |

**Response:**
```json
[
    {
        "id": 1,
        "name": "American Eagle",
        "metal": "GOLD",
        "metal_display": "Gold",
        "size": "1 oz",
        "buy_premium": 50.00,
        "sell_premium": 80.00,
        "is_active": true
    },
    {
        "id": 2,
        "name": "American Eagle",
        "metal": "GOLD",
        "metal_display": "Gold",
        "size": "1/2 oz",
        "buy_premium": 30.00,
        "sell_premium": 50.00,
        "is_active": true
    }
]
```

---

#### Create Product
```
POST /spread/api/
Content-Type: application/json
```

**Request Body:**
```json
{
    "name": "Maple Leaf",
    "metal": "GOLD",
    "size": "1 oz",
    "buy_premium": 45.00,
    "sell_premium": 75.00
}
```

---

#### Update Product
```
PUT /spread/api/
Content-Type: application/json
```

**Request Body:**
```json
{
    "id": 1,
    "buy_premium": 55.00,
    "sell_premium": 85.00
}
```

---

#### Delete Product
```
DELETE /spread/api/?id=1
```

---

### Matching API

#### Generate Matches
```
POST /matching/generate/
```

Runs the matching algorithm to find buyer-seller pairs.

**Response:**
```json
{
    "status": "success",
    "matches_created": 3,
    "matches": [
        {
            "id": 1,
            "buyer": "Jane Doe",
            "seller": "John Smith",
            "product": "American Eagle",
            "size": "1 oz",
            "metal": "GOLD",
            "quantity": 2.0,
            "score": 0.95
        }
    ]
}
```

---

#### Manual Match
```
POST /matching/manual/
Content-Type: application/json
```

**Request Body:**
```json
{
    "buyer_need_id": 15,
    "seller_need_id": 12,
    "quantity": 2.0
}
```

---

#### Update Match Status
```
POST /matching/<match_id>/<action>/
```

**Actions:**
| Action | Description |
|--------|-------------|
| `contact` | Mark as contacted |
| `confirm` | Mark as confirmed |
| `complete` | Mark as completed |
| `reject` | Mark as rejected |

---

### Texting API

#### Send SMS
```
POST /texting/send/
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | integer | Customer to send to |
| `message` | string | Message text |
| `template_id` | integer | Optional template ID |

---

#### SMS Templates
```
GET /texting/templates/api/
```

**Response:**
```json
[
    {
        "id": 1,
        "name": "Appointment Reminder",
        "content": "Hi {name}, reminder about your appointment on {date} at {time}.",
        "variables": ["name", "date", "time"]
    }
]
```

---

### External Webhook API

#### MyAIFrontDesk Appointment Webhook
```
POST /api/webhook/external
Content-Type: application/json
```

**No authentication required** (configured in nginx)

**MyAIFrontDesk Format:**
```json
{
    "call_id": "call-abc123",
    "caller_name": "David Johnson",
    "caller_number": "+15551234567",
    "appointment_time": "2026-02-15T14:00:00",
    "reason": "Selling 2 oz Gold Eagles",
    "transcript": "Full call transcript...",
    "status": "scheduled"
}
```

**Standard Format:**
```json
{
    "event": "appointment.created",
    "data": {
        "id": "ext-123",
        "customerName": "David Johnson",
        "customerPhone": "(555) 123-4567",
        "startTime": "2026-02-15T14:00:00",
        "endTime": "2026-02-15T14:30:00",
        "purpose": "Selling Gold Eagles",
        "action": "sell",
        "metal": "gold",
        "quantity": 2.0
    }
}
```

**Response:**
```json
{
    "received": true,
    "synced": true,
    "results": {
        "frontdesk": {
            "created": true,
            "id": 456
        },
        "google": {
            "success": true,
            "googleEventId": "google-event-xyz",
            "filteredTitle": "David 67"
        }
    }
}
```

**Auto-Detected Fields:**
The webhook automatically parses the `reason`/`purpose` text to extract:
- `action`: "sell"/"buy" (from "selling", "buying", "purchase", etc.)
- `metal`: "gold"/"silver"/"platinum"/"palladium"
- `quantity`: Numeric value + "oz" or "ounce"

Example: `"Selling 2 oz Gold Eagles"` → `action=sell, metal=gold, quantity=2`

---

### Dashboard Stats API

```
GET /api/dashboard/stats/
```

**Response:**
```json
{
    "total_customers": 150,
    "active_customers": 120,
    "appointments_today": 8,
    "appointments_week": 35,
    "open_inventory_needs": 12,
    "pending_matches": 5,
    "recent_activity": [
        {"type": "appointment", "description": "John Smith - Scheduled", "time": "2 hours ago"},
        {"type": "match", "description": "Match created: Jane ↔ John", "time": "3 hours ago"}
    ]
}
```

---

### High Command API (Status Check)

```
GET /api/highcommand/
```

Simple health check endpoint polled by frontend.

**Response:**
```json
{
    "status": "ok",
    "timestamp": "2026-02-05T12:00:00Z"
}
```

---

### Day Notes API

#### Get/Create Notes
```
GET /notes/api/?start=2026-02-05&end=2026-02-06
```

**Response:**
```json
[
    {
        "id": 1,
        "date": "2026-02-05",
        "content": "Expecting busy day - gold prices up",
        "created_by": "admin"
    }
]
```

```
POST /notes/api/
Content-Type: application/json
```

**Request Body:**
```json
{
    "date": "2026-02-05",
    "content": "Reminder: Check inventory levels"
}
```

---

## Webhooks

### Calendar Sync Webhooks

Located in `/home/user/AgentGPT/calendar-sync/src/routes/webhooks.js`

| Endpoint | Purpose |
|----------|---------|
| `POST /api/webhook/frontdesk` | Receive Front Desk changes |
| `POST /api/webhook/google` | Receive Google Calendar changes |
| `POST /api/webhook/external` | Receive MyAIFrontDesk appointments |

### External Webhook Response

```json
{
    "received": true,
    "synced": true,
    "results": {
        "frontdesk": { "created": true, "id": 123 },
        "google": { "success": true, "googleEventId": "abc123" }
    }
}
```

---

## Frontend Templates

### Key Templates

| Template | Path | Purpose |
|----------|------|---------|
| `calendar.html` | `/templates/calendar.html` | Main calendar view |
| `matching.html` | `/templates/matching.html` | Buyer/seller matching |
| `inventory.html` | `/templates/inventory.html` | Inventory needs management |
| `spread.html` | `/templates/spread.html` | Product pricing |
| `customers.html` | `/templates/customers.html` | Customer list |

### JavaScript Patterns

**Saving Appointments:**
```javascript
function saveAppointment() {
    const data = new FormData();
    data.append('customer', document.getElementById('apptCustomer').value);
    data.append('customer_name', document.getElementById('apptCustomerName').value);
    data.append('phone', document.getElementById('apptPhone').value);
    data.append('action', selectedAction);
    data.append('metal', selectedMetal);
    data.append('iso_datetime', selectedDateTime.toISOString());
    data.append('purpose', document.getElementById('apptPurpose').value);
    data.append('inventory_need_id', document.getElementById('apptInventoryNeed').value);
    data.append('quantity', document.getElementById('apptQuantity').value);

    fetch('/frontdesk/appointments/create/', {
        method: 'POST',
        body: data,
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'created') {
            calendar.refetchEvents();
            closeModal();
        }
    });
}
```

---

## Common Operations

### Adding a New Product

```bash
docker exec frontdesk-web python manage.py shell
```

```python
from core.models import Product
Product.objects.create(
    name="American Eagle",
    metal="GOLD",
    size="1 oz",
    buy_premium=50.00,
    sell_premium=80.00
)
```

### Viewing Recent Appointments

```bash
docker exec frontdesk-web python manage.py shell
```

```python
from core.models import Appointment
from datetime import datetime, timedelta

today = datetime.now()
week_ago = today - timedelta(days=7)

appointments = Appointment.objects.filter(
    datetime__gte=week_ago
).select_related('customer').order_by('-datetime')

for a in appointments[:10]:
    print(f"{a.datetime}: {a.customer.name} - {a.purpose}")
```

### Checking Sync Status

```bash
# Calendar sync logs
cd /home/user/AgentGPT/calendar-sync
cat data/sync.db  # SQLite database

# Or use sqlite3
sqlite3 data/sync.db "SELECT * FROM event_mappings ORDER BY created_at DESC LIMIT 10;"
sqlite3 data/sync.db "SELECT * FROM sync_log ORDER BY created_at DESC LIMIT 10;"
```

### Restarting Services

```bash
# Restart Django container
docker restart frontdesk-web

# Restart calendar-sync (if running as service)
cd /home/user/AgentGPT/calendar-sync
pm2 restart calendar-sync  # or systemctl restart calendar-sync
```

### Database Migrations

```bash
# Make migrations
docker exec frontdesk-web python manage.py makemigrations

# Apply migrations
docker exec frontdesk-web python manage.py migrate

# Check migration status
docker exec frontdesk-web python manage.py showmigrations
```

---

## Troubleshooting

### 500 Error on Appointment Create

1. Check quantity field - must be numeric (not "1.5 oz", just "1.5")
2. Check customer exists or name is provided
3. Check datetime format is valid ISO

```bash
docker logs frontdesk-web --tail 100 | grep -i error
```

### Calendar Not Syncing

1. Check Google auth status
2. Check calendar-sync service is running
3. Check webhook URL is accessible

```bash
# Test webhook endpoint
curl -X POST https://agent.opentruthai.com/frontdesk/api/external-appointment/ \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Appointments Not Showing

1. Check date range in calendar view
2. Check appointment status (canceled won't show by default)
3. Check customer relationship exists

---

## Security Notes

1. **CSRF Protection** - All forms require CSRF token
2. **Authentication** - All views require login except webhooks
3. **Webhook Auth** - External webhooks bypass auth (controlled by nginx)
4. **Privacy Filtering** - Google Calendar only shows "FirstName XX"

---

## Future Enhancements (Planned)

1. **Real-time pricing** - Integrate live spot prices from Fortune Reserve
2. **SMS confirmations** - Auto-send appointment reminders
3. **Matching notifications** - Alert staff when good matches found
4. **Mobile app** - React Native app for field operations
5. **Reporting** - Sales/inventory analytics dashboard

---

## Contact

For questions about this system, contact the development team or refer to the GitHub repository issues.

**Repository:** `github.com/Markproto/AgentGPT`
**Branch:** `claude/review-front-desk-project-TXZA7`
