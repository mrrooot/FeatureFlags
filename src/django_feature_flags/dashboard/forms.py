import json

from django import forms
from django.db import transaction

from django_feature_flags import settings as package_settings
from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


class FeatureFlagForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    key = forms.SlugField(max_length=120)
    name = forms.CharField(max_length=180)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    value_type = forms.ChoiceField(choices=FeatureFlag.VALUE_TYPES)
    default_value = forms.CharField(required=False)

    boolean_true_values = {"1", "true", "yes", "on", "enabled"}
    boolean_false_values = {"0", "false", "no", "off", "disabled"}

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.order_by("name")
        self.fields["key"].help_text = "Lowercase letters, numbers, underscores, and hyphens."
        self.fields["default_value"].help_text = "Examples: true, 42, beta, or {\"tier\": \"gold\"}."

        if self.instance:
            self.fields["project"].disabled = True
            self.initial.update(
                {
                    "project": self.instance.project,
                    "key": self.instance.key,
                    "name": self.instance.name,
                    "description": self.instance.description,
                    "value_type": self.instance.value_type,
                    "default_value": self._format_default_value(self.default_variation_value()),
                }
            )

    @property
    def configured_environments(self):
        return package_settings.configured_environment_rows()

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        key = cleaned_data.get("key")
        value_type = cleaned_data.get("value_type")
        default_value = cleaned_data.get("default_value", "")

        existing_flags = FeatureFlag.objects.filter(project=project, key=key)
        if self.instance:
            existing_flags = existing_flags.exclude(pk=self.instance.pk)
        if project and key and existing_flags.exists():
            self.add_error("key", "A flag with this key already exists in this project.")

        if value_type and "default_value" not in self.errors:
            try:
                cleaned_data["parsed_default_value"] = self._parse_default_value(value_type, default_value)
            except ValueError as exc:
                self.add_error("default_value", str(exc))

        return cleaned_data

    def save(self):
        with transaction.atomic():
            flag = self.instance or FeatureFlag()
            flag.project = self.cleaned_data["project"]
            flag.key = self.cleaned_data["key"]
            flag.name = self.cleaned_data["name"]
            flag.description = self.cleaned_data["description"]
            flag.value_type = self.cleaned_data["value_type"]
            flag.save()

            default_variation, _ = Variation.objects.update_or_create(
                flag=flag,
                key="default",
                defaults={
                    "name": "Default",
                    "value": self.cleaned_data["parsed_default_value"],
                    "is_default": True,
                },
            )
            flag.variations.exclude(pk=default_variation.pk).filter(is_default=True).update(is_default=False)
            self._sync_configured_states(flag, default_variation)
        return flag

    def default_variation_value(self):
        variation = self.instance.variations.filter(is_default=True).first()
        if variation is None:
            variation = self.instance.variations.filter(key="default").first()
        return variation.value if variation else ""

    def _sync_configured_states(self, flag, default_variation):
        environments = [
            Environment.objects.get_or_create(
                project=flag.project,
                key=environment_key,
                defaults={"name": package_settings.environment_name(environment_key)},
            )[0]
            for environment_key in package_settings.configured_environment_keys()
        ]
        existing_environment_ids = set(
            flag.states.filter(environment__in=environments).values_list("environment_id", flat=True)
        )
        FlagState.objects.bulk_create(
            [
                FlagState(
                    flag=flag,
                    environment=environment,
                    enabled=False,
                    default_variation=default_variation,
                )
                for environment in environments
                if environment.id not in existing_environment_ids
            ]
        )

    def _parse_default_value(self, value_type, raw_value):
        value = (raw_value or "").strip()
        if value_type == FeatureFlag.BOOLEAN:
            if not value:
                return False
            normalized = value.lower()
            if normalized in self.boolean_true_values:
                return True
            if normalized in self.boolean_false_values:
                return False
            raise ValueError("Use true or false for boolean flags.")

        if value_type == FeatureFlag.NUMBER:
            if not value:
                return 0
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError("Use a valid number.") from exc
            return int(number) if number.is_integer() else number

        if value_type == FeatureFlag.JSON:
            if not value:
                return {}
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("Use valid JSON.") from exc

        return raw_value or ""

    def _format_default_value(self, value):
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, sort_keys=True)


FeatureFlagCreateForm = FeatureFlagForm
