# Linkerd

> **支持版本**: Linkerd 2.16+ **最后更新**: February 22, 2026

## 概述

Linkerd 是一个 CNCF (Cloud Native Computing Foundation) 毕业项目，也是一个轻量级 service mesh（服务网格）解决方案。它最初由 Buoyant 于 2016 年开发，是首个提出“service mesh”这一术语的项目。Linkerd 的核心价值在于简洁、默认安全和极低的资源开销，使 Kubernetes 环境中的服务间通信更加安全可靠。

### 核心价值主张

| 价值                   | 说明                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| **简洁**          | 无需复杂配置即可开箱即用的合理默认设置 |
| **默认安全** | 无需任何配置即可自动进行 mTLS 加密                      |
| **轻量级**         | 使用 Rust 编写的微型代理，资源占用极低（\~10MB 内存）  |
| **高性能**    | p99 延迟开销低于 1ms                                       |
| **易于运维**    | 简单的升级流程和直观的调试工具                            |

## Linkerd 架构概览

```mermaid
graph TB
    subgraph "Control Plane"
        D[Destination<br/>Service Discovery]
        I[Identity<br/>Certificate Issuance]
        P[Proxy Injector<br/>Sidecar Injection]
    end

    subgraph "Data Plane"
        subgraph "Pod A"
            A1[Application]
            AP[linkerd-proxy]
        end
        subgraph "Pod B"
            B1[Application]
            BP[linkerd-proxy]
        end
    end

    subgraph "Extensions"
        V[Viz<br/>Dashboard/Metrics]
        J[Jaeger<br/>Distributed Tracing]
        M[Multicluster<br/>Multi-cluster]
    end

    AP -->|mTLS| BP
    AP --> D
    AP --> I
    P -->|Inject| AP
    P -->|Inject| BP
    V --> AP
    V --> BP
```

## Service Mesh 对比

对比 Linkerd、Istio 和 Cilium Service Mesh，以了解各解决方案的特性。

| 功能                | Linkerd               | Istio                  | Cilium Service Mesh     |
| ---------------------- | --------------------- | ---------------------- | ----------------------- |
| **代理**              | linkerd2-proxy (Rust) | Envoy (C++)            | eBPF + Envoy（可选） |
| **资源使用量**     | 极低（\~10MB）     | 高（\~50-100MB）      | 低（eBPF 模式）         |
| **延迟开销**   | <1ms p99              | 2-5ms p99              | <1ms（eBPF 模式）        |
| **复杂度**         | 低                   | 高                   | 中                  |
| **mTLS**               | 自动（默认）   | 需要配置 | 需要配置  |
| **流量管理** | 基础（SMI）           | 非常丰富              | 基础                   |
| **可观测性**      | 良好（内置）       | 出色              | 良好（Hubble）           |
| **多集群**      | 服务镜像     | 复杂设置          | ClusterMesh             |
| **CNI 集成**    | 独立              | 独立               | 原生                  |
| **CNCF 状态**        | 毕业             | 毕业              | 毕业              |
| **学习曲线**     | 平缓                | 陡峭                  | 中                  |
| **社区**          | 活跃                | 非常活跃            | 活跃                  |

## 何时选择 Linkerd

### 适用场景

1. **注重简洁性时**
   * 相较于复杂的流量管理功能，更需要基础 service mesh 功能时
   * 小型运维团队或 service mesh 经验有限的团队
   * 将快速采用和较低的学习曲线作为优先事项时
2. **资源效率至关重要时**
   * 每个节点运行大量 Pod 的环境
   * 需要将 sidecar 开销降至最低时
   * 对延迟敏感的应用程序
3. **应默认保障安全时**
   * 需要无需配置的自动 mTLS 时
   * 实施零信任网络
   * 满足合规性加密要求
4. **需要简化运维时**
   * 偏好简单的升级流程
   * 尽可能减少 CRD 和配置
   * 需要直观的 CLI 工具

