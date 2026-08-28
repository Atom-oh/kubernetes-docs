# Cilium Deep Dive: The Future of Cloud Native Networking

## Overview

This section provides a comprehensive understanding of Cilium's core concepts and technologies. We will explore Cilium's architecture, eBPF technology, networking models, security features, and more in depth.

> **Supported Versions**: Cilium 1.17, 1.18
> **Kubernetes Compatibility**: 1.32 and above
> **Last Updated**: August 24, 2026

### July 2026 Update: Patch Releases and a NetworkPolicy Security Issue

On July 16, 2026, the Cilium 1.19.6, 1.18.12, and 1.17.18 patch releases were published. Alongside new support for configuring Gateway API access logs (`spec.telemetry.accessLogs` in `CiliumGatewayClassConfig`), they fix a regression that could briefly drop established connections during agent restart/upgrade and a ClusterMesh bug where the `service.cilium.io/affinity: "none"` annotation caused a traffic blackhole.

Also note the **CVE-2026-56743** security issue: in Cilium 1.19.0-1.19.4 with a non-default `clusterName`, a Kubernetes NetworkPolicy using only `ipBlock` rules (no pod/namespace selectors) could unintentionally allow traffic from other workloads in the same namespace. Upgrade to 1.19.5 or later. See the [security advisory](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) for details.

On July 21, 2026, [Cilium 1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) was published — the second release candidate for the upcoming 1.20 minor release, following rc.0 on July 14.

### August 2026 Update: Cilium 1.20.0 GA

On July 29, 2026, [Cilium 1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) was released — over 2,660 new commits from 1,100+ contributors. Highlights:

- **Gateway API v1.6.1**: support for the newly GA'd TCPRoute/UDPRoute, `BackendTLSPolicy` for TLS to backends, ListenerSets for delegated listener management, an `ExternalAuth` filter (GEP-1494), and native CORS support
- **Networking**: datapath plugins for extending the eBPF datapath without forking, automatic netkit selection (`bpf.datapathMode=auto`), and IPv6 egress gateway IPs for dual-stack clusters
- **IPAM**: IPv6 for AWS ENI IPAM (Beta), and in-place migration from cluster-pool to multi-pool IPAM
- **Services/ClusterMesh**: `PreferSameZone`/`PreferSameNode` traffic distribution, weighted Maglev backends via the `service.cilium.io/weight` annotation, and stable Multi-Cluster Services (MCS) API support
- **Security**: Kubernetes ClusterNetworkPolicy (KCNP) support with Admin/Baseline tiers, ztunnel identity via internal CA or SPIRE, and a new `cluster-mesh` policy entity
- **Performance**: the `cilium-cni` binary shrank from ~77 MB to 16 MB, plus aggregated load-balancer state and optimized BPF policy-map encoding for large clusters

Take action during upgrade if you use legacy Mutual Authentication, Envoy Go extensions, Kafka-aware policies, the `cilium.io/v2alpha1` `CiliumNodeConfig` API, the libnetwork integration, or a custom CNI configuration — see the [upgrade guide](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes). The first pre-release of the next cycle, 1.21.0-pre.0, followed on August 3.

### August 2026 Update: 1.20.1 / 1.19.7 / 1.18.13 Patch Releases

On August 18, 2026, coordinated patch releases went out for the three maintained lines. [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1), the first patch on the 1.20 line, carries a Cluster Mesh documentation overhaul and backported bug fixes since 1.20.0; [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) backports VRRP and IGMP protocol support in the host firewall; and [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) adds incremental synchronization of Envoy resources (listeners, network policies, etc.), reducing CPU load and policy update latency. Updating to the latest patch on your line is recommended.

## Key Improvements in Cilium 1.18

Cilium 1.18 delivers the following major feature improvements and new capabilities:

### Networking Improvements
- **Enhanced BGP Control Plane**: More flexible and scalable BGP configuration
- **Improved Multi-cluster Routing**: Optimized inter-cluster communication performance
- **Enhanced Service Mesh Integration**: Better integration with Envoy proxy

### Security Enhancements
- **Enhanced Network Policies**: Finer-grained policy control and performance improvements
- **Improved Encryption Options**: Optimized WireGuard and IPsec encryption performance

