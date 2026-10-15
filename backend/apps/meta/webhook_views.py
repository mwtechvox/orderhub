import hmac
import json

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.common.queue import enqueue

from .services.webhooks import persist_events, verify_signature
from .tasks import process_webhook_event


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        token = request.GET.get("hub.verify_token", "")
        if (
            request.GET.get("hub.mode") == "subscribe"
            and settings.META_WEBHOOK_VERIFY_TOKEN
            and token
            and hmac.compare_digest(token, settings.META_WEBHOOK_VERIFY_TOKEN)
        ):
            return HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
        return HttpResponse(status=403)
    raw = request.body
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        return HttpResponse(status=403)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("entry", []), list)
        or any(not isinstance(e, dict) for e in payload.get("entry", []))
    ):
        return HttpResponse(status=400)
    events = persist_events(payload)
    for event in events:
        transaction.on_commit(
            lambda e=event: enqueue(process_webhook_event, str(e.company_id), str(e.pk))
        )
    return JsonResponse({"ok": True})
