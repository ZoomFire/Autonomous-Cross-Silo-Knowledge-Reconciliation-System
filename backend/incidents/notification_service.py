import json
from urllib import request as url_request
from urllib.error import HTTPError, URLError
from uuid import uuid4

from config import WEBHOOK_TIMEOUT_SECONDS
from database.repositories import NotificationDeliveryRepository, WebhookRepository

from .templates import DEFAULT_NOTIFICATION_TEMPLATES, render_template


def _event_matches(webhook: dict, event_type: str) -> bool:
    event_types = webhook.get("event_types") or []
    return not event_types or event_type in event_types or "*" in event_types


def _delivery_payload(event_type: str, incident: dict, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    template = DEFAULT_NOTIFICATION_TEMPLATES.get(event_type, {})
    context = {**incident, **metadata, "event_type": event_type}
    return {
        "event_type": event_type,
        "subject": render_template(template.get("subject", event_type), context),
        "body": render_template(template.get("body", ""), context),
        "incident": incident,
        "metadata": metadata,
    }


def notify_incident_event(workspace_id: str, event_type: str, incident: dict, metadata: dict | None = None) -> list[dict]:
    deliveries = []
    payload = _delivery_payload(event_type, incident, metadata)
    webhooks = [webhook for webhook in WebhookRepository.list_by_workspace(workspace_id, enabled_only=True) if _event_matches(webhook, event_type)]
    for webhook in webhooks:
        encoded = json.dumps(payload).encode("utf-8")
        req = url_request.Request(
            webhook["url"],
            data=encoded,
            headers={"Content-Type": "application/json", "X-DriftGuard-Event": event_type},
            method="POST",
        )
        delivery = {
            "delivery_id": str(uuid4()),
            "workspace_id": workspace_id,
            "webhook_id": webhook["webhook_id"],
            "incident_id": incident.get("incident_id", ""),
            "event_type": event_type,
            "request_payload": payload,
        }
        try:
            with url_request.urlopen(req, timeout=WEBHOOK_TIMEOUT_SECONDS) as response:
                response_text = response.read(1024).decode("utf-8", errors="replace")
                delivery.update({
                    "status": "delivered" if 200 <= response.status < 300 else "failed",
                    "response_status_code": response.status,
                    "response_text": response_text,
                })
        except HTTPError as exc:
            delivery.update({
                "status": "failed",
                "response_status_code": exc.code,
                "response_text": exc.read(1024).decode("utf-8", errors="replace"),
                "error_message": str(exc),
            })
        except (URLError, TimeoutError, OSError) as exc:
            delivery.update({"status": "failed", "error_message": str(exc)})
        deliveries.append(NotificationDeliveryRepository.create(delivery))
    return deliveries


def send_test_webhook(webhook: dict) -> dict:
    incident = {
        "incident_id": "test",
        "workspace_id": webhook.get("workspace_id", ""),
        "title": "Webhook test notification",
        "severity": "Info",
        "status": "test",
    }
    deliveries = notify_incident_event(webhook.get("workspace_id", ""), "incident.created", incident, {"test": True})
    matching = [delivery for delivery in deliveries if delivery.get("webhook_id") == webhook.get("webhook_id")]
    return matching[0] if matching else {"status": "skipped", "message": "Webhook is disabled or does not subscribe to incident.created."}
