import pytest
from django.urls import reverse

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_dashboard_requires_staff(client):
    response = client.get("/flags/")

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_staff_can_view_flag_list(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"new_checkout" in response.content
    assert b"Feature flags" in response.content


@pytest.mark.django_db
def test_create_flag_requires_staff(client):
    response = client.get("/flags/flags/new/")

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_staff_can_open_create_flag_form(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "staging", "production")
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    client.force_login(staff_user)

    response = client.get("/flags/flags/new/")

    assert response.status_code == 200
    assert b"Create flag" in response.content
    content = response.content.decode()
    assert "Deployment managed" in content
    assert "configured automatically from your .env" in content
    assert "Configured environments" not in content
    assert "development" not in content
    assert "staging" not in content
    assert "production" not in content
    assert 'name="environments"' not in content


@pytest.mark.django_db
def test_create_flag_form_exposes_interaction_hooks(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "staging", "production")
    Project.objects.create(key="ecommerce", name="Ecommerce")
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_create"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-dff-flag-form' in content
    assert 'data-dff-step-target="identity"' in content
    assert 'data-dff-step-target="payload"' in content
    assert 'data-dff-step-target="sync"' in content
    assert 'data-dff-form-section="identity"' in content
    assert 'data-dff-form-section="payload"' in content
    assert 'data-dff-form-section="sync"' in content
    assert 'data-dff-field' in content
    assert 'data-dff-launch-submit' in content


@pytest.mark.django_db
def test_staff_can_create_flag_with_default_variation_and_configured_environment_states(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "staging", "production")
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    client.force_login(staff_user)

    response = client.post(
        "/flags/flags/new/",
        {
            "project": project.id,
            "key": "recommendations",
            "name": "Recommendations",
            "description": "Personalized products module",
            "value_type": "boolean",
            "default_value": "true",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/flags/flags/"
    flag = FeatureFlag.objects.get(project=project, key="recommendations")
    assert flag.name == "Recommendations"
    assert flag.description == "Personalized products module"
    variation = flag.variations.get(key="default")
    assert variation.name == "Default"
    assert variation.value is True
    assert variation.is_default is True
    assert set(project.environments.values_list("key", flat=True)) == {"development", "staging", "production"}
    assert set(flag.states.values_list("environment__key", flat=True)) == {"development", "staging", "production"}
    assert flag.states.filter(enabled=False, default_variation=variation).count() == 3


@pytest.mark.django_db
def test_staff_can_update_flag_and_sync_configured_environment_states(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "production")
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    development = Environment.objects.create(project=project, key="development", name="Development")
    flag = FeatureFlag.objects.create(
        project=project,
        key="recommendations",
        name="Recommendations",
        description="Old copy",
        value_type="boolean",
    )
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=development, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:flag_update", kwargs={"pk": flag.pk}),
        {
            "project": project.id,
            "key": "recommendations",
            "name": "Recommendations v2",
            "description": "Updated rollout decision",
            "value_type": "boolean",
            "default_value": "true",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/flags/flags/"
    flag.refresh_from_db()
    default.refresh_from_db()
    assert flag.name == "Recommendations v2"
    assert flag.description == "Updated rollout decision"
    assert default.value is True
    assert set(project.environments.values_list("key", flat=True)) == {"development", "production"}
    assert set(flag.states.values_list("environment__key", flat=True)) == {"development", "production"}
    assert flag.states.filter(enabled=False, default_variation=default).count() == 2


@pytest.mark.django_db
def test_staff_can_open_update_flag_form(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "production")
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_update", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Update flag" in content
    assert "Deployment managed" in content
    assert "configured automatically from your .env" in content
    assert "Configured environments" not in content
    assert "development" not in content
    assert "production" not in content
    assert 'name="environments"' not in content


@pytest.mark.django_db
def test_flag_list_shows_update_action(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Open" in content
    assert reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}) in content


@pytest.mark.django_db
def test_flag_list_edit_action_opens_flag_detail(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    assert reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}) in response.content.decode()


@pytest.mark.django_db
def test_flag_detail_renders_modern_targeting_workspace(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Targeting" in content
    assert "If all prerequisites pass" in content
    assert "Individual targets" in content
    assert "Segment rules" in content
    assert "Custom rules" in content
    assert "Default rule" in content
    assert "When targeting is off" in content
    assert "Preview evaluation" in content
    assert "Unsaved changes" in content
    assert 'data-save-bar' in content
    assert "targeting.js" in content


@pytest.mark.django_db
def test_targeting_workspace_has_unsaved_change_save_bar(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-targeting-form' in content
    assert 'data-save-bar' in content
    assert 'data-dirty-count' in content
    assert "Unsaved changes" in content
    assert "Save targeting" in content


@pytest.mark.django_db
def test_flag_list_shows_create_action(client, staff_user):
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"Create flag" in response.content
    assert b"/flags/flags/new/" in response.content


@pytest.mark.django_db
def test_overview_uses_launchdarkly_style_console(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Feature flag console" in content
    assert "Recently updated flags" in content
    assert "Needs review" in content
    assert "Quick actions" in content
    assert "new_checkout" in content
    assert "Release Observatory" not in content
    assert "dff-radar" not in content
    assert "Release timeline" not in content


@pytest.mark.django_db
def test_overview_console_links_to_workflows(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'href="#"' not in content
    assert "dff-quick-actions" in content
    assert "dff-review-list" in content
    assert reverse("django_feature_flags_dashboard:segment_list") in content
    assert reverse("django_feature_flags_dashboard:experiment_list") in content
    assert reverse("django_feature_flags_dashboard:audit_list") in content
    assert reverse("django_feature_flags_dashboard:approval_list") in content
    assert reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}) in content


@pytest.mark.django_db
def test_flag_list_uses_feature_flag_console_table(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=staging, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Feature flags" in content
    assert "Create flag" in content
    assert "Rollout board" in content
    assert "Active in" in content
    assert "dff-flag-board-shell" in content
    assert "dff-flag-board-row" in content
    assert "Targeting" in content
    assert "Configured off" in content
    assert "staging" in content
    assert "Recommendations" in content
    assert "Flag ledger" not in content
    assert "Scan mode" not in content


@pytest.mark.django_db
def test_flag_list_filters_board_by_status_and_search(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    production = Environment.objects.create(project=project, key="production", name="Production")
    live_flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    off_flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    live_default = Variation.objects.create(flag=live_flag, key="default", name="Default", value=False, is_default=True)
    off_default = Variation.objects.create(flag=off_flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=live_flag, environment=production, enabled=True, default_variation=live_default)
    FlagState.objects.create(flag=off_flag, environment=production, enabled=False, default_variation=off_default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"), {"status": "live", "q": "recommend"})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Recommendations" in content
    assert "checkout" not in content
    assert 'value="recommend"' in content
    assert 'value="live" selected' in content


@pytest.mark.django_db
def test_dashboard_shell_uses_light_console_structure(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="dff-app-shell"' in content
    assert 'class="dff-sidebar"' in content
    assert 'class="dff-topbar"' in content
    assert "Feature flags" in content
    assert "Segments" in content
    assert "Audit log" in content
    assert "Project" in content
    assert "Environment" in content
    assert "Release Observatory" not in content


@pytest.mark.django_db
def test_dashboard_shell_loads_visual_refresh_layer(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-dff-visual-root' in content
    assert 'data-dff-metric-card' in content
    assert 'data-dff-metric-value' in content
    assert "django_feature_flags/dashboard.js" in content


@pytest.mark.django_db
def test_create_flag_form_uses_guided_observatory_copy(client, staff_user, settings):
    settings.DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "staging", "production")
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_create"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Launch sequence" in content
    assert "Default variation" in content
    assert "Safe by default" in content
    assert "Project scoped key" in content
    assert "Deployment managed" in content
    assert "configured automatically from your .env" in content
    assert "Configured environments" not in content
