from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from django_feature_flags.dashboard.forms import FeatureFlagForm
from django_feature_flags.models import FeatureFlag, Project


@staff_member_required(login_url="/accounts/login/")
def dashboard_home(request):
    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("-updated_at")[:5]
    context = {
        "project_count": Project.objects.count(),
        "flag_count": FeatureFlag.objects.count(),
        "recent_flags": flags,
        "style_name": "Premium SaaS",
    }
    return render(request, "django_feature_flags/dashboard.html", context)


@staff_member_required(login_url="/accounts/login/")
def flag_list(request):
    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("project__name", "key")
    flag_rows = []
    for flag in flags:
        states = list(flag.states.all())
        flag_rows.append(
            {
                "flag": flag,
                "states": states,
                "enabled_count": sum(state.enabled for state in states),
            }
        )
    return render(
        request,
        "django_feature_flags/flag_list.html",
        {
            "flag_rows": flag_rows,
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
            "form_kicker": "Launch sequence",
            "submit_label": "Create flag",
            "side_heading": "Default variation",
            "style_name": "Premium SaaS",
        },
    )


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
