#!/usr/bin/env python3
"""Small stdlib synthetic HTTP transport probe, not a production benchmark.

Every scheduled slot is either a request or an explicitly logged skip. Records
in --out may be out of sequence (completion order); sequence starts at 1.
Stdout contains interval deltas, including a final partial interval, followed
by cumulative summary totals. Errors exclude generator skips. Percentiles use
nearest rank over all completed request latencies, including failed requests;
empty samples yield null. Final quantiles use raw samples, never interval p99s.

A fresh direct HTTP(S) connection is used for each GET: no retries, redirects,
proxy environment settings, or connection pooling. The full body is consumed
in bounded chunks. --expect-text searches for a literal UTF-8 byte substring.
--timeout is a socket operation timeout, not a whole-request/DNS deadline.
Duration controls dispatch; outstanding requests are drained before exit.
Exit 0 means the run completed, even when requests failed; inspect the summary.
"""

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import http.client
import json
import math
from pathlib import Path
import socket
import time
from urllib.parse import urlsplit


COUNT_KEYS = (
    "launched", "completed", "success", "errors", "skipped",
    "http_errors", "timeouts", "body_mismatches", "transport_errors",
)
ERROR_COUNTERS = {
    "http_error": "http_errors",
    "timeout": "timeouts",
    "body_mismatch": "body_mismatches",
    "transport_error": "transport_errors",
}


