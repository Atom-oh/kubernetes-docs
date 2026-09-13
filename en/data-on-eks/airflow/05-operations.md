# Part 5: Operations and Security

> Reviewed: Airflow 3.3.1, Helm chart 1.22.0, Amazon provider 9.34.0 / Kubernetes provider 10.21.0.

This chapter covers HA, upgrades, secrets, logs, observability and recovery for the
self-managed EKS deployment in Part 2. The operating criterion is **recoverable
execution, data and logs after failure**, beyond merely having settings present.
Use the managed environment/CloudWatch procedures from Part 4 for MWAA.

## 1. Validate scheduler HA together with the database

Airflow 2 already supported scheduler HA and standalone DAG processors.
Airflow 3's mandatory processor separation clarifies resource and responsibility
boundaries, but does not eliminate database contention or guarantee linear scaling.
Schedulers use serialized DAGs and database row locks to coordinate the scheduling
critical section. A separate scheduler leader-election service is not required.

```yaml
scheduler:
  replicas: 2
```

This setting changes replica count only. Also validate node/AZ placement, database
failover and connection limits, API/processor availability, probes/PDBs and executor/
broker health. Measure scheduling delays, retries and duplicate external writes
during node/AZ failures and database failover. A scheduler page's SQL-feature notes
are not the complete supported-database matrix; use Part 1's version guidance.
Triggerers are needed when using triggers, including deferrable tasks.

## 2. Backup, restore and migration

The metadata database stores execution state and many Airflow settings. External
secrets and object-storage XCom backends mean not every value resides in it.
Preserve Fernet keys, DAG/bundle history, images/providers, external data, logs and
secrets as well as the database. Restoring encrypted rows without the decryption
key is insufficient.

Validate this sequence in an environment-specific migration runbook:

1. Check the supported upgrade path and breaking changes. Rehearse with a realistic
   database copy to measure duration, locking, disk space and DAG/provider compatibility.
2. Use the database's consistency guarantees for hot backups and test restoration.
   A successful snapshot request does not prove completion or recoverability.
3. Control new execution and drain or deliberately terminate existing work.
   Coordinate every relevant database writer, including workers/tasks, API servers
   and external automation. Stopping only schedulers, processors and triggerers
   does not quiesce all writes.
4. Establish the backup/recovery point and use one migration mechanism.
   Do not race Helm migration Jobs/hooks with manual airflow db migrate commands.
5. Verify database state, new executions, retries, logs and secret lookup before
   reopening traffic. Redeploying an old image against a migrated schema is not
   a sufficient rollback plan.

### Apply a deliberate history-retention policy

Do not unconditionally delete a fixed number of days before every upgrade.
Check audit/replay/depends_on_past requirements and foreign-key cascades first.
This command is a **non-deleting preview**:

```bash
# Preview only: replace the cutoff and table selection with your retention policy.
airflow db clean \
  --clean-before-timestamp '2026-07-01T00:00:00+00:00' \
  --tables dag_run,task_instance \
  --dry-run \
  --error-on-cleanup-failure
```

Execute cleanup separately only after reviewing the cutoff/tables and backup.
Default archive tables consume space in the same database, so cleanup does not
guarantee immediate disk reclamation or faster execution of every migration.
In 3.3.1, some cleanup failures can otherwise be hidden behind exit status zero;
automation should use --error-on-cleanup-failure and inspect results/logs.

## 3. Fernet and secret-resolution paths

Connections and variables are not simply all plaintext by default. With Fernet
configured, connection password/extra fields and Variable values are encrypted.
This does not encrypt every metadata field or every log; preserve/rotate keys and
control access. AWS Secrets Manager is one supported external backend option.

```ini
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

General server-side lookup is custom backend → environment variables → metastore.
External values are not all listed in the Airflow UI. Editing a duplicated key in
the UI can leave the higher-priority external value in effect.

Airflow 3 supports worker-specific [workers] secrets_backend and
secrets_backend_kwargs. Normal Task SDK task contexts can also resolve server-side
values through the supervisor and Execution API. Components therefore do not all
need identical prefixes or direct database access.

Document the intended path and test API-side lookup, worker overrides and the
logging supervisor's resolution/cache separately. The reviewed code logs backend
exceptions before trying subsequent paths; not every failure is silent. Test both
unexpected fallback values and explicit lookup failures. Do not print secret
contents into diagnostic logs.

## 4. S3 task logs are not instant streaming of every component log

```ini
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
delete_local_logs = False
```

Example secret name: airflow/connections/airflow_remote_logging_conn. Example value:

```json
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

This connection contains no static keys. Configure IRSA or Pod Identity and SDK
credential selection for the actual S3 readers/writers, together with bucket-prefix/
KMS permissions and networking. Receiving connection metadata through the API does
not transfer the API server's AWS credentials. Test both API/UI reading and task/
supervisor writing.

The reviewed 3.3.1 supervisor uploads remote logs after the task subprocess finishes.
The Amazon S3 handler also stores blobs through its close/upload path. Every line
is not guaranteed to reach S3 immediately. Test successful and failed tasks, forced
worker termination and UI retrieval after pod deletion. SIGKILL or node failure
before final upload can lose recent logs.

