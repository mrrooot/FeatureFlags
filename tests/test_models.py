import pytest

from django_feature_flags.models import (
    Environment,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Variation,
)


@pytest.mark.django_db
def test_flag_definition_is_global_and_state_is_per_environment():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    production = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)

    staging_state = FlagState.objects.create(flag=flag, environment=staging, enabled=True, default_variation=on)
    production_state = FlagState.objects.create(flag=flag, environment=production, enabled=False, default_variation=off)

    assert flag.states.count() == 2
    assert staging_state.default_variation.value is True
    assert production_state.default_variation.value is False


@pytest.mark.django_db
def test_sdk_key_is_environment_specific_and_secret_is_hashed():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")

    sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")

    assert sdk_key.secret.startswith("dff_")
    assert sdk_key.secret_hash != sdk_key.secret
    assert SDKKey.objects.authenticate(sdk_key.secret) == sdk_key
