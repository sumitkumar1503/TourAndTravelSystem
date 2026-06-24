from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Look up a value by key in a dict (template-friendly)."""
    if not d:
        return ''
    try:
        return d.get(key, '')
    except AttributeError:
        try:
            return d[key]
        except (KeyError, IndexError, TypeError):
            return ''


@register.filter
def stars(n):
    """Render an integer rating as filled/empty stars (text)."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    return '★' * n + '☆' * max(0, 5 - n)


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return ''
