"""
Custom template tags and filters for J. Austin Front Desk Processing.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def status_badge(status):
    """Return a Bootstrap badge for a given status string."""
    badge_map = {
        # Customer statuses
        "PENDING": ("warning", "Pending"),
        "MATCHED": ("info", "Matched"),
        "CLOSED": ("secondary", "Closed"),
        "ACTIVE": ("success", "Active"),
        # Match statuses
        "PROPOSED": ("primary", "Proposed"),
        "ACCEPTED": ("success", "Accepted"),
        "COMPLETED": ("secondary", "Completed"),
        "CANCELED": ("danger", "Canceled"),
        # Appointment statuses
        "SCHEDULED": ("primary", "Scheduled"),
        "CONFIRMED": ("success", "Confirmed"),
        "NO_SHOW": ("warning", "No Show"),
    }

    badge_class, label = badge_map.get(status, ("secondary", status))
    return mark_safe(f'<span class="badge bg-{badge_class}">{label}</span>')


@register.filter
def direction_icon(direction):
    """Return an icon for call/text direction."""
    if direction == "INBOUND":
        return mark_safe('<i class="bi bi-arrow-down-left text-success"></i> Inbound')
    elif direction == "OUTBOUND":
        return mark_safe('<i class="bi bi-arrow-up-right text-primary"></i> Outbound')
    return direction


@register.filter
def interaction_type_icon(itype):
    """Return an icon for interaction type."""
    icons = {
        "CALL": '<i class="bi bi-telephone"></i>',
        "TEXT": '<i class="bi bi-chat-dots"></i>',
        "EMAIL": '<i class="bi bi-envelope"></i>',
    }
    return mark_safe(icons.get(itype, itype))


@register.filter
def category_label(category):
    """Return a styled label for customer category."""
    labels = {
        "BUY_BULLION": ("success", "Buy Bullion"),
        "SELL_BULLION": ("danger", "Sell Bullion"),
        "BUY_SCRAP_GOLD": ("warning", "Buy Scrap Gold"),
        "BUY_SCRAP_SILVER": ("info", "Buy Scrap Silver"),
    }
    badge_class, label = labels.get(category, ("secondary", category))
    return mark_safe(f'<span class="badge bg-{badge_class}">{label}</span>')


@register.filter
def bullion_type_label(btype):
    """Return a styled label for bullion type."""
    labels = {
        "GOLD": ("warning", "Gold"),
        "SILVER": ("secondary", "Silver"),
        "PLATINUM": ("light", "Platinum"),
    }
    badge_class, label = labels.get(btype, ("secondary", btype))
    extra = ' text-dark' if btype in ("GOLD", "PLATINUM") else ""
    return mark_safe(f'<span class="badge bg-{badge_class}{extra}">{label}</span>')


@register.filter
def duration_format(seconds):
    """Format duration in seconds to mm:ss."""
    if seconds is None:
        return "--"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


@register.simple_tag
def frontdesk_url(path=""):
    """Return a prefixed URL for the frontdesk app."""
    return f"/frontdesk/{path}"
