from django.urls import path

from django_feature_flags.dashboard import views

app_name = "django_feature_flags_dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("flags/", views.flag_list, name="flag_list"),
    path("flags/new/", views.flag_create, name="flag_create"),
    path("flags/<int:pk>/edit/", views.flag_update, name="flag_update"),
]
