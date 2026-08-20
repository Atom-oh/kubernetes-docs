# The KubeRay Operator Quiz

This quiz tests your understanding of KubeRay: what it is, its three core CRDs, the two-tier autoscaling model it shares with Karpenter, and how it handles GPU scheduling.

## Multiple Choice Questions

1. What is KubeRay?
   - A) A managed AWS service for running Ray clusters
   - B) A Kubernetes operator that manages Ray clusters as native Kubernetes custom resources, translating the head/worker-node shape into Pods, Services, and related objects
   - C) A Ray-specific replacement for kubectl
   - D) A monitoring dashboard for Ray clusters with no cluster-management capability

<details>

<summary>Show Answer</summary>

**Answer: B) A Kubernetes operator that manages Ray clusters as native Kubernetes custom resources, translating the head/worker-node shape into Pods, Services, and related objects**

**Explanation:**
KubeRay is what makes "Ray on Kubernetes" declarative rather than a matter of hand-writing pod specs: it reconciles a declared RayCluster/RayJob/RayService spec into the actual Pods, Services, and other objects Kubernetes needs.
</details>

2. Which CRD represents a raw Ray cluster made up of one head Pod and one or more worker groups?
   - A) RayJob
   - B) RayService
   - C) RayCluster
   - D) RayNodePool

<details>

<summary>Show Answer</summary>

**Answer: C) RayCluster**

**Explanation:**
RayCluster is the foundational CRD: one head Pod plus one or more worker groups, each a set of homogeneous worker Pods (for example, a CPU worker group and a separate GPU worker group), reconciled by the operator to match the desired spec.
</details>

3. What makes RayJob a good fit for one-off or scheduled batch workloads?
   - A) It can only run on a pre-existing, permanently running RayCluster
   - B) It can create the RayCluster, run the submitted job, and tear the cluster down when the job finishes, so no cluster sits idle between runs
   - C) It disables the Ray autoscaler entirely
   - D) It requires a separate RayService to be running first

<details>

<summary>Show Answer</summary>

**Answer: B) It can create the RayCluster, run the submitted job, and tear the cluster down when the job finishes, so no cluster sits idle between runs**

**Explanation:**
RayJob submits a batch job and can optionally manage the underlying cluster's full lifecycle — creation, job execution, and teardown — which avoids paying for an idle cluster between runs.
</details>

4. What distinguishes RayService from RayCluster?
   - A) RayService cannot run any Ray Serve application
   - B) RayService manages a RayCluster plus a Ray Serve application on top of it, and supports rolling upgrades without downtime
   - C) RayService only runs on a single Pod with no worker groups
   - D) RayService is deprecated in favor of RayCluster

<details>

<summary>Show Answer</summary>

**Answer: B) RayService manages a RayCluster plus a Ray Serve application on top of it, and supports rolling upgrades without downtime**

**Explanation:**
RayService targets production model serving: it manages both the RayCluster and the Ray Serve application deployed on it, and supports rolling upgrades aimed at zero downtime — check the current KubeRay release notes for that upgrade path's maturity before relying on it in production.
</details>

5. In the two-tier autoscaling pattern described for Ray on EKS, what does the Ray autoscaler decide, and what does Karpenter decide?
   - A) The Ray autoscaler decides EC2 node types; Karpenter decides Ray task placement
   - B) The Ray autoscaler decides how many Ray worker Pods are needed (by adjusting RayCluster worker group replica counts); Karpenter decides how many EC2 nodes to provision for the resulting pending Pods
   - C) Both control loops decide the same thing redundantly, for fault tolerance
   - D) Karpenter decides Pod count; the Ray autoscaler decides node count

<details>

<summary>Show Answer</summary>

**Answer: B) The Ray autoscaler decides how many Ray worker Pods are needed (by adjusting RayCluster worker group replica counts); Karpenter decides how many EC2 nodes to provision for the resulting pending Pods**

**Explanation:**
One control loop (the Ray autoscaler, coordinated through KubeRay) owns Pod count; a separate one (Karpenter, or the Kubernetes Cluster Autoscaler) owns node count. They communicate only indirectly, through ordinary pending-Pod scheduling state — the same two-tier pattern this documentation site describes for Flink and Katib.
</details>

