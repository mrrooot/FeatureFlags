from django.urls import path

from django_feature_flags.dashboard import views

app_name = "django_feature_flags_dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("flags/", views.flag_list, name="flag_list"),
    path("flags/new/", views.flag_create, name="flag_create"),
    path("flags/<int:pk>/", views.flag_detail, name="flag_detail"),
    path("flags/<int:pk>/targeting/preview/", views.flag_targeting_preview, name="flag_targeting_preview"),
    path("flags/<int:pk>/edit/", views.flag_update, name="flag_update"),
    path("segments/", views.segment_list, name="segment_list"),
    path("segments/new/", views.segment_create, name="segment_create"),
    path("segments/<int:pk>/edit/", views.segment_update, name="segment_update"),
    path("experiments/", views.experiment_list, name="experiment_list"),
    path("experiments/new/", views.experiment_create, name="experiment_create"),
    path("experiments/<int:pk>/edit/", views.experiment_update, name="experiment_update"),
    path("approvals/", views.approval_list, name="approval_list"),
    path("approvals/new/", views.approval_create, name="approval_create"),
    path("approvals/<int:pk>/approve/", views.approval_approve, name="approval_approve"),
    path("approvals/<int:pk>/reject/", views.approval_reject, name="approval_reject"),
    path("audit/", views.audit_list, name="audit_list"),
    path("audit/<int:pk>/", views.audit_detail, name="audit_detail"),
]
