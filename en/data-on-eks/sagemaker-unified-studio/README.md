# SageMaker Unified Studio Governance

> **Last Updated**: September 2, 2026

## Overview

Amazon SageMaker Unified Studio is a managed workspace where data and AI teams share files, tools, data assets, and compute configuration inside projects. This section does not deploy Unified Studio on EKS. It explains **which domain and project boundaries should govern** the data and execution permissions used by Kafka, Spark, Airflow, Flink, and ML training.

It belongs beside Data on EKS because:

- datasets produced by EKS data pipelines can be discovered and shared as catalog assets;
- project profiles and blueprints standardize the SQL, data engineering, and ML experiment capabilities prepared for a project;
- project membership separates collaboration permissions for people and automation roles;
- managed SageMaker AI and self-operated EKS training can follow one data-governance model.

## Scope

| Topic | Coverage |
|---|---|
| domain | organizational data and AI governance boundary |
| project profile | blueprint and tooling template used to create projects |
| project | collaboration and resource-sharing boundary for one business use case |
| catalog asset | metadata for discovering, subscribing to, and publishing data |
| membership | project owner and member authorization |
| lifecycle | create, verify ACTIVE, use, delete, and verify absence |

[Part 4: Domain, project, and membership governance](01-domains-projects-governance.md) connects these concepts to the actual Qwen PII provisioning failures and safe rerun order.

## Current Validation Status

A read-only recheck on September 2, 2026 found **one `qwen-pii-*` project still `ACTIVE`**. The App, S3, and IAM experiment resources were reclaimed, but the current automation role cannot delete the project without project membership.

No new experiment should begin until a domain owner deletes the remaining project or grants owner membership.

Related guides:

- [SageMaker Qwen PII guidebook](../../ai-ml/sagemaker-ai/README.md)
- [Part 3: SageMaker AI and MLflow execution](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Part 5: Factual validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)
