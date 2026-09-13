"""SNS-only diagnostic reporter. No deployment or remediation operations."""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function,
)

from alerts import normalize_event
from analysis import analyze
from evidence import collect_logs, collect_metrics


class Reporter:
    def __init__(self, settings, clients, persistence):
        self.settings = settings
        self.clients = clients
        if settings["input_topic"] == settings["output_topic"]:
            raise ValueError("Input and output SNS topics must be different")
        self.catalog = settings["catalog"]
        if not isinstance(self.catalog, dict) or not 1 <= len(self.catalog) <= 2:
            raise ValueError("Configure one or two lab services")
        for name, resource in self.catalog.items():
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", name) or not isinstance(resource, dict):
                raise ValueError("Invalid service catalog")
            if not isinstance(resource.get("log_group"), str) or not resource["log_group"]:
                raise ValueError("Configure the service log group")
        self.idempotency = IdempotencyConfig(
            event_key_jmespath="message_id",
            payload_validation_jmespath="alerts",
            raise_on_no_idempotency_key=True,
            expires_after_seconds=86400,
        )
        self.process = idempotent_function(
            data_keyword_argument="record",
            persistence_store=persistence,
            config=self.idempotency,
            key_prefix="observability-lab",
        )(self._process)

    @staticmethod
    def _read_source(function, *args):
        try:
            return function(*args)
        except ClientError as error:
            return {"status": "error", "code": error.response["Error"]["Code"]}
        except BotoCoreError:
            return {"status": "error", "code": "SDKTransportError"}

    def _process(self, *, record):
        if not record["alerts"]:
            return {"message_id": record["message_id"], "status": "no_firing_alerts"}
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=15)
        observations = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            for service in sorted({alert["service"] for alert in record["alerts"]}):
                resources = self.catalog[service]
                metrics = executor.submit(
                    self._read_source, collect_metrics,
                    self.clients["cloudwatch"], resources, start, end,
                )
                logs = executor.submit(
                    self._read_source, collect_logs, self.clients["logs"],
                    resources["log_group"], service, start, end,
                )
                metric_result = metrics.result()
                observations.append({
                    "service": service,
                    "metrics": metric_result if isinstance(metric_result, list) else [],
                    "metrics_source": (
                        metric_result if isinstance(metric_result, dict) else {"status": "queried"}
                    ),
                    "logs": logs.result(),
                })
        evidence = {
            "alerts": record["alerts"],
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "observations": observations,
        }
        report = analyze(self.clients["bedrock"], self.settings["model_id"], evidence)
        # Diagnostic text is never interpreted as a command or an AWS argument.
        self.clients["sns"].publish(
            TopicArn=self.settings["output_topic"],
            Subject="[Observability lab] Diagnostic hypothesis",
            Message=json.dumps({
                "kind": "diagnostic-result",
                "message_id": record["message_id"],
                "observation_window": evidence["window"],
                "human_review_required": True,
                "report": report,
            }, ensure_ascii=True),
        )
        return {"message_id": record["message_id"], "status": "report_published"}

    def handle(self, event, context):
        records = normalize_event(
            event, self.settings["input_topic"], self.settings["allowed_alerts"],
            set(self.catalog), self.settings["alarm_services"],
        )
        self.idempotency.register_lambda_context(context)
        results = []
        for record in records:
            if context.get_remaining_time_in_millis() < 150_000:
                raise RuntimeError("Insufficient remaining time for bounded diagnostic collection")
            results.append(self.process(record=record))
        return {"records": results}


@lru_cache(maxsize=1)
def runtime():
    settings = {
        "input_topic": os.environ["INPUT_TOPIC_ARN"],
        "output_topic": os.environ["OUTPUT_TOPIC_ARN"],
        "model_id": os.environ["MODEL_ID"],
        "catalog": json.loads(os.environ["SERVICE_CATALOG"]),
        "allowed_alerts": set(json.loads(os.environ["ALLOWED_ALERTS"])),
        "alarm_services": json.loads(os.environ["ALARM_SERVICES"]),
    }
    config = Config(
        connect_timeout=2, read_timeout=3,
        retries={"mode": "adaptive", "total_max_attempts": 2},
    )
    session = boto3.Session()
    clients = {
        "cloudwatch": session.client("cloudwatch", config=config),
        "logs": session.client("logs", config=config),
        "sns": session.client("sns", config=config),
        "bedrock": session.client(
            "bedrock-runtime",
            config=Config(connect_timeout=2, read_timeout=30,
                          retries={"mode": "adaptive", "total_max_attempts": 2}),
        ),
    }
    persistence = DynamoDBPersistenceLayer(
        table_name=os.environ["IDEMPOTENCY_TABLE"],
        boto3_session=session,
        boto_config=config,
    )
    return Reporter(settings, clients, persistence)


def lambda_handler(event, context):
    return runtime().handle(event, context)
