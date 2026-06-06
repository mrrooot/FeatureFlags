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
    assert b"Premium SaaS" in response.content


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
    assert "Configured environments" in content
    assert "development" in content
    assert "staging" in content
    assert "production" in content
    assert 'name="environments"' not in content


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
    assert "Configured environments" in content
    assert "development" in content
    assert "production" in content
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
    assert "Edit flag" in content
    assert reverse("django_feature_flags_dashboard:flag_update", kwargs={"pk": flag.pk}) in content


@pytest.mark.django_db
def test_flag_list_shows_create_action(client, staff_user):
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"New flag" in response.content
    assert b"/flags/flags/new/" in response.content


@pytest.mark.django_db
def test_overview_uses_release_observatory_workspace(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Release Observatory" in content
    assert "Release posture" in content
    assert "Release timeline" in content
    assert "Latest flag ledger" in content
    assert "Reviewable by default" in content
    assert "new_checkout" in content


@pytest.mark.django_db
def test_flag_list_uses_ledger_language_and_status_stamps(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=staging, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Flag ledger" in content
    assert "Scan mode" in content
    assert "Flag keys" in content
    assert "Configured off" in content
    assert "staging" in content
    assert "Recommendations" in content


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
    assert "Configured environments" in content
