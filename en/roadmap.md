# Guidebook Roadmap

> **Last Updated**: September 1, 2026

This guidebook tells one continuous story: from the Linux kernel through containers, Kubernetes, Amazon EKS, networking, service mesh, storage, databases, data pipelines, and AI/ML — plus the cross-cutting disciplines of security, GitOps, platform engineering, observability, and operations. This page is the map, and the recommended paths through it.

![Learning-flow map of the guidebook's fifteen domains, flowing from foundations (Linux/Container) through orchestration (Kubernetes/EKS), connectivity (Networking/Service Mesh), state (Storage/Database), data and AI (Data Pipeline/AI-ML), to cross-cutting concerns (Security/GitOps/Platform/Observability/Operations).](.gitbook/assets/en-roadmap-0.png)

[🔍 Open the interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-roadmap-0.html)

## The domain map

| Layer | Domain | Start here | One-liner |
|-------|--------|-----------|-----------|
| Foundations | Linux & Container | [Linux Basics](basics/01-linux-basics.md) | Kernel, namespaces, cgroups — what a container actually is |
| Orchestration | Kubernetes Core Concepts | [Introduction to Kubernetes](basics/04-kubernetes-introduction.md) | Workloads, scheduling, and autoscaling — Kubernetes itself |
| Orchestration | Amazon EKS | [Introduction to EKS](eks/01-eks-introduction.md) | Cluster creation through Hybrid Nodes and Auto Mode |
| Connectivity | Networking | [Network Fundamentals](basics/06-network-fundamentals-part1.md) | 25 protocols up through CNI (Cilium/Calico) |
| Connectivity | Service Mesh | [Istio](service-mesh/istio/README.md) | Istio/Linkerd/Cilium Mesh — with measured mTLS latency |
| State | Storage | [Storage Overview](storage/README.md) | EBS gp2 vs gp3, measured with fio |
| State | Database | [Databases Overview](database/README.md) | The operator landscape and a 100M-row ClickHouse benchmark |
| Data & AI | Data Pipeline | [Data on EKS Overview](data-on-eks/README.md) | Kafka, Spark, Airflow, and Flink deep dives |
| Data & AI | AI/ML | [AI/ML Workloads](ai-ml/01-ai-ml-workloads.md) | vLLM, Ray, Kubeflow, MLflow on EKS |
| Cross-cutting | Security & Policy | [Kyverno](security/01-kyverno-policy-management.md) | AuthN/Z, policy, runtime security, supply chain |
| Cross-cutting | GitOps | [GitOps](gitops/README.md) | ArgoCD, Flux, progressive delivery |
| Cross-cutting | Platform Engineering | [Overview](platform-engineering/00-platform-engineering-overview.md) | ACK, KRO, Crossplane, Backstage |
| Cross-cutting | Container Registry | [Overview](container-registry/README.md) | ECR, Harbor, image supply chain |
| Cross-cutting | Observability | [Overview](observability/README.md) | Metrics, logs, tracing, alerting stacks |
| Cross-cutting | Operations Guide | [Operations Guide](ops/README.md) | Capacity planning, FinOps, upgrades — field playbooks |

## The measured-benchmark series

Documents built on numbers measured on real AWS resources, not spec sheets:

- [Istio sidecar vs ambient, measured](service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — P50/P99 latency per mTLS data plane and 503 rates during rollouts
- [EBS gp2 vs gp3 Measured Benchmark](storage/01-ebs-gp2-gp3-benchmark.md) — a 10x IOPS gap at identical capacity, and the gp2 burst-credit cliff
- [ClickHouse on EKS Measured Benchmark](database/01-clickhouse-on-eks.md) — 100M-row ingest throughput, compression ratios, query latency

## Recommended paths

### ① Infrastructure onboarding — "containers to EKS"

Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts (pods/services/storage/configuration) → EKS Cluster Creation → Network Fundamentals. Check yourself with each document's quiz, and work through the [labs](labs/README.md) in parallel.

### ② Platform / SRE — "a cluster you can operate"

EKS operations (upgrades/troubleshooting/resiliency) → Networking (VPC CNI, Cilium) → the Service Mesh comparison guide → Security & Policy → the Observability stack → GitOps → capacity planning and FinOps in the Operations Guide. The measured-benchmark series supplies the evidence this path runs on.

### ③ Data & AI platform — "the stateful world"

Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow). If you need GPUs and scheduling control, add the Custom Scheduler parts under Kubernetes Core Concepts.

## Reading with LLMs

The entire guidebook is also served under the [llms.txt convention](llm-guide.md) — hand an LLM a single URL and it can read the whole book.
