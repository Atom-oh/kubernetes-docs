# Flink on EKS Deep Dive

## Overview

Apache Flink is a distributed stream processing engine for stateful computation over unbounded and bounded data streams, widely used for real-time analytics, event-driven applications, and continuous ETL. On EKS, the standard way to run Flink is through the **Flink Kubernetes Operator** rather than submitting jobs by hand with the Flink CLI. The Operator manages the full lifecycle of Flink clusters — deployment, upgrades, savepoint-based redeploys, and autoscaling — declaratively through Kubernetes-native CRDs (Custom Resource Definitions).

> **Supported Versions**: Apache Flink 2.2+, Flink Kubernetes Operator 1.15+, Kubernetes 1.21+
> **Last Updated**: July 15, 2026

## Core Architecture Concepts

A Flink cluster is built around two pod roles. The **JobManager** is the control plane: it builds the job graph, coordinates checkpoints, and schedules work — but it does not process any records itself. The **TaskManager** pods are the workers that actually execute operator subtasks in **task slots**. Unlike YARN, which keeps a persistent daemon set of node managers running at all times, Flink's native Kubernetes deployment gives the JobManager its own **Kubernetes ResourceManager** component that talks directly to the Kubernetes API server — it dynamically requests new TaskManager pods when a job needs more slots and releases them when parallelism shrinks or the job finishes, so no fixed worker pool has to be pre-provisioned or hand-managed.

The **Flink Kubernetes Operator** sits one layer above this native deployment model. Rather than an operator submitting jobs imperatively via `flink run-application`, you declare the desired cluster state through `FlinkDeployment` (Application/Session mode clusters) and `FlinkSessionJob` (jobs submitted onto a running Session cluster) custom resources, and the Operator continuously reconciles the JobManager/TaskManager pods to match — including how to safely apply changes (stateless restart, savepoint, or last-state upgrade) and how to rescale individual job vertices via its built-in autoscaler.

![An operator applies a FlinkDeployment or FlinkSessionJob custom resource to the Kubernetes API server; the Flink Kubernetes Operator watches the API and reconciles by creating a JobManager pod, which acts as Flink's ResourceManager to request/release TaskManager pods via the API server and schedules subtasks and checkpoints on two TaskManager pods.](../../.gitbook/assets/en-data-on-eks-flink-README-0.png)

## Deep Dive Table of Contents

**[1. Flink Architecture](01-architecture.md)**
- JobManager/TaskManager cluster model and task slots
- Deployment modes: Application, Session, and legacy Per-Job
- Native Kubernetes deployment vs. standalone-on-Kubernetes

**[2. Flink Kubernetes Operator](02-flink-kubernetes-operator.md)**
- `FlinkDeployment` and `FlinkSessionJob` CRDs
- Upgrade modes: stateless, savepoint, and last-state
- The built-in per-vertex autoscaler

**[3. State, Checkpointing, and Streaming Patterns](03-state-checkpointing-streaming.md)**
- HashMap vs. RocksDB state backends and incremental checkpoints
- Checkpoints vs. savepoints
- Exactly-once delivery to Kafka via two-phase commit, and the Dynamic Iceberg Sink
- Flink SQL/Table API vs. DataStream API

**[4. Operations and High Availability](04-operations-ha.md)**
- Prometheus and RocksDB metrics monitoring
- Kubernetes-native HA via ConfigMaps (no Zookeeper)
- Two-tier autoscaling with the Flink autoscaler and Karpenter
- Amazon Managed Service for Apache Flink comparison

## References

- [Apache Flink Documentation](https://nightlies.apache.org/flink/flink-docs-release-2.2/)
- [Flink Kubernetes Operator](https://github.com/apache/flink-kubernetes-operator)
- [Flink Kubernetes Operator Autoscaler](https://nightlies.apache.org/flink/flink-kubernetes-operator-docs-main/docs/custom-resource/autoscaler/)
- [Amazon Managed Service for Apache Flink](https://docs.aws.amazon.com/managed-flink/latest/java/what-is.html)
- [AWS Data on EKS Project](https://awslabs.github.io/data-on-eks/)

## Quiz

To test what you've learned in this section, try the [Flink Architecture Quiz](../../quizzes/data-on-eks/flink/01-architecture-quiz.md).
