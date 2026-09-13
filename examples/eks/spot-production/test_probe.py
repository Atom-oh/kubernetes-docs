"""Local transport tests; run: python -B -m unittest discover -s <this-dir> -v."""

import datetime as dt
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PROBE = Path(__file__).with_name("probe.py")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with self.server.lock:
            self.server.hits.append((self.path, time.monotonic()))
            self.server.active[self.path] = self.server.active.get(self.path, 0) + 1
            self.server.peak[self.path] = max(
                self.server.peak.get(self.path, 0), self.server.active[self.path]
            )
        try:
            if self.path == "/disconnect":
                return
            if self.path == "/slow":
                time.sleep(0.18)
            elif self.path == "/hold":
                time.sleep(0.35)
            elif self.path == "/delay":
                time.sleep(0.12)
            elif self.path == "/varied":
                with self.server.lock:
                    number = sum(path == self.path for path, _ in self.server.hits)
                time.sleep((number % 4) * 0.01)
            status = {"/bad": 503, "/redirect": 302}.get(self.path, 200)
            body = b"WRONG" if self.path == "/wrong" else b"READY\n"
            if self.path == "/boundary":
                body = b"x" * 65534 + b"READY" + b"x" * 10
            self.send_response(status)
            if status == 302:
                self.send_header("Location", "/ok")
            length = len(body) + 10 if self.path == "/truncated" else len(body)
            self.send_header("Content-Length", str(length))
            self.end_headers()
            if self.path == "/slow-body":
                time.sleep(0.18)
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The timeout test intentionally disconnects.
        finally:
            with self.server.lock:
                self.server.active[self.path] -= 1

    def log_message(self, *args):
        pass


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.lock = threading.Lock()
        cls.server.hits = []
        cls.server.active = {}
        cls.server.peak = {}
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        cls.thread.start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def command(self, output, path="/ok", **overrides):
        options = dict(duration=0.01, rps=20, timeout=0.5, workers=4)
        options.update(overrides)
        command = [
            sys.executable, "-B", str(PROBE), "--url", self.url + path,
            "--out", str(output),
        ]
        for name, value in options.items():
            command.extend(["--" + name.replace("_", "-"), str(value)])
        return command

    def run_probe(self, path="/ok", **overrides):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results" / "requests.jsonl"
            process = subprocess.run(
                self.command(output, path, **overrides),
                capture_output=True, text=True, timeout=4,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(process.stderr, "")
            records = [json.loads(line) for line in output.read_text().splitlines()]
            summaries = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(summaries[-1]["kind"], "summary")
        return records, summaries

    def test_success_records_full_request_and_consistent_totals(self):
        records, summaries = self.run_probe(expect_text="READY")
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["kind"], "request")
        self.assertEqual(record["sequence"], 1)
        self.assertEqual(record["status"], 200)
        self.assertIs(record["ok"], True)
        self.assertIsNone(record["error"])
        self.assertGreater(record["latency_ms"], 0)
        start = dt.datetime.fromisoformat(record["utc_start"].replace("Z", "+00:00"))
        end = dt.datetime.fromisoformat(record["utc_end"].replace("Z", "+00:00"))
        self.assertEqual(start.utcoffset(), dt.timedelta(0))
        self.assertGreaterEqual(end, start)
        final = summaries[-1]
        for key in ("scheduled", "launched", "completed", "success"):
            self.assertEqual(final[key], 1)
        for key in ("errors", "skipped", "http_errors", "timeouts", "body_mismatches"):
            self.assertEqual(final[key], 0)
        self.assertEqual(final["p50_ms"], record["latency_ms"])
        self.assertEqual(final["p95_ms"], record["latency_ms"])
        self.assertEqual(final["p99_ms"], record["latency_ms"])

    def test_non_2xx_is_http_error_without_retry(self):
        with self.server.lock:
            before = sum(path == "/bad" for path, _ in self.server.hits)
        records, summaries = self.run_probe("/bad")
        self.assertEqual(records[0]["status"], 503)
        self.assertIs(records[0]["ok"], False)
        self.assertEqual(records[0]["error"], "http_error")
        self.assertEqual(summaries[-1]["http_errors"], 1)
        self.assertEqual(summaries[-1]["errors"], 1)
        self.assertEqual(summaries[-1]["success"], 0)
        with self.server.lock:
            self.assertEqual(sum(path == "/bad" for path, _ in self.server.hits), before + 1)

    def test_redirect_is_recorded_without_following(self):
        with self.server.lock:
            before = len(self.server.hits)
        records, summaries = self.run_probe("/redirect")
        self.assertEqual(records[0]["status"], 302)
        self.assertEqual(summaries[-1]["http_errors"], 1)
        with self.server.lock:
            self.assertEqual([path for path, _ in self.server.hits[before:]], ["/redirect"])

    def test_timeout_is_distinct_from_http_error(self):
        records, summaries = self.run_probe("/slow", timeout=0.04)
        self.assertIsNone(records[0]["status"])
        self.assertEqual(records[0]["error"], "timeout")
        self.assertGreaterEqual(records[0]["latency_ms"], 30)
        self.assertLess(records[0]["latency_ms"], 160)
        self.assertEqual(summaries[-1]["timeouts"], 1)
        self.assertEqual(summaries[-1]["http_errors"], 0)
        self.assertEqual(summaries[-1]["errors"], 1)

    def test_http_200_with_wrong_body_fails_optional_expectation(self):
        records, summaries = self.run_probe("/wrong", expect_text="READY")
        self.assertEqual(records[0]["status"], 200)
        self.assertIs(records[0]["ok"], False)
        self.assertEqual(records[0]["error"], "body_mismatch")
        self.assertEqual(summaries[-1]["body_mismatches"], 1)
        self.assertEqual(summaries[-1]["errors"], 1)
        self.assertEqual(summaries[-1]["success"], 0)

    def test_expected_text_matches_across_body_read_boundaries(self):
        records, summaries = self.run_probe("/boundary", expect_text="READY")
        self.assertIs(records[0]["ok"], True)
        self.assertEqual(summaries[-1]["success"], 1)

    def test_truncated_body_is_transport_error_even_if_expected_text_arrived(self):
        records, summaries = self.run_probe("/truncated", expect_text="READY")
        self.assertEqual(records[0]["status"], 200)
        self.assertIs(records[0]["ok"], False)
        self.assertEqual(records[0]["error"], "transport_error")
        self.assertEqual(summaries[-1]["transport_errors"], 1)
        self.assertEqual(summaries[-1]["errors"], 1)

    def test_body_timeout_keeps_received_http_status(self):
        records, summaries = self.run_probe("/slow-body", timeout=0.04)
        self.assertEqual(records[0]["status"], 200)
        self.assertIs(records[0]["ok"], False)
        self.assertEqual(records[0]["error"], "timeout")
        self.assertEqual(summaries[-1]["timeouts"], 1)

    def test_disconnect_is_transport_error_without_retry(self):
        records, summaries = self.run_probe("/disconnect")
        self.assertEqual(records[0]["error"], "transport_error")
        self.assertIsNone(records[0]["status"])
        self.assertEqual(summaries[-1]["transport_errors"], 1)
        self.assertEqual(summaries[-1]["errors"], 1)
        with self.server.lock:
            self.assertEqual(sum(path == "/disconnect" for path, _ in self.server.hits), 1)

    def test_fixed_schedule_continues_while_earlier_requests_are_in_flight(self):
        records, summaries = self.run_probe("/delay", duration=0.26)
        requests = sorted(records, key=lambda record: record["sequence"])
        self.assertEqual(len(requests), 6)
        self.assertTrue(all(record["kind"] == "request" for record in requests))
        scheduled = [
            dt.datetime.fromisoformat(record["scheduled_utc"].replace("Z", "+00:00"))
            for record in requests
        ]
        for first, second in zip(scheduled, scheduled[1:]):
            self.assertAlmostEqual((second - first).total_seconds(), 0.05, places=5)
        with self.server.lock:
            arrivals = [stamp for path, stamp in self.server.hits if path == "/delay"]
        self.assertEqual(len(arrivals), 6)
        self.assertLess(arrivals[-1] - arrivals[0], 0.34)
        self.assertGreater(arrivals[-1] - arrivals[0], 0.18)
        self.assertEqual(summaries[-1]["success"], 6)
        self.assertEqual(summaries[-1]["skipped"], 0)

    def test_saturation_logs_skips_without_queueing_requests_for_later(self):
        records, summaries = self.run_probe("/hold", duration=0.26, workers=2)
        requests = [record for record in records if record["kind"] == "request"]
        skips = [record for record in records if record["kind"] == "skip"]
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(skips), 4)
        self.assertEqual(sorted(record["sequence"] for record in records), list(range(1, 7)))
        self.assertTrue(all(record["reason"] == "workers_busy" for record in skips))
        final = summaries[-1]
        self.assertEqual(final["scheduled"], 6)
        self.assertEqual(final["launched"], 2)
        self.assertEqual(final["completed"], 2)
        self.assertEqual(final["success"], 2)
        self.assertEqual(final["skipped"], 4)
        self.assertEqual(final["errors"], 0)
        with self.server.lock:
            self.assertEqual(self.server.peak["/hold"], 2)
            self.assertEqual(sum(path == "/hold" for path, _ in self.server.hits), 2)

    @unittest.skipUnless(hasattr(signal, "SIGSTOP"), "requires POSIX process suspension")
    def test_suspended_generator_logs_missed_slots_instead_of_catching_up(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "requests.jsonl"
            process = subprocess.Popen(
                self.command(output, "/suspend", duration=0.36),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    with self.server.lock:
                        arrived = any(path == "/suspend" for path, _ in self.server.hits)
                    if arrived:
                        break
                    time.sleep(0.002)
                self.assertTrue(arrived, "initial request never arrived")
                process.send_signal(signal.SIGSTOP)
                time.sleep(0.22)
                process.send_signal(signal.SIGCONT)
                stdout, stderr = process.communicate(timeout=2)
                self.assertEqual(process.returncode, 0, stderr)
                records = [json.loads(line) for line in output.read_text().splitlines()]
                final = json.loads(stdout.splitlines()[-1])
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        skips = [record for record in records if record["kind"] == "skip"]
        self.assertGreaterEqual(len(skips), 3)
        self.assertTrue(all(record["reason"] == "scheduler_late" for record in skips))
        self.assertEqual(sorted(record["sequence"] for record in records), list(range(1, 9)))
        self.assertEqual(final["launched"] + final["skipped"], 8)
        self.assertEqual(final["errors"], 0)

    @unittest.skipUnless(os.name == "posix", "requires nonblocking POSIX pipes")
    def test_blocked_stdout_does_not_dispatch_a_stale_slot_after_logging(self):
        read_fd, write_fd = os.pipe()
        # Fill a real pipe so the first interval's flush must block.
        os.set_blocking(write_fd, False)
        while True:
            try:
                os.write(write_fd, b"\n" * 4096)
            except BlockingIOError:
                break
        os.set_blocking(write_fd, True)
        with os.fdopen(read_fd) as pipe, tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "requests.jsonl"
            process = subprocess.Popen(
                self.command(output, "/blocked-log", duration=1.31),
                stdout=write_fd, stderr=subprocess.PIPE, text=True,
            )
            os.close(write_fd)
            try:
                deadline = time.monotonic() + 1
                arrived = False
                while time.monotonic() < deadline:
                    with self.server.lock:
                        arrived = any(path == "/blocked-log" for path, _ in self.server.hits)
                    if arrived:
                        break
                    time.sleep(0.002)
                self.assertTrue(arrived, "initial request never arrived")
                time.sleep(1.18)
                drained = []
                reader = threading.Thread(target=lambda: drained.append(pipe.read()), daemon=True)
                reader.start()
                _, stderr = process.communicate(timeout=2)
                reader.join(timeout=1)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertFalse(reader.is_alive())
                records = [json.loads(line) for line in output.read_text().splitlines()]
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        at_one_second = next(record for record in records if record["sequence"] == 21)
        self.assertEqual(at_one_second["kind"], "skip")
        self.assertEqual(at_one_second["reason"], "scheduler_late")

    def test_intervals_are_flushed_live_and_final_quantiles_use_raw_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "requests.jsonl"
            process = subprocess.Popen(
                self.command(output, "/varied", duration=1.12),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                # Bound readline so a broken flush cannot hang the suite.
                lines = []
                first_line = threading.Thread(
                    target=lambda: lines.append(process.stdout.readline()), daemon=True
                )
                first_line.start()
                first_line.join(timeout=1.1)
                self.assertFalse(first_line.is_alive(), "interval output was not flushed")
                self.assertIsNone(process.poll(), "first interval arrived only after exit")
                rest, stderr = process.communicate(timeout=3)
                self.assertEqual(process.returncode, 0, stderr)
                summaries = [json.loads(line) for line in (lines[0] + rest).splitlines()]
                records = [json.loads(line) for line in output.read_text().splitlines()]
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        intervals = summaries[:-1]
        self.assertGreaterEqual(len(intervals), 2)
        for interval in intervals:
            self.assertEqual(interval["kind"], "interval")
            for key in ("utc", "launched", "completed", "success", "errors", "skipped", "p99_ms"):
                self.assertIn(key, interval)
        final = summaries[-1]
        for key in ("launched", "completed", "success", "errors", "skipped"):
            self.assertEqual(sum(interval[key] for interval in intervals), final[key])
        latencies = sorted(record["latency_ms"] for record in records)
        for percent in (50, 95, 99):
            # Nearest rank: independently index the actual JSONL samples.
            expected = latencies[math.ceil(len(latencies) * percent / 100) - 1]
            self.assertEqual(final["p{}_ms".format(percent)], expected)

    def test_invalid_arguments_fail_before_contacting_server(self):
        invalid = [
            ("duration", "0"), ("duration", "-1"), ("duration", "901"),
            ("rps", "0"), ("rps", "21"), ("rps", "nan"),
            ("timeout", "0"), ("timeout", "inf"), ("workers", "0"),
            ("workers", "1.5"),
        ]
        with self.server.lock:
            before = len(self.server.hits)
        with tempfile.TemporaryDirectory() as directory:
            for name, value in invalid:
                with self.subTest(name=name, value=value):
                    process = subprocess.run(
                        self.command(Path(directory) / "requests.jsonl", **{name: value}),
                        capture_output=True, text=True, timeout=2,
                    )
                    self.assertEqual(process.returncode, 2, process.stderr)
                    self.assertIn("error:", process.stderr)
        with self.server.lock:
            self.assertEqual(len(self.server.hits), before)


if __name__ == "__main__":
    unittest.main()
