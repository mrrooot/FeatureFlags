from django import forms

from django_feature_flags.targeting.documents import (
    TargetingValidationError,
    normalized_targeting,
    validate_targeting,
)


class TargetingDocumentForm(forms.Form):
    reason = forms.CharField(required=False)

    def __init__(self, *, flag, environment, state=None, data=None):
        self.flag = flag
        self.environment = environment
        self.state = state
        self.cleaned_document = {}
        self.enabled = False
        super().__init__(data=data)

    def clean(self):
        cleaned = super().clean()
        if self.environment.require_change_reason and not (cleaned.get("reason") or "").strip():
            self.add_error("reason", "Change reason is required for this environment.")

        document = self._build_document()
        try:
            self.cleaned_document = validate_targeting(self.flag, self.environment, document)
        except TargetingValidationError as exc:
            for section, messages in exc.errors.items():
                self.add_error(None, f"{section}: {' '.join(messages)}")

        self.enabled = self.data.get("enabled") == "on"
        return cleaned

    def initial_document(self):
        if self.state is None:
            return {}
        return normalized_targeting(self.state)

    def _build_document(self):
        return {
            "off_variation": self.data.get("off_variation", ""),
            "prerequisites": self._build_prerequisites(),
            "targets": self._build_targets(),
            "rules": self._build_rules(),
            "fallthrough": self._build_fallthrough(),
            "track_events": self.data.get("track_events") == "on",
        }

    def _build_prerequisites(self):
        items = []
        for index in self.data.getlist("prerequisite_index"):
            flag_key = self.data.get(f"prerequisite_flag_key_{index}", "").strip()
            variation_key = self.data.get(f"prerequisite_variation_key_{index}", "").strip()
            if flag_key or variation_key:
                items.append({"flag_key": flag_key, "variation_key": variation_key})
        return items

    def _build_targets(self):
        items = []
        for index in self.data.getlist("target_index"):
            values = split_values(self.data.get(f"target_values_{index}", ""))
            if values:
                items.append(
                    {
                        "context_kind": self.data.get(f"target_context_kind_{index}", "user").strip() or "user",
                        "variation_key": self.data.get(f"target_variation_key_{index}", "").strip(),
                        "values": values,
                    }
                )
        return items

    def _build_rules(self):
        rules = []
        for index in self.data.getlist("rule_index"):
            clauses = []
            for clause_index in self.data.getlist(f"rule_clause_index_{index}"):
                values = split_values(self.data.get(f"rule_clause_values_{index}_{clause_index}", ""))
                clauses.append(
                    {
                        "context_kind": self.data.get(
                            f"rule_clause_context_kind_{index}_{clause_index}",
                            "user",
                        ).strip()
                        or "user",
                        "attribute": self.data.get(f"rule_clause_attribute_{index}_{clause_index}", "").strip(),
                        "operator": self.data.get(
                            f"rule_clause_operator_{index}_{clause_index}",
                            "equals",
                        ).strip(),
                        "values": values,
                        "negate": self.data.get(f"rule_clause_negate_{index}_{clause_index}") == "on",
                    }
                )
            if clauses:
                rules.append(
                    {
                        "id": self.data.get(f"rule_id_{index}", f"rule-{index}").strip() or f"rule-{index}",
                        "description": self.data.get(f"rule_description_{index}", "").strip(),
                        "clauses": clauses,
                        "serve": {"variation_key": self.data.get(f"rule_serve_variation_key_{index}", "").strip()},
                    }
                )
        return rules

    def _build_fallthrough(self):
        variation_key = self.data.get("fallthrough_variation_key", "").strip()
        return {"variation_key": variation_key} if variation_key else {}


def split_values(raw_value):
    normalized = raw_value.replace(",", "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip()]
