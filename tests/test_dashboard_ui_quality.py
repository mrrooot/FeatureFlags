from pathlib import Path

import pytest
from django.urls import reverse

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "django_feature_flags"


@pytest.mark.django_db
def test_control_room_dashboard_renders_operational_landmarks(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'aria-label="Primary navigation"' in content
    assert 'aria-current="page"' in content
    assert "Feature release control center" in content
    assert "Environment signal" in content
    assert "Recent audit activity" in content
    assert "data-dff-command-search" in content
    assert "data-dff-theme-toggle" in content


@pytest.mark.django_db
def test_flag_workspaces_render_control_center_structure(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    production = Environment.objects.create(
        project=project,
        key="production",
        name="Production",
        requires_approval=True,
        require_change_reason=True,
    )
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=production, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Environment lanes" in content
    assert "Operational rows" in content
    assert 'data-dff-flag-row' in content

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Flag control center" in content
    assert "Release safety" in content
    assert "SDK usage" in content
    assert "Environment lanes" in content
    assert "This change affects production" in content
    assert "Copy SDK snippet" in content


def test_dashboard_static_assets_follow_no_build_security_constraints():
    static_dir = PACKAGE_ROOT / "static" / "django_feature_flags"
    template_dir = PACKAGE_ROOT / "templates" / "django_feature_flags"
    css = (static_dir / "dashboard.css").read_text()
    dashboard_js = (static_dir / "dashboard.js").read_text()
    targeting_js = (static_dir / "targeting.js").read_text()
    templates = "\n".join(path.read_text() for path in template_dir.glob("*.html"))
    project_files = {path.name for path in PACKAGE_ROOT.parents[2].iterdir() if path.is_file()}

    assert "http://" not in css
    assert "https://" not in css
    assert "@import" not in css
    assert "Aptos" not in css
    assert "Cascadia" not in css
    assert "innerHTML" not in dashboard_js
    assert "innerHTML" not in targeting_js
    assert "eval(" not in dashboard_js + targeting_js
    assert "new Function" not in dashboard_js + targeting_js
    assert "|safe" not in templates
    assert "package.json" not in project_files
    assert "package-lock.json" not in project_files
