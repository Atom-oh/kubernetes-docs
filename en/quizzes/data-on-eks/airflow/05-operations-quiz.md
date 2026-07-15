# Part 5: Operations and Security Quiz

This quiz tests your understanding of Airflow operations spanning the whole deep dive series: scheduler HA, database upgrades, secrets backend consistency, remote logging, monitoring, autoscaling, and the security checklist.

## Multiple Choice Questions

1. Why is running multiple scheduler replicas safer in Airflow 3 than it was in Airflow 2?
   - A) Airflow 3 schedulers no longer need Postgres
   - B) DAG parsing moved to the separate, mandatory `dag-processor` service, so schedulers no longer contend over parsing the same DAG bag
   - C) Airflow 3 schedulers use a built-in leader-election protocol instead of the database
   - D) Airflow 3 removed the metadata database entirely

<details>

<summary>Show Answer</summary>

**Answer: B) DAG parsing moved to the separate, mandatory `dag-processor` service, so schedulers no longer contend over parsing the same DAG bag**

**Explanation:**
In Airflow 2, the scheduler both scheduled tasks and parsed DAG files, so multiple scheduler replicas parsing the same DAGs concurrently caused contention and duplicate work. Airflow 3 makes the `dag-processor` a separate, mandatory service that owns parsing; schedulers only read the `serialized_dag` table and queue ready task instances, so adding scheduler replicas is a straightforward scaling/HA lever rather than a source of new contention. Postgres row-level locking, not a separate leader-election mechanism, is what prevents double-queuing.
</details>

2. What should you do before running a major Airflow version upgrade that includes metadata database schema changes?
   - A) Delete the `serialized_dag` table so the migration starts clean
   - B) Back up the metadata database, and consider pruning old DAG-run/task-instance history first
   - C) Disable the dag-processor permanently
   - D) Nothing — Airflow migrations are always backward-compatible and reversible

<details>

<summary>Show Answer</summary>

**Answer: B) Back up the metadata database, and consider pruning old DAG-run/task-instance history first**

**Explanation:**
The metadata database holds every DAG run, task instance, connection, variable, and XCom, so it must be backed up (hot or cold) before any major upgrade. Because Airflow 3's migration includes schema changes that can be slow on large databases, pruning old history first (e.g. `airflow db clean`) reduces how many rows the migration has to walk and rewrite.
</details>

3. Why must the Secrets Manager backend configuration be identical across the api-server, scheduler, and workers?
   - A) It isn't required — only the scheduler needs it configured
   - B) Each component independently resolves connections/variables at runtime, and a drifted config silently falls back to the metadata database for that component only
   - C) The chart automatically syncs `airflow.cfg` across all pods
   - D) Secrets Manager only allows one client to read a given secret at a time

<details>

<summary>Show Answer</summary>

**Answer: B) Each component independently resolves connections/variables at runtime, and a drifted config silently falls back to the metadata database for that component only**

**Explanation:**
There is no shared cache or single point where one component's `[secrets]` configuration covers the others. If `backend_kwargs` (prefixes) drift or a `[secrets]` section is missing on one component, that component silently falls through to the metadata database instead of Secrets Manager, causing connection lookups to fail inconsistently between components — for example working from the scheduler but not from a worker pod.
</details>

4. Why does remote logging matter specifically for `KubernetesExecutor` deployments?
   - A) `KubernetesExecutor` doesn't support StatsD metrics
   - B) Task pods are ephemeral and torn down after each task, so without remote logging the task's logs disappear once the pod is garbage-collected
   - C) `KubernetesExecutor` requires a Celery broker to store logs
   - D) Remote logging is required for `KubernetesExecutor` to function at all

<details>

<summary>Show Answer</summary>

**Answer: B) Task pods are ephemeral and torn down after each task, so without remote logging the task's logs disappear once the pod is garbage-collected**

**Explanation:**
Under `KubernetesExecutor`, each task gets its own pod that's created for the task and torn down on completion. If logs aren't shipped somewhere durable (S3, via remote logging), they're lost the moment the pod is garbage-collected, making it impossible to debug a failed run afterward.
</details>

