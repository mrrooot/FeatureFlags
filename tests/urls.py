from django.urls import include, path

urlpatterns = [
    path("flags/", include("django_feature_flags.urls")),
]
