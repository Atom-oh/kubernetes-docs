"""Normalize only the SNS formats used by the observability lab."""

import json


def _field(value, lower, upper, default=None):
    if lower in value and upper in value and value[lower] != value[upper]:
        raise ValueError(f"Conflicting {lower} fields")
    return value.get(lower, value.get(upper, default))


def normalize_event(event, input_topic, allowed_alerts, allowed_services, alarm_services):
    """Return every SNS record with a bounded list of known firing alerts.

    Alertmanager's template ``{{ . | toJson }}`` uses capitalized fields,
    while its webhook format uses lowercase fields. Neither descriptions nor
    arbitrary labels are forwarded to the model.
    """
    if not isinstance(event, dict):
        raise ValueError("Expected an SNS event object")
    records = event.get("Records")
    if not isinstance(records, list) or not 1 <= len(records) <= 10:
        raise ValueError("Expected between one and ten SNS records")
    result = []
    for record in records:
        if not isinstance(record, dict) or record.get("EventSource") != "aws:sns":
            raise ValueError("Only SNS events are accepted")
        sns = record.get("Sns")
        if not isinstance(sns, dict) or sns.get("TopicArn") != input_topic:
            raise ValueError("Unexpected SNS input topic")
        message_id = sns.get("MessageId")
        if not isinstance(message_id, str) or not 1 <= len(message_id) <= 128:
            raise ValueError("Missing or invalid SNS message ID")
        message = sns.get("Message")
        if not isinstance(message, str) or len(message.encode("utf-8")) > 256 * 1024:
            raise ValueError("Invalid or oversized SNS message")
        payload = json.loads(message)
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON message object")
        alerts = []
        if "alerts" in payload or "Alerts" in payload:
            incoming = _field(payload, "alerts", "Alerts")
            if not isinstance(incoming, list) or len(incoming) > 20:
                raise ValueError("Expected at most twenty Alertmanager alerts")
            for item in incoming:
                if not isinstance(item, dict):
                    raise ValueError("Invalid Alertmanager alert")
                status = _field(item, "status", "Status")
                if status == "resolved":
                    continue
                if status != "firing":
                    raise ValueError("Unknown Alertmanager status")
                labels = _field(item, "labels", "Labels")
                if not isinstance(labels, dict):
                    raise ValueError("Missing Alertmanager labels")
                name, service = labels.get("alertname"), labels.get("service")
                if not isinstance(name, str) or name not in allowed_alerts:
                    raise ValueError("Alert is not in the configured allowlist")
                if not isinstance(service, str) or service not in allowed_services:
                    raise ValueError("Service is not in the configured catalog")
                alerts.append({"source": "alertmanager", "name": name, "service": service})
        elif "AlarmName" in payload and "NewStateValue" in payload:
            name, state = payload["AlarmName"], payload["NewStateValue"]
            if not isinstance(name, str) or name not in alarm_services:
                raise ValueError("CloudWatch alarm is not in the configured catalog")
            service = alarm_services[name]
            if service not in allowed_services:
                raise ValueError("Invalid service in the configured alarm catalog")
            if state == "ALARM":
                alerts.append({"source": "cloudwatch", "name": name, "service": service})
            elif state not in ("OK", "INSUFFICIENT_DATA"):
                raise ValueError("Unknown CloudWatch alarm state")
        else:
            raise ValueError("Unknown alert message format")
        result.append({"message_id": message_id, "alerts": alerts})
    return result
