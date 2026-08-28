# Part 3: Kubeflow Notebooks

> **Supported Versions**: Kubeflow Community Distribution 26.03, Kubernetes 1.34+
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later, pointed at a cluster with Kubeflow installed (see Part 1)
* Access to a user Profile (namespace) in the Kubeflow Central Dashboard, to spawn notebook servers
* A GPU-enabled `NodePool`/`EC2NodeClass` pair configured via [Karpenter](../../autoscaling/02-karpenter.md), if you plan to spawn GPU-backed notebooks
* Push access to a container registry (e.g. Amazon ECR), if you plan to build and reference a custom notebook image

## What Is Kubeflow Notebooks?

Kubeflow Notebooks lets a data scientist spin up a fully configured interactive development environment — JupyterLab, RStudio, or code-server (VS Code in the browser) — as a pod running inside the cluster, without ever writing a Deployment manifest or a Dockerfile themselves. A controller watches a custom resource that describes the desired notebook (image, CPU/memory/GPU requests, and storage), reconciles it into ordinary Kubernetes objects, and Istio's per-namespace routing exposes the resulting server through the same Central Dashboard the rest of Kubeflow uses.

The point of running notebooks this way rather than as a shared JupyterHub deployment or a one-off `kubectl run` is that each user's environment participates fully in the cluster's normal operational model. It is scheduled by the same scheduler, so it competes for and benefits from GPU node pools like any other workload. It is subject to the same namespace-scoped RBAC and network policy. And it can be paused, resized, or torn down with the same `kubectl`/GitOps tooling a platform team already uses for everything else.

## Version Context: Notebooks v1 and the Coming v2

As of the 26.03 Kubeflow Community Distribution, Kubeflow Notebooks is running its long-standing **v1** design — a `Notebook` custom resource that is a fairly thin wrapper around a Kubernetes `StatefulSet`/pod spec, spawned through the Central Dashboard's notebook UI. This is the architecture the rest of this document describes in detail, and it is what you will encounter deploying 26.03 today.

