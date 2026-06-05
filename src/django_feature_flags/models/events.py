from django.db import models
from django.utils import timezone

from django_feature_flags.models.core import Environment, FeatureFlag, Variation


class Event(models.Model):
    EVALUATION = "evaluation"
    IMPRESSION = "impression"
    CONVERSION = "conversion"
    CUSTOM = "custom"
    EVENT_TYPES = (
        (EVALUATION, "Evaluation"),
        (IMPRESSION, "Impression"),
        (CONVERSION, "Conversion"),
        (CUSTOM, "Custom"),
    )

    environment = models.ForeignKey(Environment, related_name="events", on_delete=models.CASCADE)
    flag = models.ForeignKey(FeatureFlag, null=True, blank=True, related_name="events", on_delete=models.SET_NULL)
    variation = models.ForeignKey(Variation, null=True, blank=True, related_name="events", on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    context_key = models.CharField(max_length=180, blank=True)
    metric_key = models.CharField(max_length=120, blank=True)
    value = models.FloatField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
