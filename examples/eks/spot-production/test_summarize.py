"""Offline CLI tests with hand-checkable transport evidence; no cloud access."""

import copy
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("summarize.py")
ORIGIN = datetime(2026, 9, 12, tzinfo=timezone.utc)
COUNTERS = ("launched", "completed", "success", "errors", "skipped",
            "http_errors", "timeouts", "body_mismatches", "transport_errors")


def stamp(seconds):
    return (ORIGIN + timedelta(seconds=seconds)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def fixture(duration=4, rps=1, skips=(), failures=(), latencies=None, quantiles=(1, 1, 1)):
    """One interval is sufficient to represent aggregate completion observations."""
    records = []
    for index in range(round(duration * rps)):
        scheduled = stamp(index / rps)
        if index in skips:
            records.append(dict(kind="skip", sequence=index + 1, scheduled_utc=scheduled,
                                utc=scheduled, reason="workers_busy"))
        else:
            latency = 1 if latencies is None else latencies[index]
            failed = index in failures
            records.append(dict(
                kind="request", sequence=index + 1, scheduled_utc=scheduled,
                utc_start=stamp(index / rps + 0.001),
                utc_end=stamp(index / rps + 0.001 + latency / 1000),
                latency_ms=latency, status=503 if failed else 200,
                ok=not failed, error="http_error" if failed else None,
            ))
    launched = len(records) - len(skips)
    final = dict.fromkeys(COUNTERS, 0)
    final.update(
        kind="summary", utc=stamp(duration + 2), scheduled=len(records),
        launched=launched, completed=launched, success=launched - len(failures),
        errors=len(failures), skipped=len(skips), http_errors=len(failures),
        p50_ms=quantiles[0], p95_ms=quantiles[1], p99_ms=quantiles[2],
        percentile_method="nearest_rank", duration_seconds=duration, rps=rps,
        workers=4, timeout_seconds=2, elapsed_seconds=duration + 2, in_flight=0,
    )
    interval = {key: final[key] for key in COUNTERS}
    interval.update(kind="interval", utc=stamp(duration + 1),
                    elapsed_seconds=duration + 1, p99_ms=quantiles[2], in_flight=0)
    return records, [interval, final]


class SummarizeTests(unittest.TestCase):
    def invoke(self, records, metrics, valid=True, requests_text=None, metrics_text=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requests, logs = root / "requests.jsonl", root / "metrics.jsonl"
            output, timeline = root / "analysis.json", root / "timeline.csv"
            encode = lambda rows: "".join(json.dumps(row) + "\n" for row in rows)
            requests.write_text(encode(records) if requests_text is None else requests_text)
            logs.write_text(encode(metrics) if metrics_text is None else metrics_text)
            command = [sys.executable, "-B", str(SCRIPT), "--requests", str(requests),
                       "--metrics", str(logs), "--output", str(output), "--timeline", str(timeline)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=3)
            if not valid:
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("invalid evidence:", result.stderr)
                self.assertFalse(output.exists(), "invalid evidence produced an analysis")
                self.assertFalse(timeline.exists(), "invalid evidence produced a timeline")
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            raw_json, raw_csv = output.read_text(), timeline.read_text()
            with timeline.open() as stream:
                rows = list(csv.DictReader(stream))
            return json.loads(raw_json), rows, (raw_json, raw_csv)

    def test_raw_nearest_rank_percentiles_and_order_independent_output(self):
        records, metrics = fixture(5, latencies=[1, 2, 3, 4, 100], quantiles=(3, 100, 100))
        result, rows, encoded = self.invoke(records, metrics)
        self.assertEqual((result["p50_ms"], result["p95_ms"], result["p99_ms"]), (3, 100, 100))
        self.assertEqual(result["completed"], 5)
        self.assertTrue(result["generator_valid"])
        self.assertIsNone(result["failure_span_seconds"])
        self.assertIsNone(result["worst_60s_request_error_rate"])
        self.assertEqual(rows[4]["p99_ms"], "100")
        self.assertEqual(self.invoke(list(reversed(records)), metrics)[2], encoded)

    def test_skips_are_not_errors_and_timeline_uses_start_cohorts(self):
        records, metrics = fixture(3, skips={1}, failures={2},
                                   latencies=[200, 1, 1000], quantiles=(200, 1000, 1000))
        records[0].update(utc_start=stamp(0.9), utc_end=stamp(1.1))
        result, rows, _ = self.invoke(records, metrics)
        self.assertEqual((result["scheduled"], result["completed"], result["skipped"]), (3, 2, 1))
        self.assertFalse(result["generator_valid"])
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["request_error_rate"], 0.5)
        self.assertEqual(result["http_error_rate"], 0.5)
        self.assertEqual(result["first_failed_request_utc_start"], stamp(2.001))
        self.assertEqual(result["last_failed_completion_utc"], stamp(3.001))
        self.assertEqual(result["failure_span_seconds"], 1)
        self.assertIs(result["failure_span_is_downtime"], False)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["utc"], stamp(0))
        self.assertEqual((rows[0]["launched"], rows[0]["completed"], rows[0]["success"]), ("1", "1", "1"))
        self.assertEqual((rows[1]["completed"], rows[1]["skipped"], rows[1]["p99_ms"]), ("0", "1", ""))
        self.assertEqual((rows[2]["errors"], rows[2]["completed"]), ("1", "1"))

    def test_timeouts_are_request_errors_but_not_http_status_errors(self):
        records, metrics = fixture(1, failures={0})
        records[0].update(status=None, error="timeout")
        for row in metrics:
            row.update(http_errors=0, timeouts=1)
        result, _, _ = self.invoke(records, metrics)
        self.assertEqual(result["request_error_rate"], 1)
        self.assertEqual(result["http_error_rate"], 0)

    def test_full_sliding_window_exposes_spike_hidden_in_whole_run_average(self):
        records, metrics = fixture(600, failures=set(range(20, 80)),
                                   latencies=[100 if 20 <= i < 80 else 1 for i in range(600)],
                                   quantiles=(1, 100, 100))
        result, _, _ = self.invoke(records, metrics)
        self.assertEqual(result["request_error_rate"], 0.1)
        self.assertEqual(result["full_60s_windows"], 541)
        self.assertEqual(result["worst_60s_request_error_rate"], 1)
        self.assertEqual(result["worst_60s_request_error_window"]["start_second"], 20)
        self.assertEqual(result["worst_60s_p99_ms"], 100)
        self.assertEqual(result["worst_60s_p99_window"]["start_second"], 0)

    def test_unequal_interval_populations_are_not_averaged_for_percentiles(self):
        records, metrics = fixture(100, latencies=[1] * 99 + [100])
        first = dict(metrics[0], launched=99, completed=99, success=99,
                     p99_ms=1, utc=stamp(99), elapsed_seconds=99)
        second = dict(metrics[0], launched=1, completed=1, success=1,
                      p99_ms=100, utc=stamp(101), elapsed_seconds=1)
        result, _, _ = self.invoke(records, [first, second, metrics[-1]])
        self.assertEqual(result["p99_ms"], 1)
        self.assertEqual(result["worst_60s_p99_ms"], 100)
        self.assertEqual(result["worst_60s_p99_window"]["start_second"], 40)

    def test_failure_span_covers_separated_failures_without_claiming_downtime(self):
        records, metrics = fixture(10, failures={0, 9},
                                   latencies=[1000] + [1] * 8 + [2000],
                                   quantiles=(1, 2000, 2000))
        result, _, _ = self.invoke(list(reversed(records)), metrics)
        self.assertEqual(result["first_failed_request_utc_start"], stamp(0.001))
        self.assertEqual(result["last_failed_completion_utc"], stamp(11.001))
        self.assertEqual(result["failure_span_seconds"], 11)
        self.assertIs(result["failure_span_is_downtime"], False)

    def test_final_percentile_tolerance_does_not_replace_raw_result(self):
        records, metrics = fixture()
        metrics[-1]["p99_ms"] = 1.0000005
        result, _, _ = self.invoke(records, metrics)
        self.assertEqual(result["p99_ms"], 1)
        metrics[-1]["p99_ms"] = 1.00005
        self.invoke(records, metrics, valid=False)

    def test_partial_end_window_is_excluded_even_if_it_contains_the_only_failure(self):
        records, metrics = fixture(60.5, rps=2, failures={120},
                                   latencies=[1] * 120 + [1000], quantiles=(1, 1, 1))
        result, _, _ = self.invoke(records, metrics)
        self.assertEqual(result["full_60s_windows"], 1)
        self.assertEqual(result["worst_60s_request_error_rate"], 0)
        self.assertEqual(result["worst_60s_p99_ms"], 1)
        self.assertGreater(result["request_error_rate"], 0)

    def test_all_skipped_evidence_has_null_rates_and_latencies(self):
        result, rows, _ = self.invoke(*fixture(60, skips=set(range(60)), quantiles=(None, None, None)))
        self.assertFalse(result["generator_valid"])
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["full_60s_windows"], 1)
        for key in ("request_error_rate", "http_error_rate", "p50_ms", "p95_ms", "p99_ms",
                    "worst_60s_request_error_rate", "worst_60s_p99_ms"):
            self.assertIsNone(result[key], key)
        self.assertTrue(all(row["errors"] == "0" and row["skipped"] == "1" for row in rows))

    def test_missing_duplicate_and_noncontiguous_slots_are_rejected(self):
        records, metrics = fixture()
        for changed in (records[:-1], records + [records[0]], records[1:], []):
            with self.subTest(records=len(changed)):
                self.invoke(changed, metrics, valid=False)
        records[1]["sequence"] = 7
        self.invoke(records, metrics, valid=False)

    def test_missing_duplicate_misplaced_or_inconsistent_metrics_are_rejected(self):
        records, metrics = fixture()
        for changed in (metrics[:-1], metrics + [metrics[-1]], list(reversed(metrics)),
                        metrics[1:], []):
            with self.subTest(metrics=len(changed)):
                self.invoke(records, changed, valid=False)
        for index, key, value in ((0, "launched", 3), (1, "completed", 3),
                                  (1, "scheduled", 5), (1, "in_flight", 1),
                                  (1, "p99_ms", 2), (1, "p50_ms", None)):
            with self.subTest(index=index, field=key):
                changed = copy.deepcopy(metrics)
                changed[index][key] = value
                self.invoke(records, changed, valid=False)

    def test_malformed_and_truncated_jsonl_are_rejected(self):
        records, metrics = fixture()
        for text in ('{"kind":"request"', "[]\n", "\n",
                     json.dumps(records[0]), '{"kind": NaN}\n'):
            with self.subTest(text=text):
                self.invoke(records, metrics, valid=False, requests_text=text)
        self.invoke(records, metrics, valid=False, metrics_text='{"kind":"summary"')

    def test_invalid_schema_timestamps_and_latencies_are_rejected(self):
        records, metrics = fixture()
        for key, value in (("latency_ms", -1), ("latency_ms", float("nan")),
                           ("latency_ms", float("inf")), ("latency_ms", True),
                           ("ok", "true"), ("status", 503), ("error", "timeout"),
                           ("sequence", True), ("utc_start", "2026-09-12"),
                           ("utc_end", stamp(-1)), ("scheduled_utc", stamp(0.5))):
            with self.subTest(field=key, value=value):
                changed = copy.deepcopy(records)
                changed[0][key] = value
                self.invoke(changed, metrics, valid=False)

    def test_completion_after_final_summary_and_reversed_metric_times_are_rejected(self):
        records, metrics = fixture()
        changed = copy.deepcopy(records)
        changed[0]["utc_end"] = stamp(100)
        self.invoke(changed, metrics, valid=False)
        changed_metrics = copy.deepcopy(metrics)
        changed_metrics[0]["utc"] = stamp(100)
        self.invoke(records, changed_metrics, valid=False)
        skipped, skipped_metrics = fixture(1, skips={0}, quantiles=(None, None, None))
        skipped[0]["utc"] = stamp(100)
        self.invoke(skipped, skipped_metrics, valid=False)


if __name__ == "__main__":
    unittest.main()
