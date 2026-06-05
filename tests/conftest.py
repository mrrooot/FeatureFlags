import pytest


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin",
        password="password",
        is_staff=True,
    )
