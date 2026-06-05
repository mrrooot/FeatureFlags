import pytest
from django.core.management import call_command

from django_feature_flags.models import Environment, Project, SDKKey


@pytest.mark.django_db
def test_bootstrap_creates_project_environments_and_sdk_keys():
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")

    project = Project.objects.get(key="ecommerce")
    assert project.name == "Ecommerce"
    assert set(project.environments.values_list("key", flat=True)) == {"development", "staging", "production"}
    assert SDKKey.objects.filter(environment__project=project).count() == 3


@pytest.mark.django_db
def test_bootstrap_is_idempotent():
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")

    assert Project.objects.count() == 1
    assert Environment.objects.count() == 3
