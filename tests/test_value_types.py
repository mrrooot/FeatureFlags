"""Typed variation helpers return correctly-typed values."""
import pytest

from django_feature_flags import flags
from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.fixture
def project_env():
    project = Project.objects.create(key="p", name="P")
    environment = Environment.objects.create(project=project, key="production", name="Prod")
    return project, environment


def build(project, environment, key, value_type, variations, target_value_key):
    flag = FeatureFlag.objects.create(project=project, key=key, name=key, value_type=value_type)
    default = None
    for vkey, value, is_default in variations:
        variation = Variation.objects.create(flag=flag, key=vkey, value=value, is_default=is_default)
        if is_default:
            default = variation
    FlagState.objects.create(
        flag=flag, environment=environment, enabled=True, default_variation=default,
        targeting={
            "off_variation": variations[0][0],
            "targets": [{"context_kind": "user", "variation_key": target_value_key, "values": ["hit"]}],
            "fallthrough": {"variation_key": variations[0][0]},
        },
    )
    return flag


def opts():
    return dict(project="p", environment="production")


@pytest.mark.django_db
def test_bool_variation(project_env):
    project, environment = project_env
    build(project, environment, "b", "boolean", [("off", False, True), ("on", True, False)], "on")
    assert flags.bool_variation("b", {"key": "hit"}, default=False, **opts()) is True
    assert flags.bool_variation("b", {"key": "other"}, default=False, **opts()) is False


@pytest.mark.django_db
def test_string_variation(project_env):
    project, environment = project_env
    build(project, environment, "s", "string", [("control", "control", True), ("treat", "treatment", False)], "treat")
    assert flags.string_variation("s", {"key": "hit"}, default="", **opts()) == "treatment"
    assert flags.string_variation("s", {"key": "other"}, default="", **opts()) == "control"


@pytest.mark.django_db
def test_number_variation(project_env):
    project, environment = project_env
    build(project, environment, "n", "number", [("zero", 0, True), ("ten", 10, False)], "ten")
    assert flags.number_variation("n", {"key": "hit"}, default=0, **opts()) == 10
    assert flags.number_variation("n", {"key": "other"}, default=0, **opts()) == 0


@pytest.mark.django_db
def test_json_variation(project_env):
    project, environment = project_env
    build(project, environment, "j", "json", [("base", {}, True), ("blue", {"color": "blue"}, False)], "blue")
    assert flags.json_variation("j", {"key": "hit"}, **opts()) == {"color": "blue"}
    assert flags.json_variation("j", {"key": "other"}, **opts()) == {}


@pytest.mark.django_db
def test_typed_helpers_return_defaults_when_flag_missing(project_env):
    assert flags.bool_variation("ghost", {"key": "u"}, default=True, **opts()) is True
    assert flags.string_variation("ghost", {"key": "u"}, default="dv", **opts()) == "dv"
    assert flags.number_variation("ghost", {"key": "u"}, default=7, **opts()) == 7
    assert flags.json_variation("ghost", {"key": "u"}, default={"a": 1}, **opts()) == {"a": 1}
