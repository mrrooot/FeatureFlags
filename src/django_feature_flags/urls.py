from django.urls import include, path

urlpatterns = [
    path("", include("django_feature_flags.dashboard.urls")),
    path("api/", include("django_feature_flags.api.urls")),
]
