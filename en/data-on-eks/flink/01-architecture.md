# Part 1: Flink Architecture on Kubernetes

> **Supported Versions**: Apache Flink 2.2+, Kubernetes 1.21+\
> **Last Updated**: July 15, 2026

## What is Apache Flink?

Apache Flink is a distributed stream processing engine built for stateful computation over unbounded and bounded data streams. It is widely used for real-time analytics, event-driven applications, and continuous ETL pipelines that need low-latency processing with exactly-once state guarantees.

This document covers the core architectural concepts you need before running Flink on EKS: the JobManager/TaskManager cluster model, the three deployment modes, and the difference between native Kubernetes deployment and standalone-on-Kubernetes. Part 2 walks through installing and operating the **Flink Kubernetes Operator** on a real EKS cluster.

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.21 or later
* A working Kubernetes cluster (Amazon EKS recommended)
* The Flink CLI (`bin/flink`), bundled with the Apache Flink distribution, for submitting jobs directly against a cluster
* (Covered in Part 2) The Flink Kubernetes Operator's CRDs — not required for this document, since this part focuses on the architecture the Operator manages rather than the Operator itself

## 1. Core Cluster Architecture: JobManager and TaskManager

### Core Terminology

* **JobManager (JM)**: The control plane of a Flink cluster. It builds the job graph from a submitted application, coordinates checkpoints, schedules work onto TaskManagers, and serves the REST API and Web UI. On Kubernetes, the JobManager runs as its own pod.
* **TaskManager (TM)**: The worker process that actually executes the job. Each TaskManager offers one or more **task slots**, and each slot runs one parallel instance of an operator subtask. On Kubernetes, each TaskManager runs as its own pod.
* **Task Slot**: A fixed slice of a TaskManager's resources (primarily memory) reserved for exactly one operator subtask at a time. A TaskManager with 4 slots can run up to 4 subtasks concurrently.
* **Checkpoint Coordinator**: A component inside the JobManager that periodically triggers distributed snapshots of operator state across all TaskManagers, enabling exactly-once recovery after a failure.
* **Kubernetes ResourceManager**: The JobManager-internal component that talks to the Kubernetes API server to request or release TaskManager pods, used only in native Kubernetes deployment (see Section 3).

### JobManager <-> TaskManager Flow on Kubernetes

