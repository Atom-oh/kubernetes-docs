# Kubeflow on EKS Deep Dive

> **Supported Versions**: Kubeflow Community Distribution 26.03
> **Last Updated**: September 2, 2026

## Overview

Kubeflow is an open-source machine learning platform for Kubernetes that bundles the pieces a team needs to run ML workloads end to end — pipeline orchestration, notebooks, hyperparameter tuning, distributed training, and model serving — as a set of Kubernetes-native controllers and CRDs rather than a single monolithic application. On August 17, 2026, the CNCF announced Kubeflow's graduation (having joined as an incubating project in 2023), following an independent security audit and the formation of a formal steering committee — a strong signal of the project's production maturity.

## Component Map

| Component | Problem It Solves | CRD / Core Concept | Deep Dive |
|-----------|--------------------|---------------------|-----------|
| **Central Dashboard & Profiles** | Multi-tenant access, per-user namespace isolation | Profile (namespace) | [Part 1](01-architecture-installation.md) |
| **Kubeflow Pipelines** | Orchestrate multi-step ML workflows as DAGs | `Pipeline`, `Run`, `Experiment` | [Part 2](02-pipelines.md) |
| **Kubeflow Notebooks** | Managed, per-user Jupyter/RStudio/VS Code environments | `Notebook` | [Part 3](03-notebooks.md) |
| **Katib** | Hyperparameter tuning and AutoML | `Experiment`, `Trial`, `Suggestion` | [Part 4](04-katib.md) |
| **Kubeflow Trainer** | Distributed model training across frameworks | `TrainJob`, `ClusterTrainingRuntime` | [Part 5](05-training-operator.md) |
| **KServe** | Model serving and inference | `InferenceService` | [Part 6](06-kserve.md) |

![Kubeflow component map showing the Central Dashboard as the entry point to Notebooks, Pipelines, and Katib, with Pipelines and Katib both handing training to Kubeflow Trainer, whose trained model flows to KServe for serving.](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

## Why Run This on EKS

Kubeflow's components are designed to run on any conformant Kubernetes cluster, which means the operational practices this docs site already covers for EKS — Karpenter-driven autoscaling (including GPU node pools), IRSA/Pod Identity for AWS service access, EBS/S3 storage integration, and observability with Prometheus/Grafana — apply directly to ML workloads rather than requiring a separate ML-specific platform. The trade-off against a fully managed path such as [Amazon SageMaker AI](../sagemaker-ai/README.md) is the same one covered in [Data on EKS](../../data-on-eks/README.md): more operational responsibility (Operator upgrades, storage/identity wiring) in exchange for a single deployment/observability model shared across all workloads on the cluster, and the ability to run any of Kubeflow's components independently rather than adopting the whole platform at once.

## Currently Covered

1. [Part 1: Kubeflow Architecture and Installation on EKS](01-architecture-installation.md) — component architecture, CNCF graduation context, installing via `awslabs/kubeflow-manifests` on EKS
2. [Part 2: Kubeflow Pipelines](02-pipelines.md) — KFP SDK v2, IR-based pipeline compilation, S3-backed artifact storage
3. [Part 3: Kubeflow Notebooks](03-notebooks.md) — per-user notebook servers, Profile-based multi-tenancy, GPU scheduling
4. [Part 4: Katib — Hyperparameter Tuning and AutoML](04-katib.md) — Experiment/Trial/Suggestion model, search algorithms, early stopping
5. [Part 5: Kubeflow Trainer and Distributed Training](05-training-operator.md) — the v1 Training Operator to Kubeflow Trainer v2 transition, TrainJob/TrainingRuntime
6. [Part 6: KServe — Model Serving on Kubernetes](06-kserve.md) — InferenceService, Serverless vs. Raw Deployment mode, canary rollouts