S3 remote_logging configures the **Airflow task-log path**. It does not automatically
send all scheduler/API/processor service logs to the same S3 location.
Separate stdout/stderr collection, for example with Fluent Bit, complements it.
If a task writes only to files, collecting container stdout does not automatically
collect those files. PVCs or independent collectors may retain logs after pod
deletion; inspect the actual storage, retention and loss boundaries.

For KPO, the caller's get_logs behavior brings child output into the Airflow task
log. Copying airflow.cfg into an arbitrary child image without Airflow does not
create remote logging.

## 5. Metrics transport and collection

Use an image with matching OTel dependencies and choose a metrics backend.
The following selects OTel:

```ini
[metrics]
statsd_on = False
otel_on = True
```

Example environment variables for each metrics-emitting process:

```dotenv
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector.monitoring.svc:4318/v1/metrics
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf
OTEL_METRIC_EXPORT_INTERVAL=30000
OTEL_SERVICE_NAME=airflow
```

In 3.3.1, older otel_host, otel_port and otel_interval_milliseconds settings are
deprecated in favor of standard OTel environment variables. This endpoint is an
internal OTLP/HTTP example. Match the Collector HTTP receiver, Service port, network
policies and required TLS/authentication.

Prometheus does not simply scrape an OTLP endpoint. Complete the metrics pipeline,
for example by scraping a Collector Prometheus exporter or using a suitable
remote-write exporter with authentication. For AMP, verify the workspace endpoint
and AWS authentication. With StatsD, also inspect exporter mapping and actual series.

Observe scheduler heartbeat/scheduling delay, parse errors/duration, queued-task
age, worker/triggerer health, database connections/locks, Pending/OOM/disk-pressure
conditions and log-upload failures. Check exported metric names/labels before
building alerts, and test notification delivery through controlled failures.

## 6. Autoscaling and security boundaries

Celery KEDA queries must distinguish queues, executors and aliases and account for
concurrency and replica limits as in Part 2. Workers may use Deployments or
StatefulSets depending on persistence. Scaling to zero depends on minimum replicas,
triggers and cooldown; it does not remove all service idle costs.

KubernetesExecutor creates task pods directly, so it does not need the same Celery
worker-pool scaling pattern. This does not mean KEDA supports only Deployments.
Node autoscalers also do not remove every node immediately after tasks finish.
Account for capacity, quotas, PDBs, disruption policy and other workloads.

| Boundary | What to verify |
| --- | --- |
| AWS identity | Tasks on a shared Celery worker share its role. Use actual execution boundaries such as separate pools/executors/KPO children for isolation |
| Kubernetes RBAC | Grant permissions to the KubernetesExecutor or KPO caller that needs them. DAG parsing alone does not require pod-creation rights |
| Namespace/admission | Pod creation can permit selecting other service accounts or dangerous specs; inspect trust boundaries and admission controls |
| NetworkPolicy | Verify CNI enforcement and DNS, Execution API, DB/broker, Kubernetes API, credential/secret/log endpoints |

NetworkPolicy restricts L3/L4 connectivity. It does not replace IAM/RBAC/TLS
authentication or guarantee prevention of all lateral movement. Permit actual
dependencies before applying default deny, without broadening unnecessary task
access to the database.

## 7. Operational acceptance

- [ ] Record supported runtimes/providers, executor choice and DAG delivery/rerun-version policy.
- [ ] Test a suitable production database, backup/restore and Fernet/external-data recovery. RDS is one option, not the only option.
- [ ] Test failure/recovery and capacity limits for scheduler/API/processor and required triggerers.
- [ ] Rehearse migration, admission of new runs, draining and rollback with a realistic database copy.
- [ ] Verify intended secret-resolution and IAM/RBAC/admission/network boundaries.
- [ ] Inspect logs after success, failure, forced termination and pod deletion, documenting loss limits.
- [ ] Connect metrics, service/task logs and alerts to responsible responders and procedures.
- [ ] Measure latency, retries, duplicate external writes and recovery under target load and failures.

Checkboxes do not guarantee reliability. Include measured results and unresolved
limits against the required SLOs, recovery times and retention objectives.

## Validation scope and references

Official documentation and released source were checked for configuration,
secret-resolution paths and upload timing. Example structure and local file
behavior of the S3 upload method were validated. No actual database migration,
AWS secret/S3 call, Collector ingestion or failure-recovery exercise was performed.


- [Scheduler HA and database coordination](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/scheduler.html)
- [Database upgrades](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/upgrading.html)
- [Database maintenance CLI](https://airflow.apache.org/docs/apache-airflow/3.3.1/cli-and-env-variables-ref.html)
- [Fernet encryption](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/fernet.html)
- [Secrets backends and worker configuration](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/secrets-backend/index.html)
- [Task logging](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/logging-tasks.html)
- [Metrics configuration](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/metrics.html)
- [Amazon provider 9.34.0 S3 log implementation](https://github.com/apache/airflow/blob/providers-amazon/9.34.0/providers/amazon/src/airflow/providers/amazon/aws/log/s3_task_handler.py)

[README](README.md)

[Quiz](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)
