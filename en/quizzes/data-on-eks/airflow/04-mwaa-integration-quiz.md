# MWAA Integration Quiz

This quiz tests your understanding of what Amazon MWAA does and doesn't give you access to, how an MWAA DAG can still drive workloads on an EKS cluster via `KubernetesPodOperator`, what an IAM identity mapping accomplishes, and when to choose MWAA versus self-managed Airflow on EKS.

## Multiple Choice Questions

1. What does Amazon MWAA specifically NOT give you direct access to?
   - A) The DAGs themselves
   - B) The Airflow control plane (scheduler, api-server, dag-processor, workers) — it runs on AWS-managed infrastructure outside your EKS cluster
   - C) The Airflow REST API
   - D) CloudWatch logs for the environment

<details>

<summary>Show Answer</summary>

**Answer: B) The Airflow control plane (scheduler, api-server, dag-processor, workers) — it runs on AWS-managed infrastructure outside your EKS cluster**

**Explanation:**
MWAA provisions and runs the scheduler, api-server, dag-processor, and worker fleet entirely on AWS-managed infrastructure, not inside your VPC's EKS cluster. As a result, there's no `kubectl` view into the Airflow control plane itself — you can't inspect the MWAA scheduler's pods the way you would for a self-managed deployment. Health, scaling, and patching of these components are AWS's responsibility, surfaced via CloudWatch and the MWAA console/API instead of Kubernetes primitives.
</details>

2. How can an MWAA-hosted DAG still create and manage pods on a customer-owned EKS cluster?
   - A) It cannot — MWAA has no way to reach any Kubernetes cluster
   - B) By using `KubernetesPodOperator` with `in_cluster=True`, since MWAA runs inside every EKS cluster automatically
   - C) By using `KubernetesPodOperator` with `in_cluster=False` and a kubeconfig file pointed at the target EKS cluster
   - D) By installing a Kubernetes Operator directly inside the MWAA environment

<details>

<summary>Show Answer</summary>

**Answer: C) By using `KubernetesPodOperator` with `in_cluster=False` and a kubeconfig file pointed at the target EKS cluster**

**Explanation:**
Because MWAA's execution environment has no in-cluster Kubernetes API access, `KubernetesPodOperator` must authenticate the same way any external client would: with `in_cluster=False` and a `config_file` pointing at a kubeconfig generated via `aws eks update-kubeconfig` and uploaded to the environment's S3 bucket alongside the DAGs. `in_cluster=True` only works when the operator runs inside the same cluster it's targeting, which is never true for MWAA.
</details>

3. What does running `eksctl create iamidentitymapping` for the MWAA execution role accomplish?
   - A) It gives the MWAA execution role AdministratorAccess in the AWS account
   - B) It maps the MWAA execution role's IAM ARN to a Kubernetes username/group so the EKS cluster's RBAC recognizes and can authorize that identity
   - C) It uploads the kubeconfig file to the MWAA environment's S3 bucket
   - D) It upgrades the EKS cluster to a version compatible with MWAA

<details>

<summary>Show Answer</summary>

**Answer: B) It maps the MWAA execution role's IAM ARN to a Kubernetes username/group so the EKS cluster's RBAC recognizes and can authorize that identity**

**Explanation:**
`eksctl create iamidentitymapping` adds an entry to the cluster's `aws-auth` configuration, associating an IAM role ARN with a Kubernetes username and group. This only decides *who* the MWAA execution role is inside the cluster — a separate `ClusterRole`/`ClusterRoleBinding` bound to that group is what actually decides *what* it's permitted to do (e.g., create pods in a specific namespace, rather than something as broad as `system:masters`).
</details>

4. Which of the following is a real constraint MWAA imposes that self-managed Airflow on EKS (Parts 1–3) does not have?
   - A) MWAA cannot run any Python code at all
   - B) MWAA requires plugins as a zipped `plugins.zip` uploaded to S3, and Python dependencies via a `requirements.txt` resolved at build time with no root/system-package installs
   - C) MWAA cannot use the `KubernetesPodOperator`
   - D) MWAA does not support the Airflow REST API

