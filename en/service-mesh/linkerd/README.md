# Linkerd

> **Reviewed**: September 11, 2026 · Public CLI examples checked with edge-26.9.1

The upstream project publishes edge artifacts; stable distributions and their support lifecycle come from vendors. Linkerd 2.20 is a feature milestone, not a universal version string for the downloaded CLI. Choose an exact distribution/release and check its Kubernetes and Gateway API compatibility. The current public example here is edge-26.9.1, published September 4, 2026; it fixes remote-credential exec-auth-provider acceptance in multicluster and retryable destination-IP conflict handling. See the [release](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1) and [release model](https://linkerd.io/releases/).

The following entries preserve historical release context. The edge-26.8.2 tested Kubernetes maximum does not automatically extend a stable vendor distribution's support matrix.

### August 2026 Update: edge-26.8.4

The edge-26.8.4 release, published August 25, 2026, guards against a nil ExternalWorkload in opaque protocol handling, makes the policy controller negotiate the TLSRoute API version with the cluster, and bumps Go to 1.26.7. See the [release notes](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4) for details.

### August 2026 Update: edge-26.8.2 — Gateway API 1.5.1 Support

The edge-26.8.2 release, published August 14, 2026, adds Gateway API 1.5.1 support (via linkerd-kubert 0.27.0) and bumps the tested maximum Kubernetes version to 1.36. It also includes stability fixes: removing a duplicate Job informer in the destination controller and making the policy controller exit if its lease watch task dies. See the [release notes](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2) for details.

### July 2026 Update: edge-26.7.1 — Requests to Undefined Service Ports Disallowed

The GitHub release for edge-26.7.1 was published July 21, 2026. It includes a behavior-changing fix that rejects requests to ports not declared by the destination Service even when a ServiceProfile exists. Check actual Service port declarations before upgrading. The release also adds a Gateway API installation check. See the [release notes](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1).

## Overview

Linkerd is a CNCF graduated service mesh with a Rust data-plane proxy. CNCF records its first commit in 2016 and graduation in 2021. Evaluate its operational model, protocol support and resource usage against the actual workload rather than treating “simple” or “lightweight” as a guarantee.

### Core Value Propositions

| Capability | What to verify |
|---|---|
| Default workload mTLS | Both peers are meshed and traffic is not bypassing the proxy; unmeshed plaintext needs explicit authorization policy |
| Rust proxy | Memory/CPU requests, limits and usage at expected connections and traffic |
| HTTP/gRPC routing | Supported Gateway API types, attachment and protocol detection |
| Operations | Certificate lifecycle, HA, upgrade compatibility and extension ownership |
| Performance | Workload-specific latency/error/load measurements; no universal 10MB or sub-millisecond promise |

## Linkerd Architecture Overview

| Component | Role |
|---|---|
| Destination and policy controllers | Discover endpoints and distribute routing/authorization policy to proxies |
| Identity | Validate identity requests and issue short-lived workload certificates using configured trust credentials |
| Proxy Injector | Mutate eligible newly created Pods to add the proxy |
| linkerd-proxy | Intercept configured TCP traffic, authenticate/encrypt eligible mesh paths and provide supported L7 behavior |
| Optional extensions/backends | Viz metrics/dashboard, multicluster integration and separately configured trace collection/storage |

This architecture does not imply a fixed memory footprint or latency overhead. Measure those properties for the selected workload and configuration.

## Service Mesh Comparison

| Aspect | Linkerd | Istio | Cilium |
|---|---|---|---|
| Data plane | Rust sidecars | Envoy sidecars or ztunnel plus waypoints | eBPF networking with Envoy for supported L7 functions |
| HTTP routing | Gateway API routes; ServiceProfiles remain supported for earlier workflows | Istio APIs or supported Gateway API attachment | Gateway API and Cilium policy/controller features |
| Security | Automatic mTLS between eligible meshed TCP peers; authorization controls other sources | Auto mTLS, inbound enforcement and authorization are distinct controls | Peer authentication and payload encryption must be evaluated separately |
| Observability | Proxy metrics plus configured Viz/other backends | Mode-specific telemetry plus configured backends | Hubble and configured L7/metrics backends |
| Multicluster | Mirroring/federation and explicit trust/network setup | Supported topology-specific mesh configurations | ClusterMesh and its platform/network requirements |
| Selection | Test required features and operations | Test required features and operations | Test required features and operations |

SMI TrafficSplit is a legacy workflow, not the complete description of current Linkerd routing. Linkerd can route HTTP/gRPC by request properties through Gateway API. Fixed memory, p99 and staffing/complexity rankings are not comparable without a reproducible workload and versioned measurement.

## When to Choose Linkerd

Linkerd is a candidate when its default Kubernetes integration, workload identity and supported HTTP/gRPC/TCP behavior fit the application's needs. Benchmark resource efficiency and latency under realistic load, and plan CA rotation, access policy and upgrades. Automatic transport encryption alone is not a complete zero-trust or compliance program.

Validate the exact required routing/filter/extensibility features before choosing a mesh. Non-HTTP protocols can be proxied as TCP; this does not give them HTTP-level routing or metrics. Server-first/idle connections may need opaque-port or appProtocol configuration, and application-originated TLS remains opaque to HTTP inspection. Opaque traffic still traverses the proxy; skipped ports bypass it.

VM and physical-machine integration is available through [mesh expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/), including ExternalWorkload registration and an external identity/bootstrap path. It is not categorically unsupported. Network reachability, DNS, proxy installation and trust design add requirements beyond ordinary Pod injection; the upstream tutorial's bootstrap shortcuts are not a production design.

## Documentation Structure

| Document | Description |
|---|---|
| [Installation and Setup](01-installation.md) | Exact release/compatibility, CLI/Helm, trust credentials, HA and extensions |
| [Architecture](02-architecture.md) | Controllers, proxies and certificate hierarchy |
| [Traffic Management](03-traffic-management.md) | Gateway API, legacy ServiceProfiles, retries/timeouts and traffic splitting |
| [Security](04-security.md) | mTLS boundaries, authorization and CA rotation |
| [Observability](05-observability.md) | Metrics, Viz, external backends and tracing |
| [Multi-cluster](06-multi-cluster.md) | Mirroring/federation, network paths, trust and credentials |
| [Best Practices](07-best-practices.md) | Operational validation, performance and troubleshooting |

## Quick Start

### 1. Select the CLI and prerequisites

Follow the [installation guide](01-installation.md) for the chosen OS/architecture and exact release. Verify that the CLI output matches the intended distribution; do not assume an unpinned installer produces an older stable version. Gateway API CRDs are a prerequisite, and the installed bundle must be compatible with every controller using it.

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. Render, review and install

For a new controlled lab with the selected CLI and prerequisites, the CLI renders manifests:

```bash
set -euo pipefail
linkerd install --crds > linkerd-crds.yaml
# Review CRD ownership/version before applying.
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
# Review trust credentials and deployment settings before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

The default CLI setup generates trust credentials with a finite lifetime. It is not a ready-made shared-trust multicluster setup. For repeatable long-lived installations, follow the documented Helm/CA lifecycle process. This review checked offline rendering and CLI syntax, not a live installation.

### 3. Add the intended application

For an existing selected namespace and Deployment, replace both my-app names with the actual targets:

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

Review an existing conflicting annotation rather than overwriting it automatically. Only new Pods receive injection, and a rolling restart needs the workload's readiness/capacity safeguards. Manual injection can instead operate on the reviewed application manifest; do not round-trip every live Deployment through inject/apply as a blanket fix.

### 4. Add Viz if needed

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz is optional and needs its own lifecycle. Its default metrics setup is not a universal production retention/HA design.

## Checking Linkerd Component Status

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap observes supported HTTP request events; it is not a proof of every TCP path, packet or encryption boundary.

## Core Concepts

### Data Plane Proxy

The Rust linkerd-proxy runs alongside enrolled workloads. It processes configured TCP paths; skip ports, unmeshed endpoints and platform restrictions must be checked separately. HTTP-level behavior requires visible/detected HTTP. Measure resource usage and latency rather than assuming a constant per-Pod footprint.

### Service Discovery

Destination and policy components watch Service/endpoint state and provide routing information. ServiceProfiles and Gateway API are distinct configuration paths with version-specific precedence and feature support. Ensure every intended Service port is declared; see the historical breaking-change note above.

### Automatic mTLS

The documented default workload certificate lifetime is 24 hours with automatic renewal. The identity is tied to the Pod's ServiceAccount, not a unique identity for every Pod. Trust anchors and issuer credentials have separate lifecycles; default CLI-generated credentials expire after a year and need planned rotation.

Meshed TCP peers use mTLS, but traffic to/from unmeshed peers and skipped ports is outside that automatic guarantee. The default inbound policy accepts unmeshed plaintext; use authorization policy when that must be rejected. Shared trust and explicit connectivity are required for multicluster communication.

## Next Steps

1. [Installation and Setup](01-installation.md)
2. [Architecture](02-architecture.md)
3. [Installation Quiz](../../quizzes/service-mesh/linkerd/installation.md), [Architecture Quiz](../../quizzes/service-mesh/linkerd/architecture.md), [Traffic Quiz](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [Security Quiz](../../quizzes/service-mesh/linkerd/security.md), [Observability Quiz](../../quizzes/service-mesh/linkerd/observability.md), [Multicluster Quiz](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## References

- [Linkerd documentation](https://linkerd.io/docs/overview/)
- [Release tracks](https://linkerd.io/releases/) and [installation](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/) and [request routing](https://linkerd.io/docs/features/request-routing/)
- [Automatic mTLS and caveats](https://linkerd.io/docs/features/automatic-mtls/) and [TCP/protocol handling](https://linkerd.io/docs/features/protocol-detection/)
- [CNCF project record](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2), [community](https://slack.linkerd.io/), [Buoyant blog](https://buoyant.io/blog)
