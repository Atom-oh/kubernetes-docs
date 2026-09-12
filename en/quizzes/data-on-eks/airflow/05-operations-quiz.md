# Part 5: Operations and Security Quiz

Check operational and recovery boundaries for Airflow 3.3.1.

1. Does separating the DAG processor remove all scheduler database contention in Airflow 3?

<details>
<summary>Show Answer</summary>

**Answer:** No. Airflow 2 also supported HA; version 3 still requires database-lock, connection and execution-capacity checks.

**Explanation:** replicas=2 does not automatically provide placement diversity, database failover or full-service HA.

</details>

2. Does stopping schedulers, processors and triggerers quiesce all database writers before migration?

<details>
<summary>Show Answer</summary>

**Answer:** No. Coordinate ingress, draining and writes from workers/tasks, API servers and external automation too.

**Explanation:** Test database restoration and Fernet/external-data recovery; use one migration path and a verified rollback plan.

</details>

3. Must every Airflow component use an identical Secrets Manager prefix?

<details>
<summary>Show Answer</summary>

**Answer:** No. Worker-specific backends and Execution API resolution can be intentional.

**Explanation:** Verify actual lookup order, permissions, fallback and caching. Some paths log exceptions; not every failure is silent.

</details>

4. Does S3 remote_logging=True instantly upload every line from every component?

<details>
<summary>Show Answer</summary>

**Answer:** No. It configures task logs, and the reviewed supervisor uploads after task execution ends.

**Explanation:** Service stdout/stderr may need separate collection. Forced termination before upload can lose recent logs.

</details>

5. Are Connection/Variable values in a Fernet-configured metastore all plaintext?

<details>
<summary>Show Answer</summary>

**Answer:** No. Password/extra fields and Variable values are encrypted, but not all metadata or logs are.

**Explanation:** Preserve and rotate Fernet keys. External backends are options; AWS Secrets Manager is not the sole required production choice.

</details>

6. Is counting all queued/running tasks enough for a Celery KEDA query?

<details>
<summary>Show Answer</summary>

**Answer:** Account for queues, executors, aliases, worker concurrency and replica limits.

**Explanation:** Workers can use Deployments or StatefulSets, and scaling to zero depends on actual configuration.

</details>

7. Why is Celery worker-pool scaling not applied unchanged to KubernetesExecutor?

<details>
<summary>Show Answer</summary>

**Answer:** It creates task pods directly and has no equivalent fixed worker pool.

**Explanation:** This does not mean KEDA supports only Deployments. Check node-autoscaler capacity, quotas and disruption constraints separately.

</details>

8. Does assigning an IAM role to a shared Celery worker automatically isolate each task's AWS permissions?

<details>
<summary>Show Answer</summary>

**Answer:** No. Multiple tasks on that worker can share its execution permissions.

**Explanation:** Use actual boundaries such as separate pools, executors or KPO children when required, and inspect credential sources.

</details>

9. How should db clean automation preview changes and detect failures?

<details>
<summary>Show Answer</summary>

**Answer:** First use --dry-run with reviewed cutoff/tables; use --error-on-cleanup-failure and inspect logs.

**Explanation:** Execute deletion separately. Default archives consume database space and cascades matter; cleanup does not always reclaim disk or speed every migration.

</details>

10. Do a NetworkPolicy and an OTLP endpoint alone complete security and observability?

<details>
<summary>Show Answer</summary>

**Answer:** No. Verify CNI enforcement, actual allowed paths, authentication, Collector receivers/exporters, storage and alerts.

**Explanation:** NetworkPolicy does not replace IAM/RBAC/TLS. Prometheus does not simply scrape an OTLP/HTTP endpoint.

</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/05-operations.md) | [Airflow](../../../data-on-eks/airflow/README.md)