def utc(timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def emit(record, stream=None):
    print(json.dumps(record, separators=(",", ":"), allow_nan=False),
          file=stream, flush=True)


def percentile(sorted_samples, percent):
    """Exact nearest-rank percentile; caller supplies sorted raw samples."""
    if not sorted_samples:
        return None
    return sorted_samples[math.ceil(len(sorted_samples) * percent / 100) - 1]


def snapshot(kind, counts, samples, **extra):
    ordered = sorted(samples)
    result = dict(kind=kind, utc=utc(), **{key: counts[key] for key in COUNT_KEYS})
    result["p99_ms"] = percentile(ordered, 99)
    if kind == "summary":
        result["p50_ms"] = percentile(ordered, 50)
        result["p95_ms"] = percentile(ordered, 95)
        result["percentile_method"] = "nearest_rank"
    result.update(extra)
    return result


def request(url, timeout, expected, sequence, scheduled_utc):
    started = time.monotonic()
    record = dict(
        kind="request", sequence=sequence, scheduled_utc=scheduled_utc,
        utc_start=utc(), utc_end=None, latency_ms=None,
        status=None, ok=False, error=None,
    )
    connection_type = (
        http.client.HTTPSConnection if url.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_type(url.hostname, url.port, timeout=timeout)
    try:
        target = url.path or "/"
        if url.query:
            target += "?" + url.query
        connection.request("GET", target, headers={
            "Connection": "close", "Accept-Encoding": "identity",
            "User-Agent": "eks-spot-transport-probe/1",
        })
        response = connection.getresponse()
        record["status"] = response.status
        matched = expected is None or expected == b""
        tail = b""
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            if not matched:
                window = tail + chunk
                matched = expected in window
                tail = window[-(len(expected) - 1):] if len(expected) > 1 else b""
        # Bounded HTTPResponse.read(size) tolerates early EOF; unlike read(),
        # it does not always raise when a Content-Length body is incomplete.
        if response.length not in (None, 0):
            raise http.client.IncompleteRead(b"", response.length)
        if not 200 <= response.status < 300:
            record["error"] = "http_error"
        elif not matched:
            record["error"] = "body_mismatch"
        else:
            record["ok"] = True
    except (TimeoutError, socket.timeout):
        record["error"] = "timeout"
    except (OSError, http.client.HTTPException, ValueError) as exc:
        record["error"] = "transport_error"
        record["error_detail"] = "{}: {}".format(type(exc).__name__, exc)
    finally:
        connection.close()
        record["latency_ms"] = (time.monotonic() - started) * 1000
        record["utc_end"] = utc()
    return record


def run(args):
    url = urlsplit(args.url)
    expected = None if args.expect_text is None else args.expect_text.encode("utf-8")
    counts, interval_counts = Counter(), Counter()
    samples, interval_samples = [], []

    def increment(key):
        counts[key] += 1
        interval_counts[key] += 1

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream, ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        origin = time.monotonic()
        origin_wall = time.time()
        end = origin + args.duration
        next_report = origin + 1
        interval_start = origin
        period = 1 / args.rps
        scheduled = math.ceil(args.duration * args.rps)
        sequence = 1
        pending = set()
        while True:
            # Only the coordinator writes records/counters. The pending set
            # includes queued, running and completed-but-uncollected work.
            for future in tuple(pending):
                if future.done():
                    pending.remove(future)
                    record = future.result()
                    increment("completed")
                    if record["ok"]:
                        increment("success")
                    else:
                        increment("errors")
                        increment(ERROR_COUNTERS[record["error"]])
                    samples.append(record["latency_ms"])
                    interval_samples.append(record["latency_ms"])
                    emit(record, stream)
            now = time.monotonic()
            if now >= next_report:
                emit(snapshot(
                    "interval", interval_counts, interval_samples,
                    elapsed_seconds=now - interval_start, in_flight=len(pending),
                ))
                interval_counts.clear()
                interval_samples.clear()
                interval_start = now
                next_report = origin + math.floor(now - origin) + 1

            # stdout can block on its reader. Recheck dispatch time after logging
            # so a stalled metrics consumer cannot turn old slots into requests.
            now = time.monotonic()
            due = origin + (sequence - 1) / args.rps
            if sequence <= scheduled and now >= due:
                scheduled_utc = utc(origin_wall + (sequence - 1) / args.rps)
                reason = None
                if now >= end or now >= due + period:
                    reason = "scheduler_late"
                elif len(pending) >= args.workers:
                    reason = "workers_busy"
                if reason:
                    increment("skipped")
                    emit(dict(kind="skip", sequence=sequence, utc=utc(),
                              scheduled_utc=scheduled_utc, reason=reason), stream)
                else:
                    # Never submit without capacity: at most workers futures
                    # exist, so the executor cannot accumulate an unbounded queue.
                    pending.add(executor.submit(
                        request, url, args.timeout, expected, sequence, scheduled_utc
                    ))
                    increment("launched")
                sequence += 1
                continue

            if sequence > scheduled and not pending and now >= end:
                break
            wake = next_report
            if sequence <= scheduled:
                wake = min(wake, due)
            if now < end:
                wake = min(wake, end)
            delay = max(0, wake - time.monotonic())
            if pending:
                wait(pending, timeout=delay, return_when=FIRST_COMPLETED)
            else:
                time.sleep(delay)

        emit(snapshot(
            "interval", interval_counts, interval_samples,
            elapsed_seconds=time.monotonic() - interval_start, in_flight=0,
        ))
        summary = snapshot(
            "summary", counts, samples, scheduled=scheduled,
            elapsed_seconds=time.monotonic() - origin,
            duration_seconds=args.duration, rps=args.rps, workers=args.workers,
            timeout_seconds=args.timeout, in_flight=0,
        )
        emit(summary)
        return summary


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def arguments(argv=None):
    parser = argparse.ArgumentParser(
        description="Synthetic HTTP transport probe; not a production benchmark "
                    "or business correctness validator.",
        epilog="One GET per fixed scheduled slot starting at t=0; busy or late "
               "slots are logged as skips, never retried. No redirects/proxies. "
               "Drains outstanding requests after duration. Output is overwritten. "
               "Nearest-rank percentiles include all completed request latencies. "
               "Limits bound raw latency storage to at most 18,000 samples.",
    )
    parser.add_argument("--url", required=True, help="direct HTTP(S) URL")
    parser.add_argument("--duration", required=True, type=positive,
                        help="dispatch duration in seconds, 0 < duration <= 900")
    parser.add_argument("--rps", required=True, type=positive,
                        help="scheduled starts per second, 0 < rps <= 20")
    parser.add_argument("--timeout", required=True, type=positive,
                        help="socket operation timeout in seconds, <= 300; "
                             "not a whole-request or DNS deadline")
    parser.add_argument("--workers", required=True, type=int,
                        help="maximum outstanding requests, 1..256")
    parser.add_argument("--out", required=True, help="request/skip JSONL output file")
    parser.add_argument("--expect-text",
                        help="require literal UTF-8 substring in body (<= 65536 bytes)")
    args = parser.parse_args(argv)
    for key, maximum in (("duration", 900), ("rps", 20), ("timeout", 300), ("workers", 256)):
        if not 0 < getattr(args, key) <= maximum:
            parser.error("--{} must be > 0 and <= {}".format(key, maximum))
    try:
        url = urlsplit(args.url)
        if (url.scheme not in ("http", "https") or not url.hostname
                or url.username is not None or url.password is not None
                or url.fragment or (url.port is not None and url.port == 0)):
            raise ValueError("expected HTTP(S) URL without credentials or fragment")
        args.url.encode("ascii")
        if any(character.isspace() or ord(character) < 32 for character in args.url):
            raise ValueError("URL must not contain whitespace/control characters")
    except ValueError as exc:
        parser.error("--url: {}".format(exc))
    if args.expect_text is not None and len(args.expect_text.encode("utf-8")) > 65536:
        parser.error("--expect-text must be at most 65536 UTF-8 bytes")
    return args


if __name__ == "__main__":
    run(arguments())
