# Kubeflow Notebooks Quiz

This quiz tests your understanding of Kubeflow Notebooks' architecture, its Profile-based multi-tenancy model, storage and idle culling behavior, GPU scheduling on EKS, and custom notebook images.

## Multiple Choice Questions

1. What Kubernetes-native mechanism does Kubeflow Notebooks use to turn a user's spawner selections (image, CPU/memory/GPU, storage) into a running notebook server?
   - A) A shell script the dashboard executes directly against `kubectl`
   - B) A `Notebook` custom resource that a controller reconciles into a StatefulSet/pod
   - C) A cron job that polls the dashboard's database every minute
   - D) A Helm chart the user installs manually

<details>

<summary>Show Answer</summary>

**Answer: B) A `Notebook` custom resource that a controller reconciles into a StatefulSet/pod**

**Explanation:**
The Central Dashboard's spawner creates a `Notebook` custom resource describing the desired environment. A controller watches for that resource and reconciles it into ordinary Kubernetes objects (a StatefulSet/pod with the requested image, resources, and PVC), rather than the dashboard creating pods directly.
</details>

2. As of the Kubeflow Community Distribution 26.03, what is the accurate status of Kubeflow Notebooks v2?
   - A) It is already GA and has fully replaced v1
   - B) It does not exist yet, even as an alpha
   - C) It is approaching release, with alpha manifests available for testing around new `Workspace`/`WorkspaceKind` CRDs, but not yet GA
   - D) It was cancelled in favor of keeping v1 indefinitely

<details>

<summary>Show Answer</summary>

**Answer: C) It is approaching release, with alpha manifests available for testing around new `Workspace`/`WorkspaceKind` CRDs, but not yet GA**

**Explanation:**
At the time of the 26.03 distribution, Notebooks v2 — built around new `Workspace` and `WorkspaceKind` custom resources — has alpha manifests available for testing but has not reached general availability. v1's `Notebook` CRD remains the architecture in production use, and is expected to move to maintenance-only status once v2 is GA-ready.
</details>

3. What is a Profile in the context of Kubeflow Notebooks' multi-tenancy model?
   - A) A user's saved notebook UI theme and keyboard shortcuts
   - B) A namespace-per-user construct that provisions RBAC bindings and Istio authorization policies scoping that user's access
   - C) A record of which images a user has previously spawned
   - D) A billing account tied to a user's AWS IAM identity

<details>

<summary>Show Answer</summary>

**Answer: B) A namespace-per-user construct that provisions RBAC bindings and Istio authorization policies scoping that user's access**

**Explanation:**
A Profile provisions a dedicated namespace for a user (or team), RBAC bindings scoping their permissions to that namespace, and an Istio `AuthorizationPolicy` restricting which identities can reach services inside it. Notebooks are always created inside a Profile namespace, which is what isolates one user's notebook from another's by default.
</details>

4. Why does a notebook's PersistentVolumeClaim matter for its resilience to pod restarts?
   - A) The PVC is deleted and recreated automatically every time the pod restarts
   - B) The claim, not the pod, is the durable object — files and installed packages mounted from it survive pod restarts, node replacement, or a stop/start cycle
   - C) PVCs only matter for RStudio images, not JupyterLab
   - D) The PVC is only used to store logs, not user files

<details>

<summary>Show Answer</summary>

**Answer: B) The claim, not the pod, is the durable object — files and installed packages mounted from it survive pod restarts, node replacement, or a stop/start cycle**

**Explanation:**
The spawner lets a user attach a PVC typically mounted at the notebook's home directory. Because the PVC persists independently of the pod's lifecycle, a user's work is preserved across pod restarts, node replacement, or intentional stop/start cycles — and culling, which stops rather than deletes the notebook, leaves the PVC untouched.
</details>

