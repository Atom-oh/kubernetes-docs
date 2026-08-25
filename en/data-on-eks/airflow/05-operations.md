# Part 5: Operations and Security

> **Last Updated**: July 15, 2026

Across this series we covered Airflow 3's component architecture (Part 1), Helm-based deployment and the `KubernetesExecutor`/`CeleryExecutor` decision (Part 2), DAG authoring patterns for Kubernetes (Part 3), and MWAA integration (Part 4). This final document covers what's left before a deployment is actually production-ready: scheduler HA, safe upgrades, secrets, logging, monitoring, and a security checklist — then rolls all five parts up into a single go-live checklist.

## 1. Scheduler High Availability

Running multiple scheduler replicas is the standard way to avoid a single point of failure for scheduling. In Airflow 2, this was a genuinely fragile setup: the scheduler process both scheduled tasks *and* parsed DAG files, so multiple scheduler replicas parsing the same DAG bag concurrently created contention and duplicate work that could destabilize scheduling latency under load.

Part 1 covered why this is no longer a concern in Airflow 3: DAG parsing was pulled out of the scheduler entirely and moved to the separate, mandatory `dag-processor` service. Every scheduler replica now does the same thing — read task state and the `serialized_dag` table from Postgres, and queue ready task instances — instead of also racing each other to parse files. Because parsing and scheduling are fully decoupled, adding scheduler replicas is a straightforward horizontal-scaling and HA lever, not a source of new contention.

```yaml
# values.yaml — scheduler replica count
scheduler:
  replicas: 2
```

With the official Helm chart, this is a single field. Postgres itself remains the actual coordination point (schedulers use row-level locking to avoid double-queuing the same task instance), so scheduler HA doesn't require any additional leader-election mechanism on top of what the database already provides.

## 2. Database Migrations and Upgrades

The metadata Postgres database holds every DAG run, task instance, connection, variable, and XCom in the deployment — back it up before any major version upgrade, without exception.

* **Hot backup**: taking a consistent snapshot (e.g. an RDS automated/manual snapshot, or `pg_dump`) while Airflow keeps running is usually sufficient, since the upgrade process itself runs the schema migration.
* **Cold backup**: for the highest consistency guarantee, stop the scheduler, dag-processor, and triggerer first (so nothing is writing task state), then back up, then run the migration.

```bash
# RDS manual snapshot before an upgrade
aws rds create-db-snapshot \
  --db-instance-identifier airflow-metadata-db \
  --db-snapshot-identifier airflow-pre-upgrade-$(date +%Y%m%d)
```

Airflow 3's upgrade path includes schema changes to support the new `serialized_dag`-centric scheduler design, and `airflow db migrate` can take a long time on a database with years of accumulated task-instance and DAG-run history — the migration has to walk and rewrite a proportional number of rows. Before upgrading a long-running deployment, prune old history first so the migration has less to touch:

```bash
# Delete task-instance/DAG-run history older than 60 days before upgrading
airflow db clean --clean-before-timestamp "$(date -d '60 days ago' -Iseconds)" --yes
```

Run `airflow db clean` (or the equivalent retention job) on a recurring schedule going forward, not just before upgrades — it keeps the metadata database small and keeps every future migration faster.

## 3. Secrets Backend Configuration

Storing connections and variables as plaintext rows in the metadata database is the default, but production deployments should back them with AWS Secrets Manager instead, using the provider package's `SecretsManagerBackend`:

