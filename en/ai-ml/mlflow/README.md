# MLflow on EKS Deep Dive

> **Supported Versions**: MLflow 3.15.1
> **Last Updated**: August 19, 2026

## Overview

MLflow is an open-source platform for managing the machine learning lifecycle — experiment tracking, model packaging and versioning, and (since MLflow 3) GenAI/LLM observability — through a tracking server that any training script or agent can log to over a simple API. Unlike Kubeflow, which bundles a full platform of Kubernetes-native controllers, MLflow is a single service (a tracking server plus its backend/artifact stores) that teams commonly run alongside Kubeflow, a custom training setup, or nothing else at all.

## Component Map

| Concept | Problem It Solves | Deep Dive |
|---------|--------------------|-----------|
| **Tracking** | Log and query experiment parameters, metrics, artifacts, models, and GenAI traces | [Part 1](01-tracking.md) |
| **Model Registry** | Give a model a stable, versioned identity independent of any one training run | [Part 2](02-model-registry.md) |
| **EKS Deployment** | Run the tracking server, backend store, and artifact store on EKS | [Part 3](03-eks-deployment.md) |

```mermaid
graph LR
    T[Tracking<br/>Experiments, Runs, Traces] --> R[Model Registry<br/>Registered Models, Aliases]
    R -->|resolved by| S[Serving<br/>out of scope for this series]

    style T fill:#4fc3f7
    style R fill:#81c784
    style S fill:#e0e0e0,stroke-dasharray: 5 5
```

## Why Run This on EKS

The trade-off is the same one covered elsewhere in this documentation site's data/ML sections: a team already running EKS can reuse the same deployment, IAM (IRSA/Pod Identity), and observability patterns for MLflow's tracking server as for everything else on the cluster, in exchange for operating the tracking server, its backend database, and its artifact store directly rather than using a managed alternative.

## Currently Covered

1. [Part 1: MLflow Tracking](01-tracking.md) — experiments, runs, autologging, the MLflow 3 `LoggedModel` shift, and GenAI tracing
2. [Part 2: MLflow Model Registry](02-model-registry.md) — Registered Models, Model Versions, aliases, and lineage
3. [Part 3: Deploying MLflow on EKS](03-eks-deployment.md) — tracking server, PostgreSQL backend store, S3 artifact store, and IAM access
