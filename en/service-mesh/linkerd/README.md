# Linkerd

> **Supported Versions**: Linkerd 2.16+ **Last Updated**: August 17, 2026

### August 2026 Update: edge-26.8.2 — Gateway API 1.5.1 Support

The edge-26.8.2 release, published August 14, 2026, adds Gateway API 1.5.1 support (via linkerd-kubert 0.27.0) and bumps the tested maximum Kubernetes version to 1.36. It also includes stability fixes: removing a duplicate Job informer in the destination controller and making the policy controller exit if its lease watch task dies. See the [release notes](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2) for details.

### July 2026 Update: edge-26.7.1 — Requests to Undefined Service Ports Disallowed

The edge-26.7.1 release, published July 16, 2026, includes a **behavior-changing (breaking) fix**. Previously, if a ServiceProfile was defined for the target service, requests to ports not defined on the Service were still allowed. The destination controller now returns an empty `DestinationProfile` for `GetProfile` requests on ports not defined on the service, causing the proxy to fall back to the client policy API, which correctly returns a Forbidden filter and denies the connection. If any workloads communicate over ports not declared on their Service resources, clean up the port definitions before upgrading. See the [release notes](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1) for details.

## Overview

Linkerd is a CNCF (Cloud Native Computing Foundation) graduated project and a lightweight service mesh solution. Originally developed by Buoyant in 2016, it was the project that first coined the term "service mesh." Linkerd's core values are simplicity, security by default, and minimal resource overhead, making service-to-service communication in Kubernetes environments secure and reliable.

### Core Value Propositions

| Value                   | Description                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| **Simplicity**          | Sensible defaults that work out of the box without complex configuration |
| **Security by Default** | Automatic mTLS encryption without any configuration                      |
| **Lightweight**         | Micro-proxy written in Rust with minimal resource usage (\~10MB memory)  |
| **Fast Performance**    | Less than 1ms p99 latency overhead                                       |
| **Operational Ease**    | Simple upgrades and intuitive debugging tools                            |

## Linkerd Architecture Overview

![Diagram showing how Linkerd's control plane components (Destination, Identity, Proxy Injector) configure and secure the linkerd-proxy sidecars injected into application pods, which exchange traffic over mutual TLS, while the Viz extension observes both proxies.](../../.gitbook/assets/en-service-mesh-linkerd-README-0.png)

## Service Mesh Comparison

Compare Linkerd, Istio, and Cilium Service Mesh to understand the characteristics of each solution.

| Feature                | Linkerd               | Istio                  | Cilium Service Mesh     |
| ---------------------- | --------------------- | ---------------------- | ----------------------- |
| **Proxy**              | linkerd2-proxy (Rust) | Envoy (C++)            | eBPF + Envoy (optional) |
| **Resource Usage**     | Very Low (\~10MB)     | High (\~50-100MB)      | Low (eBPF mode)         |
| **Latency Overhead**   | <1ms p99              | 2-5ms p99              | <1ms (eBPF mode)        |
| **Complexity**         | Low                   | High                   | Medium                  |
| **mTLS**               | Automatic (default)   | Configuration required | Configuration required  |
| **Traffic Management** | Basic (SMI)           | Very Rich              | Basic                   |
| **Observability**      | Good (built-in)       | Excellent              | Good (Hubble)           |
| **Multi-cluster**      | Service Mirroring     | Complex setup          | ClusterMesh             |
| **CNI Integration**    | Separate              | Separate               | Native                  |
| **CNCF Status**        | Graduated             | Graduated              | Graduated               |
| **Learning Curve**     | Gentle                | Steep                  | Medium                  |
| **Community**          | Active                | Very Active            | Active                  |

## When to Choose Linkerd

### Suitable Use Cases

1. **When Simplicity Matters**
   * When basic service mesh capabilities are needed over complex traffic management features
   * Small operations teams or teams with limited service mesh experience
   * When fast adoption and low learning curve are priorities
2. **When Resource Efficiency is Critical**
   * Environments running many Pods per node
   * When sidecar overhead needs to be minimized
   * Latency-sensitive applications
3. **When Security Should Be the Default**
   * When automatic mTLS without configuration is needed
   * Zero-trust network implementation
   * Encryption requirements for compliance
4. **When Operational Simplicity is Required**
   * Preference for simple upgrade processes
   * Minimal CRDs and configuration
   * Intuitive CLI tooling

### Less Suitable Use Cases

1. **Advanced Traffic Management Needs**
   * Complex routing rules, header manipulation
   * Advanced load balancing algorithms
   * Extensive protocol support (beyond gRPC)
2. **VM Workload Integration**
   * Integration with workloads outside Kubernetes
   * Mixed VM and container environments
3. **Large-scale Multi-protocol Environments**
   * Need for various protocol support (Kafka, MongoDB, etc.)
   * Complex Wasm extension requirements

## Documentation Structure

This section covers Linkerd's main features and operational methods:

| Document                                       | Description                                                                         |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Installation and Setup](01-installation.md)   | CLI installation, control plane installation, HA configuration, extensions          |
| [Architecture](02-architecture.md)             | Control plane, data plane, certificate hierarchy details                            |
| [Traffic Management](03-traffic-management.md) | ServiceProfile, TrafficSplit, retries, timeouts, canary deployments                 |
| [Security](04-security.md)                     | mTLS, authorization policies, certificate management, external CA integration       |
| [Observability](05-observability.md)           | Metrics, dashboards, CLI tools, Prometheus/Grafana integration, distributed tracing |
| [Multi-cluster](06-multi-cluster.md)           | Service mirroring, cluster linking, failover                                        |
| [Best Practices](07-best-practices.md)         | Production checklist, performance tuning, troubleshooting                           |

