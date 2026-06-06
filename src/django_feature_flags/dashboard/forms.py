import json

from django import forms
from django.db import transaction

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


class FeatureFlagCreateForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    key = forms.SlugField(max_length=120)
    name = forms.CharField(max_length=180)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    value_type = forms.ChoiceField(choices=FeatureFlag.VALUE_TYPES)
    default_value = forms.CharField(required=False)
    environments = forms.ModelMultipleChoiceField(
        queryset=Environment.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    boolean_true_values = {"1", "true", "yes", "on", "enabled"}
    boolean_false_values = {"0", "false", "no", "off", "disabled"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.order_by("name")
        self.fields["environments"].queryset = Environment.objects.select_related("project").order_by(
            "project__name",
            "name",
        )
        self.fields["key"].help_text = "Lowercase letters, numbers, underscores, and hyphens."
        self.fields["default_value"].help_text = "Examples: true, 42, beta, or {\"tier\": \"gold\"}."

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        key = cleaned_data.get("key")
        environments = cleaned_data.get("environments")
        value_type = cleaned_data.get("value_type")
        default_value = cleaned_data.get("default_value", "")

        if project and key and FeatureFlag.objects.filter(project=project, key=key).exists():
            self.add_error("key", "A flag with this key already exists in this project.")

        if project and environments:
            invalid_environments = environments.exclude(project=project)
            if invalid_environments.exists():
                self.add_error("environments", "Choose environments from the selected project only.")

        if value_type and "default_value" not in self.errors:
            try:
                cleaned_data["parsed_default_value"] = self._parse_default_value(value_type, default_value)
            except ValueError as exc:
                self.add_error("default_value", str(exc))

        return cleaned_data

    def save(self):
        with transaction.atomic():
            flag = FeatureFlag.objects.create(
                project=self.cleaned_data["project"],
                key=self.cleaned_data["key"],
                name=self.cleaned_data["name"],
                description=self.cleaned_data["description"],
                value_type=self.cleaned_data["value_type"],
            )
            default_variation = Variation.objects.create(
                flag=flag,
                key="default",
                name="Default",
                value=self.cleaned_data["parsed_default_value"],
                is_default=True,
            )
            FlagState.objects.bulk_create(
                [
                    FlagState(
                        flag=flag,
                        environment=environment,
                        enabled=False,
                        default_variation=default_variation,
                    )
                    for environment in self.cleaned_data["environments"]
                ]
            )
        return flag

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
