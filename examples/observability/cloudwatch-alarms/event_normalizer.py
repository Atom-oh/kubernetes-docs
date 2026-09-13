"""Normalize an EventBridge alarm event for inspection; performs no AWS actions."""


def require_mapping(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def require_string(value, field):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def normalize_alarm_event(event, *, expected_account, expected_region):
    """Check the expected event shape, not the authenticity of its sender.

    The caller still needs a scoped Lambda resource policy/EventBridge rule.
    SNS notifications and direct CloudWatch Lambda actions have other schemas.
    """
    event = require_mapping(event, "event")
    expected = {
        "source": "aws.cloudwatch",
        "detail-type": "CloudWatch Alarm State Change",
        "account": expected_account,
        "region": expected_region,
    }
    for field, value in expected.items():
        if event.get(field) != value:
            raise ValueError(f"unexpected {field}")
    detail = require_mapping(event.get("detail"), "detail")
    name = require_string(detail.get("alarmName"), "alarmName")
    state = require_mapping(detail.get("state"), "state").get("value")
    if state not in ("OK", "ALARM", "INSUFFICIENT_DATA"):
        raise ValueError("unknown alarm state")

    # This example is for the commercial AWS partition.
    arn = f"arn:aws:cloudwatch:{expected_region}:{expected_account}:alarm:{name}"
    resources = event.get("resources")
    if not isinstance(resources, list) or arn not in resources:
        raise ValueError("resources do not identify the named alarm")

    configuration = require_mapping(detail.get("configuration"), "configuration")
    queries = configuration.get("metrics", [])
    if not isinstance(queries, list):
        raise ValueError("metrics must be an array")
    metrics = []
    for query in queries:
        query = require_mapping(query, "metric query")
        if "metricStat" not in query:
            continue  # Expression queries and composite alarms need no metric.
        metric_stat = require_mapping(query["metricStat"], "metricStat")
        metric = require_mapping(metric_stat.get("metric"), "metric")
        dimensions = require_mapping(metric.get("dimensions", {}), "dimensions")
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in dimensions.items()
        ):
            raise ValueError("dimension names and values must be strings")
        metrics.append(
            {
                "namespace": require_string(metric.get("namespace"), "namespace"),
                "name": require_string(metric.get("name"), "metric name"),
                "dimensions": dict(dimensions),
            }
        )
    return {"alarmArn": arn, "alarmName": name, "state": state, "metrics": metrics}
