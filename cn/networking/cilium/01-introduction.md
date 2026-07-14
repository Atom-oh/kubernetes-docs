# 第 1 部分：简介

> **支持版本**：Cilium 1.18 **最后更新**：February 23, 2026

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 必需工具

* kubectl v1.33 或更高版本
* Helm v3.12 或更高版本
* 可正常运行的 Kubernetes 集群（EKS、minikube、kind 等）
* Linux kernel 4.19 或更高版本（支持 eBPF 功能）

### 安装 Cilium

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status
```

## 什么是 Cilium？

Cilium 是一款开源软件，它利用 Linux kernel 中强大的 eBPF 技术，为容器化应用程序提供网络、安全性和可观测性。它旨在为 Kubernetes、Docker 和 Mesos 等容器编排平台提供网络、安全性和可观测性。

### 主要功能：

* **基于 eBPF**：通过 kernel 内可编程的数据路径提供高性能网络和安全能力
* **API 感知网络**：支持 L3-L7 层的 API 感知网络安全策略
* **Kubernetes 集成**：提供 Kubernetes CNI（Container Network Interface）实现
* **分布式负载均衡**：为 Service 间通信提供高效的分布式负载均衡
* **网络可见性**：通过 Hubble 进行网络流监控和故障排除
* **多集群支持**：支持跨集群网络和安全策略
* **Kubernetes 兼容性**：完全兼容 Kubernetes 1.32 及更高版本
* **增强的 BGP 支持**：通过 Cilium 1.18 改进的 BGP 控制平面提供更灵活的路由配置
* **增强的可观测性**：借助改进的指标和追踪能力获得更深入的洞察

### Cilium 架构

## 容器网络基础

容器网络提供使容器化应用程序能够相互通信并与外部世界通信的机制。

### 容器网络模型：

1. **Host Network**：容器共享宿主机的网络命名空间
2. **Bridge Network**：容器连接到宿主机内的虚拟网桥
3. **Overlay Network**：在多个宿主机之间创建虚拟网络
4. **Underlay Network**：直接利用物理网络基础设施

### 容器网络挑战：

* **可扩展性**：支持数千个容器和 Service
* **性能**：最小化延迟并最大化吞吐量
* **安全性**：保护微服务之间的通信
* **可观测性**：监控网络流并进行故障排除
* **可移植性**：在各种环境中提供一致的网络体验

## 理解 CNI（Container Network Interface）

> **核心概念**：CNI（Container Network Interface）是一个 CNCF 项目，它定义了容器运行时与网络插件之间的标准接口。

### CNI 的主要组件：

* **插件架构**：可集成各种网络解决方案的模块化设计
* **网络配置**：以 JSON 格式定义的网络设置
* **IPAM（IP Address Management）**：IP 地址分配和管理
* **标准 API**：在添加或删除容器时用于网络设置的标准 API

### 主要 CNI 插件对比：

| 功能                         | Cilium                    | Calico         | Flannel        | AWS VPC CNI            |
| ---------------------------- | ------------------------- | -------------- | -------------- | ---------------------- |
| **基础技术**                 | eBPF                      | iptables/IPVS  | VXLAN/host-gw  | AWS ENI                |
| **网络策略**                 | L3-L7                     | L3-L4          | 有限           | AWS Security Groups    |
| **加密**                     | IPsec/WireGuard           | IPsec          | 无             | 无                     |
| **可观测性**                 | Hubble                    | Flow Logs      | 有限           | VPC Flow Logs          |
| **Service Mesh**             | 内置                      | 需要 Istio     | 需要 Istio     | 需要 Istio/AppMesh     |
| **性能**                     | 非常高                    | 高             | 中             | 高                     |
| **IPAM**                     | Cluster Pool, CRD         | IPAM Plugin    | Host Subnet    | AWS IPAM               |
| **Kubernetes 兼容性**        | 1.32+                     | 1.29+          | 1.28+          | 1.29+                  |
| **BGP 支持**                 | 增强的控制平面（v1.18+）  | 有限           | 无             | VPC Routing            |

* **Weave Net**：多宿主机容器网络
* **AWS VPC CNI**：与 AWS VPC 的直接集成

## Cilium 的差异化功能

与其他 CNI 解决方案相比，Cilium 提供多项独特优势。

### 技术差异化：

* **eBPF 利用**：通过 kernel 内可编程的数据路径实现高性能和灵活性
* **API 感知网络**：支持最高到 L7 层的网络策略
* **XDP（eXpress Data Path）**：数据包处理性能优化
* **Kube-proxy 替代**：更高效的 Service 负载均衡
* **Hubble 集成**：强大的网络可观测性工具
* **最新 Kubernetes 兼容性**：完全兼容 Kubernetes 1.32 及更高版本

### 按使用场景划分的优势：

* **微服务架构**：细粒度网络策略和可观测性
* **多集群部署**：跨集群的无缝网络连接
* **以安全为重点的环境**：强大的网络安全策略
* **高性能需求**：优化的数据路径
* **Service Mesh 集成**：与 Istio 等 Service Mesh 集成

## 实验：Cilium 安装和基本配置

```bash
# Install Cilium CLI on Kubernetes cluster
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

### 应用基本网络策略：

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
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
```

[返回主页](./)

## 测验

要检验您在本章中所学的内容，请尝试[主题测验](../../quizzes/networking/cilium/01-introduction-quiz.md)。
