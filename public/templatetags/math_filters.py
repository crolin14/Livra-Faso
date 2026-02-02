from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplie deux valeurs"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divise deux valeurs"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(completed, total):
    """Calcule un pourcentage"""
    try:
        if int(total) == 0:
            return 0
        return round((int(completed) * 100) / int(total))
    except (ValueError, TypeError):
        return 0
