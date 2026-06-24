"""Template tag for navbar notification dropdown."""
from django import template
from booking.models import Notification

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_notifications(context):
    """Return a small bundle: {count, items} for the navbar bell."""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return {'count': 0, 'items': []}
    qs = Notification.objects.filter(user=request.user, is_read=False)[:5]
    return {'count': qs.count(), 'items': list(qs)}
