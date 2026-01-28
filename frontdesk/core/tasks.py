"""
Celery tasks for J. Austin Front Desk Processing.
"""

import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_text_message(customer_id, message):
    """Send a text message to a customer asynchronously."""
    from .models import Customer, Interaction

    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        logger.error(f"Customer {customer_id} not found")
        return {"status": "error", "message": "Customer not found"}

    # Record interaction
    Interaction.objects.create(
        customer=customer,
        type=Interaction.Type.TEXT,
        direction=Interaction.Direction.OUTBOUND,
        summary=message,
        raw_data={"async": True, "to": customer.phone or customer.email},
    )

    # Send via Twilio
    if customer.phone and settings.TWILIO_ACCOUNT_SID:
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            result = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE,
                to=customer.phone,
            )
            return {"status": "sent", "sid": result.sid}
        except Exception as e:
            logger.error(f"Twilio error for customer {customer_id}: {e}")
            return {"status": "error", "message": str(e)}

    # Send via SendGrid email fallback
    if customer.email and settings.SENDGRID_API_KEY:
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
            response = sg.send(sg_message)
            return {"status": "sent", "status_code": response.status_code}
        except Exception as e:
            logger.error(f"SendGrid error for customer {customer_id}: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "skipped", "message": "No phone or email configured"}


@shared_task
def sync_frontdesk_ai_calls():
    """Periodically sync call logs from Front Desk AI."""
    import requests
    from .models import Customer, CallLog, Interaction
    from django.db.models import Q

    api_key = settings.FRONTDESK_AI_API_KEY
    if not api_key:
        logger.warning("FRONTDESK_AI_API_KEY not set, skipping sync")
        return {"status": "skipped"}

    try:
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
            return {"status": "error", "code": response.status_code}

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

        return {"status": "success", "synced": synced}

    except Exception as e:
        logger.error(f"Front Desk AI sync error: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def auto_generate_matches():
    """Periodically run the matching algorithm."""
    from .models import Customer, Match
    from decimal import Decimal

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

                match_amount = min(buyer.bullion_amount, seller.bullion_amount)
                if match_amount <= 0:
                    continue

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

    return {"status": "success", "matches_created": matches_created}