```ini
# airflow.cfg
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

With this configuration, a connection lookup for `airflow_remote_logging_conn` first checks Secrets Manager at `airflow/connections/airflow_remote_logging_conn` before falling back to the metadata database.

**This configuration must be identical across the api-server, scheduler, and workers.** Each of these components independently resolves connections and variables at runtime — the secrets backend isn't a scheduler-only concept, and there's no shared cache that lets one component's `[secrets]` setting cover the others. If `backend_kwargs` drifts between components (a stale prefix on the workers, a missing `[secrets]` section on the api-server), that component silently falls through to the metadata database instead of Secrets Manager, and connection lookups start failing inconsistently — working from the scheduler but not from a worker pod, for example, which is a confusing failure mode to debug after the fact.

This matters most for remote-logging connections specifically: every component that emits logs (api-server, scheduler, dag-processor, triggerer, and every task pod under `KubernetesExecutor`) independently resolves the remote-logging connection to know where to ship its logs, so a single misconfigured component silently loses its logs to nowhere useful rather than failing loudly.

## 4. Remote Logging

Task pods are ephemeral, and this is especially true under `KubernetesExecutor` (Part 2) — a pod is created for a task and torn down once it completes. Without remote logging, a task's logs disappear the moment its pod is garbage-collected, which makes debugging a failed run after the fact impossible.

Configure S3 as the remote logging destination, using a connection stored in Secrets Manager rather than inline in `airflow.cfg`:

```ini
# airflow.cfg
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
```

```bash
# The connection itself lives in Secrets Manager, resolved via the SecretsManagerBackend from section 3
# Secret name: airflow/connections/airflow_remote_logging_conn
# Secret value (JSON-encoded Airflow connection):
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

Once this is in place, every component — including task pods that only live for the duration of a single task — ships its logs to S3 as it writes them, so the api-server can render historical logs for a task long after its pod is gone. This is the reason section 3's cross-component consistency requirement matters in practice: if the worker pods resolve `airflow_remote_logging_conn` from a differently configured secrets backend than the api-server does, task logs and UI log rendering silently diverge.

## 5. Monitoring

Airflow components natively emit metrics through either **StatsD** or **OpenTelemetry** — pick one, not both, since they're alternative emission paths configured under `[metrics]` in `airflow.cfg`.

```ini
# airflow.cfg — OpenTelemetry example
[metrics]
otel_on = True
otel_host = otel-collector.monitoring.svc
otel_port = 4318
```

On EKS, the typical stack pairs this metrics emission with **Prometheus or Amazon Managed Prometheus** for storage and **Grafana** for dashboards, using an OpenTelemetry Collector (or the StatsD-to-Prometheus exporter, if using StatsD) as the bridge between Airflow's native emission format and Prometheus's scrape model. **Fluent Bit** typically runs as the log-shipping layer for container stdout/stderr, complementing — not replacing — the S3 remote logging from section 4: Fluent Bit ships infrastructure-level pod logs to your log backend of choice, while remote logging ships Airflow's own task-execution logs to S3 for rendering back in the UI.

## 6. Autoscaling Recap

Part 2 covered KEDA-based autoscaling for `CeleryExecutor` worker pods in depth — scaling the worker `Deployment` up and down based on queued/running task counts read from the metadata database, down to zero replicas when idle. That mechanism doesn't change here; see Part 2 for the full KEDA configuration and behavior.

Under `KubernetesExecutor`, there is no worker `Deployment` to scale at the workload level in the first place — each task is already its own pod. What scales instead is cluster capacity: **Karpenter** or **Cluster Autoscaler** provisions nodes to fit the task pods the scheduler creates, and removes that capacity once the pods complete. The two executors push the autoscaling problem to different layers — KEDA scales a fixed worker pool for `CeleryExecutor`, while cluster-level autoscaling absorbs `KubernetesExecutor`'s per-task pod churn.

## 7. Security Checklist

* **Secrets backend consistency**: `SecretsManagerBackend` (section 3) is configured identically — same `backend_kwargs`, same prefixes — across the api-server, scheduler, dag-processor, triggerer, and workers/task pods. No component silently falls back to the metadata database because of a drifted or missing `[secrets]` section.
* **IRSA scoping for task-level AWS permissions**: each task pod under `KubernetesExecutor` (or each Celery worker) should assume a role scoped to only the AWS actions that task actually needs, via IRSA — not a broad, shared role reused across unrelated DAGs. See Part 3 for assigning a dedicated service account (and therefore IAM role) per task through the `KubernetesPodOperator`.
* **Least-privilege RBAC for the Airflow service account(s)**: the Kubernetes service account(s) the scheduler and dag-processor use to create/watch task pods should be scoped to exactly the verbs and resources (`pods`, `pods/log`, `pods/exec` as needed) they require in their own namespace, not a cluster-wide admin binding.
* **Network policies**: restrict pod-to-pod traffic so the scheduler, api-server, dag-processor, and worker/task pods can only reach what they actually need — the metadata database, the secrets backend's VPC endpoint, the remote-logging destination, and (for `CeleryExecutor`) the broker. Deny-by-default `NetworkPolicy` for the Airflow namespace, with explicit allow rules per component, closes off lateral movement between an unrelated compromised pod and the Airflow control plane.

