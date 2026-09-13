#!/usr/bin/env python3
"""Deterministic offline analysis of complete probe.py evidence.

Request errors include HTTP failures, timeouts, body mismatches and transport
errors. request_error_rate = errors/completed; http_error_rate counts only
the probe's http_error category/completed. Skips never enter either numerator
or denominator; generator_valid is independently skipped == 0. Rates are
fractions, empty denominators/percentiles are null (empty CSV cells).

Timeline [second, second+1) bins group launched/completed request records by
utc_start, NOT completion time; their totals are equal after validated drain.
Skips use scheduled_utc. Metrics intervals instead count coordinator-observed
events; only their cumulative counters are compared with request evidence.
Full sliding [start, start+60) windows use utc_start, advance by one second from
the scheduled origin and exclude partial windows beyond duration_seconds.
Latency quantiles include failures and use raw samples with nearest rank.
Final probe quantiles must agree within 1e-6 ms absolute / 1e-9 relative.
Ties select the earliest window. A failure span is first failed request start
through last failed completion, NOT downtime or an availability estimate.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta
import json
import math
from pathlib import Path


ERRORS = {"http_error": "http_errors", "timeout": "timeouts",
          "body_mismatch": "body_mismatches", "transport_error": "transport_errors"}
COUNTERS = ("launched", "completed", "success", "errors", "skipped", *ERRORS.values())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "{} must be finite and nonnegative".format(name))
    return value


def timestamp(value):
    require(isinstance(value, str), "timestamp must be a UTC string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.utcoffset() == timedelta(0), "timestamp must use UTC")
    return parsed


def utc(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def load(path):
    text = Path(path).read_text(encoding="utf-8")
    require(text.endswith("\n"), "{} is empty or lacks its final newline".format(path))
    rows = [json.loads(line, parse_constant=lambda _: require(False, "non-finite JSON"))
            for line in text.splitlines()]
    require(all(isinstance(row, dict) for row in rows), "JSONL records must be objects")
    return rows


def quantiles(values):
    ordered = sorted(values)
    return {"p{}_ms".format(p): ordered[math.ceil(len(ordered) * p / 100) - 1]
            if ordered else None for p in (50, 95, 99)}


def analyze(records, metrics):
    require(len(metrics) >= 2 and metrics[-1]["kind"] == "summary"
            and all(row["kind"] == "interval" for row in metrics[:-1]),
            "expected intervals followed by exactly one final summary")
    final = metrics[-1]
    duration, rps = number(final["duration_seconds"], "duration"), number(final["rps"], "rps")
    require(0 < duration <= 900 and 0 < rps <= 20, "duration/rps outside probe limits")
    require(type(final["scheduled"]) is int and final["scheduled"] >= 1
            and final["scheduled"] == math.ceil(duration * rps),
            "scheduled count disagrees with duration/rps")
    require(final["percentile_method"] == "nearest_rank", "unsupported percentile method")
    require(type(final["workers"]) is int and 1 <= final["workers"] <= 256, "invalid workers")
    require(0 < number(final["timeout_seconds"], "timeout") <= 300, "invalid timeout")
    require(number(final["elapsed_seconds"], "elapsed") >= duration, "incomplete dispatch window")
    totals = Counter()
    for row in metrics:
        timestamp(row["utc"])
        number(row["elapsed_seconds"], "interval elapsed")
        require(all(type(row[k]) is int and row[k] >= 0 for k in COUNTERS), "invalid counters")
        require(row["completed"] == row["success"] + row["errors"]
                and row["errors"] == sum(row[k] for k in ERRORS.values()), "inconsistent errors")
        require(type(row["in_flight"]) is int and 0 <= row["in_flight"] <= final["workers"],
                "invalid in_flight count")
        if row["completed"]:
            number(row["p99_ms"], "p99_ms")
        else:
            require(row["p99_ms"] is None, "empty samples must have null p99")
        if row["kind"] == "interval":
            totals.update({k: row[k] for k in COUNTERS})
            require(totals["launched"] - totals["completed"] == row["in_flight"],
                    "interval cumulative in_flight mismatch")
    require(final["in_flight"] == 0 and final["launched"] == final["completed"],
            "requests have not completely drained")
    require(all(totals[k] == final[k] for k in COUNTERS), "interval/final counter mismatch")
    require(len(records) == final["scheduled"]
            and all(type(row["sequence"]) is int for row in records), "missing/invalid slots")
    records = sorted(records, key=lambda row: row["sequence"])
    require([row["sequence"] for row in records] == list(range(1, final["scheduled"] + 1)),
            "duplicate or noncontiguous sequences")
    origin = timestamp(records[0]["scheduled_utc"])
    metric_times = [timestamp(row["utc"]) for row in metrics]
    require(origin <= metric_times[0] and metric_times == sorted(metric_times),
            "metric timestamps are inconsistent")
    finished = metric_times[-1]
    counts, bins, skipped_bins = Counter(), defaultdict(list), Counter()
    requests, failures = [], []
    for row in records:
        scheduled = (timestamp(row["scheduled_utc"]) - origin).total_seconds()
        require(abs(scheduled - (row["sequence"] - 1) / rps) <= 1e-5,
                "scheduled_utc disagrees with sequence/rps")
        if row["kind"] == "skip":
            require(row["reason"] in ("workers_busy", "scheduler_late"), "invalid skip reason")
            require(origin <= timestamp(row["utc"]) <= finished, "skip outside observed run")
            counts["skipped"] += 1
            skipped_bins[math.floor(scheduled)] += 1
            continue
        require(row["kind"] == "request", "unknown record kind")
        start, end = timestamp(row["utc_start"]), timestamp(row["utc_end"])
        require(origin <= start <= end <= finished, "invalid request chronology")
        number(row["latency_ms"], "latency_ms")
        status, ok, error = row["status"], row["ok"], row["error"]
        require(status is None or (type(status) is int and 100 <= status <= 599), "invalid status")
        require(type(ok) is bool, "ok must be boolean")
        require((ok and error is None and status is not None and 200 <= status < 300)
                or (not ok and error in ERRORS), "inconsistent request outcome")
        if error == "http_error":
            require(status is not None and not 200 <= status < 300, "invalid HTTP failure")
        if error == "body_mismatch":
            require(status is not None and 200 <= status < 300, "invalid body mismatch")
        counts["launched"] += 1
        counts["completed"] += 1
        counts["success" if ok else "errors"] += 1
        if not ok:
            counts[ERRORS[error]] += 1
            failures.append((start, end))
        offset = (start - origin).total_seconds()
        bins[math.floor(offset)].append(row)
        requests.append((offset, row))
    require(all(counts[k] == final[k] for k in COUNTERS), "request/final counter mismatch")
    raw = quantiles(row["latency_ms"] for _, row in requests)
    for key, value in raw.items():
        reported = final[key]
        if value is None:
            require(reported is None, "empty samples must have null " + key)
        else:
            number(reported, key)
            require(math.isclose(value, reported, rel_tol=1e-9, abs_tol=1e-6),
                    "raw latency/final percentile mismatch: " + key)
    result = {k: counts[k] for k in COUNTERS}
    result.update(
        scheduled=final["scheduled"], scheduled_origin_utc=utc(origin), duration_seconds=duration,
        generator_valid=counts["skipped"] == 0, percentile_method="nearest_rank", **raw,
        request_error_rate=counts["errors"] / counts["completed"] if counts["completed"] else None,
        http_error_rate=counts["http_errors"] / counts["completed"] if counts["completed"] else None,
        first_failed_request_utc_start=utc(min(a for a, _ in failures)) if failures else None,
        last_failed_completion_utc=utc(max(b for _, b in failures)) if failures else None,
        failure_span_seconds=(max(b for _, b in failures) - min(a for a, _ in failures)).total_seconds()
        if failures else None, failure_span_is_downtime=False,
        full_60s_windows=max(0, math.floor(duration - 60) + 1),
        worst_60s_request_error_rate=None, worst_60s_request_error_window=None,
        worst_60s_p99_ms=None, worst_60s_p99_window=None,
    )
    for second in range(result["full_60s_windows"]):
        window = [row for offset, row in requests if second <= offset < second + 60]
        if not window:
            continue
        errors = sum(not row["ok"] for row in window)
        detail = dict(start_second=second, utc_start=utc(origin + timedelta(seconds=second)),
                      utc_end=utc(origin + timedelta(seconds=second + 60)),
                      completed=len(window), errors=errors)
        for key, value, detail_key in (
            ("worst_60s_request_error_rate", errors / len(window), "worst_60s_request_error_window"),
            ("worst_60s_p99_ms", quantiles(row["latency_ms"] for row in window)["p99_ms"],
             "worst_60s_p99_window"),
        ):
            if result[key] is None or value > result[key]:
                result[key], result[detail_key] = value, detail
    timeline = []
    for second in range(max(math.ceil(duration), max(bins, default=-1) + 1)):
        rows = bins[second]
        success = sum(row["ok"] for row in rows)
        timeline.append(dict(utc=utc(origin + timedelta(seconds=second)), second=second,
                             launched=len(rows), completed=len(rows), success=success,
                             errors=len(rows) - success, skipped=skipped_bins[second],
                             p99_ms=quantiles(row["latency_ms"] for row in rows)["p99_ms"]))
    return result, timeline


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("requests", "metrics", "output", "timeline"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        paths = [getattr(args, name).resolve() for name in ("requests", "metrics", "output", "timeline")]
        require(len(set(paths)) == 4, "input/output paths must be distinct")
        result, timeline = analyze(load(args.requests), load(args.metrics))
    except (ValueError, KeyError, TypeError, OverflowError, OSError) as exc:
        parser.error("invalid evidence: {}".format(exc))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    with args.timeline.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("utc", "second", "launched", "completed",
                                                   "success", "errors", "skipped", "p99_ms"))
        writer.writeheader()
        writer.writerows(timeline)


if __name__ == "__main__":
    main()
