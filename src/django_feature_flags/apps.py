from django.apps import AppConfig


class DjangoFeatureFlagsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_feature_flags"
    verbose_name = "Django Feature Flags"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from django_feature_flags.evaluation.config import bump_generation
        from django_feature_flags.models import (
            Environment,
            Experiment,
            ExperimentAllocation,
            FeatureFlag,
            FlagState,
            Project,
            Segment,
            SegmentRule,
            TargetingRule,
            Variation,
        )

        def invalidate(sender, **kwargs):
            bump_generation()

        # Any write to a model that feeds a config snapshot invalidates every
        # cached snapshot. Writes here are admin/config actions (rare); reads
        # are the hot path, so coarse global invalidation is the right trade.
        config_models = (
            Project,
            Environment,
            FeatureFlag,
            Variation,
            FlagState,
            TargetingRule,
            Segment,
            SegmentRule,
            Experiment,
            ExperimentAllocation,
        )
        for model in config_models:
            dispatch_uid = f"dff_cfg_invalidate_{model.__name__}"
            post_save.connect(invalidate, sender=model, dispatch_uid=f"{dispatch_uid}_save", weak=False)
            post_delete.connect(invalidate, sender=model, dispatch_uid=f"{dispatch_uid}_delete", weak=False)
