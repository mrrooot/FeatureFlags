from django_feature_flags.models import SDKKey


def authenticate_request(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    raw_secret = header.removeprefix("Bearer ").strip()
    return SDKKey.objects.authenticate(raw_secret)

