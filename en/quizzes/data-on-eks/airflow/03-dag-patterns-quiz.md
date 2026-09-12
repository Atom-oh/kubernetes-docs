# DAG Patterns and KubernetesPodOperator Quiz

Based on Airflow 3.3.1 and Kubernetes provider 10.21.0. Check execution structure, merge behavior, permissions, bundle versioning and validation limits.

## Concepts

1. Who creates a new workload pod for a synchronous KPO task using CeleryExecutor?

<details>
<summary>Show Answer</summary>

**Answer:** KPO calls the Kubernetes API from the existing Celery worker.

**Explanation:** The workload runs in a separate pod. Multiple tasks can share the worker pod, and the workload image does not inherently require Airflow.

</details>

2. How can changing from CeleryExecutor to KubernetesExecutor change physical pod creation for a new KPO execution?

<details>
<summary>Show Answer</summary>

**Answer:** It can create both a task-runner pod and a workload pod instead of using an existing Celery worker.

**Explanation:** Two logical execution roles do not always mean two newly created pods. Retries, reattachment and deferral also affect the live pod count.

</details>

3. Does provider 10.21.0 sequentially merge both pod_template_file and pod_template_dict when both are supplied?

<details>
<summary>Show Answer</summary>

**Answer:** No. The file is selected and the dictionary from that call is not additionally merged.

**Explanation:** The selected template is reconciled with full_pod_spec and the KPO-built pod. This is not an unconditional five-source merge.

</details>

4. Are template requests preserved when container_resources supplies only limits?

<details>
<summary>Show Answer</summary>

**Answer:** Do not assume so: this merge replaces the resources object and drops the previous requests.

**Explanation:** Specify all required requests and limits and inspect the final pod. Other fields have different rules, including list concatenation, per-key label merging and falsy-value inheritance.

</details>

5. Does setting KPO service_account_name alone grant the pod S3 access?

<details>
<summary>Show Answer</summary>

**Answer:** No. It needs the corresponding IAM trust or association and a compatible credential provider.

**Explanation:** Verify IRSA or Pod Identity setup, SDK credential selection and actual allowed/denied access. The KPO caller's Kubernetes RBAC differs from the child's AWS permissions.

</details>

6. Does a toleration alone force a workload onto a dedicated tainted NodePool?

<details>
<summary>Show Answer</summary>

**Answer:** No. It permits the taint; selectors or required affinity may also be needed.

**Explanation:** KPO pods use standard Kubernetes scheduling. A dedicated pool does not eliminate node failure, Spot reclamation or disk pressure.

</details>

7. Must every rerun of a version-enabled GitDagBundle use its earlier commit?

<details>
<summary>Show Answer</summary>

**Answer:** No. Request, DAG and global rerun settings, followed by per-call defaults, can select the latest version.

**Explanation:** In 3.3.1 the unset fallback is False for clear/rerun and True for backfill. Disabling bundle versioning removes run version tracking; a pinned commit alone does not pin data or images.

</details>

8. Do LocalDagBundle, S3DagBundle and GCSDagBundle guarantee that a later worker reads the parser's exact snapshot?

<details>
<summary>Show Answer</summary>

**Answer:** No. These bundles currently do not provide per-run bundle versioning.

**Explanation:** Files or objects can change after parsing. Manage deployment consistency and distribution of related files separately.

</details>

9. Was the git-sync sidecar removed in Airflow 3?

<details>
<summary>Show Answer</summary>

**Answer:** No. The official Helm chart still supports it.

**Explanation:** GitDagBundle versioning is a separate capability. Using git-sync neither forces migration nor inherently preserves each run's commit.

</details>

10. What can go wrong when a fixed-name SparkApplication is applied and only COMPLETED is awaited?

<details>
<summary>Show Answer</summary>

**Answer:** A previous COMPLETED state can be mistaken for a new success; the wrong namespace may be watched; FAILED handling can be delayed.

**Explanation:** Use explicit execution identity, namespace, terminal-state handling and cleanup contracts. Native Spark operators also require validation of the generated CR against the target CRD.

</details>

## Short Answers

11. Write the KubernetesPodOperator import and name its container-resource argument.

<details>
<summary>Show Answer</summary>

**Answer:** `from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator`; use `container_resources` for container resources.

**Explanation:** Use Kubernetes V1ResourceRequirements. Do not treat a generic resources argument as the same setting.

</details>

12. Does is_delete_operator_pod=False alone guarantee pod retention in 10.21.0?

<details>
<summary>Show Answer</summary>

**Answer:** No. The argument remains in the constructor but is unused; configure on_finish_action and on_kill_action separately.

**Explanation:** Normal finish and killing are distinct paths. Reattachment also does not guarantee exactly-once external writes.

</details>

13. Does a namespace-scoped KPO Role restrict the caller to pods belonging to its own task?

<details>
<summary>Show Answer</summary>

**Answer:** No. The example Role can affect permitted pod resources throughout that namespace.

**Explanation:** Distinguish caller and workload service accounts. Use admission controls and trust boundaries for untrusted DAG authors who could select other identities or dangerous specs.

</details>

## Application

14. Show the kpo_smoke arguments that pass the run ID and delete the pod after finish or kill.

<details>
<summary>Show Answer</summary>

**Answer:** These are the relevant arguments inside the chapter's complete DAG.

```python
run_smoke = KubernetesPodOperator(
    task_id="run_smoke",
cmds=["python", "-B", "-c"],
arguments=[
    "import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])",
    "{{ run_id }}",
],
on_finish_action="delete_pod",
on_kill_action="delete_pod",
)
```

**Explanation:** Pass run_id as a separate argument rather than interpolating a shell command. Do not assume asset-triggered runs have ds. Use the chapter for the full DAG, RBAC and template setup.

</details>

15. After overriding template automountServiceAccountToken=True with False and checking dry_run, what else must be checked?

<details>
<summary>Show Answer</summary>

**Answer:** Inspect the final merged value and the admitted pod, then verify rendering, task-instance labels and actual execution separately.

**Explanation:** The reviewed merge function can inherit base True instead of falsy False. dry_run does not prove admission or task success, and the chapter's local checks do not replace cluster execution.

</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/03-dag-patterns.md)
