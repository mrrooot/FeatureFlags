import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from django_feature_flags.audit.service import create_approval_request, create_audit_log
from django_feature_flags.dashboard.forms import ApprovalRequestForm, ExperimentForm, FeatureFlagForm, SegmentForm
from django_feature_flags.dashboard.targeting_forms import TargetingDocumentForm
from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import ApprovalRequest, AuditLog, Environment, Experiment, FeatureFlag, FlagState, Project, Segment


@staff_member_required(login_url="/accounts/login/")
def dashboard_home(request):
    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("-updated_at")[:5]
    context = {
        "project_count": Project.objects.count(),
        "flag_count": FeatureFlag.objects.count(),
        "segment_count": Segment.objects.count(),
        "experiment_count": Experiment.objects.count(),
        "approval_count": ApprovalRequest.objects.filter(status=ApprovalRequest.PENDING).count(),
        "audit_count": AuditLog.objects.count(),
        "recent_flags": flags,
        "style_name": "Premium SaaS",
    }
    return render(request, "django_feature_flags/dashboard.html", context)


@staff_member_required(login_url="/accounts/login/")
def flag_list(request):
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "all")
    if selected_status not in {"all", "live", "mixed", "off", "archived"}:
        selected_status = "all"

    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("project__name", "key")
    all_rows = []
    for flag in flags:
        states = list(flag.states.all())
        enabled_count = sum(state.enabled for state in states)
        state_count = len(states)
        if flag.archived:
            status_key = "archived"
            status_label = "Archived"
        elif enabled_count and enabled_count == state_count:
            status_key = "live"
            status_label = "On everywhere"
        elif enabled_count:
            status_key = "mixed"
            status_label = f"{enabled_count} on"
        else:
            status_key = "off"
            status_label = "Configured off"

        all_rows.append(
            {
                "flag": flag,
                "states": states,
                "enabled_count": enabled_count,
                "state_count": state_count,
                "status_key": status_key,
                "status_label": status_label,
                "rollout_percent": round((enabled_count / state_count) * 100) if state_count else 0,
            }
        )

    flag_rows = all_rows
    if query:
        lowered_query = query.lower()
        flag_rows = [
            row
            for row in flag_rows
            if lowered_query in row["flag"].key.lower()
            or lowered_query in row["flag"].name.lower()
            or lowered_query in row["flag"].project.key.lower()
            or lowered_query in row["flag"].project.name.lower()
        ]
    if selected_status != "all":
        flag_rows = [row for row in flag_rows if row["status_key"] == selected_status]

    board_stats = {
        "total": len(all_rows),
        "live": sum(1 for row in all_rows if row["status_key"] == "live"),
        "mixed": sum(1 for row in all_rows if row["status_key"] == "mixed"),
        "off": sum(1 for row in all_rows if row["status_key"] == "off"),
        "archived": sum(1 for row in all_rows if row["status_key"] == "archived"),
    }
    return render(
        request,
        "django_feature_flags/flag_list.html",
        {
            "flag_rows": flag_rows,
            "board_stats": board_stats,
            "query": query,
            "selected_status": selected_status,
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def flag_create(request):
    if request.method == "POST":
        form = FeatureFlagForm(request.POST)
        if form.is_valid():
            flag = form.save()
            messages.success(request, f"Flag {flag.key} was created.")
            return redirect("django_feature_flags_dashboard:flag_list")
    else:
        form = FeatureFlagForm()

    return render(
        request,
        "django_feature_flags/flag_form.html",
        {
            "form": form,
            "form_title": "Create flag",
            "form_kicker": "Flag console",
            "submit_label": "Create flag",
            "side_heading": "Current default",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def flag_detail(request, pk):
    flag = get_object_or_404(
        FeatureFlag.objects.select_related("project").prefetch_related("variations", "states__environment"),
        pk=pk,
    )
    environment_key = request.POST.get("environment") or request.GET.get("environment")
    states = list(flag.states.select_related("environment", "default_variation").order_by("environment__name"))
    state = _selected_state(states, environment_key)

    if request.method == "POST":
        form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state, data=request.POST)
        if form.is_valid():
            before = {"enabled": state.enabled, "targeting": state.targeting}
            proposed_change = {"enabled": form.enabled, "targeting": form.cleaned_document}
            if state.environment.requires_approval:
                create_approval_request(
                    requested_by=request.user,
                    environment=state.environment,
                    flag=flag,
                    proposed_change=proposed_change,
                    reason=form.cleaned_data.get("reason", ""),
                )
                messages.success(request, f"Approval request for {flag.key} targeting was created.")
            else:
                with transaction.atomic():
                    state.enabled = form.enabled
                    state.targeting = form.cleaned_document
                    state.save(update_fields=["enabled", "targeting", "updated_at"])
                    create_audit_log(
                        user=request.user,
                        environment=state.environment,
                        flag=flag,
                        action="flag.targeting.updated",
                        before=before,
                        after=proposed_change,
                        reason=form.cleaned_data.get("reason", ""),
                    )
                messages.success(request, f"Targeting for {flag.key} was updated.")
            return redirect(f"{request.path}?environment={state.environment.key}")
    else:
        form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state)

    return render(
        request,
        "django_feature_flags/flag_detail.html",
        {
            "flag": flag,
            "states": states,
            "state": state,
            "form": form,
            "targeting": form.initial_document(),
            "variations": flag.variations.order_by("key"),
            "available_flags": flag.project.flags.exclude(pk=flag.pk).order_by("key"),
            "segments": flag.project.segments.order_by("key"),
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
@require_POST
def flag_targeting_preview(request, pk):
    flag = get_object_or_404(FeatureFlag.objects.select_related("project"), pk=pk)
    state = get_object_or_404(
        FlagState.objects.select_related("environment", "default_variation"),
        flag=flag,
        environment__key=request.POST.get("environment", ""),
    )
    form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state, data=request.POST)
    preview_error = ""
    preview_result = None
    preview_context = request.POST.get("preview_context", "{}") or "{}"
    if form.is_valid():
        try:
            parsed_context = json.loads(preview_context)
        except json.JSONDecodeError:
            preview_error = "Preview context must be valid JSON."
        else:
            preview_result = evaluate(
                flag.key,
                parsed_context,
                default=None,
                project_key=flag.project.key,
                environment_key=state.environment.key,
                targeting_override=form.cleaned_document,
                enabled_override=form.enabled,
            )

    states = list(flag.states.select_related("environment", "default_variation").order_by("environment__name"))
    return render(
        request,
        "django_feature_flags/flag_detail.html",
        {
            "flag": flag,
            "states": states,
            "state": state,
            "form": form,
            "targeting": form.cleaned_document or form.initial_document(),
            "variations": flag.variations.order_by("key"),
            "available_flags": flag.project.flags.exclude(pk=flag.pk).order_by("key"),
            "segments": flag.project.segments.order_by("key"),
            "preview_context": preview_context,
            "preview_result": preview_result,
            "preview_error": preview_error,
            "style_name": "Premium SaaS",
        },
    )


def _selected_state(states, environment_key):
    if environment_key:
        for state in states:
            if state.environment.key == environment_key:
                return state
    return states[0]


@staff_member_required(login_url="/accounts/login/")
def flag_update(request, pk):
    flag = get_object_or_404(FeatureFlag.objects.select_related("project"), pk=pk)
    if request.method == "POST":
        form = FeatureFlagForm(request.POST, instance=flag)
        if form.is_valid():
            flag = form.save()
            messages.success(request, f"Flag {flag.key} was updated.")
            return redirect("django_feature_flags_dashboard:flag_list")
    else:
        form = FeatureFlagForm(instance=flag)

    return render(
        request,
        "django_feature_flags/flag_form.html",
        {
            "flag": flag,
            "form": form,
            "form_title": "Update flag",
            "form_kicker": "Flag console",
            "submit_label": "Update flag",
            "side_heading": "Current default",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def segment_list(request):
    segments = Segment.objects.select_related("project").prefetch_related("rules").order_by("project__name", "key")
    return render(
        request,
        "django_feature_flags/segment_list.html",
        {
            "segments": segments,
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def segment_create(request):
    if request.method == "POST":
        form = SegmentForm(request.POST)
        if form.is_valid():
            segment = form.save()
            messages.success(request, f"Segment {segment.key} was created.")
            return redirect("django_feature_flags_dashboard:segment_list")
    else:
        form = SegmentForm()

    return render(
        request,
        "django_feature_flags/segment_form.html",
        {
            "form": form,
            "form_title": "Create segment",
            "form_kicker": "Audience console",
            "submit_label": "Create segment",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def segment_update(request, pk):
    segment = get_object_or_404(Segment.objects.select_related("project").prefetch_related("rules"), pk=pk)
    if request.method == "POST":
        form = SegmentForm(request.POST, instance=segment)
        if form.is_valid():
            segment = form.save()
            messages.success(request, f"Segment {segment.key} was updated.")
            return redirect("django_feature_flags_dashboard:segment_list")
    else:
        form = SegmentForm(instance=segment)

    return render(
        request,
        "django_feature_flags/segment_form.html",
        {
            "segment": segment,
            "form": form,
            "form_title": "Update segment",
            "form_kicker": "Audience console",
            "submit_label": "Update segment",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def experiment_list(request):
    experiments = (
        Experiment.objects.select_related("flag", "flag__project")
        .prefetch_related("allocations__variation")
        .order_by("flag__project__name", "key")
    )
    experiment_rows = []
    for experiment in experiments:
        allocations = []
        for allocation in experiment.allocations.all():
            allocations.append(
                {
                    "allocation": allocation,
                    "percent": allocation.weight / 1000,
                }
            )
        experiment_rows.append({"experiment": experiment, "allocations": allocations})
    return render(
        request,
        "django_feature_flags/experiment_list.html",
        {
            "experiments": experiments,
            "experiment_rows": experiment_rows,
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def experiment_create(request):
    if request.method == "POST":
        form = ExperimentForm(request.POST)
        if form.is_valid():
            experiment = form.save()
            messages.success(request, f"Experiment {experiment.key} was created.")
            return redirect("django_feature_flags_dashboard:experiment_list")
    else:
        form = ExperimentForm()

    return render(
        request,
        "django_feature_flags/experiment_form.html",
        {
            "form": form,
            "form_title": "Create experiment",
            "form_kicker": "Experiment console",
            "submit_label": "Create experiment",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def experiment_update(request, pk):
    experiment = get_object_or_404(
        Experiment.objects.select_related("flag", "flag__project").prefetch_related("allocations__variation"),
        pk=pk,
    )
    if request.method == "POST":
        form = ExperimentForm(request.POST, instance=experiment)
        if form.is_valid():
            experiment = form.save()
            messages.success(request, f"Experiment {experiment.key} was updated.")
            return redirect("django_feature_flags_dashboard:experiment_list")
    else:
        form = ExperimentForm(instance=experiment)

    return render(
        request,
        "django_feature_flags/experiment_form.html",
        {
            "experiment": experiment,
            "form": form,
            "form_title": "Update experiment",
            "form_kicker": "Experiment console",
            "submit_label": "Update experiment",
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def approval_list(request):
    approvals = (
        ApprovalRequest.objects.select_related("environment", "environment__project", "flag", "requested_by", "reviewed_by")
        .order_by("status", "-created_at")
    )
    return render(
        request,
        "django_feature_flags/approval_list.html",
        {
            "approvals": approvals,
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def approval_create(request):
    if request.method == "POST":
        form = ApprovalRequestForm(request.POST, requested_by=request.user)
        if form.is_valid():
            approval = form.save()
            messages.success(request, f"Approval request for {approval.flag.key} was created.")
            return redirect("django_feature_flags_dashboard:approval_list")
    else:
        form = ApprovalRequestForm(requested_by=request.user)

    return render(
        request,
        "django_feature_flags/approval_form.html",
        {
            "form": form,
            "form_title": "Create approval request",
            "form_kicker": "Approval queue",
            "submit_label": "Create request",
            "style_name": "Premium SaaS",
        },
    )


def _review_approval(request, pk, status, action):
    approval = get_object_or_404(
        ApprovalRequest.objects.select_related("environment", "flag"),
        pk=pk,
    )
    before = {"status": approval.status}
    approval.status = status
    approval.reviewed_by = request.user
    approval.reviewed_at = timezone.now()
    approval.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    create_audit_log(
        user=request.user,
        environment=approval.environment,
        flag=approval.flag,
        action=action,
        before=before,
        after={"status": approval.status},
        reason=approval.reason,
    )
    messages.success(request, f"Approval request for {approval.flag.key} was {status}.")
    return redirect("django_feature_flags_dashboard:approval_list")


@staff_member_required(login_url="/accounts/login/")
@require_POST
def approval_approve(request, pk):
    return _review_approval(request, pk, ApprovalRequest.APPROVED, "approval.approved")


@staff_member_required(login_url="/accounts/login/")
@require_POST
def approval_reject(request, pk):
    return _review_approval(request, pk, ApprovalRequest.REJECTED, "approval.rejected")


@staff_member_required(login_url="/accounts/login/")
def audit_list(request):
    logs = AuditLog.objects.select_related("user", "environment", "flag").order_by("-created_at")
    action = request.GET.get("action", "").strip()
    flag_id = request.GET.get("flag", "").strip()
    environment_id = request.GET.get("environment", "").strip()
    if action:
        logs = logs.filter(action__icontains=action)
    if flag_id:
        logs = logs.filter(flag_id=flag_id)
    if environment_id:
        logs = logs.filter(environment_id=environment_id)

    return render(
        request,
        "django_feature_flags/audit_list.html",
        {
            "logs": logs[:100],
            "filters": {
                "action": action,
                "flag": flag_id,
                "environment": environment_id,
            },
            "flags": FeatureFlag.objects.order_by("project__name", "key"),
            "environments": Environment.objects.order_by("project__name", "name"),
            "style_name": "Premium SaaS",
        },
    )


@staff_member_required(login_url="/accounts/login/")
def audit_detail(request, pk):
    log = get_object_or_404(AuditLog.objects.select_related("user", "environment", "flag"), pk=pk)
    return render(
        request,
        "django_feature_flags/audit_detail.html",
        {
            "log": log,
            "before_json": json.dumps(log.before, indent=2, sort_keys=True),
            "after_json": json.dumps(log.after, indent=2, sort_keys=True),
            "style_name": "Premium SaaS",
        },
    )
