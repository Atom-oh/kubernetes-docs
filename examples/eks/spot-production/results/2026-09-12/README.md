# Measured EKS Spot experiments — 2026-09-12

This is one exploratory run per scenario on a synthetic ClusterIP HTTP workload.
The conclusion is **hold production expansion**, with version compatibility,
interruption handling, application shutdown, and representative workload testing
still required.

`results.json` contains the environment, topology, limitations, summaries, event
timeline, price snapshot, and verified cleanup status.

| Directory | Stimulus | Duration |
|---|---|---:|
| `e0-baseline` | Steady traffic without faults | 120 seconds |
| `e1-drain` | Drain one dedicated Spot node, then uncordon it | 180 seconds |
| `e2-interruption` | FIS interruption of one dedicated Spot instance | 900 seconds |
| `e4-ondemand-transition` | Explicitly change the cohort's Pod selector to On-Demand | 240 seconds |

Each directory has three path prefixes:

- `baseline`: three On-Demand control Pods.
- `mixed`: one On-Demand Pod plus the two Spot Pods before E4.
- `spot-only`: the same two Spot Pods as the mixed path, not an independent
  workload. During E4 these Pods migrate to On-Demand; the filename remains the
  original Service name.

The On-Demand control, stable mixed Pod, and load generator share a node. These
paths are useful for observing request behavior, not independent comparisons of
cost, throughput, or high-availability designs. Every request is a fresh
connection, HTTP GET `/`, with an empty response body and no retries.

For each path:

- `*-requests.jsonl.gz`: all request and generator-skip records, with deterministic
  gzip headers. Responses, credentials, account IDs, and node/network identifiers
  are not included.
- `*-metrics.jsonl`: original interval counters and final probe summary.
- `*-analysis.json`: offline validation and recomputed statistics.
- `*-timeline.csv`: one-second bins by request start time; skips use scheduled
  time. Completed and launched counts are equal here because these are complete,
  drained records, not live completion-rate measurements.

`raw-request-sha256.json` hashes the **uncompressed** request files.
`e2-node-pod-timeline.json` contains sanitized event times and Ready Pod
observations. API observation time and reported condition/event time are
different fields.

To independently recompute a result from the repository root:

```bash
gzip -dc examples/eks/spot-production/results/2026-09-12/e2-interruption/mixed-requests.jsonl.gz \
  > /tmp/eks-spot-mixed-requests.jsonl

python3 examples/eks/spot-production/summarize.py \
  --requests /tmp/eks-spot-mixed-requests.jsonl \
  --metrics examples/eks/spot-production/results/2026-09-12/e2-interruption/mixed-metrics.jsonl \
  --output /tmp/eks-spot-mixed-analysis.json \
  --timeline /tmp/eks-spot-mixed-timeline.csv
```

The worst error window is a complete sliding 60-second window evaluated every
second. Overall low error rates or p99 values do not establish an interruption
window SLO. A failure span is not continuous downtime. Socket timeouts are per
operation, and the experiments did not measure business-data correctness.

`resources.template.json` is the initial applied Kubernetes configuration with
infrastructure identifiers replaced by `REPLACE_*` markers. It is **not directly
deployable**. Select a compatible Karpenter version and review the node role,
AMI, private subnets, security group, resource names, and experiment scope before
using it. It describes the historical test, not a production recommendation.
The On-Demand probe Pod, private collection helper, IAM role, alarm, and observer
queue are described in the guide; this sanitized initial manifest is not an
end-to-end provisioning tool.

Actual billing, capacity-error automatic fallback, external load balancers,
concurrent reclamation, AZ failure, peak/HPA behavior, and business correctness
were not validated. Unit-price comparisons in `results.json` are not realized
workload savings.

The experiment's live instances, volumes, Kubernetes resources, FIS template and
role, instance profile, alarm, EventBridge rule, and SQS queue were removed.
AWS historical FIS records and metric data remain under service retention.