### Observability Improvements
- **Hubble Improvements**: Richer metrics and tracing information
- **Enhanced Prometheus Integration**: New metrics and dashboards
- **Improved Flow Logging**: More detailed network flow information

### Performance Optimizations
- **eBPF Program Optimization**: Faster packet processing
- **Memory Usage Improvements**: Better resource efficiency in large-scale clusters
- **CPU Usage Optimization**: Lower overhead

## Introduction

Cilium is an open source networking, security, and observability solution for Linux container management platforms such as Kubernetes, Docker, and Mesos. Cilium is based on eBPF (extended Berkeley Packet Filter) technology, providing more powerful and efficient networking and security features than traditional Linux networking approaches.

### What is eBPF?

eBPF is a technology that acts like a sandboxed virtual machine within the Linux kernel, allowing programs to be safely executed within the kernel without modifying kernel code. This enables efficient execution of various tasks such as network packet processing, system call monitoring, and performance analysis.

Key characteristics of eBPF:
- High performance through kernel space execution
- Native performance through JIT (Just-In-Time) compilation
- Safe execution environment (program verification through verifier)
- Dynamic loading and unloading possible

### Key Benefits of Cilium

1. **High-Performance Networking**: Efficient packet processing using eBPF
2. **Granular Network Policies**: L3-L7 level network policy support
3. **Transparent Encryption**: Transparent IPsec or WireGuard encryption between nodes
4. **Load Balancing**: XDP (eXpress Data Path) based high-performance load balancing
5. **Observability**: Network flow visibility through Hubble
6. **Service Mesh**: L7 traffic management without existing sidecars
7. **Multi-Cluster Networking**: Transparent connectivity between clusters
8. **BGP Support**: Integration with external networks

### Comparison with Existing CNIs

| Feature | Cilium | Calico | Flannel | AWS VPC CNI |
|---------|--------|--------|---------|-------------|
| Network Model | eBPF | iptables/IPVS | VXLAN/host-gw | AWS ENI |
| Network Policies | L3-L7 | L3-L4 | Limited | AWS Security Groups |
| Encryption | IPsec/WireGuard | IPsec | None | None |
| Observability | Hubble | Flow Logs | Limited | VPC Flow Logs |
| Service Mesh | Built-in | Requires Istio | Requires Istio | Requires Istio/AppMesh |
| Performance | Very High | High | Medium | High |
| Multi-Cluster | Built-in | Limited | None | Requires Transit Gateway |

## Architecture

Cilium consists of a data plane based on eBPF and a control plane integrated with Kubernetes.

![The Cilium Agent runs on every node and is managed by the Cilium Operator (fronted by the Cilium API Server); the Agent loads eBPF programs into the kernel and reports metrics to the Hubble Server, which the Hubble Relay aggregates cluster-wide for the Hubble UI to visualize.](../../.gitbook/assets/en-networking-cilium-README-0.png)

### Key Components

1. **Cilium Agent**: Runs on each node, loads and manages eBPF programs
2. **Cilium Operator**: Manages cluster-level resources and operations
3. **eBPF Programs**: Loaded into kernel for packet processing and policy enforcement
4. **Hubble**: Provides network flow monitoring and observability
5. **Cilium CLI**: Command-line tool for Cilium and Hubble management

### Networking Models

Cilium supports multiple networking modes:

1. **Direct Routing**: Direct routing between nodes (BGP or static routing)
2. **Tunneling**: Overlay networking through VXLAN or Geneve tunnels
3. **AWS ENI**: Utilizing Elastic Network Interface (ENI) on Amazon EKS
4. **Azure IPAM**: Utilizing Azure IPAM on Azure AKS

### Packet Flow

How packets are processed in Cilium:

1. Packet arrives at network interface
2. eBPF XDP program performs initial processing (DDoS defense, load balancing)
3. eBPF TC (Traffic Control) program applies network policies
4. Packet is delivered to container network namespace
5. Response packets are processed through similar path

## Integration with Amazon EKS

There are two main ways to use Cilium on Amazon EKS:

1. **Install as Amazon EKS Add-on**: Amazon EKS provides Cilium as a managed add-on.
2. **Manual Installation**: Install directly using Helm chart.

### Installing as Amazon EKS Add-on

