import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import Environment, Event, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_tracked_evaluation_records_event():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    evaluate("new_checkout", {"key": "user-1"}, default=False, project_key="ecommerce", environment_key="production", track=True)

    event = Event.objects.get()
    assert event.event_type == Event.EVALUATION
    assert event.context_key == "user-1"
    assert event.variation == on
