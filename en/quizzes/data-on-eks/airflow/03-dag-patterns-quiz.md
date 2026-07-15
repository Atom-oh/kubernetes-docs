# DAG Patterns and KubernetesPodOperator Quiz

This quiz tests your understanding of `KubernetesPodOperator`'s relationship to the chosen executor, pod spec precedence, per-task IRSA scoping, and Airflow 3's DAG bundle model.

## Multiple Choice Questions

1. A DAG runs under `CeleryExecutor`, and one of its tasks is a `KubernetesPodOperator`. What actually happens when that task runs?
   - A) The task instance itself gets special-cased to run as a Kubernetes pod instead of on a Celery worker
   - B) A warm Celery worker executes the KPO task's `execute()` method, which then creates and watches a separate Pod for the actual work
   - C) Airflow silently switches the whole deployment's executor to `KubernetesExecutor` for that task
   - D) The task fails, since `KubernetesPodOperator` requires `KubernetesExecutor`

<details>

<summary>Show Answer</summary>

**Answer: B) A warm Celery worker executes the KPO task's `execute()` method, which then creates and watches a separate Pod for the actual work**

**Explanation:**
`KubernetesPodOperator` is available under either executor. Whichever mechanism runs the task instance itself — a Celery worker under `CeleryExecutor`, or a fresh per-task pod under `KubernetesExecutor` — that process calls KPO's `execute()` method, which creates a second, separate Pod through the Kubernetes API and waits for it to finish. The executor choice never blocks or requires KPO.
</details>

2. A team switches a DAG's deployment from `CeleryExecutor` to `KubernetesExecutor`. The DAG has one `KubernetesPodOperator` task. What changes about how many pods that task produces?
   - A) It now produces two pods for that task where it used to produce one
   - B) It now produces one pod for that task where it used to produce two
   - C) Nothing changes — it was already producing a task-execution pod/process plus KPO's own launched pod, and it still is
   - D) It stops using pods entirely and runs the task as a local process

<details>

<summary>Show Answer</summary>

**Answer: C) Nothing changes — it was already producing a task-execution pod/process plus KPO's own launched pod, and it still is**

**Explanation:**
A KPO task always involves two distinct executions: the context that runs the task instance (a Celery worker process, or a `KubernetesExecutor` pod) and the separate Pod that KPO itself creates for the actual work via the Kubernetes API. Switching executors only changes how the first half is scheduled — it neither adds nor removes the Pod KPO launches.
</details>

3. When multiple pod configuration sources are set for the same `KubernetesPodOperator` task, which one wins?
   - A) `pod_template_dict` always wins over everything else
   - B) The default empty `V1Pod` always wins, since it's the safest fallback
   - C) KPO's own constructor arguments (like `image` or `resources`) take precedence over `full_pod_spec`, which takes precedence over `pod_template_file`, which takes precedence over `pod_template_dict`
   - D) Whichever source was declared last in the DAG file wins

<details>

<summary>Show Answer</summary>

**Answer: C) KPO's own constructor arguments (like `image` or `resources`) take precedence over `full_pod_spec`, which takes precedence over `pod_template_file`, which takes precedence over `pod_template_dict`**

**Explanation:**
The precedence order, from highest to lowest, is: KPO constructor arguments, then `full_pod_spec`, then `pod_template_file`, then `pod_template_dict`, then the default empty `V1Pod`. This lets a shared `pod_template_file` supply defaults for an entire deployment while individual tasks override only the specific fields they need through constructor arguments.
</details>

4. A base `pod_template_file` sets `image: python:3.12-slim`, and a specific `KubernetesPodOperator` task also passes `image="my-registry/orders-extractor:1.4.0"` as a constructor argument. Which image does the launched pod actually run?
   - A) `python:3.12-slim`, since the template file is considered the source of truth
   - B) `my-registry/orders-extractor:1.4.0`, since constructor arguments outrank `pod_template_file`
   - C) Both images are merged into a single multi-container pod
   - D) Neither — KPO raises a configuration conflict error

<details>

<summary>Show Answer</summary>

**Answer: B) `my-registry/orders-extractor:1.4.0`, since constructor arguments outrank `pod_template_file`**

**Explanation:**
KPO constructor arguments sit at the top of the precedence order and always override the same field set through `pod_template_file`. This is exactly the intended usage pattern: the template supplies shared defaults, and constructor arguments override the handful of fields that are genuinely task-specific.
</details>

