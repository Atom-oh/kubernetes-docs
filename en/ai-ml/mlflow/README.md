# MLflow on EKS Deep Dive

> **Supported Versions**: MLflow 3.15.1
> **Last Updated**: September 2, 2026

## Overview

MLflow is an open-source platform for managing the machine learning lifecycle — experiment tracking, model packaging and versioning, and (since MLflow 3) GenAI/LLM observability — through a tracking server that any training script or agent can log to over a simple API. Unlike Kubeflow, which bundles a full platform of Kubernetes-native controllers, MLflow is a single service (a tracking server plus its backend/artifact stores) that teams commonly run alongside Kubeflow, a custom training setup, or nothing else at all.

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

For a comparison of a managed MLflow App and MLflow on EKS using one Qwen PII fine-tuning contract, see the [SageMaker AI Qwen PII guidebook](../sagemaker-ai/README.md) and its [Part 3 execution guide](../sagemaker-ai/03-sagemaker-mlflow-execution.md).

## Currently Covered

1. [Part 1: MLflow Tracking](01-tracking.md) — experiments, runs, autologging, the MLflow 3 `LoggedModel` shift, and GenAI tracing
2. [Part 2: MLflow Model Registry](02-model-registry.md) — Registered Models, Model Versions, aliases, and lineage
3. [Part 3: Deploying MLflow on EKS](03-eks-deployment.md) — tracking server, PostgreSQL backend store, S3 artifact store, and IAM access