## 8. Series Wrap-Up: Go-Live Checklist

Rolling up the key items from Parts 1 through 5 of this deep dive into a single pre-production checklist:

- [ ] **Architecture**: all four Airflow 3 services (api-server, scheduler, dag-processor, triggerer) are deployed and DAG parsing is confirmed to happen only in the dag-processor (Part 1)
- [ ] **Metadata database**: running on Amazon RDS for PostgreSQL (not the chart's bundled Postgres) for anything beyond a lab, with automated backups enabled (Parts 1, 5)
- [ ] **Executor decision**: `KubernetesExecutor` vs. `CeleryExecutor` — or a deliberate per-task/per-DAG mix — is documented with its rationale, not left as the chart's default (Part 2)
- [ ] **Autoscaling**: KEDA is wired up for `CeleryExecutor` worker pools, or cluster-level autoscaling (Karpenter/Cluster Autoscaler) is confirmed to absorb `KubernetesExecutor` task-pod churn (Parts 2, 5)
- [ ] **DAG authoring conventions**: task-level executor overrides and `KubernetesPodOperator` usage follow the patterns established for the dag-processor (Part 3)
- [ ] **MWAA vs. self-managed decision**: the choice between managed MWAA and a self-managed EKS deployment is documented with its operational and cost rationale (Part 4)
- [ ] **Scheduler HA**: multiple scheduler replicas are running, relying on Airflow 3's decoupled dag-processor rather than the fragile Airflow 2 pattern (Part 5)
- [ ] **Upgrade rehearsal**: a metadata database backup and history-pruning step have actually been exercised before a major-version upgrade in staging (Part 5)
- [ ] **Secrets backend**: `SecretsManagerBackend` is configured identically across every component, with remote-logging connections verified end to end (Part 5)
- [ ] **Remote logging**: S3 remote logging is enabled and task logs are confirmed viewable in the UI after a task pod has been garbage-collected (Part 5)
- [ ] **Monitoring**: StatsD or OpenTelemetry metrics flow into Prometheus/Amazon Managed Prometheus and Grafana, with Fluent Bit shipping container logs (Part 5)
- [ ] **Security**: IRSA scoping, least-privilege RBAC, and network policies from the section 7 checklist are all in place (Part 5)
- [ ] **Load testing**: DAG concurrency and task volume have actually been exercised at expected peak load before go-live

Satisfying this checklist is a reasonable bar for saying an Airflow 3 deployment is ready to run in production on EKS.

## Lab Environment Setup

To exercise the operational pieces covered in this document hands-on:

* **A working Airflow 3 deployment from Part 2**, with either executor.
* **An S3 bucket** dedicated to remote logging (e.g. `my-airflow-logs-bucket`), with a lifecycle policy if you want to age out old logs automatically.
* **A Secrets Manager secret** holding the remote-logging connection JSON, at a path matching your `connections_prefix` (e.g. `airflow/connections/airflow_remote_logging_conn`).
* **IRSA set up** for the Airflow service account(s) that need to reach Secrets Manager and S3 — this is what lets `SecretsManagerBackend` and remote logging authenticate without static credentials.
* **An OpenTelemetry Collector (or StatsD exporter)** plus a Prometheus/Amazon Managed Prometheus + Grafana stack, if you want to follow along with the monitoring section — an existing `kube-prometheus-stack` installation is sufficient.
* **A staging copy of the metadata database** (an RDS snapshot restored to a separate instance works well) if you want to safely rehearse the backup-and-migrate upgrade procedure from section 2 without touching a real deployment.

---

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/airflow/05-operations-quiz.md).
