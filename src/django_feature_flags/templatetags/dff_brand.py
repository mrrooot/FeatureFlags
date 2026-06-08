from django import template

from django_feature_flags import settings as package_settings


register = template.Library()


@register.simple_tag
def dff_dashboard_brand():
    return package_settings.dashboard_brand()
