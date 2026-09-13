# Ray on EKS Deep Dive

> **Review baseline**: Ray 2.58.0, KubeRay v1.7.0
> **Documentation reviewed**: September 12, 2026

## Overview

Ray distributes Python work using tasks, actors, ObjectRefs, and per-node object stores. Train, Tune, and Serve use that foundation while adding training, search, and serving policies. One object-store path does not automatically handle every communication or recovery concern.

KubeRay is the Kubernetes operator reconciling RayCluster, RayJob, and RayService. It does not select the application's ML library as a dispatcher. Ray work scheduling, Kubernetes Pod placement, and EC2 node provisioning are separate layers.

## Component Map

| Concept | Problem It Solves | Deep Dive |
|---------|--------------------|-----------|
| **Architecture** | Tasks, actors, and the object store that everything else builds on | [Part 1](01-architecture.md) |
| **KubeRay Operator** | Run Ray clusters as native Kubernetes resources (`RayCluster`/`RayJob`/`RayService`) | [Part 2](02-kuberay-operator.md) |
| **Ray Train & Tune** | Distributed model training and hyperparameter search | [Part 3](03-ray-train-tune.md) |
| **Ray Serve** | Model serving, including dedicated LLM-serving building blocks | [Part 4](04-ray-serve.md) |

![Application libraries such as Train, Tune, and Serve use Ray Core tasks and actors; KubeRay separately manages Ray resources on Kubernetes.](../../.gitbook/assets/en-ai-ml-ray-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-readme-0.html)

## Why Run This on EKS

The trade-off is the same one covered elsewhere in this documentation site's data/ML sections: a team already running EKS can reuse the same node-pool autoscaling (via Karpenter), IAM, and observability patterns for Ray workloads as for everything else on the cluster, in exchange for operating the KubeRay operator and its RayCluster/RayJob/RayService resources directly rather than using a managed alternative.

The foundation check is a small single-node Ray run. It is not evidence of GPU training, multi-node recovery, a live EKS installation, or autoscaling.

## Currently Covered

1. [Part 1: Ray Architecture](01-architecture.md) — tasks, actors, the object store, and the head/worker cluster model
2. [Part 2: The KubeRay Operator](02-kuberay-operator.md) — RayCluster, RayJob, RayService, and the two-tier autoscaling pattern with Karpenter
3. [Part 3: Ray Train and Ray Tune](03-ray-train-tune.md) — distributed training and hyperparameter tuning
4. [Part 4: Ray Serve](04-ray-serve.md) — model serving, Ray Serve LLM, and RayService-based production deployment

## Primary Sources

- [Ray 2.58.0](https://github.com/ray-project/ray/releases/tag/ray-2.58.0)
- [KubeRay 1.7.0](https://github.com/ray-project/kuberay/releases/tag/v1.7.0)
