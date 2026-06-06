import json
from io import StringIO

import pytest
from django.core.management import call_command

from django_feature_flags.models import (
    Environment,
    Event,
    Experiment,
    ExperimentResultSnapshot,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Variation,
)


@pytest.mark.django_db
def test_export_omits_sdk_keys_and_events():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    SDKKey.create_for_environment(environment, name="Server SDK")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    variation = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=variation)
    Event.objects.create(environment=environment, flag=flag, variation=variation, event_type=Event.EVALUATION, context_key="user-1")
    output = StringIO()

    call_command("featureflags", "export", "--project", "ecommerce", stdout=output)

    payload = json.loads(output.getvalue())
    assert payload["project"]["key"] == "ecommerce"
    assert payload["flags"][0]["key"] == "new_checkout"
    assert "sdk_keys" not in payload
    assert "events" not in payload


@pytest.mark.django_db
def test_rotate_key_deactivates_old_key_and_creates_new_key():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    old_key = SDKKey.create_for_environment(environment, name="Server SDK")
    output = StringIO()

    call_command("featureflags", "rotate-key", "--project", "ecommerce", "--environment", "production", stdout=output)

    old_key.refresh_from_db()
    assert old_key.active is False
    assert SDKKey.objects.filter(environment=environment, active=True).count() == 1
    assert "dff_" in output.getvalue()


@pytest.mark.django_db
def test_snapshot_results_creates_experiment_snapshot():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)

    call_command("featureflags", "snapshot-results")

    assert ExperimentResultSnapshot.objects.filter(experiment=experiment).exists()