6. What does the Ray autoscaler's `idleTimeoutSeconds` setting control, and what is its default value?
   - A) How long the KubeRay operator waits before installing CRDs; default 60 seconds
   - B) How long a worker Pod must sit idle, with no tasks, actors, or referenced objects, before the autoscaler scales it down; default 60 seconds
   - C) How long Karpenter waits before provisioning a new EC2 node; default 60 seconds
   - D) The TTL for a completed RayJob's head Pod; default 60 seconds

<details>

<summary>Show Answer</summary>

**Answer: B) How long a worker Pod must sit idle, with no tasks, actors, or referenced objects, before the autoscaler scales it down; default 60 seconds**

**Explanation:**
`idleTimeoutSeconds` defaults to 60 seconds and is the wait period the Ray autoscaler applies before scaling down an idle worker Pod.
</details>

7. How does KubeRay determine how many GPUs a worker group's Ray processes see?
   - A) It reads a separate `numGPUs` field in the RayCluster spec's top-level metadata
   - B) It reads the GPU resource limit (e.g. `nvidia.com/gpu`) set on the worker group's Pod spec, advertises it to the Ray scheduler and autoscaler, and automatically sets the Ray process's `--num-gpus` flag to match
   - C) GPU count must be set manually with a separate `kubectl ray gpu-config` command after the Pods start
   - D) KubeRay always assumes exactly one GPU per worker Pod regardless of the Pod spec

<details>

<summary>Show Answer</summary>

**Answer: B) It reads the GPU resource limit (e.g. `nvidia.com/gpu`) set on the worker group's Pod spec, advertises it to the Ray scheduler and autoscaler, and automatically sets the Ray process's `--num-gpus` flag to match**

**Explanation:**
A GPU worker group's Pod spec is the single source of truth: KubeRay advertises the container's GPU resource limits to both the Ray scheduler and autoscaler, and configures `--num-gpus` on the Ray process to match, so there is no separate place to keep a GPU count in sync by hand.
</details>

8. What is the standard way to install the KubeRay operator, according to this document?
   - A) Manually applying raw manifests downloaded from a random GitHub gist
   - B) The official Helm chart, added via `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`
   - C) A one-line `kubectl create clusterrole kuberay` command
   - D) There is no supported installation method; KubeRay must be built from source

<details>

<summary>Show Answer</summary>

**Answer: B) The official Helm chart, added via `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`**

**Explanation:**
The `ray-project/kuberay-helm` repository hosts the official Helm chart for installing the KubeRay operator, its controller, and the RayCluster/RayJob/RayService CRDs.
</details>

## Short Answer Questions

9. Name the three core CRDs KubeRay exposes and briefly state what each one is used for.

<details>

<summary>Show Answer</summary>

**Answer:**
- RayCluster: a raw Ray cluster of one head Pod and one or more worker groups, reconciled to match a declared spec.
- RayJob: submits a batch job to a Ray cluster, optionally managing that cluster's full create-run-teardown lifecycle for one-off or scheduled workloads.
- RayService: manages a RayCluster plus a Ray Serve application on top of it for production model serving, supporting zero-downtime rolling upgrades.

**Explanation:**
Each CRD targets a different usage pattern — raw cluster management, batch job execution, and production serving — built on the same underlying reconciliation model.
</details>

10. Explain why Ray-on-EKS autoscaling needs two separate control loops instead of one, and what each loop is responsible for.

<details>

<summary>Show Answer</summary>

**Answer:**
The Ray autoscaler understands Ray-level state (pending tasks and actors) but knows nothing about EC2 capacity; Karpenter understands Kubernetes-level pending Pods and EC2 provisioning but knows nothing about Ray tasks or actors. The Ray autoscaler decides how many Ray worker Pods are needed and requests them via the RayCluster worker group replica count; Karpenter separately reacts to the resulting pending Pods and provisions matching EC2 nodes to run them.

**Explanation:**
Neither loop can substitute for the other because each operates on information the other doesn't have. This two-tier division — one loop for Pod count, one for node count, communicating only through ordinary Kubernetes scheduling state — is the same pattern this documentation site uses to describe autoscaling for Flink and Katib.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/02-kuberay-operator.md) | [Next Quiz: Ray Train and Tune](./03-ray-train-tune-quiz.md)