The project is **actively working toward a v2 release** built around two new custom resources, `Workspace` and `WorkspaceKind`, which separate "what a notebook environment looks like" (a `WorkspaceKind` template that an admin defines and versions) from "which one a given user is running" (a `Workspace` that references a kind). As of the 26.03 base distribution, v2 (`Workspaces`) had shipped alpha manifests for testing; the 26.03.1 patch moved it to **beta**, though it has **not yet reached general availability**. The v1 `Notebook` CRD is expected to move into a maintenance-only state once v2 is ready for production use. Treat v2 as forward-looking context worth planning for — check the [Kubeflow Notebooks docs](https://www.kubeflow.org/docs/components/notebooks/) for the current GA status before committing a production platform design to either API.

## Multi-Tenancy Model: Profiles as the Notebook Boundary

Every Kubeflow Notebooks user operates inside a **Profile** — the same namespace-per-user construct used across the rest of Kubeflow (covered in Part 1). Creating a Profile provisions:

* A dedicated Kubernetes namespace for that user (or team).
* RBAC bindings that scope the user's permissions to their own namespace via the Profile Controller.
* An Istio `AuthorizationPolicy` that restricts which identities can reach services (including notebook pods) inside that namespace, so one user's notebook cannot be reached, and cannot reach, another user's workloads by default.

A notebook server is always created inside a Profile namespace, never in a shared namespace. This is what lets a platform team hand out self-service notebook creation without every user's pod being mutually reachable — the isolation boundary is the same one used for pipeline runs, KServe endpoints, and every other per-user resource in the cluster.

### Persistent Storage

The Central Dashboard's spawner lets a user attach one or more PersistentVolumeClaims to the notebook pod, typically mounted at the notebook server's home directory (e.g. `/home/jovyan` for the Jupyter-based images, following the upstream Jupyter Docker Stacks convention). Because the claim — not the pod — is the durable object, a user's files, installed packages, and Jupyter configuration survive a pod restart, a node replacement, or an intentional stop/start cycle of the notebook itself. On EKS this PVC is typically backed by the Amazon EBS CSI driver for single-pod ReadWriteOnce access, or Amazon EFS via its CSI driver when a team wants the same working directory shared read-write across multiple notebook or pipeline pods.

### Idle Culling

Because a running notebook pod holds its requested CPU, memory, and — most expensively — GPU allocation for as long as it exists, regardless of whether anyone is actively using it, Kubeflow Notebooks includes a culling mechanism that can stop (not delete) notebooks that have gone idle for a configured period. Culling frees the node capacity the idle notebook was holding — which matters most for GPU-backed notebooks, where an idle server can otherwise sit on an expensive GPU instance for hours after a user has walked away. The underlying PVC is untouched by culling, so a culled notebook's environment and files are exactly as the user left them the next time it's started.

## Notebook Reconciliation Flow

![Sequence diagram showing a user configuring a notebook in the Central Dashboard, which creates a Notebook custom resource watched by the Notebook Controller; the controller reconciles a StatefulSet and Pod that mounts its PVC and requests a GPU, gets an Istio sidecar injected for namespace-scoped routing, and then the notebook UI is exposed back to the user through the Dashboard proxy.](../../.gitbook/assets/en-ai-ml-kubeflow-03-notebooks-0.png)

The controller's reconciliation loop is the same pattern used elsewhere in Kubernetes: it doesn't create the pod directly on every dashboard interaction, it continuously reconciles the live `StatefulSet` toward whatever the `Notebook` custom resource currently declares. A dashboard-driven stop, for instance, updates the custom resource's desired state to zero replicas rather than issuing an imperative pod delete, so the controller — not the dashboard UI — is the single source of truth for whether a notebook pod should be running.

## GPU Scheduling for Notebooks on EKS

A notebook pod that needs accelerator access requests it the same way any other pod on the cluster would: the spawner's GPU field on the `Notebook` custom resource translates into a `resources.limits."nvidia.com/gpu"` entry on the underlying pod spec, and the NVIDIA device plugin running on GPU nodes advertises `nvidia.com/gpu` as an allocatable resource to the scheduler.

This means notebook GPU scheduling is not a separate subsystem from the rest of the cluster's GPU capacity — it competes for, and is served by, the same GPU-capable node pools that back training jobs, KServe endpoints, and any other GPU workload. On EKS, that capacity is commonly provisioned dynamically via Karpenter, which can scale a GPU `NodePool` up when a notebook pod's `nvidia.com/gpu` request can't be satisfied by existing capacity, and scale it back down once the notebook is culled or stopped. The mechanics of configuring GPU-aware Karpenter NodePools, instance-type selection, and taints/tolerations for accelerator nodes are covered in depth in [Karpenter for Autoscaling](../../autoscaling/02-karpenter.md). The notebook-specific detail worth remembering here is simply that an idle GPU notebook is one of the most common causes of a GPU node pool refusing to scale to zero — which is exactly what the culling behavior above exists to prevent.

## Custom Notebook Images

The stock notebook images the Kubeflow spawner ships with cover a general JupyterLab/RStudio/code-server baseline, but most teams running notebooks in production build and reference their own custom images so that every data scientist starts from an identical, reproducible environment rather than `pip install`-ing dependencies by hand inside a running container.

The common pattern is:

1. **Start from an upstream Kubeflow (or Jupyter Docker Stacks) base image** that already has the notebook server, the Kubeflow SDK integrations, and the expected UID/working-directory conventions the spawner expects.
2. **Layer on the team's actual dependencies** — a fixed set of Python/R packages, internal libraries, GPU-framework versions (matching the CUDA driver on the target node pool), and any credentials-free tooling the team standardizes on.
3. **Build and push the image to a registry the cluster can pull from** — on EKS, typically Amazon ECR, with image scanning and lifecycle policies applied the same way as any other production image.
4. **Reference the image from the spawner.** The Central Dashboard's spawner UI accepts an arbitrary image reference in its image field (subject to whatever allow-list an admin has configured), so a custom image behaves identically to a stock one from the end user's point of view — it's just another option to pick.

Keeping these images versioned and rebuilt through the same CI pipeline as any other application image is what makes notebook environments reproducible across a team: two data scientists picking the same image tag get byte-identical package sets, rather than each user's kernel drifting from manual installs over time.

## Next Steps

This document covered what Kubeflow Notebooks does, the Profile-based multi-tenancy model that isolates each user's notebook, persistent storage and idle culling, the notebook controller's reconciliation flow, GPU scheduling on EKS, and the practice of building custom notebook images for reproducible environments. Part 4 moves on to Katib and hyperparameter tuning, building on the same Profile and custom-resource patterns introduced here.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/03-notebooks-quiz.md).