5. Why is idle culling particularly important for GPU-backed notebooks specifically?
   - A) GPUs cannot be requested by notebook pods at all, so culling is irrelevant to them
   - B) A running notebook pod holds its GPU allocation for as long as it exists regardless of active use, so an idle GPU notebook can occupy expensive capacity for hours
   - C) Culling deletes the notebook's PVC to free GPU memory
   - D) GPU nodes require a full cluster restart to reclaim capacity, which culling triggers

<details>

<summary>Show Answer</summary>

**Answer: B) A running notebook pod holds its GPU allocation for as long as it exists regardless of active use, so an idle GPU notebook can occupy expensive capacity for hours**

**Explanation:**
A notebook pod holds its requested CPU, memory, and GPU allocation continuously while running, whether or not anyone is actively using it. Culling stops (without deleting) idle notebooks after a configured period, which is especially valuable for GPU notebooks since an idle GPU-backed server can otherwise tie up expensive accelerator capacity indefinitely.
</details>

6. How does a notebook pod on EKS request GPU access, and how does this interact with cluster autoscaling?
   - A) It uses a dedicated Notebooks-only GPU scheduler separate from the rest of the cluster
   - B) It sets `resources.limits."nvidia.com/gpu"` like any other pod, competing for the same GPU-capable node pools (e.g. Karpenter-managed NodePools) used by training jobs and inference workloads
   - C) GPU access for notebooks must be manually assigned by an administrator via SSH to the node
   - D) Notebook pods cannot request GPUs; only KServe endpoints can

<details>

<summary>Show Answer</summary>

**Answer: B) It sets `resources.limits."nvidia.com/gpu"` like any other pod, competing for the same GPU-capable node pools (e.g. Karpenter-managed NodePools) used by training jobs and inference workloads**

**Explanation:**
The spawner's GPU selection translates into a standard `nvidia.com/gpu` resource request on the pod spec, advertised as allocatable by the NVIDIA device plugin. This is not a separate GPU subsystem — the notebook pod competes for the same GPU node pools as any other GPU workload, and on EKS that capacity is commonly provisioned dynamically via Karpenter.
</details>

7. What is the typical reason teams build custom notebook images rather than using the stock spawner images as-is?
   - A) Custom images are required by Kubeflow and stock images cannot be used at all
   - B) To give every data scientist an identical, reproducible environment with team-specific dependencies pre-installed, instead of manually installing packages inside a running container
   - C) Stock images do not support PVC mounts
   - D) Custom images remove the need for a Profile namespace

<details>

<summary>Show Answer</summary>

**Answer: B) To give every data scientist an identical, reproducible environment with team-specific dependencies pre-installed, instead of manually installing packages inside a running container**

**Explanation:**
Most production teams build custom images on top of an upstream Kubeflow/Jupyter base image, layering in fixed Python/R packages, internal libraries, and matched GPU-framework versions, then push the image to a registry (e.g. Amazon ECR on EKS) and reference it directly from the spawner. This ensures two users on the same image tag get identical package sets rather than drifting from manual installs.
</details>

## Short Answer Questions

8. In one or two sentences, explain how a notebook pod's GPU request interacts with Karpenter on EKS, and why this matters for cost.

<details>

<summary>Show Answer</summary>

**Answer:**
When a notebook Pod's spec requests `nvidia.com/gpu` resources and no existing node has capacity, Karpenter provisions a new GPU-backed EC2 instance to satisfy the pending Pod; because GPU instances are expensive, idle-culling and right-sizing notebook GPU requests directly controls how much unused GPU capacity a team pays for between active sessions.
</details>

9. What does per-namespace Istio isolation give a Kubeflow Profile that plain Kubernetes namespace RBAC alone would not?

<details>

<summary>Show Answer</summary>

**Answer:**
RBAC controls who can create/read/modify Kubernetes API objects in a namespace, but says nothing about network traffic; Istio's per-namespace `AuthorizationPolicy` additionally restricts which services can actually send requests to a user's notebook Pod at the network layer, giving isolation between users' notebook servers even if RBAC alone would have allowed some cross-namespace object access.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/03-notebooks.md)
