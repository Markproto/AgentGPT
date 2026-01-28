"""
Additional API views for J. Austin Front Desk Processing.
These provide supplementary JSON endpoints for AJAX operations.
"""

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q

from .models import Customer, Match, Appointment, Interaction, CallLog


@login_required
def dashboard_stats_api(request):
    """Return dashboard statistics as JSON for dynamic updates."""
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "total_customers": Customer.objects.count(),
        "pending_matches": Match.objects.filter(status=Match.Status.PROPOSED).count(),
        "active_matches": Match.objects.filter(status=Match.Status.ACCEPTED).count(),
        "todays_appointments": Appointment.objects.filter(
            datetime__gte=today_start,
            datetime__lt=today_start + timedelta(days=1),
        ).count(),
        "recent_interactions_count": Interaction.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).count(),
    }

    # Volume by bullion type
    for bt_value, bt_label in Customer.BullionType.choices:
        buy_vol = (
            Customer.objects.filter(
                category=Customer.Category.BUY_BULLION,
                bullion_type=bt_value,
            ).aggregate(total=Sum("bullion_amount"))["total"]
            or 0
        )
        sell_vol = (
            Customer.objects.filter(
                category=Customer.Category.SELL_BULLION,
                bullion_type=bt_value,
            ).aggregate(total=Sum("bullion_amount"))["total"]
            or 0
        )
        stats[f"buy_{bt_label.lower()}_volume"] = float(buy_vol)
        stats[f"sell_{bt_label.lower()}_volume"] = float(sell_vol)

    return JsonResponse(stats)


@login_required
def customer_search_api(request):
    """Search customers by name, phone, or email."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    customers = Customer.objects.filter(
        Q(name__icontains=query)
        | Q(phone__icontains=query)
        | Q(email__icontains=query)
    )[:20]

    results = [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "category": c.get_category_display(),
            "status": c.status,
        }
        for c in customers
    ]

    return JsonResponse({"results": results})


@login_required
@require_POST
def interaction_create_api(request):
    """Create a new interaction record."""
    try:
        body = json.loads(request.body)
        customer_id = body.get("customer_id")
        customer = get_object_or_404(Customer, pk=customer_id)

        interaction = Interaction.objects.create(
            customer=customer,
            type=body.get("type", "CALL"),
            direction=body.get("direction", "OUTBOUND"),
            summary=body.get("summary", ""),
            raw_data=body.get("raw_data"),
        )

        return JsonResponse(
            {
                "status": "created",
                "id": interaction.id,
                "created_at": interaction.created_at.isoformat(),
            },
            status=201,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
