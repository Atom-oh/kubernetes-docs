# MLflow on EKS Deep Dive

> **Review baseline**: MLflow 3.16.0
> **Documentation reviewed**: September 12, 2026

## Overview

MLflow provides experiment tracking, model logging and registration, version management, GenAI evaluation, and tracing. Tracing arrived in 2.14.0; 3.x expanded LoggedModel, evaluation, and UI integration. Version 3.16.0 was released on 2026-09-04.

Use it locally with the SDK and SQLite, or operate an HTTP tracking service with separate SQL metadata and artifact stores. A logical service need not be one Pod or storage system. This series covers Tracking, Registry, and EKS deployment; it does not validate every MLflow feature or successful GPU training.

## Component Map

| Concept | Problem It Solves | Deep Dive |
|---------|--------------------|-----------|
| **Tracking** | Log and query experiment parameters, metrics, artifacts, models, and GenAI traces | [Part 1](01-tracking.md) |
| **Model Registry** | Give a model a stable, versioned identity independent of any one training run | [Part 2](02-model-registry.md) |
| **EKS Deployment** | Run the tracking server, backend store, and artifact store on EKS | [Part 3](03-eks-deployment.md) |

![A three-stage pipeline diagram showing MLflow Tracking (experiments, runs, traces) feeding the Model Registry (registered models, aliases), which is in turn resolved by a Serving stage that is out of scope for this documentation series.](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## Why Run This on EKS

The trade-off is the same one covered elsewhere in this documentation site's data/ML sections: a team already running EKS can reuse the same deployment, IAM (IRSA/Pod Identity), and observability patterns for MLflow's tracking server as for everything else on the cluster, in exchange for operating the tracking server, its backend database, and its artifact store directly rather than using a managed alternative.

The [SageMaker AI guidebook](../sagemaker-ai/README.md) describes a Qwen comparison design. That example has separate historical version pins and currently blocks GPU execution because its DLC reached end of patch. This series' MLflow 3.16.0 local checks are not end-to-end validation of that example.

Model Registry registration is an optional lifecycle step. Serving systems consume model URIs or aliases through separate configuration; registration or an alias change does not automatically deploy a model.

## Currently Covered

1. [Part 1: MLflow Tracking](01-tracking.md) — experiments, runs, autologging, the MLflow 3 `LoggedModel` shift, and GenAI tracing
2. [Part 2: MLflow Model Registry](02-model-registry.md) — Registered Models, Model Versions, aliases, and lineage
3. [Part 3: Deploying MLflow on EKS](03-eks-deployment.md) — tracking server, PostgreSQL backend store, S3 artifact store, and IAM access

## Primary Sources

- [MLflow 3.16.0 release](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracing introduced in MLflow 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
