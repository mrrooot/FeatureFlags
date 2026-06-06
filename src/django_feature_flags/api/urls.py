from django.urls import path

from django_feature_flags.api.views import evaluate_view

app_name = "django_feature_flags_api"

urlpatterns = [
    path("evaluate/", evaluate_view, name="evaluate"),
]

