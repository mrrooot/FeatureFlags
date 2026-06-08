import django_feature_flags


def test_package_exposes_version():
    assert django_feature_flags.__version__ == "0.2.0"
