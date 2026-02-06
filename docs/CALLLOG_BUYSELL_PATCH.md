# Call Log Buy/Sell Detection - Implementation Guide

This patch adds buy/sell action detection to the call log page at `/frontdesk/calls/`.

## Overview

The call log will detect and display:
- **Action**: Buy or Sell intent from customer
- **Metal**: Gold, Silver, Platinum, or Palladium
- **Quantity**: Amount in ounces

---

## Step 1: Update CallLog Model

Add these fields to `/app/core/models.py` in the `CallLog` class:

```python
class CallLog(models.Model):
    # ... existing fields ...
    customer = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    direction = models.CharField(max_length=20, default='inbound')
    duration = models.IntegerField(default=0)
    transcript = models.TextField(blank=True)
    category_detected = models.CharField(max_length=50, blank=True)
    frontdesk_ai_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW FIELDS - Add these
    action_detected = models.CharField(max_length=20, blank=True, help_text="buy or sell")
    metal_detected = models.CharField(max_length=20, blank=True, help_text="gold, silver, platinum, palladium")
    quantity_detected = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount in oz")
```

---

## Step 2: Add Detection Functions

Add these helper functions to `/app/core/views.py` (or create `/app/core/detection.py`):

```python
import re

def detect_action_from_text(text):
    """
    Detect buy/sell action from text (transcript, purpose, etc.)
    Returns 'buy', 'sell', or None
    """
    if not text:
        return None
    lower = text.lower()

    # Check for sell indicators first (customer selling to us)
    if 'sell' in lower or 'selling' in lower or 'liquidat' in lower:
        return 'sell'
    # Check for buy indicators (customer buying from us)
    if 'buy' in lower or 'buying' in lower or 'purchas' in lower:
        return 'buy'
    return None


def detect_metal_from_text(text):
    """
    Detect metal type from text.
    Returns 'gold', 'silver', 'platinum', 'palladium', or None
    """
    if not text:
        return None
    lower = text.lower()

    if 'gold' in lower or 'au ' in lower:
        return 'gold'
    if 'silver' in lower or 'ag ' in lower:
        return 'silver'
    if 'platinum' in lower or 'pt ' in lower:
        return 'platinum'
    if 'palladium' in lower or 'pd ' in lower:
        return 'palladium'
    return None


def detect_quantity_from_text(text):
    """
    Detect quantity (oz) from text.
    Returns quantity as float or None
    """
    if not text:
        return None

    # Look for patterns like "2 oz", "10 ounce", "5oz", "1/2 oz"
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)',  # 2 oz, 10.5 ounce
        r'(\d+)\s*/\s*(\d+)\s*(?:oz|ounce)',  # 1/2 oz
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex == 2:
                # Fraction like 1/2
                return float(match.group(1)) / float(match.group(2))
            return float(match.group(1))
    return None
```

---

## Step 3: Update Call Webhook

Update the call webhook view in `/app/core/views.py` or `/app/core/api_views.py`:

```python
@csrf_exempt
def call_webhook(request):
    """Handle incoming call webhook from MyAIFrontDesk"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)

        transcript = data.get('transcript', '') or data.get('call_summary', '') or ''

        # Detect buy/sell from transcript
        action = detect_action_from_text(transcript)
        metal = detect_metal_from_text(transcript)
        quantity = detect_quantity_from_text(transcript)

        call_log = CallLog.objects.create(
            customer=data.get('caller_name', '') or data.get('name', ''),
            phone_number=data.get('caller_number', '') or data.get('phone', ''),
            direction=data.get('direction', 'inbound'),
            duration=data.get('duration', 0),
            transcript=transcript,
            category_detected=data.get('category', ''),
            frontdesk_ai_id=data.get('call_id', ''),
            # NEW: Set detected fields
            action_detected=action or '',
            metal_detected=metal or '',
            quantity_detected=quantity,
        )

        return JsonResponse({'success': True, 'id': call_log.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

## Step 4: Update Call Log Template

Update `/app/templates/call_log.html`:

```html
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="container-fluid mt-4">
    <h2>Call Log</h2>

    <div class="table-responsive">
        <table class="table table-striped table-hover">
            <thead class="table-dark">
                <tr>
                    <th>Date</th>
                    <th>Phone</th>
                    <th>Customer</th>
                    <th>Direction</th>
                    <th>Duration</th>
                    <th>Action</th>
                    <th>Metal</th>
                    <th>Qty (oz)</th>
                    <th>Category</th>
                    <th>Transcript</th>
                </tr>
            </thead>
            <tbody>
                {% for call in calls %}
                <tr>
                    <td>{{ call.created_at|date:"M d, Y H:i" }}</td>
                    <td>{{ call.phone_number }}</td>
                    <td>{{ call.customer }}</td>
                    <td>
                        {% if call.direction == 'inbound' %}
                            <span class="badge bg-info">Inbound</span>
                        {% else %}
                            <span class="badge bg-secondary">Outbound</span>
                        {% endif %}
                    </td>
                    <td>{{ call.duration }}s</td>
                    <td>
                        {% if call.action_detected == 'buy' %}
                            <span class="badge bg-success">BUY</span>
                        {% elif call.action_detected == 'sell' %}
                            <span class="badge bg-warning text-dark">SELL</span>
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if call.metal_detected %}
                            <span class="badge bg-secondary">{{ call.metal_detected|title }}</span>
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if call.quantity_detected %}
                            {{ call.quantity_detected }}
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                    <td>{{ call.category_detected|default:"-" }}</td>
                    <td>
                        {% if call.transcript %}
                            <button class="btn btn-sm btn-outline-secondary"
                                    data-bs-toggle="modal"
                                    data-bs-target="#transcriptModal{{ call.id }}">
                                View
                            </button>
                            <!-- Modal -->
                            <div class="modal fade" id="transcriptModal{{ call.id }}" tabindex="-1">
                                <div class="modal-dialog modal-lg">
                                    <div class="modal-content">
                                        <div class="modal-header">
                                            <h5 class="modal-title">Call Transcript - {{ call.created_at|date:"M d, Y H:i" }}</h5>
                                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                        </div>
                                        <div class="modal-body">
                                            <p><strong>Customer:</strong> {{ call.customer }}</p>
                                            <p><strong>Phone:</strong> {{ call.phone_number }}</p>
                                            <hr>
                                            <pre style="white-space: pre-wrap;">{{ call.transcript }}</pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {% else %}
                            <span class="text-muted">-</span>
                        {% endif %}
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="10" class="text-center text-muted">No call logs found</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

---

## Step 5: Apply Changes via Docker

Run these commands on your server:

```bash
# 1. Copy files to container (run from directory with modified files)
docker cp models.py frontdesk-web:/app/core/models.py
docker cp views.py frontdesk-web:/app/core/views.py
docker cp call_log.html frontdesk-web:/app/templates/call_log.html

# 2. Create and apply migration
docker exec frontdesk-web python manage.py makemigrations core
docker exec frontdesk-web python manage.py migrate

# 3. Restart the container
docker restart frontdesk-web

# 4. Verify changes
docker logs frontdesk-web --tail 20
```

---

## Step 6: Backfill Existing Calls (Optional)

To detect buy/sell from existing transcripts, run in Django shell:

```bash
docker exec -it frontdesk-web python manage.py shell
```

```python
from core.models import CallLog
import re

def detect_action_from_text(text):
    if not text:
        return None
    lower = text.lower()
    if 'sell' in lower or 'selling' in lower or 'liquidat' in lower:
        return 'sell'
    if 'buy' in lower or 'buying' in lower or 'purchas' in lower:
        return 'buy'
    return None

def detect_metal_from_text(text):
    if not text:
        return None
    lower = text.lower()
    if 'gold' in lower:
        return 'gold'
    if 'silver' in lower:
        return 'silver'
    if 'platinum' in lower:
        return 'platinum'
    if 'palladium' in lower:
        return 'palladium'
    return None

def detect_quantity_from_text(text):
    if not text:
        return None
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

# Backfill all existing calls
for call in CallLog.objects.all():
    updated = False
    if call.transcript:
        action = detect_action_from_text(call.transcript)
        metal = detect_metal_from_text(call.transcript)
        quantity = detect_quantity_from_text(call.transcript)

        if action and not call.action_detected:
            call.action_detected = action
            updated = True
        if metal and not call.metal_detected:
            call.metal_detected = metal
            updated = True
        if quantity and not call.quantity_detected:
            call.quantity_detected = quantity
            updated = True

        if updated:
            call.save()
            print(f"Updated call {call.id}: action={action}, metal={metal}, qty={quantity}")

print("Done!")
```

---

## Testing

After applying changes:

1. Visit https://agent.opentruthai.com/frontdesk/calls/
2. You should see new columns: Action, Metal, Qty
3. Test the webhook by sending a test call:

```bash
curl -X POST https://agent.opentruthai.com/frontdesk/api/call-webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "caller_name": "Test Customer",
    "caller_number": "+15551234567",
    "direction": "inbound",
    "duration": 120,
    "transcript": "Hi, I am looking to sell 10 oz of gold",
    "category": "metals"
  }'
```

Expected result: New call log entry with:
- Action: SELL (badge)
- Metal: Gold (badge)
- Qty: 10
