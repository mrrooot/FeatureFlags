import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.experiments.service import choose_experiment_variation
from django_feature_flags.models import (
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    FlagState,
    Project,
    Variation,
)


@pytest.mark.django_db
def test_choose_experiment_variation_is_stable_for_context():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    control = Variation.objects.create(flag=flag, key="control", value=False)
    treatment = Variation.objects.create(flag=flag, key="treatment", value=True)
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)
    ExperimentAllocation.objects.create(experiment=experiment, variation=control, weight=50000)
    ExperimentAllocation.objects.create(experiment=experiment, variation=treatment, weight=50000)

    first = choose_experiment_variation(experiment, {"key": "user-1"})
    second = choose_experiment_variation(experiment, {"key": "user-1"})

    assert first == second
    assert first.key in {"control", "treatment"}


@pytest.mark.django_db
def test_evaluator_uses_running_experiment_before_fallthrough():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=off)
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)
    ExperimentAllocation.objects.create(experiment=experiment, variation=on, weight=100000)

    result = evaluate("new_checkout", {"key": "user-1"}, default=False, project_key="ecommerce", environment_key="production")

    assert result.value is True
    assert result.reason == "experiment"