5. Which AWS Secrets Manager-backed class implements Airflow's secrets backend integration?
   - A) `airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend`
   - B) `airflow.secrets.aws.AWSSecretsClient`
   - C) `airflow.providers.aws.secrets_backend.SecretsManagerConnection`
   - D) `airflow.utils.secrets.SecretsManagerHook`

<details>

<summary>Show Answer</summary>

**Answer: A) `airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend`**

**Explanation:**
This is configured under `[secrets] backend = ...` in `airflow.cfg`, along with `backend_kwargs` specifying `connections_prefix`, `variables_prefix`, and `config_prefix`. It must be set identically on every component that resolves connections or variables.
</details>

6. Under `CeleryExecutor`, what does KEDA scale based on (as covered in Part 2)?
   - A) CPU and memory utilization of the worker pods
   - B) Queued/running task instance counts read from the metadata database
   - C) The number of DAG files in the dags folder
   - D) Network throughput on the Redis broker

<details>

<summary>Show Answer</summary>

**Answer: B) Queued/running task instance counts read from the metadata database**

**Explanation:**
KEDA polls the metadata database for the count of running/queued task instances and scales the Celery worker `Deployment` to match, including scaling down to zero when idle. CPU/memory-based HPA doesn't reflect actual queue depth the way this does.
</details>

7. Why is there no KEDA-based autoscaling pattern for `KubernetesExecutor`?
   - A) KEDA doesn't support Kubernetes-native workloads
   - B) `KubernetesExecutor` already creates one pod per task, so there's no fixed worker pool to right-size — cluster-level autoscaling handles capacity instead
   - C) `KubernetesExecutor` doesn't support autoscaling at all
   - D) KEDA is only compatible with Redis-backed brokers

<details>

<summary>Show Answer</summary>

**Answer: B) `KubernetesExecutor` already creates one pod per task, so there's no fixed worker pool to right-size — cluster-level autoscaling handles capacity instead**

**Explanation:**
KEDA's role is to resize a long-running Deployment based on an external metric. `KubernetesExecutor` never has such a Deployment — each task pod is created and destroyed independently — so what needs to scale is cluster capacity for those pods, which is Karpenter's or Cluster Autoscaler's job.
</details>

8. In the security checklist, why should each task's IRSA role be scoped narrowly rather than shared broadly across DAGs?
   - A) IRSA roles have a hard limit of one policy each
   - B) A broad, shared role grants every task the union of all permissions any task might need, defeating least-privilege
   - C) Narrow roles are required by the Kubernetes API server
   - D) IRSA doesn't support role reuse across pods

<details>

<summary>Show Answer</summary>

**Answer: B) A broad, shared role grants every task the union of all permissions any task might need, defeating least-privilege**

**Explanation:**
Each task pod (or Celery worker) should assume a role scoped to only the AWS actions that specific task needs, via IRSA. A single shared role reused across unrelated DAGs effectively gives every task the combined permissions of all of them, which is exactly what least-privilege scoping is meant to prevent.
</details>

## Short Answer Questions

9. Name two components (besides the metadata database) that would fail to log correctly if the Secrets Manager backend configuration for the remote-logging connection drifted between them.

<details>

<summary>Show Answer</summary>

**Answer: Any two of: api-server, scheduler, dag-processor, triggerer, or task pods (under `KubernetesExecutor`) / Celery workers**

**Explanation:**
Every log-emitting component independently resolves the remote-logging connection at runtime. If one component's secrets backend configuration drifts from the others, that component silently falls back to the metadata database (or fails to resolve the connection at all), and its logs stop shipping to the remote destination while other components' logs continue working normally.
</details>

10. What two things restrict pod-to-pod traffic in the security checklist, and what should they allow by default?

<details>

<summary>Show Answer</summary>

**Answer: Network policies, restricting scheduler/api-server/dag-processor/worker traffic to only what's needed — default deny, with explicit allow rules per component**

**Explanation:**
A deny-by-default `NetworkPolicy` for the Airflow namespace, with explicit allow rules for each component's actual dependencies (metadata database, secrets backend VPC endpoint, remote-logging destination, and the broker for `CeleryExecutor`), prevents lateral movement between an unrelated compromised pod and the Airflow control plane.
</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/05-operations.md) | [Back to Airflow Deep Dive Home](../../../data-on-eks/airflow/README.md)