### 不太适用的场景

1. **需要高级流量管理时**
   * 复杂的路由规则、header 操作
   * 高级负载均衡算法
   * 广泛的协议支持（除 gRPC 外）
2. **VM 工作负载集成**
   * 与 Kubernetes 外部工作负载集成
   * 混合 VM 和容器环境
3. **大规模多协议环境**
   * 需要支持多种协议（Kafka、MongoDB 等）
   * 复杂的 Wasm 扩展需求

## 文档结构

本节涵盖 Linkerd 的主要功能和运维方法：

| 文档                                       | 说明                                                                         |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| [安装与设置](01-installation.md)   | CLI 安装、control plane 安装、HA 配置、扩展          |
| [架构](02-architecture.md)             | control plane、data plane、证书层次结构详情                            |
| [流量管理](03-traffic-management.md) | ServiceProfile、TrafficSplit、重试、超时、金丝雀 Deployment                 |
| [安全](04-security.md)                     | mTLS、授权策略、证书管理、外部 CA 集成       |
| [可观测性](05-observability.md)           | 指标、仪表板、CLI 工具、Prometheus/Grafana 集成、分布式追踪 |
| [多集群](06-multi-cluster.md)           | 服务镜像、集群连接、故障转移                                        |
| [最佳实践](07-best-practices.md)         | 生产检查清单、性能调优、故障排除                           |

## 快速开始

### 1. 安装 Linkerd CLI

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$HOME/.linkerd2/bin:$PATH

# Verify installation
linkerd version
```

### 2. 集群预检验证

```bash
# Verify cluster meets Linkerd requirements
linkerd check --pre
```

### 3. 安装 Linkerd

```bash
# Install CRDs
linkerd install --crds | kubectl apply -f -

# Install control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

### 4. 将应用程序添加到 Mesh

```bash
# Enable automatic injection for namespace
kubectl annotate namespace my-app linkerd.io/inject=enabled

# Restart existing deployments to inject proxy
kubectl rollout restart deployment -n my-app

# Or manually inject
kubectl get deploy -n my-app -o yaml | linkerd inject - | kubectl apply -f -
```

### 5. 安装并访问仪表板

```bash
# Install Viz extension
linkerd viz install | kubectl apply -f -

# Open dashboard
linkerd viz dashboard
```

## 检查 Linkerd 组件状态

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

## 核心概念

### Data Plane 代理

Linkerd 会向每个 Pod 注入一个名为 `linkerd-proxy` 的 sidecar 容器。该代理：

* 使用 Rust 编写，兼具内存安全性和高性能
* 仅使用 \~10MB 内存
* 增加的延迟低于 1ms
* 处理所有入站/出站流量
* 自动应用 mTLS 加密

### 服务发现

Destination 组件监控 Kubernetes Service，并向代理提供 endpoint 信息：

* 实时 endpoint 更新
* 基于 ServiceProfile 的路由信息
* 流量拆分策略分发

### 自动 mTLS

Linkerd 无需配置即可自动加密所有 mesh 流量：

1. Identity 组件向每个代理颁发证书
2. 代理之间进行双向 TLS 身份验证
3. 自动续订证书（默认 24 小时）

## 后续步骤

1. [**安装与设置**](01-installation.md): 在集群中安装 Linkerd 的详细指南
2. [**架构**](02-architecture.md): 了解 Linkerd 的内部结构
3. [**测验**](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/service-mesh/linkerd/README.md): 测试你的知识

## 参考资料

* [Linkerd 官方文档](https://linkerd.io/2/overview/)
* [Linkerd GitHub](https://github.com/linkerd/linkerd2)
* [CNCF Linkerd 项目页面](https://www.cncf.io/projects/linkerd/)
* [Linkerd Slack 社区](https://slack.linkerd.io/)
* [Buoyant 博客](https://buoyant.io/blog)
