import os
from django import template

register = template.Library()

@register.filter(name='basename')
def basename(value):
    """Return the basename of a file path or name."""
    if value is None:
        return ''
    return os.path.basename(str(value))