5. What is the purpose of setting a task-specific `service_account_name` on a `KubernetesPodOperator` task, distinct from whatever service account the base pod template uses?
   - A) It changes which executor runs the task
   - B) It lets that one task assume its own IAM role via IRSA, scoped to only the AWS permissions that task needs
   - C) It disables IRSA for that task entirely
   - D) It is required for `pod_template_file` to work at all

<details>

<summary>Show Answer</summary>

**Answer: B) It lets that one task assume its own IAM role via IRSA, scoped to only the AWS permissions that task needs**

**Explanation:**
The Kubernetes ServiceAccount referenced by `service_account_name` can be annotated with an IAM role ARN through IRSA. Any pod running under that ServiceAccount — including a KPO-launched task pod — assumes that role's permissions for its lifetime. Overriding it per task gives that task a permission boundary distinct from both the base pod template's default service account and whatever role the Airflow control-plane components use.
</details>

6. How does `affinity`/`tolerations` on a `KubernetesPodOperator` task relate to pinning ordinary Kubernetes workloads to dedicated node pools?
   - A) It's a completely different, Airflow-specific mechanism unrelated to standard Kubernetes scheduling
   - B) It's the same `affinity`/`tolerations` mechanism used for any workload, applied to KPO's launched task pods
   - C) It only works if the executor is `KubernetesExecutor`
   - D) It replaces the need for taints on the node pool entirely

<details>

<summary>Show Answer</summary>

**Answer: B) It's the same `affinity`/`tolerations` mechanism used for any workload, applied to KPO's launched task pods**

**Explanation:**
KPO's launched pods are ordinary Kubernetes Pods, so the standard `affinity`/`tolerations` scheduling mechanism applies to them exactly as it would to any other workload. Setting these — directly on KPO or baked into the pod template — pins task pods onto a tainted, dedicated node pool (such as a Karpenter-managed NodePool) the same way you would for any workload.
</details>

7. What is the key property `GitDagBundle` provides that a `git-sync` sidecar alone never did?
   - A) `git-sync` requires a paid Airflow license, while `GitDagBundle` is free
   - B) `GitDagBundle` runs faster than `git-sync`
   - C) Every DAG run records the exact Git commit SHA it executed against, so reruns are reproducible even after the repository has moved on
   - D) `GitDagBundle` eliminates the need for a dag-processor

<details>

<summary>Show Answer</summary>

**Answer: C) Every DAG run records the exact Git commit SHA it executed against, so reruns are reproducible even after the repository has moved on**

**Explanation:**
`GitDagBundle` is natively versioning-aware: each DAG run records the commit SHA it ran against, so re-running a historical run replays it against the code as it existed at that commit rather than the repository's current HEAD. A `git-sync` sidecar keeps a working copy current but never recorded which commit a given run actually saw.
</details>

8. Which DAG bundle type has no per-run versioning, meaning whatever is currently on disk (or at the configured object key) is simply what runs?
   - A) `GitDagBundle` only
   - B) `LocalDagBundle`, `S3DagBundle`, and `GCSDagBundle`
   - C) None of the bundle types support this — all of them version every run
   - D) Only `S3DagBundle`

<details>

<summary>Show Answer</summary>

**Answer: B) `LocalDagBundle`, `S3DagBundle`, and `GCSDagBundle`**

**Explanation:**
`LocalDagBundle` reads from a local filesystem path and `S3DagBundle`/`GCSDagBundle` read from object storage; none of the three track a version per run — whatever is present when the dag-processor parses it is what executes. `GitDagBundle` is the one bundle type that natively records a commit SHA per run.
</details>

9. Does Airflow 3 remove support for `git-sync` sidecars entirely?
   - A) Yes, `git-sync` sidecars no longer work with the official Helm chart in Airflow 3
   - B) No, `git-sync` still works with the official Helm chart; `GitDagBundle` is positioned as its modern replacement for cases where commit-level reproducibility matters
   - C) Yes, but only for `KubernetesExecutor` deployments
   - D) No, but `git-sync` now requires `GitDagBundle` to be configured first

<details>

<summary>Show Answer</summary>

**Answer: B) No, `git-sync` still works with the official Helm chart; `GitDagBundle` is positioned as its modern replacement for cases where commit-level reproducibility matters**

**Explanation:**
Airflow 3 does not remove `git-sync` support — it continues to work with the official Helm chart. `GitDagBundle` is presented as the modern replacement rather than a forced migration, because it adds the commit-SHA versioning guarantee that `git-sync` alone never provided.
</details>

