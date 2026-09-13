"""Bounded telemetry reads; no model-generated queries or raw log messages."""

import math
import re
import time
from datetime import timedelta, timezone


def _window(start, end):
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Use timezone-aware observation times")
    if not timedelta(0) < end - start <= timedelta(minutes=15):
        raise ValueError("Observation window must be positive and at most 15 minutes")


def collect_logs(client, log_group, service, start, end, *, sleep=time.sleep, polls=10):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", service):
        raise ValueError("Invalid configured service name")
    _window(start, end)
    if not 1 <= polls <= 10:
        raise ValueError("polls must be between one and ten")
    # The lab emits a structured `service` and `level` field. This is an
    # aggregate over those fields, not a regex over arbitrary raw messages.
    query = (
        f'filter service = "{service}" '
        '| filter level = "ERROR" or level = "FATAL" '
        '| stats count(*) as error_records'
    )
    deadline = time.monotonic() + 12
    query_id = client.start_query(
        logGroupName=log_group,
        startTime=int(start.timestamp()),
        endTime=int(end.timestamp()),
        queryString=query,
        limit=1,
    )["queryId"]
    terminal = False
    try:
        for attempt in range(polls):
            if time.monotonic() >= deadline:
                return {"status": "timeout"}
            response = client.get_query_results(queryId=query_id)
            status = response["status"]
            if status == "Complete":
                terminal = True
                rows = response.get("results", [])
                if not rows:
                    return {"status": "no_data"}
                values = [
                    field["value"]
                    for row in rows
                    for field in row
                    if field.get("field") == "error_records"
                ]
                if len(values) != 1 or not re.fullmatch(r"\d+", values[0]):
                    raise ValueError("Unexpected aggregate result")
                return {"status": "complete", "error_records": int(values[0])}
            if status in ("Failed", "Cancelled", "Timeout", "Unknown"):
                terminal = True
                return {"status": status.lower()}
            if status not in ("Scheduled", "Running"):
                raise ValueError("Unknown Logs Insights query status")
            if attempt + 1 < polls:
                sleep(1)
        return {"status": "timeout"}
    finally:
        if not terminal:
            client.stop_query(queryId=query_id)


def collect_metrics(client, resources, start, end):
    _window(start, end)
    queries = []
    definitions = [
        ("queue", "queue_visible", "AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "Maximum"),
        ("queue", "queue_oldest", "AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", "Maximum"),
        ("db_instance", "db_cpu", "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "Average"),
    ]
    for key, metric_id, namespace, name, dimension, statistic in definitions:
        if key not in resources:
            continue
        resource = resources[key]
        if not isinstance(resource, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", resource):
            raise ValueError("Invalid resource in the configured catalog")
        queries.append({
            "Id": metric_id,
            "MetricStat": {
                "Metric": {
                    "Namespace": namespace,
                    "MetricName": name,
                    "Dimensions": [{"Name": dimension, "Value": resource}],
                },
                "Period": 60,
                "Stat": statistic,
            },
            "ReturnData": True,
        })
    if not queries:
        return []
    paginator = client.get_paginator("get_metric_data")
    by_id = {query["Id"]: {"id": query["Id"], "status": "no_data", "samples": []} for query in queries}
    for page_number, page in enumerate(paginator.paginate(
        MetricDataQueries=queries,
        StartTime=start,
        EndTime=end,
        ScanBy="TimestampAscending",
        MaxDatapoints=100,
    )):
        if page_number >= 2:
            raise ValueError("Unexpected pagination beyond the bounded metric window")
        for result in page.get("MetricDataResults", []):
            target = by_id[result["Id"]]
            timestamps, values = result.get("Timestamps", []), result.get("Values", [])
            if len(timestamps) != len(values):
                raise ValueError("Metric timestamps and values do not align")
            status = result.get("StatusCode", "Unknown").lower()
            if target["status"] in ("no_data", "complete"):
                if status != "complete" or values:
                    target["status"] = status
            for timestamp, value in zip(timestamps, values):
                if type(value) not in (float, int) or not math.isfinite(value):
                    raise ValueError("Invalid metric value")
                target["samples"].append({
                    "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
                    "value": value,
                })
    return list(by_id.values())
