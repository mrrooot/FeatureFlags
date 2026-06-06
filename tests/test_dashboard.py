import pytest

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
def test_staff_can_open_create_flag_form(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    Environment.objects.create(project=project, key="staging", name="Staging")
    client.force_login(staff_user)

    response = client.get("/flags/flags/new/")

    assert response.status_code == 200
    assert b"Create flag" in response.content
    assert b"staging" in response.content


@pytest.mark.django_db
def test_staff_can_create_flag_with_default_variation_and_environment_states(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    production = Environment.objects.create(project=project, key="production", name="Production")
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
            "environments": [staging.id, production.id],
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
    assert set(flag.states.values_list("environment__key", flat=True)) == {"staging", "production"}
    assert flag.states.filter(enabled=False, default_variation=variation).count() == 2


@pytest.mark.django_db
def test_flag_list_shows_create_action(client, staff_user):
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"New flag" in response.content
    assert b"/flags/flags/new/" in response.content
