# Observability lab load tests

Reviewed September 13, 2026 with k6 2.2.0 and Locust 2.46.5/Python 3.12.
Run only against a disposable lab you own. These examples create orders and
simulated payments. They must never target a real payment gateway.

Both tools follow the same contract:

1. `POST /orders` → 201 and an `id`.
2. `POST /payments` with that `order_id` → 200/201 and `status: completed`.
3. `GET /orders/{id}` → 200 and the same ID.

Adapt the paths and assertions together if your application has another API.
Non-JSON responses, missing IDs, unsuccessful payment states and mismatched
read results fail the test. Metrics group dynamic IDs under `GET /orders/:id`
to avoid an unbounded series per order.

From this directory, in separate terminals:

```bash
kubectl --context service -n msa port-forward svc/api-gateway 8080:8080
```

```bash
BASE_URL=http://127.0.0.1:8080 LOAD_PROFILE=smoke \
  k6 run --no-usage-report k6-scenario.js
```

The default smoke test runs two iterations. `LOAD_PROFILE=scale` runs one
continuous sequence: 30 s ramp to 5 VUs, 60 s at 5, 15 s ramp to 20,
30 s at 20, 15 s back to 5, then 30 s down to zero. VUs are concurrent
script executions, not requests per second. The assertions and latency
thresholds are exercise acceptance criteria, not measured production SLOs.

For an in-cluster smoke test, create the script ConfigMap before the Job:

```bash
kubectl --context service -n msa create configmap obs-lab-k6 \
  --from-file=k6-scenario.js --dry-run=client -o yaml |
  kubectl --context service apply -f -
kubectl --context service apply -f k6-job.yaml
kubectl --context service -n msa logs -f job/obs-lab-k6-smoke
kubectl --context service -n msa get job obs-lab-k6-smoke
```

The Job has no retries and a two-minute deadline. Inspect `Complete`/`Failed`
and the container exit code; merely creating a Job is not a successful test.
The summary file is ephemeral; preserve logs/results before deleting the Pod.
To rerun, delete only this finished Job, then apply it again.

Locust runs headless without exposing a web UI or worker RPC port:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/locust -f locustfile.py --headless \
  --host http://127.0.0.1:8080 --users 1 --spawn-rate 1 \
  --run-time 10s --stop-timeout 5 --exit-code-on-error 99 \
  --csv locust-results
```

Local validation used each real load tool against a synthetic loopback HTTP
server for success and five failure cases. This validates request/assertion
behavior, not the MSA, Kubernetes Job execution, KEDA/Karpenter scaling,
throughput, latency capacity or a real AWS deployment.
