from django.apps import AppConfig


class DjangoFeatureFlagsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_feature_flags"
    verbose_name = "Django Feature Flags"
