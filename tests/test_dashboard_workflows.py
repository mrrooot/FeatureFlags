import pytest
from django.urls import reverse

from django_feature_flags.models import (
    ApprovalRequest,
    AuditLog,
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    Project,
    Segment,
    SegmentRule,
    Variation,
)


@pytest.mark.django_db
def test_staff_can_create_and_update_segment_rules(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:segment_create"),
        {
            "project": project.id,
            "key": "pro_users",
            "name": "Pro Users",
            "description": "Customers on paid plans",
            "conditions": '[{"attribute": "plan", "operator": "equals", "value": "pro"}]',
        },
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("django_feature_flags_dashboard:segment_list")
    segment = Segment.objects.get(project=project, key="pro_users")
    rule = segment.rules.get()
    assert rule.conditions == [{"attribute": "plan", "operator": "equals", "value": "pro"}]
    assert rule.exclude is False

    response = client.post(
        reverse("django_feature_flags_dashboard:segment_update", kwargs={"pk": segment.pk}),
        {
            "project": project.id,
            "key": "pro_users",
            "name": "Paid Accounts",
            "description": "Paid customer accounts",
            "conditions": '[{"attribute": "tier", "operator": "contains", "value": "paid"}]',
            "exclude": "on",
        },
    )

    assert response.status_code == 302
    segment.refresh_from_db()
    rule.refresh_from_db()
    assert segment.name == "Paid Accounts"
    assert rule.conditions == [{"attribute": "tier", "operator": "contains", "value": "paid"}]
    assert rule.exclude is True


@pytest.mark.django_db
def test_staff_can_create_and_update_experiment_allocations(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    control = Variation.objects.create(flag=flag, key="control", name="Control", value=False)
    treatment = Variation.objects.create(flag=flag, key="treatment", name="Treatment", value=True)
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:experiment_create"),
        {
            "flag": flag.id,
            "key": "checkout_test",
            "name": "Checkout Test",
            "status": Experiment.RUNNING,
            "config": '{"minimum_sample": 500}',
            "allocations": '[{"variation": "control", "weight": 50000}, {"variation": "treatment", "weight": 50000}]',
        },
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("django_feature_flags_dashboard:experiment_list")
    experiment = Experiment.objects.get(flag=flag, key="checkout_test")
    assert experiment.config == {"minimum_sample": 500}
    assert set(experiment.allocations.values_list("variation__key", "weight")) == {
        ("control", 50000),
        ("treatment", 50000),
    }

    response = client.post(
        reverse("django_feature_flags_dashboard:experiment_update", kwargs={"pk": experiment.pk}),
        {
            "flag": flag.id,
            "key": "checkout_test",
            "name": "Checkout Test v2",
            "status": Experiment.PAUSED,
            "config": "{}",
            "allocations": '[{"variation": "control", "weight": 100000}]',
        },
    )

    assert response.status_code == 302
    experiment.refresh_from_db()
    assert experiment.name == "Checkout Test v2"
    assert experiment.status == Experiment.PAUSED
    assert list(experiment.allocations.values_list("variation__key", "weight")) == [("control", 100000)]


@pytest.mark.django_db
def test_staff_can_create_and_review_approval_requests(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:approval_create"),
        {
            "environment": environment.id,
            "flag": flag.id,
            "reason": "Production release",
            "proposed_change": '{"enabled": true}',
        },
    )

    assert response.status_code == 302
    approval = ApprovalRequest.objects.get(flag=flag, environment=environment)
    assert approval.status == ApprovalRequest.PENDING
    assert approval.proposed_change == {"enabled": True}
    assert approval.requested_by == staff_user

    response = client.post(reverse("django_feature_flags_dashboard:approval_approve", kwargs={"pk": approval.pk}))

    assert response.status_code == 302
    approval.refresh_from_db()
    assert approval.status == ApprovalRequest.APPROVED
    assert approval.reviewed_by == staff_user
    assert approval.reviewed_at is not None
    assert AuditLog.objects.filter(action="approval.approved", flag=flag, environment=environment).exists()


@pytest.mark.django_db
def test_staff_can_reject_approval_requests(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    approval = ApprovalRequest.objects.create(
        environment=environment,
        flag=flag,
        requested_by=staff_user,
        proposed_change={"enabled": True},
        reason="Needs review",
    )
    client.force_login(staff_user)

    response = client.post(reverse("django_feature_flags_dashboard:approval_reject", kwargs={"pk": approval.pk}))

    assert response.status_code == 302
    approval.refresh_from_db()
    assert approval.status == ApprovalRequest.REJECTED
    assert approval.reviewed_by == staff_user
    assert AuditLog.objects.filter(action="approval.rejected", flag=flag, environment=environment).exists()


@pytest.mark.django_db
def test_staff_can_view_and_filter_audit_trail(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    log = AuditLog.objects.create(
        user=staff_user,
        environment=environment,
        flag=flag,
        action="flag.update",
        reason="Release",
        before={"enabled": False},
        after={"enabled": True},
    )
    AuditLog.objects.create(action="segment.update", reason="Other")
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:audit_list"), {"action": "flag"})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Audit trail" in content
    assert "flag.update" in content
    assert "segment.update" not in content
    assert reverse("django_feature_flags_dashboard:audit_detail", kwargs={"pk": log.pk}) in content

    response = client.get(reverse("django_feature_flags_dashboard:audit_detail", kwargs={"pk": log.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert '"enabled": false' in content
    assert '"enabled": true' in content


@pytest.mark.django_db
def test_sidebar_links_to_full_workflows(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert reverse("django_feature_flags_dashboard:segment_list") in content
    assert reverse("django_feature_flags_dashboard:experiment_list") in content
    assert reverse("django_feature_flags_dashboard:approval_list") in content
    assert reverse("django_feature_flags_dashboard:audit_list") in content


from django.http import QueryDict

from django_feature_flags.dashboard.targeting_forms import TargetingDocumentForm


@pytest.mark.django_db
def test_targeting_document_form_builds_targets_rules_and_fallthrough():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    data = QueryDict(mutable=True)
    data.update(
        {
            "enabled": "on",
            "off_variation": off.key,
            "target_context_kind_0": "user",
            "target_variation_key_0": on.key,
            "target_values_0": "user-1\nuser-2",
            "rule_id_0": "ios-rule",
            "rule_description_0": "iOS devices",
            "rule_serve_variation_key_0": on.key,
            "rule_clause_context_kind_0_0": "device",
            "rule_clause_attribute_0_0": "platform",
            "rule_clause_operator_0_0": "in",
            "rule_clause_values_0_0": "ios,android",
            "fallthrough_variation_key": off.key,
        }
    )
    data.setlist("target_index", ["0"])
    data.setlist("rule_index", ["0"])
    data.setlist("rule_clause_index_0", ["0"])

    form = TargetingDocumentForm(flag=flag, environment=environment, data=data)

    assert form.is_valid(), form.errors
    assert form.enabled is True
    assert form.cleaned_document["targets"][0]["values"] == ["user-1", "user-2"]
    assert form.cleaned_document["rules"][0]["clauses"][0]["values"] == ["ios", "android"]


@pytest.mark.django_db
def test_targeting_document_form_requires_change_reason_when_environment_requires_it():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(
        project=project,
        key="production",
        name="Production",
        require_change_reason=True,
    )
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    data = QueryDict(mutable=True)
    data.update({"off_variation": off.key, "fallthrough_variation_key": off.key})

    form = TargetingDocumentForm(flag=flag, environment=environment, data=data)

    assert form.is_valid() is False
    assert form.errors["reason"] == ["Change reason is required for this environment."]
