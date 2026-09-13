"""Transactional outbox delivery and independent synthetic SQS consumers."""

import json

from botocore.exceptions import BotoCoreError, ClientError
from opentelemetry import propagate
from opentelemetry.trace import SpanKind, Status, StatusCode
from sqlalchemy.exc import SQLAlchemyError


class Publisher:
    def __init__(self, store, sns, topic_arn, telemetry):
        self.store, self.sns, self.topic_arn, self.telemetry = store, sns, topic_arn, telemetry

    def once(self):
        for event in self.store.pending_events():
            parent = propagate.extract({"traceparent": event["traceparent"]})
            with self.telemetry.tracer.start_as_current_span(
                "publish lab event", context=parent, kind=SpanKind.PRODUCER,
                record_exception=False, set_status_on_exception=False,
            ) as span:
                span.set_attribute("messaging.system", "aws_sns")
                span.set_attribute("messaging.operation.type", "send")
                message = {
                    "id": event["id"], "event_type": event["event_type"],
                    "payload": event["payload"],
                    "traceparent": self.telemetry.inject().get("traceparent", ""),
                }
                try:
                    self.sns.publish(
                        TopicArn=self.topic_arn,
                        Message=json.dumps(message),
                        MessageAttributes={
                            "event_type": {"DataType": "String", "StringValue": event["event_type"]},
                        },
                    )
                    self.store.mark_published(event["id"])
                except Exception:
                    # Preserve the outbox row for retry; do not export raw SDK
                    # errors, SQL parameters or message payloads in spans/logs.
                    span.set_status(Status(StatusCode.ERROR))
                    self.telemetry.log("ERROR", "outbox_publish_failed", span)
                    raise


class Consumer:
    def __init__(self, store, sqs, queue_url, role, topic_arn, telemetry):
        self.store, self.sqs, self.queue_url = store, sqs, queue_url
        self.role, self.topic_arn, self.telemetry = role, topic_arn, telemetry

    def once(self):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=10,
            WaitTimeSeconds=5, VisibilityTimeout=30,
        )
        for message in response.get("Messages", []):
            try:
                envelope = json.loads(message["Body"])
                if not isinstance(envelope, dict) or envelope.get("Type") != "Notification" or envelope.get("TopicArn") != self.topic_arn:
                    raise ValueError("Unexpected SNS envelope")
                event = json.loads(envelope["Message"])
                if not isinstance(event, dict) or not isinstance(event.get("payload"), dict):
                    raise ValueError("Invalid event")
                if not isinstance(event.get("id"), str) or not 1 <= len(event["id"]) <= 36:
                    raise ValueError("Invalid event ID")
                if not isinstance(event.get("traceparent", ""), str):
                    raise ValueError("Invalid trace context")
                context = propagate.extract({"traceparent": event.get("traceparent", "")})
                with self.telemetry.tracer.start_as_current_span(
                    "process lab event", context=context, kind=SpanKind.CONSUMER,
                    record_exception=False, set_status_on_exception=False,
                ) as span:
                    span.set_attribute("messaging.system", "aws_sqs")
                    span.set_attribute("messaging.operation.type", "process")
                    created = self.store.consume(self.role, event)
                    self.telemetry.log("INFO", "event_processed" if created else "duplicate_event", span)
                # The DB transaction has committed before acknowledgement.
                self.sqs.delete_message(
                    QueueUrl=self.queue_url, ReceiptHandle=message["ReceiptHandle"],
                )
            except (ValueError, KeyError, TypeError, SQLAlchemyError, ClientError, BotoCoreError):
                # Do not acknowledge invalid/failed messages. Process remaining
                # batch members; the queue's redrive policy handles poison data.
                self.telemetry.log("ERROR", "event_processing_failed")