10. In the KPO-launched Spark example in this chapter, why does the container image apply a `SparkApplication` manifest and poll it, rather than the Airflow DAG code calling the Kubernetes API directly?
    - A) Airflow DAG code is not permitted to import the Kubernetes Python client
    - B) It follows the Kubernetes-native Spark pattern (via the Spark Operator) instead of reimplementing job submission logic inside DAG code
    - C) `KubernetesPodOperator` cannot run shell commands
    - D) `SparkApplication` manifests can only be applied from inside a Pod, never from a DAG file

<details>

<summary>Show Answer</summary>

**Answer: B) It follows the Kubernetes-native Spark pattern (via the Spark Operator) instead of reimplementing job submission logic inside DAG code**

**Explanation:**
The KPO task's container image applies a `SparkApplication` manifest and waits for it to complete, letting the Spark Operator (covered in the Spark section) own submission, retries, and status reporting — the same pattern used for any Kubernetes-native Spark job. This keeps DAG code focused on orchestration rather than duplicating Spark submission logic.
</details>

## Short Answer Questions

11. What is the fully qualified Python import path for `KubernetesPodOperator`?

<details>

<summary>Show Answer</summary>

**Answer: `airflow.providers.cncf.kubernetes.operators.pod`**

**Explanation:**
`KubernetesPodOperator` lives in the `cncf.kubernetes` provider package, under `airflow.providers.cncf.kubernetes.operators.pod`.
</details>

12. List the five sources of pod configuration `KubernetesPodOperator` merges, in order from highest to lowest priority.

<details>

<summary>Show Answer</summary>

**Answer: KPO constructor arguments, `full_pod_spec`, `pod_template_file`, `pod_template_dict`, default empty `V1Pod`**

**Explanation:**
KPO's own constructor arguments always win. Below that, `full_pod_spec` (a complete `V1Pod` object) outranks `pod_template_file` (a YAML file path), which in turn outranks `pod_template_dict` (the same content as an in-memory dict). Whatever none of these sets falls back to Airflow's default, empty `V1Pod`.
</details>

13. Why does giving a KPO task its own `service_account_name` matter even though the base pod template already sets one?

<details>

<summary>Show Answer</summary>

**Answer: It scopes that specific task to its own IAM role via IRSA, distinct from the template's default and from the Airflow control-plane components' role.**

**Explanation:**
A task-specific `service_account_name` follows the same precedence order as other KPO fields, so it overrides the base template's service account. This lets a task that only needs narrow access (e.g., one S3 prefix) run with exactly that permission scope, rather than inheriting a broader default or whatever role the scheduler/api-server/dag-processor use.
</details>

## Hands-on Questions

14. Write a `KubernetesPodOperator` task named `extract_orders` that uses a shared pod template at `/opt/airflow/dags/templates/base-pod-template.yaml`, overrides the image to `my-registry/orders-extractor:1.4.0`, runs `python extract.py --date {{ ds }}`, uses the service account `orders-extractor-sa`, and deletes its pod on completion.

<details>

<summary>Show Answer</summary>

**Answer:**
```python
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

extract_orders = KubernetesPodOperator(
    task_id="extract_orders",
    namespace="airflow",
    name="extract-orders",
    image="my-registry/orders-extractor:1.4.0",
    cmds=["python", "extract.py"],
    arguments=["--date", "{{ ds }}"],
    pod_template_file="/opt/airflow/dags/templates/base-pod-template.yaml",
    service_account_name="orders-extractor-sa",
    is_delete_operator_pod=True,
)
```

**Explanation:**
`pod_template_file` supplies the shared defaults (resources, tolerations, base service account), while `image`, `cmds`, `arguments`, and `service_account_name` override exactly the fields that are specific to this task, per KPO's constructor-arguments-win precedence rule. `is_delete_operator_pod=True` cleans up the launched pod once the task finishes.
</details>

15. Explain why pinning KPO task pods to a dedicated, tainted node pool via `affinity`/`tolerations` is the same mechanism you'd use for any other Kubernetes workload, rather than an Airflow-specific feature.

<details>

<summary>Show Answer</summary>

**Answer:** Because the Pod that `KubernetesPodOperator` launches is an ordinary Kubernetes Pod — Airflow doesn't wrap it in anything special — the standard `affinity`/`tolerations` scheduling fields work on it exactly as they would on any Deployment, Job, or other workload's Pod, whether set directly as KPO constructor arguments or baked into the shared `pod_template_file`.

**Explanation:**
This is a direct consequence of KPO creating a plain `V1Pod` through the Kubernetes API — there's no Airflow-specific scheduling layer involved, so any node-pinning technique that works for Kubernetes workloads in general (matching a NodeGroup/NodePool taint with a toleration, or a `nodeAffinity` rule) applies unchanged to KPO's launched pods.
</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/03-dag-patterns.md)
