import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.fixture
def boolean_flag_stack():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", name="Off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", name="On", value=True)
    state = FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    return project, environment, flag, state, off, on


@pytest.mark.django_db
def test_flag_state_targeting_defaults_to_empty_document(boolean_flag_stack):
    _, _, _, state, _, _ = boolean_flag_stack

    assert state.targeting == {}
