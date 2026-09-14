# EKS Spot experiment measurement tools

These standard-library Python tools measure a synthetic HTTP transport workload.
They do not provision AWS resources, inject faults, publish metrics, or certify a
production workload.

The [Korean guide](../../../ko/ops/17-spot-production-experiments.md) and
[English guide](../../../en/ops/17-spot-production-experiments.md) describe the
experiment protocol, compute-manager differences, evidence requirements, and
production adoption gates.

## Startup CPU and Guaranteed QoS (E10)

The guides connect the existing
[phase-aware resizer prototype](../../../en/eks/12-kubernetes-version-roadmap.md)
to a separate **E10 experiment**: provide more CPU during application startup,
then lower CPU requests and limits together while retaining Guaranteed QoS.
Container-level resize is stable from Kubernetes 1.35; MAP admission mutation is
stable from 1.36. The existing MAP injects missing resize policies; it does not
choose startup CPU or monitor application startup.

Use the [E10 protocol](../../../en/ops/17-spot-production-experiments.md#e10-startup-resizing)
and its [Korean counterpart](../../../ko/ops/17-spot-production-experiments.md#e10-startup-resizing).
This directory does not install a MAP, webhook, or resizer, and its HTTP probe
does not measure kubelet resource application or application warmup milestones.

For each independently identified CPU-profile run, collect these alongside the
existing request and metrics files:

- Full Pod snapshots before, during, and after resize, with observation times,
  UID, generation, desired and reported resources, resize conditions, QoS,
  containerID, and restartCount.
- Application initialization and startupProbe/Ready/LB milestones; do not use
  the first successful HTTP probe as an unqualified warmup measurement.
- CPU throttling, memory/OOM, readiness changes, and request SLOs after the
  steady CPU is actually applied, including the relevant peak load.
- Node placement, image-cache state, initial CPU headroom, and the exact
  template, admission policy, resizer build/configuration, and resource-owner
  settings used for the run.

Keep the old dataset unchanged. Its initial templates use requests `50m`/`64Mi`
and limits `500m`/`256Mi`, without this opt-in or a startupProbe; they are not
Guaranteed resource specifications. E10 has **not been run** in the published
Spot measurements. The roadmap's illustrative values and older resize report
are separate from both an observed startup speedup and a combined Spot SLO test.

## Probe

Run the probe on a host or Pod outside the node-reclamation target. Use the same
application path and traffic settings for the comparison runs.

```bash
python3 probe.py \
  --url http://mixed:8080/ \
  --duration 900 \
  --rps 20 \
  --timeout 2 \
  --workers 64 \
  --out ./requests.jsonl > ./metrics.jsonl
```

- Each scheduled slot produces either one request or an explicit generator-skip
  record. The executor queue is bounded.
- Each request uses a new direct connection. There are no retries, redirects,
  connection pooling, or proxy-environment settings.
- HTTP errors, socket timeouts, incomplete bodies, and optional `--expect-text`
  mismatches count as request failures.
- The socket timeout is per socket operation. It is not an end-to-end deadline
  or a DNS timeout.
- Request records contain UTC timestamps, status, error classification, and
  latency. Responses and credentials are not logged.
- Stdout contains interval deltas and one final summary. Exit code zero means
  the measurement completed; it does **not** mean the service passed.
- Quantiles use nearest rank over raw completed-request latencies, including
  failures. Empty samples are `null`. Generator skips remain separate from
  service failures and invalidate claims that all planned load was delivered.
- Runs are bounded to 900 seconds, 20 RPS, and 256 workers. Outstanding requests
  drain after dispatch ends. Existing output files are overwritten.

The actual HTTP path matters. A ClusterIP test does not exercise external load
balancer target deregistration, public DNS, client retry policies, or business
data correctness.

## Offline analysis

After the run completes and both files have been exported:

```bash
python3 summarize.py \
  --requests ./requests.jsonl \
  --metrics ./metrics.jsonl \
  --output ./summary.json \
  --timeline ./timeline.csv
```

The analyzer checks completeness against the final probe summary and recomputes
statistics from request records. It reports whole-run metrics and full rolling
60-second windows; a long healthy tail must not conceal errors during
interruption. The interval between the first failed request's start and the last
failed request's completion is a **failure span**, not continuous downtime.

## Local verification

From the repository root:

```bash
python3 -B -m unittest discover \
  -s examples/eks/spot-production -p 'test_*.py'
```

Tests use local HTTP servers and synthetic records. They do not access AWS.
POSIX process-suspension tests require a POSIX host. The PR workflow runs the
suite on Ubuntu.

## Measured data and chart

[The 2026-09-12 dataset](results/2026-09-12/README.md) includes compressed raw
requests, hashes, summaries, timelines, limitations, and cleanup evidence.

To regenerate the chart with the optional plotting dependency:

```bash
python3 -m venv /tmp/eks-spot-plot
/tmp/eks-spot-plot/bin/python -m pip install matplotlib==3.9.4
/tmp/eks-spot-plot/bin/python examples/eks/spot-production/plot_results.py \
  --results-dir examples/eks/spot-production/results/2026-09-12 \
  --output assets/experiments/eks-spot/2026-09-12-interruption.png
```