<details>

<summary>Show Answer</summary>

**Answer: B) MWAA requires plugins as a zipped `plugins.zip` uploaded to S3, and Python dependencies via a `requirements.txt` resolved at build time with no root/system-package installs**

**Explanation:**
Self-managed Airflow lets you bake a plugins folder and arbitrary system packages directly into your image. MWAA instead requires plugins as a `plugins.zip` in S3 and Python dependencies as a `requirements.txt` in S3, subject to MWAA's build-time dependency resolution — there's no way to install root or system-level packages. `KubernetesPodOperator` and the REST API are both still available in MWAA.
</details>

5. How does MWAA deliver DAG files to the scheduler, in contrast to Part 3's `GitDagBundle`?
   - A) MWAA also supports `GitDagBundle` natively
   - B) MWAA syncs DAGs from an S3 bucket only; it has no git-sync or DAG-bundle support of any kind
   - C) MWAA requires DAGs to be baked into a custom container image
   - D) MWAA pulls DAGs directly from GitHub without any intermediate storage

<details>

<summary>Show Answer</summary>

**Answer: B) MWAA syncs DAGs from an S3 bucket only; it has no git-sync or DAG-bundle support of any kind**

**Explanation:**
Part 3 covered Airflow 3's native `GitDagBundle`, which lets a self-managed dag-processor pull DAGs directly from a git repository on its own polling interval — no S3 step involved. MWAA has no equivalent capability: every DAG change must first land as a file in the environment's S3 bucket, whether via manual `aws s3 sync` or a CI step, adding one more moving part between merging code and having it run.
</details>

6. Which release did MWAA add support for in April 2026, and how does that illustrate MWAA's version-currency trade-off?
   - A) Airflow 2.11, roughly three months after Airflow's 2.11 release
   - B) Airflow 3.2, roughly three months after Airflow's own 3.2 release, after previously bridging forward with Airflow 2.11 in January 2026
   - C) Airflow 4.0, ahead of the upstream release
   - D) MWAA does not track specific Airflow versions

<details>

<summary>Show Answer</summary>

**Answer: B) Airflow 3.2, roughly three months after Airflow's own 3.2 release, after previously bridging forward with Airflow 2.11 in January 2026**

**Explanation:**
MWAA added Airflow 3.2 support in April 2026, about three months behind upstream Airflow's own 3.2 release, and only after MWAA had first moved its 2.x line forward to Airflow 2.11 in January 2026 as a bridge release. This lag is the concrete version-currency trade-off you accept by choosing MWAA over self-managed Airflow, which can adopt an upstream release the moment it ships.
</details>

7. When is Amazon MWAA the better fit compared to self-managed Airflow on EKS?
   - A) When you need custom executors and per-task Docker image isolation
   - B) When you need multi-cloud portability
   - C) When your DAGs are simple, pure-Python/PyPI workloads and your team has low appetite for operating the Airflow control plane's infrastructure
   - D) When you want the newest upstream Airflow feature the same month it ships

<details>

<summary>Show Answer</summary>

**Answer: C) When your DAGs are simple, pure-Python/PyPI workloads and your team has low appetite for operating the Airflow control plane's infrastructure**

**Explanation:**
MWAA fits AWS-only shops running simple DAGs with no custom executors or system-level dependencies, where teams would rather not patch, scale, or manage the availability of the Airflow control plane at all. Custom executors, per-task image isolation, multi-cloud portability, and same-month adoption of new upstream features are all reasons favoring self-managed Airflow on EKS instead.
</details>