![Diagram of the Flink JobManager pod (Job Graph and Scheduler, Checkpoint Coordinator, Kubernetes ResourceManager, REST API and Web UI) coordinating two TaskManager pods, showing the ResourceManager requesting and releasing pods, the Job Graph and Scheduler deploying subtasks into each pod's task slots, and the Checkpoint Coordinator triggering snapshots on one slot per pod.](../../.gitbook/assets/en-data-on-eks-flink-01-architecture-0.png)

The JobManager decomposes a submitted application into a job graph, splits each operator into parallel subtasks, and assigns those subtasks to task slots across the available TaskManager pods. When native Kubernetes deployment is used, the JobManager's own Kubernetes ResourceManager dynamically requests new TaskManager pods when more slots are needed and releases them when a job's parallelism shrinks or the job finishes.

### Slot Sharing: Why Slot Count Isn't the Sum of All Parallelism

By default, Flink places subtasks from different operators of the same job into the same slot via a shared **slot sharing group**, rather than requiring one slot per operator per parallel instance. This means the number of task slots a job actually needs is generally the job's **maximum operator parallelism**, not the sum of every operator's parallelism. For example, a job with a `source` (parallelism 4) -> `map` (parallelism 4) -> `sink` (parallelism 2) pipeline needs only 4 slots total, since the three operators' subtasks for a given parallel "pipeline instance" co-locate in the same slot. This is one of the main levers for sizing how many TaskManager pods a cluster actually needs.

## 2. Deployment Modes

Flink supports three deployment modes that differ in where a job's `main()` method runs and how tightly a job is bound to its own cluster.

| Mode | How it works | Isolation | Recommendation |
| --- | --- | --- | --- |
| **Application Mode** | A dedicated cluster is created per job; the job's `main()` runs inside the JobManager itself | Full resource isolation and fencing between jobs — one job's failure or resource spike cannot affect another | **Recommended default for production** |
| **Session Mode** | A single, shared, long-lived cluster runs multiple jobs submitted independently over time | Lower isolation — jobs share the same JobManager and compete for the same TaskManager pool | Good fit for many short-lived or ad-hoc jobs where cluster startup overhead matters more than isolation |
| **Per-Job Mode** | Legacy mode; the client executed `main()` locally and submitted a pre-built job graph, spinning up a dedicated cluster per job | Full isolation, similar to Application Mode | **Not supported on native Kubernetes deployment** — effectively dead going forward |

**Application Mode is the recommended default** because running the job's `main()` inside the JobManager avoids shipping a large, client-side-constructed job graph over the network and, more importantly, gives every job its own dedicated JobManager and TaskManager pods. That per-job resource isolation and fencing means a misbehaving or resource-hungry job cannot starve or destabilize any other job's cluster — a property that matters a lot in a shared EKS cluster running many Flink workloads.

**Session Mode** trades away that isolation for lower per-job startup latency, since the cluster already exists and a new job simply gets submitted to it. It remains a reasonable choice for interactive exploration or a large number of small, short-lived batch jobs, as long as you accept that a single noisy job can affect the whole session cluster.

**Per-Job Mode** is only mentioned here to explain why you won't see it recommended anywhere in a Kubernetes context: native Kubernetes deployment never implemented it, so on EKS it is simply not an available option. Application Mode covers the same per-job isolation goal without the legacy client-side submission path.

## 3. Native Kubernetes Deployment vs. Standalone-on-Kubernetes

Flink can run on Kubernetes in two fundamentally different ways, and the distinction matters when deciding how a cluster's TaskManager count is managed.

| Aspect | Native Kubernetes Deployment | Standalone-on-Kubernetes |
| --- | --- | --- |
| Resource management | Flink's own Kubernetes ResourceManager integration talks directly to the Kubernetes API to request and release TaskManager pods | None — Flink has no visibility into Kubernetes; pods are just plain processes |
| TaskManager pod count | Elastic — grows and shrinks dynamically based on the job's required slots | Fixed — a set number of TaskManager pods defined upfront via plain Kubernetes `Deployment`/YAML manifests |
| How it's deployed | `flink run-application` / `flink run` targeting a Kubernetes context, or a controller built on top of it (e.g., the Flink Kubernetes Operator) | Hand-written Kubernetes `Deployment`, `Service`, and `ConfigMap` YAML that starts JobManager and TaskManager containers directly |
| Operational maturity | The modern, recommended path — this is what the **Flink Kubernetes Operator** (covered in Part 2) is built on top of | Legacy/manual path — still technically works, but requires manually editing and reapplying YAML to change TaskManager count |

**Native Kubernetes deployment** is the recommended path in 2026: because the JobManager can talk to the Kubernetes API server directly, it can request exactly as many TaskManager pods as a job's parallelism requires and release them when they're no longer needed, without an operator or human editing YAML by hand. This dynamic resource allocation is also the foundation the Flink Kubernetes Operator builds on — the Operator adds a Kubernetes-native CRD layer (`FlinkDeployment`, `FlinkSessionJob`) on top of native mode so that cluster lifecycle, upgrades, and savepoint-based redeploys can be managed declaratively.

**Standalone-on-Kubernetes** predates native support and simply runs JobManager and TaskManager as plain containers with a fixed pod count, with no elastic resource requests at all. It still works and is sometimes used where tighter control over exactly which pods exist is wanted, but it is legacy and manual: scaling TaskManagers means editing and reapplying a `Deployment` manifest yourself, and there is no built-in mechanism for the cluster to ask Kubernetes for more capacity on demand.

Submitting a job directly with native Kubernetes deployment (Application Mode) looks like this from the Flink CLI, with no operator involved:

```bash
# Submit a job in Application Mode using native Kubernetes deployment
./bin/flink run-application \
  --target kubernetes-application \
  -Dkubernetes.cluster-id=my-flink-app \
  -Dkubernetes.container.image=my-registry/my-flink-app:2.3.0 \
  -Dkubernetes.namespace=data-processing \
  -Dtaskmanager.numberOfTaskSlots=2 \
  local:///opt/flink/usrlib/my-job.jar
```

This single command causes the Flink client to talk to the Kubernetes API to create the JobManager deployment; from there, the JobManager's own Kubernetes ResourceManager takes over requesting TaskManager pods as the job needs them. Part 2 replaces this imperative CLI invocation with a declarative `FlinkDeployment` custom resource applied via `kubectl apply`, managed continuously by the Flink Kubernetes Operator.

## 4. Flink 2.x on Kubernetes: Version Baseline

Apache Flink's 2.x line is the current stable baseline as of mid-2026, with **Flink 2.3.0** released in June 2026 as the latest stable release. A notable platform change carried through the 2.x line is the move to **Java 17 as the baseline runtime** for JobManager and TaskManager images, replacing the Java 11 baseline used historically. This affects the base images referenced in Kubernetes pod specs and any custom Flink images built on top of them — they should be built on a Java 17 (or later) JRE/JDK rather than Java 11.

## Next Steps

This document covered Flink's core architecture on Kubernetes — the JobManager/TaskManager model, the three deployment modes and why Application Mode is the production default, and the difference between native Kubernetes deployment and the legacy standalone-on-Kubernetes path. Part 2 covers installing and operating the **Flink Kubernetes Operator**, which builds on native Kubernetes deployment to manage Flink clusters declaratively via `FlinkDeployment` and `FlinkSessionJob` custom resources.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/flink/01-architecture-quiz.md).
