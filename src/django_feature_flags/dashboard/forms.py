import json

from django import forms
from django.db import transaction

from django_feature_flags import settings as package_settings
from django_feature_flags.audit.service import create_approval_request
from django_feature_flags.models import (
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    FlagState,
    Project,
    Segment,
    SegmentRule,
    Variation,
)


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


class SegmentForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    key = forms.SlugField(max_length=120)
    name = forms.CharField(max_length=180)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    conditions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 7}))
    exclude = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.order_by("name")
        self.fields["conditions"].help_text = 'JSON list, for example [{"attribute": "plan", "operator": "equals", "value": "pro"}].'
        if self.instance:
            rule = self.instance.rules.order_by("id").first()
            self.initial.update(
                {
                    "project": self.instance.project,
                    "key": self.instance.key,
                    "name": self.instance.name,
                    "description": self.instance.description,
                    "conditions": json.dumps(rule.conditions if rule else [], sort_keys=True),
                    "exclude": rule.exclude if rule else False,
                }
            )

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        key = cleaned_data.get("key")
        existing = Segment.objects.filter(project=project, key=key)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if project and key and existing.exists():
            self.add_error("key", "A segment with this key already exists in this project.")

        try:
            cleaned_data["parsed_conditions"] = self._parse_json_list(cleaned_data.get("conditions", ""), "conditions")
        except ValueError as exc:
            self.add_error("conditions", str(exc))
        return cleaned_data

    def save(self):
        with transaction.atomic():
            segment = self.instance or Segment()
            segment.project = self.cleaned_data["project"]
            segment.key = self.cleaned_data["key"]
            segment.name = self.cleaned_data["name"]
            segment.description = self.cleaned_data["description"]
            segment.save()
            rule = segment.rules.order_by("id").first()
            if rule is None:
                SegmentRule.objects.create(
                    segment=segment,
                    conditions=self.cleaned_data["parsed_conditions"],
                    exclude=self.cleaned_data["exclude"],
                )
            else:
                rule.conditions = self.cleaned_data["parsed_conditions"]
                rule.exclude = self.cleaned_data["exclude"]
                rule.save(update_fields=["conditions", "exclude"])
                segment.rules.exclude(pk=rule.pk).delete()
        return segment

    def _parse_json_list(self, raw_value, field_name):
        value = (raw_value or "").strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Use valid JSON for {field_name}.") from exc
        if not isinstance(parsed, list):
            raise ValueError(f"Use a JSON list for {field_name}.")
        return parsed


