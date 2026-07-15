# Helm Deployment and Executor Choice Quiz

This quiz tests your understanding of the two Airflow Helm charts, installation with the official chart, the KubernetesExecutor vs. CeleryExecutor trade-off, and KEDA-based autoscaling for Celery workers.

## Multiple Choice Questions

1. Which Helm chart is the official one maintained by the Apache Airflow project?
   - A) `airflow-helm/charts`
   - B) `apache/airflow`
   - C) `bitnami/airflow`
   - D) Both are equally official

<details>

<summary>Show Answer</summary>

**Answer: B) `apache/airflow`**

**Explanation:**
`apache/airflow` is published from the `chart` directory of the main `apache/airflow` repository and is the chart referenced by upstream documentation and release notes. `airflow-helm/charts` is an older, independently maintained community chart with a different values schema and no affiliation with the Apache Airflow project — a common source of confusion when following outdated tutorials.

</details>

2. What is the minimum Helm version required by the official `apache/airflow` chart as of chart 1.22.0?
   - A) Helm 2.x
   - B) Helm 3.12.0
   - C) Helm 3.19.0
   - D) Any Helm 3.x version

<details>

<summary>Show Answer</summary>

**Answer: C) Helm 3.19.0**

**Explanation:**
The chart declares Helm 3.19.0 as its minimum required version. This constraint is enforced by the chart's own `Chart.yaml`, so installing with an older Helm client fails at install time rather than producing a partially broken deployment.

</details>

3. Since which chart version has the official `apache/airflow` chart required Kubernetes 1.30+?
   - A) 1.0.0
   - B) 1.10.0
   - C) 1.16.0
   - D) 1.22.0

<details>

<summary>Show Answer</summary>

**Answer: C) 1.16.0**

**Explanation:**
Chart version 1.16.0 introduced the Kubernetes 1.30+ requirement, and it has carried forward into later versions including the current 1.22.0.

</details>

4. Which single top-level `values.yaml` field determines whether the chart deploys a Celery worker Deployment and Redis broker at all?
   - A) `workers.replicas`
   - B) `executor`
   - C) `postgresql.enabled`
   - D) `scheduler.replicas`

<details>

<summary>Show Answer</summary>

**Answer: B) `executor`**

**Explanation:**
Setting `executor: CeleryExecutor` conditionally renders the worker Deployment and Redis broker; `executor: KubernetesExecutor` renders neither. Because this field changes which components are deployed at all, changing it after a deployment already carries production traffic is disruptive.

</details>

5. Roughly how long is a `KubernetesExecutor` task pod's cold-start latency, even for a trivial task?
   - A) A few milliseconds
   - B) 1–2 minutes
   - C) 10–15 minutes
   - D) There is no cold start with KubernetesExecutor

<details>

<summary>Show Answer</summary>

**Answer: B) 1–2 minutes**

**Explanation:**
Even a trivial task pays for pod scheduling, a potential image pull, and possibly a node scale-out event through Karpenter or Cluster Autoscaler if no spare capacity exists — together this typically costs roughly 1–2 minutes before the task actually starts running.

</details>

6. What additional infrastructure does `CeleryExecutor` require that `KubernetesExecutor` does not?
   - A) A dedicated StorageClass
   - B) A message broker (Redis or RabbitMQ) and a worker Deployment
   - C) A separate Kubernetes cluster
   - D) A service mesh

<details>

<summary>Show Answer</summary>

**Answer: B) A message broker (Redis or RabbitMQ) and a worker Deployment**

**Explanation:**
`CeleryExecutor` needs a broker to queue tasks between the scheduler and workers, plus a long-running worker Deployment that stays warm and pulls tasks from that broker. `KubernetesExecutor` needs neither — the scheduler talks directly to the Kubernetes API to create per-task pods.

</details>

7. What does the KEDA `ScaledObject` query (`SELECT ceil(COUNT(*)/worker_concurrency) FROM task_instance WHERE state IN (running, queued)`) actually measure to decide the Celery worker replica count?
   - A) Total number of DAGs ever registered
   - B) The number of worker replicas needed to cover all currently running/queued task instances at the configured concurrency per pod
   - C) CPU utilization of the scheduler pod
   - D) The size of the PostgreSQL database

<details>

<summary>Show Answer</summary>

**Answer: B) The number of worker replicas needed to cover all currently running/queued task instances at the configured concurrency per pod**

**Explanation:**
The query counts task instances currently in `running` or `queued` state, then divides by `worker_concurrency` (rounded up) to get the number of worker pods needed to keep up with that workload. KEDA polls this roughly every 10 seconds and resizes the worker Deployment accordingly.

</details>

8. After Celery worker task activity drops to zero, roughly how long does KEDA wait before scaling the worker Deployment down to zero replicas?
   - A) Immediately
   - B) About 30 seconds
   - C) About 5 minutes
   - D) About 1 hour

<details>

<summary>Show Answer</summary>

**Answer: C) About 5 minutes**

**Explanation:**
KEDA waits roughly 5 minutes after the last task activity before scaling the worker Deployment to zero, so a brief lull between DAG runs doesn't cause the worker pool to be torn down and immediately recreated.

</details>

9. Why is there no "KEDA for KubernetesExecutor" autoscaling pattern equivalent to the Celery worker setup?
   - A) KEDA doesn't support Kubernetes-based Airflow deployments at all
   - B) KubernetesExecutor already creates one pod per task, so there's no fixed-size worker Deployment to resize — the thing that needs to scale is cluster compute capacity via Karpenter/Cluster Autoscaler
   - C) KubernetesExecutor tasks cannot be scaled under any circumstances
   - D) KEDA is only compatible with Redis-backed workloads

