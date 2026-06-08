import pytest
from django.urls import reverse

from django_feature_flags.models import ApprovalRequest, AuditLog, Environment, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_primary_console_screens_expose_visual_smoke_checkpoints(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    approval = ApprovalRequest.objects.create(
        environment=environment,
        flag=flag,
        requested_by=staff_user,
        proposed_change={"enabled": True},
        reason="Production launch",
    )
    log = AuditLog.objects.create(
        user=staff_user,
        environment=environment,
        flag=flag,
        action="flag.targeting.updated",
        before={"enabled": False},
        after={"enabled": True},
        reason="Production launch",
    )
    client.force_login(staff_user)

    routes = {
        "overview": reverse("django_feature_flags_dashboard:home"),
        "flags": reverse("django_feature_flags_dashboard:flag_list"),
        "flag-detail": reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}),
        "segments": reverse("django_feature_flags_dashboard:segment_list"),
        "approvals": reverse("django_feature_flags_dashboard:approval_list"),
        "audit": reverse("django_feature_flags_dashboard:audit_list"),
        "audit-detail": reverse("django_feature_flags_dashboard:audit_detail", kwargs={"pk": log.pk}),
    }

    for screen, url in routes.items():
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert f'data-dff-screen="{screen}"' in content
        assert 'data-dff-visual-checkpoint="primary"' in content
        assert 'class="dff-app-shell"' in content
        assert 'class="dff-topbar"' in content
        assert 'id="main"' in content

    response = client.get(reverse("django_feature_flags_dashboard:approval_list"))
    content = response.content.decode()
    assert str(approval.pk) in content


def test_stylesheet_has_browser_visual_qa_primitives():
    from pathlib import Path

    stylesheet = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "django_feature_flags"
        / "static"
        / "django_feature_flags"
        / "dashboard.css"
    ).read_text()

    assert "final control-room override layer" in stylesheet
    assert ':root[data-dff-theme="dark"]' in stylesheet
    assert "@media (max-width: 1180px)" in stylesheet
    assert "@media (max-width: 760px)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
    assert ".dff-toast-region" in stylesheet
