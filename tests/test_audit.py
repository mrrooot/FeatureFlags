import pytest

from django_feature_flags.audit.service import create_audit_log, create_approval_request
from django_feature_flags.models import ApprovalRequest, AuditLog, Environment, FeatureFlag, Project


@pytest.mark.django_db
def test_create_audit_log_records_before_after(staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")

    log = create_audit_log(
        user=staff_user,
        environment=environment,
        flag=flag,
        action="flag.update",
        before={"enabled": False},
        after={"enabled": True},
        reason="Release checkout",
    )

    assert AuditLog.objects.get() == log
    assert log.before["enabled"] is False
    assert log.after["enabled"] is True


@pytest.mark.django_db
def test_create_approval_request_for_environment(staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")

    request = create_approval_request(
        requested_by=staff_user,
        environment=environment,
        flag=flag,
        proposed_change={"enabled": True},
        reason="Production launch",
    )

    assert request.status == ApprovalRequest.PENDING
    assert request.proposed_change["enabled"] is True
