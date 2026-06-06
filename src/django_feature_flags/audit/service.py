from django_feature_flags.models import ApprovalRequest, AuditLog


def create_audit_log(user, environment, flag, action, before, after, reason=""):
    return AuditLog.objects.create(
        user=user,
        environment=environment,
        flag=flag,
        action=action,
        before=before,
        after=after,
        reason=reason,
    )


def create_approval_request(requested_by, environment, flag, proposed_change, reason=""):
    return ApprovalRequest.objects.create(
        requested_by=requested_by,
        environment=environment,
        flag=flag,
        proposed_change=proposed_change,
        reason=reason,
    )
