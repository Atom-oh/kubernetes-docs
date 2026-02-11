# Cilium Deep Dive: The Future of Cloud Native Networking

## Overview

This section provides a comprehensive understanding of Cilium's core concepts and technologies. We will explore Cilium's architecture, eBPF technology, networking models, security features, and more in depth.

> **Supported Versions**: Cilium 1.18
> **Kubernetes Compatibility**: 1.32 and above
> **Last Updated**: November 24, 2025

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

### Table of Contents

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
