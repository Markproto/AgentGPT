"""
Views for J. Austin Front Desk Processing.
"""

import csv
import io
import json
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, Q, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods

from .forms import CustomerForm, AppointmentForm, TextTemplateForm, SendTextForm, LoginForm
from .models import Customer, Interaction, TextTemplate, Match, Appointment, CallLog, DayNote, InventoryNeed, Product, HighCommandMessage, ProductToggle
from .services import fetch_metal_prices

logger = logging.getLogger(__name__)


# ============================================================================
# Authentication Views
# ============================================================================


def login_view(request):
    """Custom login view."""
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next", "/")
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout_view(request):
    """Logout and redirect to login."""
    logout(request)
    return redirect("/login/")


# ============================================================================
# Dashboard
# ============================================================================


@login_required
def dashboard(request):
    """Main dashboard with stats and recent activity."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    total_customers = Customer.objects.count()
    pending_matches = Match.objects.filter(status=Match.Status.PROPOSED).count()
    todays_appointments = Appointment.objects.filter(
        datetime__gte=today_start,
        datetime__lt=today_end,
    ).count()
    recent_interactions = Interaction.objects.select_related("customer")[:10]

    # Volume stats for dashboard chart
    buy_gold = (
        Customer.objects.filter(
            category=Customer.Category.BUY_BULLION,
            bullion_type=Customer.BullionType.GOLD,
        ).aggregate(total=Sum("bullion_amount"))["total"]
        or 0
    )
    sell_gold = (
        Customer.objects.filter(
            category=Customer.Category.SELL_BULLION,
            bullion_type=Customer.BullionType.GOLD,
        ).aggregate(total=Sum("bullion_amount"))["total"]
        or 0
    )
    buy_silver = (
        Customer.objects.filter(
            category=Customer.Category.BUY_BULLION,
            bullion_type=Customer.BullionType.SILVER,
        ).aggregate(total=Sum("bullion_amount"))["total"]
        or 0
    )
    sell_silver = (
        Customer.objects.filter(
            category=Customer.Category.SELL_BULLION,
            bullion_type=Customer.BullionType.SILVER,
        ).aggregate(total=Sum("bullion_amount"))["total"]
        or 0
    )

    context = {
        "total_customers": total_customers,
        "pending_matches": pending_matches,
        "todays_appointments": todays_appointments,
        "recent_interactions": recent_interactions,
        "buy_gold": float(buy_gold),
        "sell_gold": float(sell_gold),
        "buy_silver": float(buy_silver),
        "sell_silver": float(sell_silver),
    }
    return render(request, "dashboard.html", context)


# ============================================================================
# Customer Views
# ============================================================================


@login_required
def customer_list(request):
    """Render the customer spreadsheet view with Handsontable."""
    categories = Customer.Category.choices
    statuses = Customer.Status.choices
    bullion_types = Customer.BullionType.choices
    sources = Customer.Source.choices
    actions = Customer.Action.choices
    metals = Customer.Metal.choices
    metal_forms = Customer.MetalForm.choices
    return render(
        request,
        "customers.html",
        {
            "categories": categories,
            "statuses": statuses,
            "bullion_types": bullion_types,
            "sources": sources,
            "actions": actions,
            "metals": metals,
            "metal_forms": metal_forms,
        },
    )


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def customer_api(request):
    """JSON API for customer CRUD operations (Handsontable integration)."""
    if request.method == "GET":
        customers = Customer.objects.all()
        filter_action = request.GET.get("action", "")
        filter_metal = request.GET.get("metal", "")
        filter_form = request.GET.get("metal_form", "")
        filter_category = request.GET.get("category", "")
        if filter_action:
            customers = customers.filter(action=filter_action)
        if filter_metal:
            customers = customers.filter(metal=filter_metal)
        if filter_form:
            customers = customers.filter(metal_form=filter_form)
        if filter_category:
            customers = customers.filter(category=filter_category)

        data = []
        for c in customers:
            last_interaction = c.interactions.first()
            data.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "email": c.email,
                    "action": c.action,
                    "metal": c.metal,
                    "metal_form": c.metal_form,
                    "bullion_amount": str(c.bullion_amount) if c.bullion_amount else "",
                    "price_per_oz": str(c.price_per_oz) if c.price_per_oz else "",
                    "status": c.status,
                    "source": c.source,
                    "notes": c.notes,
                    "last_contact": (
                        last_interaction.created_at.strftime("%Y-%m-%d %H:%M")
                        if last_interaction
                        else ""
                    ),
                    "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )
        return JsonResponse({"data": data}, safe=False)

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            customer = Customer.objects.create(
                name=body.get("name", "New Customer"),
                phone=body.get("phone", ""),
                email=body.get("email", ""),
                action=body.get("action", ""),
                metal=body.get("metal", ""),
                metal_form=body.get("metal_form", ""),
                bullion_amount=body.get("bullion_amount") or None,
                price_per_oz=body.get("price_per_oz") or None,
                status=body.get("status", Customer.Status.PENDING),
                source=body.get("source", Customer.Source.WALK_IN),
                notes=body.get("notes", ""),
            )
            return JsonResponse({"id": customer.id, "status": "created"}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "PUT":
        try:
            body = json.loads(request.body)
            customer_id = body.get("id")
            if not customer_id:
                return JsonResponse({"error": "id required"}, status=400)

            customer = get_object_or_404(Customer, pk=customer_id)

            # Update fields
            for field in [
                "name",
                "phone",
                "email",
                "action",
                "metal",
                "metal_form",
                "category",
                "bullion_type",
                "status",
                "source",
                "notes",
            ]:
                if field in body:
                    setattr(customer, field, body[field])

            if "bullion_amount" in body:
                val = body["bullion_amount"]
                customer.bullion_amount = Decimal(val) if val else None

            if "price_per_oz" in body:
                val = body["price_per_oz"]
                customer.price_per_oz = Decimal(val) if val else None

            customer.save()
            return JsonResponse({"status": "updated"})
        except (InvalidOperation, ValueError) as e:
            return JsonResponse({"error": f"Invalid number: {e}"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            body = json.loads(request.body)
            customer_id = body.get("id")
            if not customer_id:
                return JsonResponse({"error": "id required"}, status=400)
            customer = get_object_or_404(Customer, pk=customer_id)
            customer.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
def customer_detail(request, pk):
    """Customer detail view with interactions and history."""
    customer = get_object_or_404(Customer, pk=pk)
    interactions = customer.interactions.all()[:20]
    appointments = customer.appointments.all()[:10]
    matches_as_buyer = customer.matches_as_buyer.all()[:10]
    matches_as_seller = customer.matches_as_seller.all()[:10]
    call_logs = customer.call_logs.all()[:10]

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect("customer_detail", pk=pk)
    else:
        form = CustomerForm(instance=customer)

    context = {
        "customer": customer,
        "form": form,
        "interactions": interactions,
        "appointments": appointments,
        "matches_as_buyer": matches_as_buyer,
        "matches_as_seller": matches_as_seller,
        "call_logs": call_logs,
    }
    return render(request, "customer_detail.html", context)


# ============================================================================
# Matching Views
# ============================================================================


@login_required
def matching_view(request):
    """Display matching interface with balance sheet."""
    proposed_matches = Match.objects.filter(status=Match.Status.PROPOSED).select_related(
        "buyer", "seller"
    )
    accepted_matches = Match.objects.filter(status=Match.Status.ACCEPTED).select_related(
        "buyer", "seller"
    )
    completed_matches = Match.objects.filter(status=Match.Status.COMPLETED).select_related(
        "buyer", "seller"
    )

    # Balance sheet calculations
    balance = {}
    for bt_value, bt_label in Customer.BullionType.choices:
        buy_total = (
            Customer.objects.filter(
                category=Customer.Category.BUY_BULLION,
                bullion_type=bt_value,
                status__in=[Customer.Status.PENDING, Customer.Status.ACTIVE],
            ).aggregate(total=Sum("bullion_amount"))["total"]
            or Decimal("0")
        )
        sell_total = (
            Customer.objects.filter(
                category=Customer.Category.SELL_BULLION,
                bullion_type=bt_value,
                status__in=[Customer.Status.PENDING, Customer.Status.ACTIVE],
            ).aggregate(total=Sum("bullion_amount"))["total"]
            or Decimal("0")
        )
        balance[bt_label] = {
            "buy": buy_total,
            "sell": sell_total,
            "net": buy_total - sell_total,
        }

    context = {
        "proposed_matches": proposed_matches,
        "accepted_matches": accepted_matches,
        "completed_matches": completed_matches,
        "balance": balance,
        "customers": Customer.objects.all().order_by("name"),
        "bullion_types": Customer.BullionType.choices,
    }
    return render(request, "matching.html", context)


@login_required
@require_POST
def generate_matches(request):
    """Run matching algorithm to pair buyers with sellers."""
    matches_created = 0

    for bt_value, bt_label in Customer.BullionType.choices:
        buyers = list(
            Customer.objects.filter(
                category=Customer.Category.BUY_BULLION,
                bullion_type=bt_value,
                status__in=[Customer.Status.PENDING, Customer.Status.ACTIVE],
                bullion_amount__isnull=False,
            ).order_by("created_at")
        )

        sellers = list(
            Customer.objects.filter(
                category=Customer.Category.SELL_BULLION,
                bullion_type=bt_value,
                status__in=[Customer.Status.PENDING, Customer.Status.ACTIVE],
                bullion_amount__isnull=False,
            ).order_by("created_at")
        )

        # Skip existing matches
        existing_pairs = set(
            Match.objects.filter(
                status__in=[Match.Status.PROPOSED, Match.Status.ACCEPTED],
                bullion_type=bt_value,
            ).values_list("buyer_id", "seller_id")
        )

        for buyer in buyers:
            for seller in sellers:
                if (buyer.id, seller.id) in existing_pairs:
                    continue

                # Match on the minimum available amount
                match_amount = min(buyer.bullion_amount, seller.bullion_amount)
                if match_amount <= 0:
                    continue

                # Calculate profit margin if both have prices
                profit_margin = None
                if buyer.price_per_oz and seller.price_per_oz:
                    profit_margin = (buyer.price_per_oz - seller.price_per_oz) * match_amount

                Match.objects.create(
                    buyer=buyer,
                    seller=seller,
                    amount=match_amount,
                    bullion_type=bt_value,
                    status=Match.Status.PROPOSED,
                    profit_margin=profit_margin,
                )
                matches_created += 1
                existing_pairs.add((buyer.id, seller.id))

    return JsonResponse(
        {"status": "success", "matches_created": matches_created}
    )


@login_required
@require_POST
def match_action(request, pk, action):
    """Accept or cancel a match."""
    match = get_object_or_404(Match, pk=pk)

    if action == "accept":
        match.status = Match.Status.ACCEPTED
        match.buyer.status = Customer.Status.MATCHED
        match.seller.status = Customer.Status.MATCHED
        match.buyer.save()
        match.seller.save()
    elif action == "complete":
        match.status = Match.Status.COMPLETED
        match.buyer.status = Customer.Status.CLOSED
        match.seller.status = Customer.Status.CLOSED
        match.buyer.save()
        match.seller.save()
    elif action == "cancel":
        match.status = Match.Status.CANCELED
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)

    match.save()
    return JsonResponse({"status": "success", "new_status": match.status})


@login_required
@require_POST
def manual_match(request):
    """Create a manual match for consignment sales."""
    try:
        body = json.loads(request.body)

        # Get or create buyer (optional - use placeholder if not provided)
        buyer_id = body.get("buyer_id")
        buyer_name = body.get("buyer_name", "").strip()
        if buyer_id:
            buyer = get_object_or_404(Customer, pk=buyer_id)
        elif buyer_name:
            buyer, _ = Customer.objects.get_or_create(
                name__iexact=buyer_name,
                defaults={
                    "name": buyer_name,
                    "category": Customer.Category.BUY_BULLION,
                    "status": Customer.Status.CLOSED,
                },
            )
        else:
            # Create placeholder buyer
            buyer, _ = Customer.objects.get_or_create(
                name="Unknown Buyer",
                defaults={
                    "category": Customer.Category.BUY_BULLION,
                    "status": Customer.Status.CLOSED,
                },
            )

        # Get or create seller (optional - use placeholder if not provided)
        seller_id = body.get("seller_id")
        seller_name = body.get("seller_name", "").strip()
        if seller_id:
            seller = get_object_or_404(Customer, pk=seller_id)
        elif seller_name:
            seller, _ = Customer.objects.get_or_create(
                name__iexact=seller_name,
                defaults={
                    "name": seller_name,
                    "category": Customer.Category.SELL_BULLION,
                    "status": Customer.Status.CLOSED,
                },
            )
        else:
            # Create placeholder seller
            seller, _ = Customer.objects.get_or_create(
                name="Unknown Seller",
                defaults={
                    "category": Customer.Category.SELL_BULLION,
                    "status": Customer.Status.CLOSED,
                },
            )

        # Create the match (amount defaults to 1 if not provided)
        amount = Decimal(body.get("amount") or "1")

        bullion_type = body.get("bullion_type", "GOLD")
        product = body.get("product", "").strip()
        notes = body.get("notes", "").strip()

        match = Match.objects.create(
            buyer=buyer,
            seller=seller,
            amount=amount,
            bullion_type=bullion_type,
            status=Match.Status.COMPLETED,  # Manual matches go straight to completed
            profit_margin=body.get("profit_margin") or None,
            notes=f"{product}\n{notes}".strip() if product or notes else "",
        )

        # Mark both parties as closed since this is a completed transaction
        buyer.status = Customer.Status.CLOSED
        seller.status = Customer.Status.CLOSED
        buyer.save(update_fields=["status"])
        seller.save(update_fields=["status"])

        return JsonResponse({"status": "created", "id": match.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ============================================================================
# Appointment Views
# ============================================================================


@login_required
@ensure_csrf_cookie
def appointment_list(request):
    """Day planner / week view for appointments."""
    from datetime import date as date_type

    date_str = request.GET.get("date", "")
    if date_str:
        try:
            selected_date = date_type.fromisoformat(date_str)
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    customers = Customer.objects.all()

    context = {
        "customers": customers,
        "selected_date": selected_date,
        "statuses": Appointment.Status.choices,
    }
    return render(request, "appointments.html", context)


@login_required
def appointment_create(request):
    """Create a new appointment.

    Accepts either a customer ID (dropdown) or a typed customer_name.
    If customer_name is provided and doesn't match, a new customer is created.
    Supports duration_minutes (default 30) for split-slot 15-min appointments.
    """
    if request.method == "POST":
        customer = None
        customer_id = request.POST.get("customer", "").strip()
        customer_name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        action = request.POST.get("action", "").strip()
        metal = request.POST.get("metal", "").strip()
        metal_form = request.POST.get("metal_form", "").strip()

        # Try existing customer by ID first
        if customer_id:
            try:
                customer = Customer.objects.get(pk=int(customer_id))
            except (Customer.DoesNotExist, ValueError):
                pass

        # If no customer selected but name typed, find or create
        if not customer and customer_name:
            customer = Customer.objects.filter(name__iexact=customer_name).first()
            if not customer:
                customer = Customer.objects.create(
                    name=customer_name,
                    phone=phone,
                    action=action,
                    metal=metal,
                    metal_form=metal_form,
                    source=Customer.Source.WALK_IN,
                    status=Customer.Status.ACTIVE,
                )

        # Update phone on existing customer if provided and not already set
        if customer and phone and not customer.phone:
            customer.phone = phone
            customer.save(update_fields=["phone"])

        # Update category fields on existing customer if provided and not already set
        update_fields = []
        if customer and action and not customer.action:
            customer.action = action
            update_fields.append("action")
        if customer and metal and not customer.metal:
            customer.metal = metal
            update_fields.append("metal")
        if customer and metal_form and not customer.metal_form:
            customer.metal_form = metal_form
            update_fields.append("metal_form")
        if update_fields:
            customer.save(update_fields=update_fields)

        if not customer:
            return JsonResponse(
                {"errors": {"customer": ["Select or type a customer name."]}},
                status=400,
            )

        iso_datetime = request.POST.get("iso_datetime", "").strip()
        appt_date = request.POST.get("appt_date", "")
        appt_time = request.POST.get("appt_time", "")
        purpose = request.POST.get("purpose", "").strip()
        duration_minutes = int(request.POST.get("duration", "30") or "30")

        if not purpose:
            return JsonResponse(
                {"errors": {"form": ["Purpose is required."]}},
                status=400,
            )

        dt = None
        try:
            from dateutil.parser import parse as dt_parse
            if iso_datetime:
                # Calendar sends UTC ISO datetime — timezone-aware
                dt = dt_parse(iso_datetime)
            elif appt_date and appt_time:
                # Day planner sends local date + time — treat as server timezone
                naive = dt_parse(f"{appt_date} {appt_time}")
                dt = timezone.make_aware(naive, timezone.get_current_timezone())
            else:
                return JsonResponse(
                    {"errors": {"form": ["Date and time are required."]}},
                    status=400,
                )
        except Exception:
            return JsonResponse(
                {"errors": {"datetime": ["Invalid date or time."]}},
                status=400,
            )

        iso_end = request.POST.get("iso_end_datetime", "").strip()
        if iso_end:
            try:
                end_dt = dt_parse(iso_end)
            except Exception:
                end_dt = dt + timedelta(minutes=duration_minutes)
        else:
            end_dt = dt + timedelta(minutes=duration_minutes)

        # Handle inventory link
        inventory_need = None
        inventory_need_id = request.POST.get("inventory_need_id", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        if inventory_need_id:
            try:
                inventory_need = InventoryNeed.objects.get(pk=int(inventory_need_id))
            except (InventoryNeed.DoesNotExist, ValueError):
                pass

        appointment = Appointment.objects.create(
            customer=customer,
            datetime=dt,
            end_datetime=end_dt,
            purpose=purpose,
            location="J. Austin",
            inventory_need=inventory_need,
            quantity=Decimal(quantity) if quantity else None,
        )

        return JsonResponse(
            {
                "status": "created",
                "id": appointment.id,
                "title": f"{customer.name} - {purpose}",
            }
        )

    return JsonResponse({"error": "POST required"}, status=405)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def appointment_api(request):
    """JSON API for calendar events."""
    if request.method == "GET":
        start = request.GET.get("start", "")
        end = request.GET.get("end", "")

        appointments = Appointment.objects.select_related("customer").all()

        if start:
            appointments = appointments.filter(datetime__gte=start)
        if end:
            appointments = appointments.filter(datetime__lte=end)

        color_map = {
            "SCHEDULED": "#0d6efd",
            "CONFIRMED": "#198754",
            "COMPLETED": "#6c757d",
            "CANCELED": "#dc3545",
            "NO_SHOW": "#ffc107",
        }

        events = []
        for appt in appointments:
            end_dt = appt.end_datetime or (appt.datetime + timedelta(minutes=30))
            duration_min = int((end_dt - appt.datetime).total_seconds() / 60)
            events.append(
                {
                    "id": appt.id,
                    "title": f"{appt.customer.name} - {appt.purpose}",
                    "start": appt.datetime.isoformat(),
                    "end": end_dt.isoformat(),
                    "color": color_map.get(appt.status, "#0d6efd"),
                    "extendedProps": {
                        "customer_id": appt.customer.id,
                        "customer_name": appt.customer.name,
                        "phone": appt.customer.phone,
                        "action": appt.customer.action,
                        "metal": appt.customer.metal,
                        "metal_form": appt.customer.metal_form,
                        "purpose": appt.purpose,
                        "location": appt.location,
                        "status": appt.status,
                        "notes": appt.notes,
                        "duration_minutes": duration_min,
                        "inventory_need_id": appt.inventory_need_id,
                        "quantity": appt.quantity,
                    },
                }
            )

        return JsonResponse(events, safe=False)

    elif request.method == "PUT":
        try:
            body = json.loads(request.body)
            appt_id = body.get("id")
            appt = get_object_or_404(Appointment, pk=appt_id)

            if body.get("shorten_to_15"):
                # Split operation: shorten this appointment to 15 minutes
                appt.end_datetime = appt.datetime + timedelta(minutes=15)
                appt.save()
                return JsonResponse({"status": "updated"})

            if "datetime" in body:
                from dateutil.parser import parse

                appt.datetime = parse(body["datetime"])
            if "end_datetime" in body:
                from dateutil.parser import parse

                appt.end_datetime = parse(body["end_datetime"])
            if "status" in body:
                old_status = appt.status
                new_status = body["status"]
                appt.status = new_status
                # When marking COMPLETED, fulfill linked inventory need
                if new_status == "COMPLETED" and old_status != "COMPLETED":
                    if appt.inventory_need and appt.quantity:
                        inv = appt.inventory_need
                        inv.quantity_fulfilled = inv.quantity_fulfilled + appt.quantity
                        inv.save(update_fields=["quantity_fulfilled"])
                        inv.update_status()
            if "notes" in body:
                appt.notes = body["notes"]
            if "purpose" in body:
                appt.purpose = body["purpose"]
            if "location" in body:
                appt.location = body["location"]
            if "customer_name" in body:
                name = body["customer_name"].strip()
                if name:
                    cust = Customer.objects.filter(name__iexact=name).first()
                    if not cust:
                        cust = Customer.objects.create(
                            name=name,
                            source=Customer.Source.WALK_IN,
                            status=Customer.Status.ACTIVE,
                        )
                    appt.customer = cust

            appt.save()

            # Update customer fields (phone, categories)
            cust = appt.customer
            cust_fields = []
            if "phone" in body:
                phone = body["phone"].strip()
                if phone:
                    cust.phone = phone
                    cust_fields.append("phone")
            if "action" in body:
                cust.action = body["action"]
                cust_fields.append("action")
            if "metal" in body:
                cust.metal = body["metal"]
                cust_fields.append("metal")
            if "metal_form" in body:
                cust.metal_form = body["metal_form"]
                cust_fields.append("metal_form")
            if cust_fields:
                cust.save(update_fields=cust_fields)

            # Handle inventory link updates
            appt_fields = []
            if "inventory_need_id" in body:
                inv_id = body["inventory_need_id"]
                if inv_id:
                    try:
                        inv = InventoryNeed.objects.get(pk=int(inv_id))
                        appt.inventory_need = inv
                    except (InventoryNeed.DoesNotExist, ValueError):
                        appt.inventory_need = None
                else:
                    appt.inventory_need = None
                appt_fields.append("inventory_need")
            if "quantity" in body:
                qty = body["quantity"]
                appt.quantity = Decimal(qty) if qty else None
                appt_fields.append("quantity")
            if appt_fields:
                appt.save(update_fields=appt_fields)

            return JsonResponse({"status": "updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            body = json.loads(request.body)
            appt_id = body.get("id")
            appt = get_object_or_404(Appointment, pk=appt_id)
            appt.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def notes_api(request):
    """JSON API for day notes."""
    if request.method == "GET":
        start = request.GET.get("start", "")
        end = request.GET.get("end", "")
        notes = DayNote.objects.all()
        if start:
            notes = notes.filter(date__gte=start[:10])
        if end:
            notes = notes.filter(date__lte=end[:10])
        result = []
        for note in notes:
            result.append({
                "id": note.id,
                "date": note.date.isoformat(),
                "time": note.time.strftime("%H:%M") if note.time else None,
                "content": note.content,
            })
        return JsonResponse(result, safe=False)

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}
            body["date"] = request.POST.get("date", "")
            body["time"] = request.POST.get("time", "")
            body["content"] = request.POST.get("content", "")

        from datetime import date as date_cls, time as time_cls
        from dateutil.parser import parse as dt_parse

        date_str = body.get("date", "")
        time_str = body.get("time", "")
        content = body.get("content", "").strip()
        if not date_str or not content:
            return JsonResponse({"error": "Date and content are required."}, status=400)

        try:
            note_date = dt_parse(date_str).date()
        except Exception:
            return JsonResponse({"error": "Invalid date."}, status=400)

        note_time = None
        if time_str:
            try:
                note_time = dt_parse(time_str).time()
            except Exception:
                pass

        note = DayNote.objects.create(date=note_date, time=note_time, content=content)
        return JsonResponse({"status": "created", "id": note.id})

    elif request.method == "PUT":
        try:
            body = json.loads(request.body)
            note = get_object_or_404(DayNote, pk=body.get("id"))
            if "content" in body:
                note.content = body["content"]
            if "date" in body:
                from dateutil.parser import parse as dt_parse
                note.date = dt_parse(body["date"]).date()
            if "time" in body:
                if body["time"]:
                    from dateutil.parser import parse as dt_parse
                    note.time = dt_parse(body["time"]).time()
                else:
                    note.time = None
            note.save()
            return JsonResponse({"status": "updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            body = json.loads(request.body)
            note = get_object_or_404(DayNote, pk=body.get("id"))
            note.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
@ensure_csrf_cookie
def calendar_view(request):
    """Render FullCalendar interface."""
    customers = Customer.objects.all()
    return render(request, "calendar.html", {"customers": customers})


# ============================================================================
# Texting Views
# ============================================================================


@login_required
def texting_view(request):
    """Texting interface with customer selector and message composer."""
    customers = Customer.objects.all()
    templates = TextTemplate.objects.filter(is_active=True)
    recent_texts = Interaction.objects.filter(type=Interaction.Type.TEXT).select_related(
        "customer"
    )[:20]

    context = {
        "customers": customers,
        "templates": templates,
        "recent_texts": recent_texts,
        "actions": Customer.Action.choices,
        "metals": Customer.Metal.choices,
        "metal_forms": Customer.MetalForm.choices,
    }
    return render(request, "texting.html", context)


@login_required
@require_POST
def send_text(request):
    """Send a text message via SendGrid/Twilio."""
    try:
        body = json.loads(request.body)
        customer_ids = body.get("customer_ids", [])
        message = body.get("message", "")

        if not customer_ids or not message:
            return JsonResponse(
                {"error": "Customer IDs and message are required"}, status=400
            )

        customers = Customer.objects.filter(id__in=customer_ids)
        sent_count = 0
        errors = []

        for customer in customers:
            if not customer.phone and not customer.email:
                errors.append(f"{customer.name}: No phone or email on file")
                continue

            # Record the interaction
            Interaction.objects.create(
                customer=customer,
                type=Interaction.Type.TEXT,
                direction=Interaction.Direction.OUTBOUND,
                summary=message,
                raw_data={
                    "to": customer.phone or customer.email,
                    "message": message,
                    "sent_via": "sendgrid" if customer.email else "twilio",
                },
            )

            # Attempt to send via Twilio if phone is available
            if customer.phone and settings.TWILIO_ACCOUNT_SID:
                try:
                    from twilio.rest import Client

                    client = Client(
                        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
                    )
                    client.messages.create(
                        body=message,
                        from_=settings.TWILIO_PHONE,
                        to=customer.phone,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Twilio send failed for {customer.name}: {e}")
                    sent_count += 1  # Still count as sent since interaction was recorded

            # Attempt to send via SendGrid if email is available
            elif customer.email and settings.SENDGRID_API_KEY:
                try:
                    from sendgrid import SendGridAPIClient
                    from sendgrid.helpers.mail import Mail

                    sg_message = Mail(
                        from_email="frontdesk@jaustin.com",
                        to_emails=customer.email,
                        subject="Message from J. Austin",
                        plain_text_content=message,
                    )
                    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                    sg.send(sg_message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"SendGrid send failed for {customer.name}: {e}")
                    sent_count += 1  # Still count as sent since interaction was recorded
            else:
                sent_count += 1  # Count as sent (interaction recorded even without API)

        return JsonResponse(
            {
                "status": "success",
                "sent_count": sent_count,
                "errors": errors,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def template_manage(request):
    """Manage text templates."""
    templates = TextTemplate.objects.all()

    if request.method == "POST":
        action = request.POST.get("action", "create")

        if action == "create":
            form = TextTemplateForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("template_manage")
        elif action == "update":
            template_id = request.POST.get("template_id")
            template = get_object_or_404(TextTemplate, pk=template_id)
            form = TextTemplateForm(request.POST, instance=template)
            if form.is_valid():
                form.save()
                return redirect("template_manage")
        elif action == "delete":
            template_id = request.POST.get("template_id")
            template = get_object_or_404(TextTemplate, pk=template_id)
            template.delete()
            return redirect("template_manage")

    form = TextTemplateForm()
    context = {
        "templates": templates,
        "form": form,
        "categories": TextTemplate.Category.choices,
    }
    return render(request, "templates_manage.html", context)


@login_required
def template_api(request):
    """JSON API to get template content."""
    template_id = request.GET.get("id")
    if template_id:
        template = get_object_or_404(TextTemplate, pk=template_id)
        return JsonResponse({"content": template.content, "name": template.name})
    else:
        templates = TextTemplate.objects.filter(is_active=True).values(
            "id", "name", "content", "category"
        )
        return JsonResponse({"templates": list(templates)})


# ============================================================================
# Call Log Views
# ============================================================================


@login_required
def call_log_view(request):
    """Display call logs."""
    calls = CallLog.objects.select_related("customer").all()[:100]
    context = {"calls": calls}
    return render(request, "call_log.html", context)


@csrf_exempt
@require_POST
def call_webhook(request):
    """Webhook endpoint for Front Desk AI call data.

    Receives POST data from Front Desk AI after each call and creates
    a CallLog entry. Attempts to match the phone number to an existing customer.
    """
    try:
        body = json.loads(request.body)

        phone_number = body.get("phone_number", body.get("caller_id", ""))
        direction = body.get("direction", "INBOUND").upper()
        duration = body.get("duration", body.get("call_duration", None))
        transcript = body.get("transcript", body.get("summary", ""))
        category_detected = body.get("category", body.get("intent", ""))
        frontdesk_ai_id = body.get("id", body.get("call_id", ""))

        # Try to match phone number to existing customer
        customer = None
        if phone_number:
            # Clean phone number for matching
            clean_phone = phone_number.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
            customer = Customer.objects.filter(
                Q(phone__icontains=clean_phone[-10:]) if len(clean_phone) >= 10
                else Q(phone__icontains=phone_number)
            ).first()

        call_log = CallLog.objects.create(
            customer=customer,
            phone_number=phone_number,
            direction=direction if direction in ["INBOUND", "OUTBOUND"] else "INBOUND",
            duration=int(duration) if duration else None,
            transcript=transcript,
            category_detected=category_detected,
            frontdesk_ai_id=str(frontdesk_ai_id),
        )

        # Also create an Interaction record if customer is matched
        if customer:
            Interaction.objects.create(
                customer=customer,
                type=Interaction.Type.CALL,
                direction=(
                    Interaction.Direction.INBOUND
                    if direction == "INBOUND"
                    else Interaction.Direction.OUTBOUND
                ),
                summary=transcript[:500] if transcript else f"Call from {phone_number}",
                raw_data=body,
            )

        return JsonResponse(
            {"status": "received", "call_log_id": call_log.id}, status=201
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Call webhook error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def sync_calls(request):
    """Sync call logs from Front Desk AI API."""
    api_key = settings.FRONTDESK_AI_API_KEY
    if not api_key:
        return JsonResponse(
            {"error": "FRONTDESK_AI_API_KEY not configured"}, status=400
        )

    try:
        import requests

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.get(
            "https://api.frontdeskai.com/v1/calls",
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            return JsonResponse(
                {"error": f"API returned {response.status_code}"}, status=400
            )

        calls = response.json().get("calls", [])
        synced = 0

        for call_data in calls:
            ext_id = str(call_data.get("id", ""))
            if ext_id and CallLog.objects.filter(frontdesk_ai_id=ext_id).exists():
                continue

            phone = call_data.get("phone_number", "")
            customer = None
            if phone:
                clean = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
                customer = Customer.objects.filter(
                    Q(phone__icontains=clean[-10:]) if len(clean) >= 10
                    else Q(phone__icontains=phone)
                ).first()

            CallLog.objects.create(
                customer=customer,
                phone_number=phone,
                direction=call_data.get("direction", "INBOUND"),
                duration=call_data.get("duration"),
                transcript=call_data.get("transcript", ""),
                category_detected=call_data.get("category", ""),
                frontdesk_ai_id=ext_id,
            )
            synced += 1

        return JsonResponse({"status": "success", "synced": synced})

    except requests.RequestException as e:
        return JsonResponse({"error": f"API request failed: {e}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# CSV Import
# ============================================================================


@login_required
def csv_import_view(request):
    """Import customers/calls from a CSV file."""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        import_type = request.POST.get("import_type", "calls")

        if not csv_file:
            return render(request, "csv_import.html", {"error": "Please select a CSV file."})

        if not csv_file.name.endswith(".csv"):
            return render(request, "csv_import.html", {"error": "File must be a .csv file."})

        try:
            decoded = csv_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            headers = reader.fieldnames or []

            imported = 0
            skipped = 0
            errors = []

            if import_type == "calls":
                imported, skipped, errors = _import_calls_csv(reader, headers)
            elif import_type == "customers":
                imported, skipped, errors = _import_customers_csv(reader, headers)
            elif import_type == "texts":
                imported, skipped, errors = _import_texts_csv(reader, headers)

            return render(
                request,
                "csv_import.html",
                {
                    "success": True,
                    "imported": imported,
                    "skipped": skipped,
                    "errors": errors[:20],
                    "headers_found": headers,
                    "import_type": import_type,
                },
            )

        except Exception as e:
            return render(request, "csv_import.html", {"error": f"Error processing file: {e}"})

    return render(request, "csv_import.html")


def _import_calls_csv(reader, headers):
    """Import call log records from CSV."""
    imported = 0
    skipped = 0
    errors = []

    # Map common header names
    phone_fields = ["phone", "phone_number", "phonenumber", "caller_id", "from", "number", "phone number", "caller"]
    name_fields = ["name", "customer_name", "customer", "contact", "caller_name", "contact name"]
    date_fields = ["date", "datetime", "call_date", "created_at", "timestamp", "time", "call date"]
    duration_fields = ["duration", "call_duration", "length", "seconds"]
    direction_fields = ["direction", "type", "call_type"]
    summary_fields = ["summary", "transcript", "notes", "description", "content", "call summary"]
    category_fields = ["category", "intent", "reason", "call_reason", "purpose"]

    def find_header(field_names):
        for h in headers:
            if h.lower().strip() in field_names:
                return h
        return None

    phone_col = find_header(phone_fields)
    name_col = find_header(name_fields)
    date_col = find_header(date_fields)
    duration_col = find_header(duration_fields)
    direction_col = find_header(direction_fields)
    summary_col = find_header(summary_fields)
    category_col = find_header(category_fields)

    for i, row in enumerate(reader, start=2):
        try:
            phone = row.get(phone_col, "").strip() if phone_col else ""
            name = row.get(name_col, "").strip() if name_col else ""
            summary = row.get(summary_col, "").strip() if summary_col else ""
            category = row.get(category_col, "").strip() if category_col else ""

            if not phone and not name:
                skipped += 1
                continue

            # Parse duration
            duration = None
            if duration_col and row.get(duration_col, "").strip():
                try:
                    dur_str = row[duration_col].strip().replace("s", "").replace("sec", "")
                    duration = int(float(dur_str))
                except (ValueError, TypeError):
                    pass

            # Parse direction
            direction = "INBOUND"
            if direction_col and row.get(direction_col, ""):
                d = row[direction_col].strip().upper()
                if "OUT" in d:
                    direction = "OUTBOUND"

            # Try to match to existing customer
            customer = None
            if phone:
                clean = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+", "")
                if len(clean) >= 10:
                    customer = Customer.objects.filter(phone__icontains=clean[-10:]).first()
                else:
                    customer = Customer.objects.filter(phone__icontains=phone).first()

            # If no customer found but we have name+phone, create one
            if not customer and name and phone:
                customer = Customer.objects.create(
                    name=name,
                    phone=phone,
                    source=Customer.Source.PHONE,
                    status=Customer.Status.ACTIVE,
                )

            CallLog.objects.create(
                customer=customer,
                phone_number=phone,
                direction=direction,
                duration=duration,
                transcript=summary,
                category_detected=category,
            )

            # Also create Interaction if customer matched
            if customer:
                Interaction.objects.create(
                    customer=customer,
                    type=Interaction.Type.CALL,
                    direction=(
                        Interaction.Direction.INBOUND
                        if direction == "INBOUND"
                        else Interaction.Direction.OUTBOUND
                    ),
                    summary=summary or f"Imported call - {phone}",
                    raw_data=dict(row),
                )

            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return imported, skipped, errors


def _import_customers_csv(reader, headers):
    """Import customer records from CSV."""
    imported = 0
    skipped = 0
    errors = []

    name_fields = ["name", "customer_name", "customer", "contact", "full_name", "contact name"]
    phone_fields = ["phone", "phone_number", "phonenumber", "mobile", "cell", "telephone", "phone number"]
    email_fields = ["email", "email_address", "e-mail"]
    notes_fields = ["notes", "comments", "description"]
    action_fields = ["action", "buying_selling", "buy_sell", "transaction", "type"]
    metal_fields = ["metal", "metal_type", "precious_metal"]
    form_fields = ["form", "metal_form", "product_type", "bullion_scrap"]

    def find_header(field_names):
        for h in headers:
            if h.lower().strip() in field_names:
                return h
        return None

    name_col = find_header(name_fields)
    phone_col = find_header(phone_fields)
    email_col = find_header(email_fields)
    notes_col = find_header(notes_fields)
    action_col = find_header(action_fields)
    metal_col = find_header(metal_fields)
    form_col = find_header(form_fields)

    if not name_col:
        return 0, 0, ["Could not find a 'name' column in the CSV headers."]

    # Valid choice values for matching
    valid_actions = {v.upper(): v for v, _ in Customer.Action.choices}
    valid_metals = {v.upper(): v for v, _ in Customer.Metal.choices}
    valid_forms = {v.upper(): v for v, _ in Customer.MetalForm.choices}

    for i, row in enumerate(reader, start=2):
        try:
            name = row.get(name_col, "").strip()
            phone = row.get(phone_col, "").strip() if phone_col else ""
            email = row.get(email_col, "").strip() if email_col else ""
            notes = row.get(notes_col, "").strip() if notes_col else ""
            action_val = row.get(action_col, "").strip().upper() if action_col else ""
            metal_val = row.get(metal_col, "").strip().upper() if metal_col else ""
            form_val = row.get(form_col, "").strip().upper() if form_col else ""

            if not name:
                skipped += 1
                continue

            # Check for duplicate by phone
            if phone:
                clean = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
                existing = Customer.objects.filter(phone__icontains=clean[-10:] if len(clean) >= 10 else clean).first()
                if existing:
                    skipped += 1
                    continue

            Customer.objects.create(
                name=name,
                phone=phone,
                email=email,
                notes=notes,
                action=valid_actions.get(action_val, ""),
                metal=valid_metals.get(metal_val, ""),
                metal_form=valid_forms.get(form_val, ""),
                source=Customer.Source.WALK_IN,
                status=Customer.Status.ACTIVE,
            )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return imported, skipped, errors


def _import_texts_csv(reader, headers):
    """Import text message records from CSV."""
    imported = 0
    skipped = 0
    errors = []

    phone_fields = ["phone", "phone_number", "from", "to", "number", "phone number"]
    message_fields = ["message", "body", "text", "content", "sms_body", "message body"]
    direction_fields = ["direction", "type"]
    date_fields = ["date", "datetime", "sent_at", "created_at", "timestamp"]

    def find_header(field_names):
        for h in headers:
            if h.lower().strip() in field_names:
                return h
        return None

    phone_col = find_header(phone_fields)
    message_col = find_header(message_fields)
    direction_col = find_header(direction_fields)

    for i, row in enumerate(reader, start=2):
        try:
            phone = row.get(phone_col, "").strip() if phone_col else ""
            message = row.get(message_col, "").strip() if message_col else ""

            if not phone or not message:
                skipped += 1
                continue

            # Match customer by phone
            customer = None
            clean = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+", "")
            if len(clean) >= 10:
                customer = Customer.objects.filter(phone__icontains=clean[-10:]).first()

            direction = Interaction.Direction.INBOUND
            if direction_col and row.get(direction_col, ""):
                d = row[direction_col].strip().upper()
                if "OUT" in d:
                    direction = Interaction.Direction.OUTBOUND

            Interaction.objects.create(
                customer=customer,
                type=Interaction.Type.TEXT,
                direction=direction,
                summary=message,
                raw_data={"phone": phone, "imported": True, **dict(row)},
            )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return imported, skipped, errors


@login_required
def csv_export_calls(request):
    """Export call logs as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="frontdesk_calls.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Phone Number", "Customer", "Direction", "Duration (s)", "Category", "Transcript"])

    for call in CallLog.objects.select_related("customer").all():
        writer.writerow([
            call.created_at.strftime("%Y-%m-%d %H:%M"),
            call.phone_number,
            call.customer.name if call.customer else "",
            call.direction,
            call.duration or "",
            call.category_detected,
            call.transcript,
        ])
    return response


