from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from django_feature_flags.models import FeatureFlag, Project


@staff_member_required(login_url="/accounts/login/")
def dashboard_home(request):
    context = {
        "project_count": Project.objects.count(),
        "flag_count": FeatureFlag.objects.count(),
        "style_name": "Premium SaaS",
    }
    return render(request, "django_feature_flags/dashboard.html", context)


@staff_member_required(login_url="/accounts/login/")
def flag_list(request):
    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("project__name", "key")
    return render(request, "django_feature_flags/flag_list.html", {"flags": flags, "style_name": "Premium SaaS"})
