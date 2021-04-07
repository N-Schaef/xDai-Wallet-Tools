from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def format_money(val):
    if val is None or val == "":
        return ""
    if val < 1.0:
        return "{:.3g} $".format(val)
    return "{:.2f} $".format(val)

@register.simple_tag
def format_balance(val):
    if val is None or val == "":
        return ""
    if val < 1.0:
        return "{:.3g}".format(val)
    return "{:.2f}".format(val)

@register.simple_tag
def format_address(address):
    return address.lower()