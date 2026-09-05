# Part 2: The KubeRay Operator

> **Supported Versions**: KubeRay v1.6.1, Ray 2.57.0
> **Last Updated**: August 20, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later, pointed at a working Amazon EKS cluster
* Helm v3
* A GPU-capable `NodePool`/`EC2NodeClass` pair provisioned via Karpenter, if you plan to test GPU worker groups

## What KubeRay Does

[Part 1](01-architecture.md) described a Ray cluster as a head node plus one or more groups of worker nodes. That shape is a Ray-native concept, not a Kubernetes one, so something has to translate it into actual Pods, Services, and the other objects Kubernetes understands. That something is KubeRay.

KubeRay is a Kubernetes operator that manages Ray clusters as native Kubernetes custom resources. Instead of hand-writing a Deployment, a StatefulSet, and a Service for a head node and every worker group, an operator user declares the desired Ray cluster shape in a YAML manifest, and KubeRay's controller continuously reconciles the cluster's live state against that declared spec. This is what makes "Ray on Kubernetes" declarative: the desired state lives in a custom resource, and the operator does the work of creating, updating, and deleting the underlying Pods to match it.

This document targets **KubeRay v1.6.1** — check the [KubeRay releases page](https://github.com/ray-project/kuberay/releases) for the current version, since KubeRay ships on its own release cadence independent of this document. KubeRay v1.6 added full support for Ray's authentication token mode (securing access to a running cluster's dashboard and client ports) and switched RayJob to a lighter default submitter image, improving RayJob startup performance over the previous default. An earlier v1.5 release had already added incremental, rolling upgrades for RayService, aimed at zero-downtime updates with lower resource overhead than a full blue-green replacement of the entire cluster — but check the current release notes before relying on it, since a feature like this can move from an opt-in, feature-gated state toward being enabled by default as a project matures.

## The Core CRDs

KubeRay exposes most of its functionality through three Custom Resource Definitions, each aimed at a different way of running Ray on Kubernetes (the KubeRay Helm chart also installs CRDs for newer, still-evolving capabilities — check the current release notes for the full set before assuming these three are exhaustive).

**RayCluster** is the foundational resource: a raw Ray cluster made up of one head Pod and one or more worker groups. Each worker group is a set of homogeneous worker Pods — for example, a CPU worker group for general Ray tasks and a separate GPU worker group for model training or inference. The KubeRay operator continuously reconciles the live Pods against the RayCluster spec, creating or removing worker Pods as the spec (or the autoscaler, described below) changes the desired replica count for a group.

**RayJob** submits a batch job to a Ray cluster and, optionally, manages that cluster's entire lifecycle: creating the RayCluster, running the submitted job against it, and tearing the cluster down once the job finishes. This is the natural fit for one-off or scheduled batch workloads, since it avoids paying for a cluster that sits idle between runs.

**RayService** targets production model serving. It manages a RayCluster together with a Ray Serve application deployed on top of it, and can perform rolling upgrades of the underlying cluster and application aimed at zero downtime — check the current release notes for that upgrade path's maturity and any prerequisites before relying on it in production.

![The KubeRay Operator reconciles a RayCluster CR into a Head Pod and CPU/GPU worker group Pods, the Ray Autoscaler monitors those groups and requests more replicas on the RayCluster, and Karpenter reacts to pending Pods by provisioning EC2 nodes.](../../.gitbook/assets/en-ai-ml-ray-02-kuberay-operator-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-02-kuberay-operator-0.html)

## Two-Tier Autoscaling: Ray Autoscaler and Karpenter

Running Ray on EKS means dealing with two separate autoscaling control loops, a pattern this documentation site also covers for other autoscaled workloads such as Flink and Katib. Each loop answers a different question, and neither one can answer the other's.

**The Ray autoscaler** runs as part of the Ray cluster itself, coordinated through KubeRay. It watches Ray's own scheduling state — pending tasks and actors that can't be placed on the current workers — and decides how many Ray worker Pods are needed. It acts on that decision by adjusting the replica count on the relevant RayCluster worker group, which in turn tells the KubeRay operator to create (or remove) worker Pods. The autoscaler also has an `idleTimeoutSeconds` setting, 60 seconds by default, which is how long a worker Pod must sit idle — with no tasks, actors, or referenced objects — before the autoscaler scales it down.

**Karpenter** (or, on clusters not using Karpenter, the Kubernetes Cluster Autoscaler) operates one layer below, at the Kubernetes node level. It doesn't know anything about Ray tasks or actors; it only reacts to Pods that are pending because no node has room for them, and provisions new EC2 nodes sized to match those pending Pods.

Put together: the Ray autoscaler decides *how many Ray worker Pods* the cluster needs, and Karpenter decides *how many EC2 nodes* are needed to actually run them. One control loop owns Pod count, a separate one owns node count, and they communicate only indirectly — through the ordinary Kubernetes scheduling state of pending Pods. See this repo's [Karpenter documentation](../../autoscaling/02-karpenter.md) for how the node-provisioning side of that loop works in more depth.

## GPU Scheduling

A GPU worker group's Pod spec is the single source of truth for how many GPUs that group's Ray workers can see. When a worker group's container spec sets a GPU resource limit — for example, `nvidia.com/gpu: 1` — KubeRay reads that limit and advertises it to both the Ray scheduler and the Ray autoscaler as GPU capacity on the resulting worker Pods. KubeRay also automatically configures the Ray process's `--num-gpus` flag on that worker to match the Pod spec's GPU limit, so there's no separate place to keep a GPU count in sync by hand.

This means GPU-aware scheduling and GPU-aware autoscaling both fall out of the same Kubernetes-native declaration. The Ray autoscaler will only request more GPU worker replicas when GPU-bound tasks are actually pending, and Karpenter provisions the GPU-backed EC2 nodes to satisfy those Pods using the node pool and node class configuration described in [Karpenter](../../autoscaling/02-karpenter.md) — this document doesn't re-derive that mechanism.

## Installing the Operator

The standard way to install KubeRay is the official Helm chart, published from the `ray-project/kuberay-helm` repository:

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.6.1
```

This installs the operator's controller and its CRDs, including RayCluster, RayJob, and RayService described above, into the cluster. Once the operator Pod is running, it watches for those objects across the cluster (or a namespace, depending on installation flags) and begins reconciling them.

## Next Steps

This part covered what KubeRay is, its core CRDs, and how its two-tier autoscaling model divides work with Karpenter. The next part moves from cluster mechanics to Ray's ML libraries running on top of a KubeRay-managed cluster: see [Part 3: Ray Train and Ray Tune](03-ray-train-tune.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/ray/02-kuberay-operator-quiz.md).