@login_required
def csv_export_texts(request):
    """Export text interactions as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="frontdesk_texts.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Customer", "Phone", "Direction", "Message"])

    for text in Interaction.objects.filter(type=Interaction.Type.TEXT).select_related("customer").all():
        writer.writerow([
            text.created_at.strftime("%Y-%m-%d %H:%M"),
            text.customer.name if text.customer else "",
            text.customer.phone if text.customer else "",
            text.direction,
            text.summary,
        ])
    return response


# ============================================================================
# Conversation History
# ============================================================================


@login_required
def conversation_view(request, pk):
    """Per-customer conversation thread showing all texts sent and received."""
    customer = get_object_or_404(Customer, pk=pk)

    # Get all text interactions for this customer, ordered chronologically
    messages = Interaction.objects.filter(
        customer=customer,
        type=Interaction.Type.TEXT,
    ).order_by("created_at")

    # If sending a quick reply from the conversation view
    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()
        if message_text:
            Interaction.objects.create(
                customer=customer,
                type=Interaction.Type.TEXT,
                direction=Interaction.Direction.OUTBOUND,
                summary=message_text,
                raw_data={
                    "to": customer.phone or customer.email,
                    "message": message_text,
                    "sent_via": "conversation_view",
                },
            )
            # Send via Twilio if configured
            if customer.phone and settings.TWILIO_ACCOUNT_SID:
                try:
                    from twilio.rest import Client
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        body=message_text,
                        from_=settings.TWILIO_PHONE,
                        to=customer.phone,
                    )
                except Exception as e:
                    logger.error(f"Twilio send from conversation failed: {e}")

            return redirect("conversation", pk=pk)

    context = {
        "customer": customer,
        "messages": messages,
    }
    return render(request, "conversation.html", context)


# ============================================================================
# Inbound SMS Webhook (Twilio)
# ============================================================================


@csrf_exempt
@require_POST
def sms_webhook(request):
    """Webhook endpoint for inbound SMS from Twilio.

    Twilio sends POST data with:
    - From: the sender phone number
    - To: your Twilio phone number
    - Body: the text message content
    - MessageSid: unique Twilio message ID
    """
    from_number = request.POST.get("From", "")
    to_number = request.POST.get("To", "")
    body = request.POST.get("Body", "")
    message_sid = request.POST.get("MessageSid", "")

    logger.info(f"Inbound SMS from {from_number}: {body[:100]}")

    # Match phone number to customer
    customer = None
    if from_number:
        clean = from_number.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+", "")
        if len(clean) >= 10:
            customer = Customer.objects.filter(phone__icontains=clean[-10:]).first()
        else:
            customer = Customer.objects.filter(phone__icontains=from_number).first()

    # If no customer found, create one
    if not customer and from_number:
        customer = Customer.objects.create(
            name=f"Unknown ({from_number})",
            phone=from_number,
            source=Customer.Source.TEXT,
            status=Customer.Status.ACTIVE,
        )

    # Record the inbound text
    if customer:
        Interaction.objects.create(
            customer=customer,
            type=Interaction.Type.TEXT,
            direction=Interaction.Direction.INBOUND,
            summary=body,
            raw_data={
                "from": from_number,
                "to": to_number,
                "body": body,
                "message_sid": message_sid,
                "source": "twilio_webhook",
            },
        )

    # Return TwiML empty response (no auto-reply)
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        content_type="text/xml",
    )


# ============================================================================
# Integration Guide
# ============================================================================


@login_required
def integration_guide(request):
    """Display the integration setup guide."""
    return render(request, "integration_guide.html")


# ============================================================================
# Inventory Management
# ============================================================================


@login_required
def inventory_view(request):
    """Inventory needs management page."""
    inventory_items = InventoryNeed.objects.all()
    context = {
        "inventory_items": inventory_items,
        "actions": InventoryNeed.Action.choices,
        "metals": Customer.Metal.choices,
        "statuses": InventoryNeed.Status.choices,
    }
    return render(request, "inventory.html", context)


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def inventory_api(request):
    """API for inventory CRUD operations."""

    # GET - list all inventory items (with optional filters)
    if request.method == "GET":
        items = InventoryNeed.objects.all()

        # Filter by action
        action = request.GET.get("action")
        if action:
            items = items.filter(action=action)

        # Filter by status
        status = request.GET.get("status")
        if status:
            items = items.filter(status=status)

        # Filter by metal
        metal = request.GET.get("metal")
        if metal:
            items = items.filter(metal=metal)

        data = [
            {
                "id": item.id,
                "action": item.action,
                "action_display": item.get_action_display(),
                "product": item.product,
                "metal": item.metal,
                "metal_display": item.get_metal_display() if item.metal else "",
                "size": item.size,
                "quantity_needed": item.quantity_needed,
                "quantity_pending": item.quantity_pending,
                "quantity_fulfilled": item.quantity_fulfilled,
                "quantity_remaining": item.quantity_remaining,
                "status": item.status,
                "status_display": item.get_status_display(),
                "notes": item.notes,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
        return JsonResponse({"items": data})

    # POST - create new inventory item
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            item = InventoryNeed.objects.create(
                action=body.get("action", "BUY"),
                product=body.get("product", "").strip(),
                metal=body.get("metal", ""),
                size=body.get("size", "").strip(),
                quantity_needed=int(body.get("quantity_needed", 1)),
                notes=body.get("notes", "").strip(),
            )
            return JsonResponse({"status": "created", "id": item.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # PUT - update inventory item
    if request.method == "PUT":
        try:
            body = json.loads(request.body)
            item_id = body.get("id")
            item = get_object_or_404(InventoryNeed, pk=item_id)

            update_fields = []
            if "action" in body:
                item.action = body["action"]
                update_fields.append("action")
            if "product" in body:
                item.product = body["product"].strip()
                update_fields.append("product")
            if "metal" in body:
                item.metal = body["metal"]
                update_fields.append("metal")
            if "size" in body:
                item.size = body["size"].strip()
                update_fields.append("size")
            if "quantity_needed" in body:
                item.quantity_needed = int(body["quantity_needed"])
                update_fields.append("quantity_needed")
            if "quantity_fulfilled" in body:
                item.quantity_fulfilled = int(body["quantity_fulfilled"])
                update_fields.append("quantity_fulfilled")
            if "status" in body:
                item.status = body["status"]
                update_fields.append("status")
            if "notes" in body:
                item.notes = body["notes"].strip()
                update_fields.append("notes")

            if update_fields:
                item.save(update_fields=update_fields)
                # Auto-update status based on fulfillment
                item.update_status()

            return JsonResponse({"status": "updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # DELETE - delete inventory item
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            item_id = body.get("id")
            item = get_object_or_404(InventoryNeed, pk=item_id)
            item.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
def inventory_for_appointment(request):
    """API to get open inventory items that match an appointment's criteria.

    When appointment is SELLING, show inventory items where we need to BUY.
    When appointment is BUYING, show inventory items where we need to SELL.
    """
    # Customer action (what customer is doing)
    customer_action = request.GET.get("customer_action", "")
    metal = request.GET.get("metal", "")

    # Opposite action: customer SELLING means we BUY, customer BUYING means we SELL
    if customer_action == "SELLING":
        inventory_action = "BUY"
    elif customer_action == "BUYING":
        inventory_action = "SELL"
    else:
        inventory_action = None

    items = InventoryNeed.objects.filter(status__in=["OPEN", "PARTIAL"])

    if inventory_action:
        items = items.filter(action=inventory_action)
    if metal:
        items = items.filter(metal=metal)

    data = [
        {
            "id": item.id,
            "action": item.action,
            "product": item.product,
            "metal": item.metal,
            "size": item.size,
            "quantity_needed": item.quantity_needed,
            "quantity_fulfilled": item.quantity_fulfilled,
            "quantity_remaining": item.quantity_remaining,
            "display": f"{item.get_action_display()} {item.quantity_remaining}x {item.product} {item.size}".strip(),
        }
        for item in items
    ]
    return JsonResponse({"items": data})


# ============================================================================
# Prices API
# ============================================================================


def prices_api(request):
    """
    API endpoint for live precious metal prices.

    Returns real-time bid/ask prices from Fortune Reserve (FizTrade/Dillon Gage).
    Prices are cached for 60 seconds.

    Response format:
    {
        "success": true,
        "prices": [
            {
                "metal": "XAU",
                "name": "Gold",
                "bid": 2650.80,
                "ask": 2652.40,
                "spot": 2651.60,
                "spread": 1.60,
                "change": -12.50,
                "changePercent": -0.47
            },
            ...
        ],
        "timestamp": "Thursday, Jan 16 10:30:00 AM",
        "source": "FizTrade via Fortune Reserve",
        "cached": false
    }
    """
    data = fetch_metal_prices()
    return JsonResponse(data)


# ============================================================================
# Spread / Product Pricing
# ============================================================================


@login_required
def spread_view(request):
    """Spread page showing live prices and product premiums."""
    products = Product.objects.filter(is_active=True)
    context = {
        "products": products,
        "metals": Product.Metal.choices,
    }
    return render(request, "spread.html", context)


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def product_api(request):
    """API for product CRUD operations."""

    # GET - list all products
    if request.method == "GET":
        products = Product.objects.all()

        # Filter by active
        active_only = request.GET.get("active")
        if active_only == "true":
            products = products.filter(is_active=True)

        # Filter by metal
        metal = request.GET.get("metal")
        if metal:
            products = products.filter(metal=metal)

        data = [
            {
                "id": p.id,
                "name": p.name,
                "metal": p.metal,
                "metal_display": p.get_metal_display(),
                "size": p.size,
                "buy_premium": float(p.buy_premium),
                "sell_premium": float(p.sell_premium),
                "is_active": p.is_active,
                "notes": p.notes,
            }
            for p in products
        ]
        return JsonResponse({"products": data})

    # POST - create new product
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            product = Product.objects.create(
                name=body.get("name", "").strip(),
                metal=body.get("metal", "GOLD"),
                size=body.get("size", "").strip(),
                buy_premium=Decimal(str(body.get("buy_premium", 0))),
                sell_premium=Decimal(str(body.get("sell_premium", 0))),
                is_active=body.get("is_active", True),
                notes=body.get("notes", "").strip(),
            )
            return JsonResponse({"status": "created", "id": product.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # PUT - update product
    if request.method == "PUT":
        try:
            body = json.loads(request.body)
            product_id = body.get("id")
            product = get_object_or_404(Product, pk=product_id)

            if "name" in body:
                product.name = body["name"].strip()
            if "metal" in body:
                product.metal = body["metal"]
            if "size" in body:
                product.size = body["size"].strip()
            if "buy_premium" in body:
                product.buy_premium = Decimal(str(body["buy_premium"]))
            if "sell_premium" in body:
                product.sell_premium = Decimal(str(body["sell_premium"]))
            if "is_active" in body:
                product.is_active = body["is_active"]
            if "notes" in body:
                product.notes = body["notes"].strip()

            product.save()
            return JsonResponse({"status": "updated", "id": product.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # DELETE - delete product
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            product_id = body.get("id")
            product = get_object_or_404(Product, pk=product_id)
            product.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ============================================================================
# High Command Alert System
# ============================================================================

HIGH_COMMAND_PASSWORD = "highcommand"


@csrf_exempt
@require_http_methods(["GET", "POST"])
def highcommand_api(request):
    """
    API for High Command alert system.
    GET: Returns active message (if any)
    POST: Create new message (requires password) or respond to message
    """

    # GET - Check for active message
    if request.method == "GET":
        active_msg = HighCommandMessage.objects.filter(status=HighCommandMessage.Status.ACTIVE).first()
        if active_msg:
            return JsonResponse({
                "has_message": True,
                "id": active_msg.id,
                "message": active_msg.message,
                "sender": active_msg.sender_name,
                "created_at": active_msg.created_at.isoformat(),
            })
        return JsonResponse({"has_message": False})

    # POST - Create message or respond
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            action = body.get("action", "")

            # Create new message (requires password)
            if action == "send":
                password = body.get("password", "")
                if password != HIGH_COMMAND_PASSWORD:
                    return JsonResponse({"error": "Invalid password"}, status=403)

                message = body.get("message", "").strip()
                sender = body.get("sender", "").strip()

                if not message or not sender:
                    return JsonResponse({"error": "Message and sender name required"}, status=400)

                # Archive any existing active messages
                HighCommandMessage.objects.filter(status=HighCommandMessage.Status.ACTIVE).update(
                    status=HighCommandMessage.Status.ARCHIVED
                )

                # Create new message
                msg = HighCommandMessage.objects.create(
                    message=message,
                    sender_name=sender,
                    status=HighCommandMessage.Status.ACTIVE,
                )
                return JsonResponse({"status": "sent", "id": msg.id})

            # Respond to message (anyone can respond)
            elif action == "respond":
                msg_id = body.get("id")
                response = body.get("response", "").strip()
                responder = body.get("responder", "").strip()

                if not response or not responder:
                    return JsonResponse({"error": "Response and your name required"}, status=400)

                msg = get_object_or_404(HighCommandMessage, pk=msg_id)
                msg.response = response
                msg.responder_name = responder
                msg.responded_at = timezone.now()
                msg.status = HighCommandMessage.Status.ACKNOWLEDGED
                msg.save()

                return JsonResponse({"status": "responded"})

            # Get message history
            elif action == "history":
                messages = HighCommandMessage.objects.all()[:20]
                data = [
                    {
                        "id": m.id,
                        "message": m.message,
                        "sender": m.sender_name,
                        "status": m.status,
                        "response": m.response,
                        "responder": m.responder_name,
                        "created_at": m.created_at.isoformat(),
                        "responded_at": m.responded_at.isoformat() if m.responded_at else None,
                    }
                    for m in messages
                ]
                return JsonResponse({"messages": data})

            return JsonResponse({"error": "Invalid action"}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ============================================================================
# Toggle Board — Voice Receptionist Product Scheduling Control
# ============================================================================


@login_required
def toggle_board_view(request):
    """Toggle board page for controlling Tark1 auto-scheduling behavior."""
    toggles = ProductToggle.objects.all()
    return render(request, "toggle_board.html", {"toggles": toggles})


@login_required
@require_http_methods(["GET", "POST"])
def toggle_api(request):
    """Internal API for flipping toggles from the UI.

    POST: { "id": 1, "is_active": true }
    GET: returns all toggles
    """
    if request.method == "GET":
        toggles = ProductToggle.objects.all()
        data = [
            {
                "id": t.id,
                "category": t.category,
                "label": t.get_category_display(),
                "is_active": t.is_active,
                "updated_at": t.updated_at.isoformat(),
                "updated_by": t.updated_by,
            }
            for t in toggles
        ]
        return JsonResponse({"toggles": data})

    # POST — flip a toggle
    try:
        body = json.loads(request.body)
        toggle = get_object_or_404(ProductToggle, pk=body["id"])
        toggle.is_active = body["is_active"]
        toggle.updated_by = request.user.username
        toggle.save()
        return JsonResponse({
            "status": "updated",
            "id": toggle.id,
            "is_active": toggle.is_active,
            "updated_by": toggle.updated_by,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ============================================================================
# Tark1 External API — Called by voice receptionist on 192.168.1.200
# ============================================================================


@csrf_exempt
@require_http_methods(["GET"])
def tark1_toggles_api(request):
    """Public API for Tark1 to check which product categories are auto-schedule.

    GET /api/toggles/

    Response:
    {
        "toggles": {
            "SCRAP_GOLD": {"label": "Scrap Gold", "auto_schedule": true},
            "SCRAP_SILVER": {"label": "Scrap Silver", "auto_schedule": false},
            ...
        }
    }

    Tark1 logic:
    - If category is in toggles and auto_schedule == true -> schedule appointment
    - If category is in toggles and auto_schedule == false -> tell caller to wait for callback
    - If category is NOT in toggles -> tell caller to wait for callback
    """
    toggles = ProductToggle.objects.all()
    data = {}
    for t in toggles:
        data[t.category] = {
            "label": t.get_category_display(),
            "auto_schedule": t.is_active,
        }
    return JsonResponse({"toggles": data})


@csrf_exempt
@require_POST
def tark1_voice_schedule_api(request):
    """API for Tark1 to auto-create appointments from voice calls.

    POST /api/voice-schedule/

    Payload:
    {
        "caller_name": "John Smith",
        "caller_phone": "+15415551234",
        "category": "SCRAP_GOLD",
        "preferred_date": "2026-03-04",       (optional)
        "preferred_time": "14:00",             (optional)
        "notes": "Has about 3 oz scrap gold",  (optional)
        "location": "Ashland"                  (optional, defaults to J. Austin Office)
    }

    Response:
    {
        "status": "scheduled",
        "appointment_id": 42,
        "customer_id": 15,
        "datetime": "2026-03-04T14:00:00"
    }
    """
    try:
        body = json.loads(request.body)

        caller_name = body.get("caller_name", "").strip()
        caller_phone = body.get("caller_phone", "").strip()
        category = body.get("category", "").strip()

        if not caller_name or not caller_phone:
            return JsonResponse(
                {"error": "caller_name and caller_phone are required"}, status=400
            )

        # Verify the category is toggled ON
        toggle = ProductToggle.objects.filter(category=category).first()
        if not toggle or not toggle.is_active:
            return JsonResponse(
                {"error": "Category not available for auto-scheduling", "action": "callback"},
                status=403,
            )

        # Find or create the customer
        clean_phone = caller_phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+", "")
        customer = None
        if len(clean_phone) >= 10:
            customer = Customer.objects.filter(phone__icontains=clean_phone[-10:]).first()

        if not customer:
            customer = Customer.objects.create(
                name=caller_name,
                phone=caller_phone,
                source=Customer.Source.PHONE,
                status=Customer.Status.ACTIVE,
            )

        # Determine appointment datetime
        from datetime import datetime as dt
        preferred_date = body.get("preferred_date", "")
        preferred_time = body.get("preferred_time", "")

        if preferred_date and preferred_time:
            appt_datetime = timezone.make_aware(
                dt.strptime(f"{preferred_date} {preferred_time}", "%Y-%m-%d %H:%M")
            )
        elif preferred_date:
            appt_datetime = timezone.make_aware(
                dt.strptime(f"{preferred_date} 10:00", "%Y-%m-%d %H:%M")
            )
        else:
            # Default: next business day at 10 AM
            tomorrow = timezone.now() + timedelta(days=1)
            # Skip weekends
            while tomorrow.weekday() >= 5:
                tomorrow += timedelta(days=1)
            appt_datetime = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        location = body.get("location", "J. Austin Office")
        notes = body.get("notes", "")

        # Get the display label for purpose
        category_label = toggle.get_category_display() if toggle else category

        appointment = Appointment.objects.create(
            customer=customer,
            datetime=appt_datetime,
            end_datetime=appt_datetime + timedelta(minutes=30),
            purpose=f"Voice AI: {category_label}",
            location=location,
            status=Appointment.Status.SCHEDULED,
            notes=f"Auto-scheduled by Tark1 voice receptionist.\n{notes}".strip(),
        )

        # Log the interaction
        Interaction.objects.create(
            customer=customer,
            type=Interaction.Type.CALL,
            direction=Interaction.Direction.INBOUND,
            summary=f"Tark1 auto-scheduled appointment for {category_label}. {notes}".strip(),
            raw_data=body,
        )

        return JsonResponse({
            "status": "scheduled",
            "appointment_id": appointment.id,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "datetime": appointment.datetime.isoformat(),
            "location": appointment.location,
            "purpose": appointment.purpose,
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Tark1 voice-schedule error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
