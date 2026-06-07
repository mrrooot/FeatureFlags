import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from django_feature_flags import settings as package_settings


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Project(TimeStampedModel):
    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Environment(TimeStampedModel):
    project = models.ForeignKey(Project, related_name="environments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=160)
    requires_approval = models.BooleanField(default=False)
    require_change_reason = models.BooleanField(default=False)

    class Meta:
        ordering = ["project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_environment_key_per_project"),
        ]

    def __str__(self):
        return f"{self.project.key}:{self.key}"


class FeatureFlag(TimeStampedModel):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"
    VALUE_TYPES = (
        (BOOLEAN, "Boolean"),
        (STRING, "String"),
        (NUMBER, "Number"),
        (JSON, "JSON"),
    )

    project = models.ForeignKey(Project, related_name="flags", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES)
    archived = models.BooleanField(default=False)
    rules = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["project__name", "key"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_flag_key_per_project"),
        ]

    def __str__(self):
        return self.key


class Variation(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="variations", on_delete=models.CASCADE)
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120, blank=True)
    value = models.JSONField()
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["flag__key", "key"]
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_variation_key_per_flag"),
        ]

    def __str__(self):
        return f"{self.flag.key}:{self.key}"


class FlagState(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="states", on_delete=models.CASCADE)
    environment = models.ForeignKey(Environment, related_name="flag_states", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)
    default_variation = models.ForeignKey(Variation, related_name="+", null=True, blank=True, on_delete=models.PROTECT)
    rollout = models.JSONField(default=dict, blank=True)
    targeting = models.JSONField(default=dict, blank=True)
    emergency_override = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["environment__project__name", "environment__name", "flag__key"]
        constraints = [
            models.UniqueConstraint(fields=["flag", "environment"], name="dff_unique_flag_state_per_environment"),
        ]

    def __str__(self):
        return f"{self.environment}:{self.flag.key}"


class Segment(TimeStampedModel):
    project = models.ForeignKey(Project, related_name="segments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["project__name", "key"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_segment_key_per_project"),
        ]


class SegmentRule(TimeStampedModel):
    segment = models.ForeignKey(Segment, related_name="rules", on_delete=models.CASCADE)
    conditions = models.JSONField(default=list)
    exclude = models.BooleanField(default=False)


class TargetingRule(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="targeting_rules", on_delete=models.CASCADE)
    priority = models.PositiveIntegerField(default=0)
    conditions = models.JSONField(default=list)
    variation = models.ForeignKey(Variation, related_name="+", on_delete=models.PROTECT)

    class Meta:
        ordering = ["flag__key", "priority", "id"]


class SDKKeyQuerySet(models.QuerySet):
    def authenticate(self, raw_secret):
        digest = SDKKey.hash_secret(raw_secret)
        return self.filter(secret_hash=digest, active=True).first()


class SDKKey(TimeStampedModel):
    environment = models.ForeignKey(Environment, related_name="sdk_keys", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    secret_hash = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    objects = SDKKeyQuerySet.as_manager()

    class Meta:
        ordering = ["environment__project__name", "environment__name", "name"]

    @staticmethod
    def hash_secret(raw_secret):
        return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_environment(cls, environment, name, created_by=None):
        raw_secret = f"{package_settings.SDK_KEY_PREFIX}_{secrets.token_urlsafe(32)}"
        instance = cls.objects.create(
            environment=environment,
            name=name,
            secret_hash=cls.hash_secret(raw_secret),
            created_by=created_by,
        )
        instance.secret = raw_secret
        return instance

    def __str__(self):
        return f"{self.environment}:{self.name}"
