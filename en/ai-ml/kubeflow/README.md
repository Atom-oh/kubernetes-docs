# Kubeflow on EKS Deep Dive

> **Review baseline**: Kubeflow Community Distribution 26.03.1
> **Last reviewed**: September 12, 2026

## Overview

Kubeflow provides Kubernetes-based tools for ML pipelines, notebooks, tuning, training, and serving. The Community Distribution assembles component revisions, shared services, and a dashboard; individual projects also have their own releases and installation requirements.

CNCF [announced Kubeflow's graduation on August 17, 2026](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/). This recognizes project maturity and governance, including an independent security audit. It does not certify the security or regulatory compliance of a particular EKS deployment.

## Component Map

| Component | Purpose | API or concept | Guide |
| --- | --- | --- | --- |
| Dashboard, Profiles, access management | UI navigation, namespace ownership and membership | Cluster-scoped `Profile`; optional quota | [Part 1](01-architecture-installation.md) |
| Pipelines | Compile and execute workflows; track runs and artifacts | Pipeline/Run/Experiment APIs; optional Kubernetes Native API mode adds `Pipeline`/`PipelineVersion` CRDs | [Part 2](02-pipelines.md) |
| Notebooks | User notebook workloads | `Notebook`; image and PVC configuration | [Part 3](03-notebooks.md) |
| Katib | Hyperparameter search and trials | `Experiment`, `Trial`, `Suggestion` CRDs | [Part 4](04-katib.md) |
| Trainer | Distributed training with configured runtimes | `TrainJob`, `TrainingRuntime`, `ClusterTrainingRuntime` | [Part 5](05-training-operator.md) |
| KServe | Model inference services | `InferenceService`; mode-specific dependencies | [Part 6](06-kserve.md) |

This map covers the guide's scope, not the entire distribution. Release 26.03.1 also includes Hub/model registry and Spark Operator. A KFP Experiment is not the Katib Experiment CRD.

![Kubeflow component map separating dashboard navigation from explicitly configured pipeline, tuning, training, and model deployment integrations.](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

The dashboard links component UIs. Pipelines and Katib use Trainer only when their implementation explicitly submits a supported training resource. Connecting a trained artifact to KServe requires a separate deployment step; the diagram does not imply automatic model promotion.

## Why Run This on EKS

An existing EKS platform can share capacity management, storage integration, workload identity, and monitoring with ML workloads. Compatibility still depends on Kubernetes version, CPU architecture, images, networking, storage drivers, and authentication. Kubernetes conformance alone is insufficient; the release documentation notes incomplete ARM64 image coverage.

The team remains responsible for component/CRD upgrades, tenant authorization, persistent data, credentials, and recovery. [Amazon SageMaker AI](../sagemaker-ai/README.md) reduces some infrastructure responsibilities, while data access, application correctness, model quality, and cost control still need owners. Choose based on required interfaces, operating capacity, and workload constraints.

## Currently Covered

1. [Part 1: Architecture and installation on EKS](01-architecture-installation.md) — current community release, legacy AWS distribution limitations, Profiles, identity, and manifest rendering.
2. [Part 2: Pipelines](02-pipelines.md) — SDK v2, compilation, execution, and artifact storage.
3. [Part 3: Notebooks](03-notebooks.md) — workloads, Profiles, storage, and GPU placement.
4. [Part 4: Katib](04-katib.md) — experiments, trials, search, and early stopping.
5. [Part 5: Trainer](05-training-operator.md) — legacy Training Operator and Trainer v2 APIs.
6. [Part 6: KServe](06-kserve.md) — inference resources, deployment modes, and rollouts.

Use each chapter's component baseline. Check the [26.03.1 release](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1) and [pinned inventory](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md) before selecting an installation.
