from django.urls import path

from django_feature_flags.dashboard import views

app_name = "django_feature_flags_dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("flags/", views.flag_list, name="flag_list"),
]
