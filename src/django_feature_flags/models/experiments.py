from django.db import models

from django_feature_flags.models.core import FeatureFlag, Variation
from django_feature_flags.models.events import Event


class Metric(models.Model):
    CONVERSION = "conversion"
    FUNNEL = "funnel"
    GUARDRAIL = "guardrail"
    METRIC_TYPES = (
        (CONVERSION, "Conversion"),
        (FUNNEL, "Funnel"),
        (GUARDRAIL, "Guardrail"),
    )

    flag = models.ForeignKey(FeatureFlag, related_name="metrics", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    event_name = models.CharField(max_length=120)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_metric_key_per_flag"),
        ]


class Experiment(models.Model):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    STATUSES = (
        (DRAFT, "Draft"),
        (RUNNING, "Running"),
        (PAUSED, "Paused"),
        (STOPPED, "Stopped"),
    )

    flag = models.ForeignKey(FeatureFlag, related_name="experiments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)
    primary_metric = models.ForeignKey(Metric, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    guardrail_metrics = models.ManyToManyField(Metric, related_name="guardrail_experiments", blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_experiment_key_per_flag"),
        ]


class ExperimentAllocation(models.Model):
    experiment = models.ForeignKey(Experiment, related_name="allocations", on_delete=models.CASCADE)
    variation = models.ForeignKey(Variation, related_name="experiment_allocations", on_delete=models.CASCADE)
    weight = models.PositiveIntegerField(default=0)
    holdout = models.BooleanField(default=False)


class ExperimentResultSnapshot(models.Model):
    experiment = models.ForeignKey(Experiment, related_name="result_snapshots", on_delete=models.CASCADE)
    event_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_for_experiment(cls, experiment):
        event_count = Event.objects.filter(flag=experiment.flag).count()
        conversion_count = Event.objects.filter(flag=experiment.flag, event_type=Event.CONVERSION).count()
        return cls.objects.create(
            experiment=experiment,
            event_count=event_count,
            conversion_count=conversion_count,
            summary={
                "event_count": event_count,
                "conversion_count": conversion_count,
            },
        )
