import json

import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, SDKKey, Variation


@pytest.mark.django_db
def test_evaluate_endpoint_requires_valid_sdk_key(client):
    response = client.post("/flags/api/evaluate/", data={}, content_type="application/json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_evaluate_endpoint_returns_variation_for_sdk_environment(client):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    key = SDKKey.create_for_environment(environment, name="Server SDK")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    response = client.post(
        "/flags/api/evaluate/",
        data=json.dumps({"flag_key": "new_checkout", "context": {"key": "user-1"}, "default": False}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {key.secret}",
    )

    assert response.status_code == 200
    assert response.json()["value"] is True
    assert response.json()["variation_key"] == "on"
