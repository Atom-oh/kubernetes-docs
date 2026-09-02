# Fine-Tuning Qwen for PII with SageMaker AI

> **Last Updated**: September 2, 2026

## Overview

This guidebook applies QLoRA to `Qwen/Qwen3-30B-A3B-Instruct-2507` so the model extracts PII entities from a document and deterministic code replaces the original values with tokens such as `[PERSON_1]` and `[EMAIL_1]`.

The same source code and synthetic dataset support two execution paths:

- **Managed path**: SageMaker AI Training Job + SageMaker MLflow App
- **Kubernetes path**: ephemeral Amazon EKS GPU Job + MLflow on EKS

The model does not generate the final masked document. Its responsibility ends at emitting one `TYPE<TAB>ORIGINAL` entity per line; tested Python code performs validation, ordering, replacement, and round-trip restoration.

## Five-Part Learning Path

| Part | Topic | Core Question |
|---|---|---|
| [Part 1](01-platform-architecture.md) | Platform architecture | How should SageMaker AI, EKS, MLflow, and Unified Studio divide responsibilities? |
| [Part 2](02-pii-data-tokenization.md) | PII data and tokenization | How do you build training data without real PII and measure leakage? |
| [Part 3](03-sagemaker-mlflow-execution.md) | SageMaker AI and MLflow execution | How does one training contract run on managed and EKS paths? |
| [Part 4](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Unified Studio governance | How should domains, project profiles, projects, and membership be operated? |
| [Part 5](04-validation-results.md) | Factual validation results | What ran, where did it stop, and what was not measured? |

## Current Validation Status

| Status | Verified Scope |
|---|---|
| **Validated locally** | synthetic dataset, tokenizer, aggregate metrics, SageMaker/EKS request contracts |
| **Observed in AWS** | quotas, SageMaker MLflow App, Unified Studio project-creation failure paths |
| **Not executed** | SageMaker Training Job, EKS GPU Job |
| **Blocked** | cleanup of one Unified Studio project |

The September 1, 2026 AWS validation stopped before GPU training. Consequently, this guidebook does not report a fine-tuned F1, training duration, GPU memory, or GPU cost as a measured result.

## Safety Rules

1. Use only fully synthetic data generated with seed `42`.
2. Never write source text, extracted values, token mappings, or raw completions to stdout, CloudWatch, or MLflow parameters/tags.
3. Log only configuration, versions, dataset hashes, aggregate metrics, and non-sensitive artifacts to MLflow.
4. Do not begin a full run until a smoke run passes.
5. Complete inventory-based teardown and verify that no experiment resources remain.

The runnable package lives at `examples/ai-ml/qwen-pii-finetuning/`.
