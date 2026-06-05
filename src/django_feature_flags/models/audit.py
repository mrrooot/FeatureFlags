from django.conf import settings
from django.db import models
from django.utils import timezone

from django_feature_flags.models.core import Environment, FeatureFlag


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    environment = models.ForeignKey(Environment, null=True, blank=True, related_name="audit_logs", on_delete=models.SET_NULL)
    flag = models.ForeignKey(FeatureFlag, null=True, blank=True, related_name="audit_logs", on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    reason = models.TextField(blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class ApprovalRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUSES = (
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    )

    environment = models.ForeignKey(Environment, related_name="approval_requests", on_delete=models.CASCADE)
    flag = models.ForeignKey(FeatureFlag, related_name="approval_requests", on_delete=models.CASCADE)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUSES, default=PENDING)
    reason = models.TextField(blank=True)
    proposed_change = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
