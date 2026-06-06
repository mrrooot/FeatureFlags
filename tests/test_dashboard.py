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