```bash
# Install Cilium add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name cilium \
  --addon-version v1.17.0-eksbuild.1 \
  --service-account-role-arn arn:aws:iam::123456789012:role/AmazonEKSCiliumAddonRole

# Check add-on status
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name cilium
```

### Manual Installation with Helm

```bash
# Add Cilium Helm repository
helm repo add cilium https://helm.cilium.io/

# Update Helm repository
helm repo update

# Install Cilium
helm install cilium cilium/cilium \
  --version 1.17.0 \
  --namespace kube-system \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled
```

### EKS-Specific Configuration Options

Key configuration options to consider when using Cilium with EKS:

1. **ENI Mode**: Leverage native AWS networking performance using AWS Elastic Network Interface
2. **IPAM Mode**: Integration with AWS VPC IP address management
3. **Encryption**: Inter-node traffic encryption (WireGuard or IPsec)
4. **NodeLocal DNSCache**: DNS performance improvement
5. **Hubble**: Enable network observability

### ENI Mode Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-endpoint-routes: "true"
  auto-create-cilium-node-resource: "true"
  ipam: "eni"
  eni-tags: "{\"Owner\": \"Cilium\"}"
  tunnel: "disabled"
  enable-ipv4: "true"
  enable-ipv6: "false"
  egress-masquerade-interfaces: "eth0"
```

### Installing Cilium on EKS Cluster

#### Installing Cilium on Existing EKS Cluster

```bash
# Remove AWS CNI
kubectl delete daemonset -n kube-system aws-node

# Install Cilium
cilium install --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled
```

#### Creating New EKS Cluster with Cilium CNI

```bash
eksctl create cluster --name cilium-cluster \
  --without-nodegroup

eksctl create nodegroup --cluster cilium-cluster \
  --node-ami-family AmazonLinux2 \
  --node-type m5.large \
  --nodes 3 \
  --max-pods-per-node 110

# Install Cilium
cilium install --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled
```

### EKS Cluster Interconnection

EKS cluster interconnection using Cilium Cluster Mesh:

```bash
# On cluster 1
cilium clustermesh enable --service-type LoadBalancer

# On cluster 2
cilium clustermesh enable --service-type LoadBalancer

# Connect clusters
cilium clustermesh connect --context cluster1 --destination-context cluster2
```

## Installation and Configuration

### Prerequisites

- Kubernetes cluster (v1.16 or higher)
- Linux kernel 4.9 or higher (recommended: 5.4 or higher)
- kubectl configured
- Helm (optional)

### Install Cilium CLI

```bash
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz
```

### Configuration Options

#### Networking Mode Configuration

Direct routing mode:
```bash
cilium install --set tunnel=disabled --set autoDirectNodeRoutes=true
```

VXLAN mode:
```bash
cilium install --set tunnel=vxlan
```

#### kube-proxy Replacement Configuration

Full replacement mode:
```bash
cilium install --set kubeProxyReplacement=strict
```

#### Encryption Configuration

WireGuard encryption:
```bash
cilium install --set encryption.enabled=true --set encryption.type=wireguard
```

IPsec encryption:
```bash
cilium install --set encryption.enabled=true --set encryption.type=ipsec
```

## Network Policies

Cilium extends the Kubernetes NetworkPolicy API to provide granular network policies at L3-L7 levels.

### Basic Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### Cilium Network Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-specific-http-methods
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/products"
```

### FQDN-Based Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-specific-domains
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.amazonaws.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

## Observability with Hubble

Hubble is Cilium's observability layer, enabling visualization and analysis of network flow data collected through eBPF.

### Installing Hubble

```bash
cilium hubble enable --ui
```

### Observing Network Flows

```bash
# Observe all flows
hubble observe

# Observe flows in specific namespace
hubble observe --namespace app

# Observe HTTP requests
hubble observe --protocol http

# Observe flows between pods with specific labels
hubble observe --from-label app=frontend --to-label app=backend

# Observe failed connections
hubble observe --verdict DROPPED
```

### Prometheus Integration

```bash
cilium hubble enable --metrics="{dns:query;ignoreAAAA,drop:sourceContext=pod;destinationContext=pod,tcp,flow,icmp,http}"
```

## Cilium Testing

```bash
# Basic connectivity test
cilium connectivity test

# Run specific test
cilium connectivity test --test=client-to-echo-service

# Network performance test
cilium connectivity test --test=performance
```

