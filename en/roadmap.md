# Guidebook Roadmap

> **Last Updated**: September 2, 2026

This guidebook tells one continuous story: from the Linux kernel through containers, Kubernetes, Amazon EKS, networking, service mesh, storage, databases, data pipelines, and AI/ML — plus the cross-cutting disciplines of security, GitOps, platform engineering, container registries, observability, and operations. This page is the map, and the recommended paths through it.

![Learning-flow map of the guidebook's fifteen domains, flowing from foundations (Linux/Container) through orchestration (Kubernetes/EKS), connectivity (Networking/Service Mesh), state (Storage/Database), data and AI (Data Pipeline/AI-ML), to cross-cutting concerns (Security/GitOps/Platform/Container Registry/Observability/Operations).](.gitbook/assets/en-roadmap-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-roadmap-0.html)

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
| Data & AI | Data Pipeline | [Data on EKS Overview](data-on-eks/README.md) | Kafka, Spark, Airflow, and Flink deep dives — with a measured Kafka RF3/gp3 ingest ceiling |
| Data & AI | AI/ML | [AI/ML Workloads](ai-ml/01-ai-ml-workloads.md) | vLLM, Ray, Kubeflow, MLflow on EKS |
| Cross-cutting | Security & Policy | [Kyverno](security/01-kyverno-policy-management.md) | AuthN/Z, policy, runtime security, supply chain |
| Cross-cutting | GitOps | [GitOps](gitops/README.md) | ArgoCD, Flux, progressive delivery |
| Cross-cutting | Platform Engineering | [Overview](platform-engineering/00-platform-engineering-overview.md) | ACK, KRO, Crossplane, Backstage |
| Cross-cutting | Container Registry | [Overview](container-registry/README.md) | ECR, Harbor, image supply chain |
| Cross-cutting | Observability | [Overview](observability/README.md) | Metrics, logs, tracing, alerting stacks |
| Cross-cutting | Operations Guide | [Operations Guide](ops/README.md) | Capacity planning, FinOps, upgrades, and a symptom-first [troubleshooting playbook](ops/16-troubleshooting-playbook.md) |

## The measured-benchmark series

Documents built on numbers measured on real AWS resources, not spec sheets:

- [Istio sidecar vs ambient, measured](service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — P50/P99 latency per mTLS data plane and 503 rates during rollouts
- [EBS gp2 vs gp3 Measured Benchmark](storage/01-ebs-gp2-gp3-benchmark.md) — a 10x IOPS gap at the same 100 GiB capacity, and the gp2 burst-credit cliff
- [ClickHouse on EKS Measured Benchmark](database/01-clickhouse-on-eks.md) — 100M-row ingest throughput, compression ratios, query latency
- [Kafka on EKS Measured Benchmark](data-on-eks/kafka/09-kafka-benchmark.md) — RF3 ingest ceiling of ≈130–135 MiB/s (= one gp3 volume's write cap) vs 338 MiB/s at RF1, p99 by acks setting, and cold consumers cutting producer throughput by ~45%
- [Pod Network Benchmark](networking/06-pod-network-benchmark.md) — the 0.040 → 0.339 → 0.544 ms RTT ladder (same node → same AZ → cross-AZ), a 4.96 Gbps single-flow cap regardless of AZ vs 9.94 Gbps with 8 flows, and `ndots:5`'s 10-query/8-NXDOMAIN amplification

## Share a diagram — exports for LinkedIn and talks

Every interactive diagram in this guidebook opens at `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`, and the **Export** button in the viewer toolbar (shortcut `E`) produces share-ready files on the spot. No screenshot tooling — the diagram page is all you need.

### What the Export menu offers

| Group | Menu item | Output | Use it for |
|-------|-----------|--------|-----------|
| Share | **Share Card** / **Copy Share Card** | 1200×630 PNG (download / clipboard) | LinkedIn and X link previews, READMEs, release notes |
| Share | **Route Share Card** | 1200×630 PNG (download only) | Appears only after a Route Probe (`R`) has resolved a path between two nodes |
| Share | **Reach Share Card** | 1200×630 PNG (download only) | Appears only after you trace a node's upstream/downstream reachability from its Semantic Passport |
| Share | **Copy diagram** | Full-diagram PNG to the clipboard | Pasting straight into slides or docs |
| Image | **PNG** / **JPEG** / **WebP** | Full-diagram raster image | PNG when you need lossless, JPEG/WebP when size matters |
| Vector & motion | **SVG** | Dual-theme (light + dark) vector | Slides that stay crisp at any zoom |
| Vector & motion | **WebM** | 6-second recording of the trace animation | A LinkedIn post where the flow actually moves in the feed |

Exports strip all viewer state — the Guide panel, Lens, finder, focus, route, story, camera position, radar, presentation mode, and temporary overlays — leaving only the diagram itself. The Share Card keeps your current theme and visual preset and always contains the complete diagram, uncropped. WebM recording needs a trace-animated diagram and MediaRecorder support in your browser; unsupported browsers say so in the menu.

### The 30-second LinkedIn recipe

1. **Open the diagram** — click the "Open full screen ↗" link under any embedded diagram (on GitBook, "🔍 View interactive diagram").
2. **Check the trace is playing** — the toolbar **Live/Still** toggle should read Live. The motion flowing along the arrows is what the recording captures. Rehearsing a talk? **Presentation stage** (`F`) gives the diagram the whole viewport.
3. **Export → WebM** for a moving post, or **Export → Share Card** for a static 1200×630 preview — WebM shows "Recording 6 seconds of motion…" and then the file downloads.
4. **Post** — upload the WebM as a video or the Share Card as an image, and add the source document's URL. To point at a specific node, path, or story moment, use **Copy link** in the Semantic Passport or Route Probe, or **Copy moment** on a Story Beat (shown only on diagrams that define story chapters), and drop the deep link into a comment or slide.

### The truth boundary

- Exports are **communication assets**. They are not evidence that an architecture was validated, and they do not replace the published HTML or the author's own validation. The Share Card never claims validation.
- A Route Share Card follows only **authored, directed relationships**. It never infers a route from geometry, and it refuses to export a stale or unreachable route.
- A Reach Share Card shows *authored reachability*. Do not present it as impact analysis, blast radius, breakage, or runtime causality.

## Recommended paths

### ① Infrastructure onboarding — "containers to EKS"

Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts (pods/services/storage/configuration) → EKS Cluster Creation → Network Fundamentals. Check yourself with each document's quiz, and work through the [labs](labs/README.md) in parallel.

### ② Platform / SRE — "a cluster you can operate"

EKS operations (upgrades/troubleshooting/resiliency) → Networking (VPC CNI, Cilium) → the Service Mesh comparison guide → Security & Policy → the Observability stack → GitOps → capacity planning and FinOps in the Operations Guide. The measured-benchmark series supplies the evidence this path runs on.

### ③ Data & AI platform — "the stateful world"

Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow). If you need GPUs and scheduling control, add the Custom Scheduler parts under Kubernetes Core Concepts.

## Reading with LLMs

The entire guidebook is also served under the llms.txt convention — hand an LLM a single URL and it can read the whole book. See [Reading with LLMs](llm-guide.md) for the endpoints and usage examples.
