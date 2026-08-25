# Ray on EKS Deep Dive

> **Supported Versions**: Ray 2.57.0, KubeRay v1.6.1
> **Last Updated**: August 20, 2026

## Overview

Ray is an open-source distributed computing framework for scaling Python workloads — from ad hoc parallel tasks to distributed training, hyperparameter tuning, and model serving — built around a small set of core primitives (tasks, actors, and a shared object store) rather than a separate tool per workload type. On Kubernetes, the KubeRay operator translates a Ray cluster's head/worker-node shape into native Kubernetes resources, making Ray clusters declarative and giving EKS the same deployment and autoscaling story it already uses for other workloads.

## Component Map

| Concept | Problem It Solves | Deep Dive |
|---------|--------------------|-----------|
| **Architecture** | Tasks, actors, and the object store that everything else builds on | [Part 1](01-architecture.md) |
| **KubeRay Operator** | Run Ray clusters as native Kubernetes resources (`RayCluster`/`RayJob`/`RayService`) | [Part 2](02-kuberay-operator.md) |
| **Ray Train & Tune** | Distributed model training and hyperparameter search | [Part 3](03-ray-train-tune.md) |
| **Ray Serve** | Model serving, including dedicated LLM-serving building blocks | [Part 4](04-ray-serve.md) |

```mermaid
graph LR
    A[Architecture<br/>Tasks, Actors, Object Store] --> K[KubeRay Operator<br/>RayCluster/RayJob/RayService]
    K --> T[Ray Train &amp; Tune<br/>Distributed training, tuning]
    K --> S[Ray Serve<br/>Model &amp; LLM serving]

    style A fill:#4fc3f7
    style K fill:#81c784
    style T fill:#ffb74d
    style S fill:#ce93d8
```

## Why Run This on EKS

The trade-off is the same one covered elsewhere in this documentation site's data/ML sections: a team already running EKS can reuse the same node-pool autoscaling (via Karpenter), IAM, and observability patterns for Ray workloads as for everything else on the cluster, in exchange for operating the KubeRay operator and its RayCluster/RayJob/RayService resources directly rather than using a managed alternative.

## Currently Covered

1. [Part 1: Ray Architecture](01-architecture.md) — tasks, actors, the object store, and the head/worker cluster model
2. [Part 2: The KubeRay Operator](02-kuberay-operator.md) — RayCluster, RayJob, RayService, and the two-tier autoscaling pattern with Karpenter
3. [Part 3: Ray Train and Ray Tune](03-ray-train-tune.md) — distributed training and hyperparameter tuning
4. [Part 4: Ray Serve](04-ray-serve.md) — model serving, Ray Serve LLM, and RayService-based production deployment