## Best Practices

### Performance Optimization

1. **Kernel Version Optimization**: Use Linux kernel 5.4 or higher
2. **Enable BBR Congestion Control**: Improve network throughput
3. **Enable XDP Acceleration**: Improve packet processing performance
4. **MTU Optimization**: Set MTU appropriate for network environment

```bash
cilium install --set bpf.preallocateMaps=true \
  --set bpf.masquerade=true \
  --set devices=eth0 \
  --set loadBalancer.acceleration=native \
  --set loadBalancer.mode=dsr
```

### Security Hardening

1. **Apply Default Deny Policy**: Only allow explicitly permitted traffic
2. **Enable Encryption**: Encrypt inter-node traffic
3. **Apply Least Privilege Principle**: Design policies to allow only necessary communication

### Improved Observability

```bash
cilium hubble enable --metrics="{dns,drop,tcp,flow,http}"
```

## Troubleshooting

### Connectivity Issues

```bash
# Check Cilium status
cilium status

# Check endpoint status
cilium endpoint list

# Review network policies
kubectl get cnp,ccnp -A

# Analyze flows
hubble observe --verdict DROPPED
```

### Performance Issues

```bash
# Check eBPF map status
cilium bpf maps list

# Monitor system resources
cilium metrics list
```

### Debugging Tools

```bash
# Check status
cilium status --verbose

# Collect environment information
cilium sysdump

# Cilium agent logs
kubectl logs -n kube-system -l k8s-app=cilium
```

## Deep Dive Table of Contents

**[Introduction to Cilium and Basic Concepts](01-introduction.md)**
- Cilium Overview and History
- Container Networking Basics
- Understanding CNI (Container Network Interface)
- Cilium's Differentiating Features

**[eBPF Technology Deep Dive](02-ebpf.md)**
- Introduction to eBPF Technology and History
- How eBPF Works Inside the Kernel
- eBPF Program Types and Maps
- Utilizing eBPF in Cilium

**[Networking Models and VXLAN](03-networking.md)**
- Comparison of Container Networking Models
- VXLAN Technology Deep Dive
- Cilium's Overlay Networking
- Performance Optimization Techniques
- Routing Mechanisms (Encapsulation vs Native-Routing)
- Cloud Provider Networking (AWS ENI, Google Cloud)

**[IPAM and Network Policies](04-ipam-policy.md)**
- IP Address Management (IPAM) Strategies
- Kubernetes and Cilium IPAM Integration
- Network Policy Design and Implementation
- Multi-Cluster Scenarios
- IPAM Mode Deep Dive (Cluster Scope, Kubernetes Host Scope, Multi-Pool)
- Cloud Provider IPAM (Azure IPAM, AWS ENI, GKE)
- CRD-based IPAM

**[L2-L7 Networking and Load Balancing](05-l2-l7-networking.md)**
- Understanding OSI Model Layers (L2, L3, L4, L7)
- Cilium's Layer-specific Features
- Service Mesh Integration
- Load Balancing Architecture
- Masquerading Configuration and Implementation Modes
- IPv4 Fragment Handling

**[Security and Visibility](06-security-visibility.md)**
- Cilium's Security Features
- Network Visibility and Monitoring
- Hubble Architecture and Usage
- Real-time Threat Detection

**[Advanced Topics and Real-World Cases](07-advanced-topics.md)**
- Performance Tuning and Troubleshooting
- Large-Scale Deployment Strategies
- Real-World Use Case Studies
- Future Roadmap and Development Direction

## Additional Resources

- [Networking Concepts Deep Dive](networking-concepts.md)
- [Glossary and Abbreviations](glossary.md)

## References

- [Cilium Official Documentation](https://docs.cilium.io/)
- [Cilium GitHub Repository](https://github.com/cilium/cilium)
- [eBPF Documentation](https://ebpf.io/)
- [Hubble Documentation](https://github.com/cilium/hubble)
- [Cilium Network Policy Editor](https://editor.cilium.io/)
- [AWS EKS Workshop - Cilium](https://www.eksworkshop.com/beginner/115_cilium/)

## Quiz

To test what you've learned in this section, try the [Cilium Deep Dive Quiz](../../quizzes/networking/cilium/01-introduction-quiz.md).
