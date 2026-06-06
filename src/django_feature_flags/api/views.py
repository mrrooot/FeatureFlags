import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_feature_flags.api.auth import authenticate_request
from django_feature_flags.evaluation.evaluator import evaluate


@csrf_exempt
@require_POST
def evaluate_view(request):
    sdk_key = authenticate_request(request)
    if sdk_key is None:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    result = evaluate(
        payload.get("flag_key", ""),
        payload.get("context", {}),
        default=payload.get("default"),
        project_key=sdk_key.environment.project.key,
        environment_key=sdk_key.environment.key,
        track=payload.get("track", False),
    )
    return JsonResponse(
        {
            "value": result.value,
            "variation_key": result.variation_key,
            "reason": result.reason,
            "flag_key": result.flag_key,
            "environment_key": result.environment_key,
        }
    )