<details>

<summary>Show Answer</summary>

**Answer: B) KubernetesExecutor already creates one pod per task, so there's no fixed-size worker Deployment to resize — the thing that needs to scale is cluster compute capacity via Karpenter/Cluster Autoscaler**

**Explanation:**
KEDA's role is to resize a long-running Deployment based on an external metric. `KubernetesExecutor` never has such a Deployment — scaling is already granular at the pod level, one per task — so the relevant scaling concern shifts to cluster-level compute capacity, which is Karpenter's or Cluster Autoscaler's job rather than a workload autoscaler's.

</details>

10. What does Airflow 3's "multiple executors concurrently" feature allow you to do?
    - A) Run two independent Airflow installations side by side
    - B) Assign an executor per task or per DAG instead of committing one executor to the entire deployment
    - C) Automatically choose the cheaper executor at runtime
    - D) Replace the scheduler with two redundant instances

<details>

<summary>Show Answer</summary>

**Answer: B) Assign an executor per task or per DAG instead of committing one executor to the entire deployment**

**Explanation:**
This lets a single deployment mix executors — for example, most DAGs on a warm `CeleryExecutor` pool for low-latency dispatch, with a handful of resource-heavy or GPU tasks explicitly routed to `KubernetesExecutor` for isolation — rather than forcing an all-or-nothing choice for the whole deployment.

</details>

## Short Answer Questions

11. What is the name of the older, independently maintained community Helm chart that is often confused with the official `apache/airflow` chart?

<details>

<summary>Show Answer</summary>

**Answer: `airflow-helm/charts`**

**Explanation:**
It predates the official chart, uses a different values schema, and has no affiliation with the Apache Airflow project — a frequent source of values.yaml snippets that don't apply to `apache/airflow`.

</details>

12. What is the minimum `minReplicaCount` value that lets KEDA scale the Celery worker Deployment all the way down when idle?

<details>

<summary>Show Answer</summary>

**Answer: 0**

**Explanation:**
Setting `workers.celery.keda.minReplicaCount: 0` allows the ScaledObject to scale the worker Deployment to zero replicas after roughly 5 minutes without task activity, eliminating idle worker cost entirely.

</details>

13. Which two Kubernetes cluster-level autoscalers handle capacity for `KubernetesExecutor` task pods, since there is no workload-level KEDA scaler for them?

<details>

<summary>Show Answer</summary>

**Answer: Karpenter and Cluster Autoscaler**

**Explanation:**
Because `KubernetesExecutor` creates one pod per task rather than maintaining a fixed worker pool, the scaling concern shifts entirely to cluster compute capacity — provisioning enough nodes for those task pods — which is Karpenter's or Cluster Autoscaler's responsibility.

</details>

14. Which two `task_instance` states does the KEDA `ScaledObject` query count when calculating the required Celery worker replica count?

<details>

<summary>Show Answer</summary>

**Answer: `running` and `queued`**

**Explanation:**
The query sums task instances in the `running` or `queued` state and divides by `worker_concurrency` to determine how many worker pods are needed to keep up with current demand.

</details>

15. What top-level `values.yaml` field must be set to `CeleryExecutor` before `workers.celery.keda.enabled` has any effect?

<details>

<summary>Show Answer</summary>

**Answer: `executor`**

**Explanation:**
The KEDA autoscaling settings under `workers.celery` are only relevant once `executor: CeleryExecutor` is set — `KubernetesExecutor` deployments never render a Celery worker Deployment for KEDA to target.

</details>

## Hands-on Questions

16. Write the full command sequence to add the official Apache Airflow Helm repository and install chart version 1.22.0 into a new `airflow` namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Add the official Apache Airflow Helm repository
helm repo add apache-airflow https://airflow.apache.org/
helm repo update

# Install into a dedicated namespace, pinned to a specific chart version
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --create-namespace \
  --version 1.22.0

# Verify the installation
kubectl get pods -n airflow
helm list -n airflow
```

**Explanation:**
`helm repo add` registers the official repository (not to be confused with `airflow-helm/charts`), and `--create-namespace` avoids a separate `kubectl create namespace` step. Pinning `--version 1.22.0` ensures a reproducible deployment rather than whatever happens to be latest at install time.

</details>

17. Write a `values.yaml` snippet that selects `KubernetesExecutor` and disables the chart's bundled PostgreSQL (for use with an external RDS instance).

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
executor: KubernetesExecutor

postgresql:
  enabled: false
```

**Explanation:**
`executor: KubernetesExecutor` means no Celery worker Deployment or Redis broker is rendered at all. Setting `postgresql.enabled: false` skips the chart's bundled in-cluster PostgreSQL pod so the deployment can point at an external database via connection settings elsewhere in `values.yaml`.

</details>

18. Write a `values.yaml` snippet that selects `CeleryExecutor` and enables KEDA autoscaling for the Celery workers, scaling from zero up to 20 replicas.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
executor: CeleryExecutor

workers:
  celery:
    keda:
      enabled: true
      minReplicaCount: 0
      maxReplicaCount: 20
```

**Explanation:**
`executor: CeleryExecutor` renders the worker Deployment and Redis broker. `workers.celery.keda.enabled: true` creates a KEDA `ScaledObject` that polls the metadata database roughly every 10 seconds and resizes the worker Deployment between 0 and 20 replicas based on running/queued task counts, scaling to zero after roughly 5 minutes of inactivity.

</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/02-helm-deployment.md) | [Previous Quiz: Airflow Architecture](./01-architecture-quiz.md)
