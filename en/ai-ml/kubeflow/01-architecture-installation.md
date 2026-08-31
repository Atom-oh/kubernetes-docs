# Part 1: Kubeflow Architecture and Installation on EKS

> **Supported Versions**: Kubeflow Community Distribution 26.03 (Kubeflow Pipelines 2.16.0, Katib 0.19.0), Kubernetes 1.34+
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later
* A working Amazon EKS cluster
* kustomize (bundled with recent kubectl, or installed standalone) for manifest-based deployment
* Terraform, if you plan to use the Terraform-based deployment path instead
* An IAM role associated with a Kubernetes service account (IRSA or EKS Pod Identity) for pods that need to reach S3 or RDS
* An Amazon Cognito user pool, if you plan to use Cognito for cluster authentication instead of the bundled Dex

## What Is Kubeflow?

Kubeflow is an open-source machine learning platform that runs natively on Kubernetes. Rather than being a single tool, it is a distribution that bundles a set of independently developed components under one installation and one Central Dashboard:

- **Kubeflow Pipelines** — orchestrates multi-step ML workflows as directed acyclic graphs (DAGs) of containerized steps.
- **Notebooks** — provisions Jupyter (and other) notebook servers as Kubernetes pods, scoped to a user's namespace.
- **Katib** — runs hyperparameter tuning and neural architecture search as Kubernetes-native jobs.
- **Kubeflow Trainer** — schedules distributed training jobs (the legacy Training Operator, and its v2 successor, both covered in this series).
- **KServe** — serves trained models as scalable inference endpoints, including via a dedicated web app in the dashboard.

The value proposition is that all of these components sit on top of the same Kubernetes API, the same RBAC and namespace model, and the same underlying compute — so a platform team that already operates Kubernetes doesn't need to stand up a second stack for ML-specific workloads.

### CNCF Graduation — August 17, 2026

On August 17, 2026, the [Cloud Native Computing Foundation announced](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) that **Kubeflow has graduated** — CNCF's highest maturity tier, reserved for projects that have demonstrated broad production adoption, a healthy multi-vendor contributor base, and sound governance. Kubeflow entered CNCF as an incubating project in 2023 (it originated at Google in 2017), and reaching graduation required it to pass an independent third-party security audit and establish a formal steering committee for project governance. For platform teams evaluating Kubeflow, graduation is a meaningful signal: it is no longer treated as an early-stage bet but as a project CNCF considers stable enough for regulated, production AI workloads.

## Release Model and Current Version

The **Kubeflow Community Distribution** — the reference distribution maintained by the Kubeflow project itself, as distinct from vendor distributions like the one AWS packages via `kubeflow-manifests` — uses **calendar versioning** (`YY.MM.patch`), with roughly two base releases per year. At the time of writing, the base release is **26.03**, which bundles:

| Component | Version in 26.03 |
| --- | --- |
| Kubeflow Pipelines | 2.16.0 |
| KServe web app | 0.16.1 |
| Training Operator (legacy v1) | 1.9.2 |
| Kubeflow Trainer (v2) | v2.1.0 |
| Katib | 0.19.0 |
| Notebooks | approaching a v2 release |