## Quick Start

### 1. Install Linkerd CLI

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$HOME/.linkerd2/bin:$PATH

# Verify installation
linkerd version
```

### 2. Pre-flight Cluster Validation

```bash
# Verify cluster meets Linkerd requirements
linkerd check --pre
```

### 3. Install Linkerd

```bash
# Install CRDs
linkerd install --crds | kubectl apply -f -

# Install control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

### 4. Add Application to Mesh

```bash
# Enable automatic injection for namespace
kubectl annotate namespace my-app linkerd.io/inject=enabled

# Restart existing deployments to inject proxy
kubectl rollout restart deployment -n my-app

# Or manually inject
kubectl get deploy -n my-app -o yaml | linkerd inject - | kubectl apply -f -
```

### 5. Install and Access Dashboard

```bash
# Install Viz extension
linkerd viz install | kubectl apply -f -

# Open dashboard
linkerd viz dashboard
```

## Checking Linkerd Component Status

```bash
# Full status check
linkerd check

# Control plane status
linkerd check --proxy

# Data plane proxy status
linkerd viz stat deploy -n my-app

# Real-time traffic monitoring
linkerd viz tap deploy/my-app -n my-app
```

## Core Concepts

### Data Plane Proxy

Linkerd injects a sidecar container called `linkerd-proxy` into each Pod. This proxy:

* Written in Rust for memory safety and high performance
* Uses only \~10MB of memory
* Adds less than 1ms latency
* Handles all inbound/outbound traffic
* Automatically applies mTLS encryption

### Service Discovery

The Destination component monitors Kubernetes services and provides endpoint information to proxies:

* Real-time endpoint updates
* ServiceProfile-based routing information
* Traffic split policy distribution

### Automatic mTLS

Linkerd automatically encrypts all mesh traffic without configuration:

1. Identity component issues certificates to each proxy
2. Mutual TLS authentication between proxies
3. Automatic certificate renewal (24-hour default)

## Next Steps

1. [**Installation and Setup**](01-installation.md): Detailed guide on installing Linkerd in your cluster
2. [**Architecture**](02-architecture.md): Understanding Linkerd's internal structure
3. [**Quizzes**](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/service-mesh/linkerd/README.md): Test your knowledge

## References

* [Linkerd Official Documentation](https://linkerd.io/2/overview/)
* [Linkerd GitHub](https://github.com/linkerd/linkerd2)
* [CNCF Linkerd Project Page](https://www.cncf.io/projects/linkerd/)
* [Linkerd Slack Community](https://slack.linkerd.io/)
* [Buoyant Blog](https://buoyant.io/blog)