8. Which statement about the cost trade-off between self-managed Airflow on EKS and MWAA is most accurate?
   - A) Self-managed Airflow is always 30–60% cheaper than MWAA in every scenario
   - B) Well-tuned self-managed deployments have reported 30–60% lower spend than a poorly-tuned MWAA setup at scale, but this depends heavily on traffic pattern and tuning effort and isn't guaranteed
   - C) MWAA has no meaningful cost, since AWS absorbs all compute costs
   - D) Cost is identical between the two approaches regardless of scale

<details>

<summary>Show Answer</summary>

**Answer: B) Well-tuned self-managed deployments have reported 30–60% lower spend than a poorly-tuned MWAA setup at scale, but this depends heavily on traffic pattern and tuning effort and isn't guaranteed**

**Explanation:**
The 30–60% figure is a real, reported outcome for teams running large, well-tuned self-managed deployments compared against a poorly-tuned MWAA setup — but it's context-dependent, not a universal guarantee, and it must be weighed against the ongoing engineering effort self-hosting requires.
</details>

## Short Answer Questions

9. What must be added to an MWAA environment's `requirements.txt` for a DAG to be able to use `KubernetesPodOperator`?

<details>

<summary>Show Answer</summary>

**Answer: `apache-airflow[cncf.kubernetes]`**

**Explanation:**
The `cncf.kubernetes` provider package supplies `KubernetesPodOperator` and related Kubernetes integration classes. Without adding it to `requirements.txt`, the import in the DAG file would fail during parsing.
</details>

10. What `KubernetesPodOperator` parameter must be set to `False` when the operator runs from MWAA and targets a separate EKS cluster, since MWAA never runs inside that cluster?

<details>

<summary>Show Answer</summary>

**Answer: `in_cluster`**

**Explanation:**
`in_cluster=True` tells the operator to use the Kubernetes API access available from inside the same cluster it's running in — which is never the case for MWAA, since MWAA's control plane runs on separate AWS-managed infrastructure. Setting `in_cluster=False` and providing `config_file` pointing at an uploaded kubeconfig is what lets the operator authenticate to an external EKS cluster instead.
</details>

## Hands-on Questions

11. Write the `eksctl` command that binds an MWAA execution role (`arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment`) into the RBAC of an EKS cluster named `data-eks-cluster` in `us-east-1`, mapping it to the Kubernetes group `mwaa-pod-launcher`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
eksctl create iamidentitymapping \
  --cluster data-eks-cluster \
  --region us-east-1 \
  --arn arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment \
  --username mwaa-executor \
  --group mwaa-pod-launcher
```

**Explanation:**
This adds an entry to the cluster's `aws-auth` configuration so the EKS cluster's RBAC recognizes the MWAA execution role's IAM ARN as the Kubernetes user `mwaa-executor` belonging to group `mwaa-pod-launcher`. A separate `ClusterRole`/`ClusterRoleBinding` bound to `mwaa-pod-launcher` — scoped narrowly to what the DAGs actually need, not something as broad as `system:masters` — determines what that identity can actually do.
</details>

12. Write a `KubernetesPodOperator` task definition for an MWAA DAG that runs the image `123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest` in the `data-processing` namespace of an external EKS cluster, using a kubeconfig staged at `/usr/local/airflow/dags/kube_config.yaml`.

<details>

<summary>Show Answer</summary>

**Answer:**
```python
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

process_data = KubernetesPodOperator(
    task_id="process_data_on_eks",
    name="process-data",
    namespace="data-processing",
    image="123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest",
    cmds=["python", "process.py"],
    in_cluster=False,
    config_file="/usr/local/airflow/dags/kube_config.yaml",
    is_delete_operator_pod=True,
)
```

**Explanation:**
`in_cluster=False` tells the operator not to assume it's running inside the target cluster. `config_file` points at the kubeconfig MWAA synced down to the DAGs folder alongside the DAG code itself, generated ahead of time via `aws eks update-kubeconfig` and uploaded to the environment's S3 bucket. `is_delete_operator_pod=True` cleans up the pod after the task finishes, which is standard practice to avoid leaving completed task pods around on the target cluster.
</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/04-mwaa-integration.md)
