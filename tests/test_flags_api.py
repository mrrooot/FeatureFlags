import pytest

from django_feature_flags import flags
from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_bool_variation_returns_boolean_value():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    assert flags.bool_variation("new_checkout", {"key": "user-1"}, default=False, project="ecommerce", environment="production") is True


@pytest.mark.django_db
def test_string_variation_returns_default_when_flag_missing():
    assert flags.string_variation("missing", {"key": "user-1"}, default="control", project="ecommerce", environment="production") == "control"
