from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def perc_diff(old, new):
    if old == 0.0 and new == 0.0:
        return None
    if old is None or old == 0.0:
        return "None"
    if new is None or new == 0:
        return "-100%"
    perc_diff = ((new - old) / abs(old)) * 100

    out = "{:+.2f}%".format(perc_diff)

    if perc_diff == 0.0:
        return None
    return out

@register.simple_tag
def classed_perc_diff(old, new):
    if old == 0.0 and new == 0.0:
        return None
    if old is None or old == 0.0:
        return "None"
    if new is None or new == 0:
        return "-100%"
    perc_diff = ((new - old) / abs(old)) * 100

    out = "{:+.2f}%".format(perc_diff)

    if perc_diff == 0.0:
        return None
    if perc_diff > 0:
      return mark_safe("<span class=\"positive_diff\">{}</span>".format(out))
    if perc_diff < 0:
      return mark_safe("<span class=\"negative_diff\">{}</span>".format(out))
    return out

@register.simple_tag
def labelled_perc_diff(old, new, label):
  out = classed_perc_diff(old,new)
  if out is not None:
    return mark_safe("<div class=\"perc_diff_cont\">({}: {})</div>".format(label,out))
  return ""