A later patch, **26.03.1**, bumped several of these further (Kubeflow Pipelines 2.16.1, KServe web app v0.18.0, Kubeflow Trainer v2.2.0, Notebooks' v2 `workspaces` reaching beta) — always check the [Kubeflow Community Distribution releases](https://github.com/kubeflow/community-distribution/releases) for the current patch level rather than assuming 26.03 itself is still the latest.

A nuance worth flagging now: **Kubeflow Trainer v2** — built around new `TrainJob`, `ClusterTrainingRuntime`, and `TrainingRuntime` custom resources — is the project's designated successor to the legacy Training Operator (v1) shipped as 1.9.2 in 26.03. The two exist side by side during this transition period. Part 5 of this series covers Trainer v2's APIs and migration path in depth; for this installation-focused part, it's enough to know that a distribution's Training Operator version number does not tell the whole story of which training API you'll actually be writing jobs against.

## Component Architecture

Kubeflow's architecture centers on a shared Kubernetes API server that every component talks to as a set of controllers and CRDs, with an Istio-based multi-tenancy layer providing namespace isolation and a Central Dashboard providing a single UI entry point.

![The Istio ingress gateway routes requests through Dex/Cognito OIDC authentication to the Kubeflow Central Dashboard, which acts as the hub connecting the Profile Controller (managing per-team namespace profiles) and the component controllers for Pipelines, Notebooks, Katib, Kubeflow Trainer, and KServe, all of which reconcile custom resources against the Kubernetes API server under namespace-scoped access.](../../.gitbook/assets/en-ai-ml-kubeflow-01-architecture-installation-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-01-architecture-installation-0.html)

A few points worth calling out:

- **Profiles as tenancy boundary.** A "Kubeflow Profile" is a Kubernetes namespace plus a bundle of RBAC bindings, resource quotas, and Istio `AuthorizationPolicy` objects, all reconciled by the Profile Controller from a single `Profile` custom resource. Every user or team typically gets one profile, and every other component (Notebooks, Pipelines runs, Katib experiments) creates its resources inside the requesting user's profile namespace.
- **Istio as the isolation mechanism.** Kubeflow relies on Istio's sidecar proxies and `AuthorizationPolicy` resources to enforce that a request bound for one profile's namespace can't be served by workloads in another — this is what makes multi-tenancy possible without every component reinventing its own authorization logic.
- **Components as independent controllers.** Pipelines, Notebooks, Katib, Trainer, and KServe are each separate sets of controllers and CRDs reconciling against the same Kubernetes API server. This is why Kubeflow releases are described as a "distribution" — the project pins compatible versions of each component and ships them together, but each one is independently versioned and could, in principle, be run alone.

## Installation Approaches on EKS

Kubeflow's upstream manifests assume a fairly self-contained deployment: Dex for authentication, an in-cluster MySQL StatefulSet for Pipelines/Katib metadata, and MinIO for Pipelines artifact storage. None of those defaults are ideal for a production EKS deployment, so AWS maintains **`awslabs/kubeflow-manifests`**, a distribution overlay that swaps in managed AWS services in place of Kubeflow's bundled self-hosted dependencies:

| Kubeflow default | AWS-native replacement |
| --- | --- |
| Dex (static or LDAP-backed OIDC) | Amazon Cognito user pool as the OIDC provider |
| In-cluster MySQL for Pipelines/Katib metadata | Amazon RDS (MySQL-compatible) |
| MinIO for Pipelines artifact storage | Amazon S3 |

`awslabs/kubeflow-manifests` documents two parallel deployment paths for wiring these substitutions together:

1. **Manifest-based (`kustomize`)** — a set of kustomize overlays layered on top of the upstream Kubeflow manifests, applied directly with `kubectl apply -k` against pre-existing (or newly created) RDS instances, S3 buckets, and a Cognito user pool.
2. **Terraform-based** — Terraform modules that provision the supporting AWS infrastructure (RDS, S3, Cognito, IAM roles) and then drive the kustomize-based manifest installation as part of the same apply, so the AWS side and the Kubernetes side are stood up together rather than as two disconnected steps.

Which one to pick is mostly a question of how the rest of your infrastructure is already provisioned: teams that manage EKS add-ons and supporting AWS resources with Terraform elsewhere will generally prefer the Terraform path for consistency; teams that prefer a more manual, inspectable installation — or that already have RDS/S3/Cognito provisioned through some other IaC tool — often start from the plain kustomize guide.

## IAM Access Pattern: IRSA, KFPv2, and the Move Toward Pod Identity

Granting Kubeflow Pipelines pods access to their S3 artifact bucket is the IAM decision that comes up first in any EKS installation, and it has a history worth understanding rather than glossing over:

- **IRSA has been the standard mechanism** for binding an IAM role to a Kubernetes service account so that Pipelines pods can read/write S3 without long-lived static credentials — the usual least-privilege, per-pod-scoped approach `kubeflow-manifests` documents for the RDS/S3 deployment path.
- **IRSA support for KFPv2 specifically has historically lagged.** Earlier `kubeflow-manifests` guidance called out that IRSA was supported for KFPv1 pipelines but not yet for KFPv2, and recommended a workaround using a dedicated IAM user with static credentials for KFPv2 deployments in the interim, with IRSA support for KFPv2 tracked as forthcoming.
- **EKS Pod Identity is the direction of travel for new IAM-to-pod bindings on EKS generally.** It's the newer, simpler mechanism AWS has been steering customers toward for granting pods AWS permissions, and it applies broadly across EKS workloads, not just Kubeflow. Whether `kubeflow-manifests`' Pipelines guidance has fully picked up Pod Identity support for KFPv2 by the time you're reading this is worth confirming directly against the current `awslabs/kubeflow-manifests` docs, rather than building an installation around one assumption or the other. This is a fast-moving area of the AWS distribution, and it's the kind of detail that's better verified live than assumed from older documentation.

The practical takeaway: don't hardcode an assumption about which mechanism (IRSA, an IAM user workaround, or Pod Identity) is currently required for your specific Pipelines version — check the current component guide before you provision IAM resources.

## Why Run Kubeflow on EKS Instead of a Managed Alternative

Amazon SageMaker (and similar fully managed ML platforms) removes essentially all of the operational surface covered in this document — no manifests to apply, no controllers to upgrade, no Istio mesh to reason about. That's a legitimate, often correct choice, especially for teams without existing Kubernetes operational capacity.

Kubeflow on EKS earns its complexity when a few things are already true of your environment:

- **You're already running mixed workloads on EKS.** If data processing, application services, and ML training all need to share a cluster's node pools, Karpenter autoscaling, and observability stack, running the ML platform as just another set of Kubernetes controllers avoids maintaining a second, parallel operational model.
- **You need portability or want to avoid platform lock-in.** Kubeflow's pipelines, training jobs, and serving manifests are Kubernetes-native artifacts; the same YAML can, with more or less effort, run on any conformant Kubernetes cluster, which matters for multi-cloud or on-prem-plus-cloud strategies.
- **You want fine-grained control over the training/serving stack.** Custom training runtimes, specific accelerator scheduling behavior, or serving frameworks not exposed the way you need through a managed service are all easier to accommodate when you own the underlying controllers.

The trade-off is real: your team takes on manifest and CRD upgrade management, Istio operational knowledge, and the IAM/networking plumbing described above. As with the rest of this documentation site's "why run this on EKS" sections for other data and ML tools, this isn't an argument that Kubeflow is strictly better than SageMaker — it's a description of the conditions under which the added operational cost is worth paying.

## Next Steps

Part 2 of this series covers Kubeflow Pipelines in depth: pipeline authoring, the KFP SDK, and artifact/metadata storage patterns on EKS.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md).