class ExperimentForm(forms.Form):
    flag = forms.ModelChoiceField(queryset=FeatureFlag.objects.none())
    key = forms.SlugField(max_length=120)
    name = forms.CharField(max_length=180)
    status = forms.ChoiceField(choices=Experiment.STATUSES)
    config = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    allocations = forms.CharField(widget=forms.Textarea(attrs={"rows": 7}))

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        self.fields["flag"].queryset = FeatureFlag.objects.select_related("project").order_by("project__name", "key")
        self.fields["config"].help_text = "Optional JSON object for experiment settings."
        self.fields["allocations"].help_text = 'JSON list, for example [{"variation": "control", "weight": 50000}]. Weights use 0-100000.'
        if self.instance:
            self.initial.update(
                {
                    "flag": self.instance.flag,
                    "key": self.instance.key,
                    "name": self.instance.name,
                    "status": self.instance.status,
                    "config": json.dumps(self.instance.config, sort_keys=True),
                    "allocations": json.dumps(
                        [
                            {
                                "variation": allocation.variation.key,
                                "weight": allocation.weight,
                                "holdout": allocation.holdout,
                            }
                            for allocation in self.instance.allocations.select_related("variation").order_by("id")
                        ],
                        sort_keys=True,
                    ),
                }
            )

    def clean(self):
        cleaned_data = super().clean()
        flag = cleaned_data.get("flag")
        key = cleaned_data.get("key")
        existing = Experiment.objects.filter(flag=flag, key=key)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if flag and key and existing.exists():
            self.add_error("key", "An experiment with this key already exists for this flag.")

        try:
            cleaned_data["parsed_config"] = self._parse_json_object(cleaned_data.get("config", ""), "config")
        except ValueError as exc:
            self.add_error("config", str(exc))

        if flag:
            try:
                cleaned_data["parsed_allocations"] = self._parse_allocations(
                    flag,
                    cleaned_data.get("allocations", ""),
                )
            except ValueError as exc:
                self.add_error("allocations", str(exc))
        return cleaned_data

    def save(self):
        with transaction.atomic():
            experiment = self.instance or Experiment()
            experiment.flag = self.cleaned_data["flag"]
            experiment.key = self.cleaned_data["key"]
            experiment.name = self.cleaned_data["name"]
            experiment.status = self.cleaned_data["status"]
            experiment.config = self.cleaned_data["parsed_config"]
            experiment.save()
            experiment.allocations.all().delete()
            ExperimentAllocation.objects.bulk_create(
                [
                    ExperimentAllocation(
                        experiment=experiment,
                        variation=item["variation"],
                        weight=item["weight"],
                        holdout=item["holdout"],
                    )
                    for item in self.cleaned_data["parsed_allocations"]
                ]
            )
        return experiment

    def _parse_json_object(self, raw_value, field_name):
        value = (raw_value or "").strip()
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Use valid JSON for {field_name}.") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"Use a JSON object for {field_name}.")
        return parsed

    def _parse_allocations(self, flag, raw_value):
        value = (raw_value or "").strip()
        if not value:
            raise ValueError("Add at least one allocation.")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Use valid JSON for allocations.") from exc
        if not isinstance(parsed, list) or not parsed:
            raise ValueError("Use a non-empty JSON list for allocations.")

        variations_by_key = {variation.key: variation for variation in flag.variations.all()}
        allocations = []
        seen_variations = set()
        for item in parsed:
            if not isinstance(item, dict):
                raise ValueError("Each allocation must be a JSON object.")
            variation_key = str(item.get("variation", "")).strip()
            variation = variations_by_key.get(variation_key)
            if variation is None:
                raise ValueError(f"Variation {variation_key or '<missing>'} does not exist for this flag.")
            if variation.key in seen_variations:
                raise ValueError(f"Variation {variation.key} is allocated more than once.")
            seen_variations.add(variation.key)
            try:
                weight = int(item.get("weight", 0))
            except (TypeError, ValueError) as exc:
                raise ValueError("Allocation weights must be numbers.") from exc
            if weight < 0 or weight > 100000:
                raise ValueError("Allocation weights must be between 0 and 100000.")
            allocations.append(
                {
                    "variation": variation,
                    "weight": weight,
                    "holdout": bool(item.get("holdout", False)),
                }
            )
        return allocations


class ApprovalRequestForm(forms.Form):
    environment = forms.ModelChoiceField(queryset=Environment.objects.none())
    flag = forms.ModelChoiceField(queryset=FeatureFlag.objects.none())
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    proposed_change = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}))

    def __init__(self, *args, **kwargs):
        self.requested_by = kwargs.pop("requested_by", None)
        super().__init__(*args, **kwargs)
        self.fields["environment"].queryset = Environment.objects.select_related("project").order_by("project__name", "name")
        self.fields["flag"].queryset = FeatureFlag.objects.select_related("project").order_by("project__name", "key")
        self.fields["proposed_change"].help_text = 'JSON object, for example {"enabled": true}.'

    def clean(self):
        cleaned_data = super().clean()
        environment = cleaned_data.get("environment")
        flag = cleaned_data.get("flag")
        if environment and flag and environment.project_id != flag.project_id:
            self.add_error("flag", "Choose a flag from the same project as the environment.")
        try:
            cleaned_data["parsed_proposed_change"] = self._parse_json_object(cleaned_data.get("proposed_change", ""))
        except ValueError as exc:
            self.add_error("proposed_change", str(exc))
        return cleaned_data

    def save(self):
        return create_approval_request(
            requested_by=self.requested_by,
            environment=self.cleaned_data["environment"],
            flag=self.cleaned_data["flag"],
            proposed_change=self.cleaned_data["parsed_proposed_change"],
            reason=self.cleaned_data["reason"],
        )

    def _parse_json_object(self, raw_value):
        value = (raw_value or "").strip()
        if not value:
            raise ValueError("Use a JSON object for the proposed change.")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Use valid JSON for the proposed change.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Use a JSON object for the proposed change.")
        return parsed
