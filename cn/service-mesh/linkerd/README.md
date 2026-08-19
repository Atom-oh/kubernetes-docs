# Linkerd

> **支持的版本**: Linkerd 2.16+ **最后更新**: August 17, 2026

### 2026 年 8 月更新：edge-26.8.2 — 支持 Gateway API 1.5.1

于 2026 年 8 月 14 日发布的 edge-26.8.2 版本新增了对 Gateway API 1.5.1 的支持（通过 linkerd-kubert 0.27.0），并将经过测试的最高 Kubernetes 版本提升至 1.36。该版本还包括稳定性修复：移除 destination controller 中重复的 Job informer，并使 policy controller 在其 lease watch task 终止时退出。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)。

### 2026 年 7 月更新：edge-26.7.1 — 禁止对未定义 Service 端口发起请求

于 2026 年 7 月 16 日发布的 edge-26.7.1 版本包含一项**会改变行为（破坏兼容性）的修复**。此前，如果为目标 Service 定义了 ServiceProfile，仍允许向该 Service 中未定义的端口发起请求。destination controller 现在会针对 Service 中未定义端口上的 `GetProfile` 请求返回空的 `DestinationProfile`，使 proxy 回退到 client policy API；该 API 会正确返回 Forbidden filter 并拒绝连接。如果有任何 workload 通过其 Service 资源中未声明的端口通信，请在升级前清理端口定义。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)。

## 概述

Linkerd 是一个 CNCF（Cloud Native Computing Foundation）毕业项目，也是轻量级服务网格解决方案。它最初由 Buoyant 于 2016 年开发，是第一个提出“服务网格”这一术语的项目。Linkerd 的核心价值是简洁、默认安全和极低的资源开销，可使 Kubernetes 环境中的服务间通信安全可靠。

### 核心价值主张

| 价值                   | 描述                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| **简洁**          | 无需复杂配置即可开箱即用的合理默认值 |
| **默认安全** | 无需任何配置即可自动启用 mTLS 加密                      |
| **轻量级**         | 使用 Rust 编写的微型 proxy，资源使用量极低（\~10MB 内存）  |
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

## 服务网格对比

比较 Linkerd、Istio 和 Cilium Service Mesh，以了解各解决方案的特点。

| 特性                | Linkerd               | Istio                  | Cilium Service Mesh     |
| ---------------------- | --------------------- | ---------------------- | ----------------------- |
| **Proxy**              | linkerd2-proxy (Rust) | Envoy (C++)            | eBPF + Envoy (optional) |
| **资源使用量**     | 非常低（\~10MB）     | 高（\~50-100MB）      | 低（eBPF 模式）         |
| **延迟开销**   | <1ms p99              | 2-5ms p99              | <1ms（eBPF 模式）        |
| **复杂度**         | 低                   | 高                   | 中                  |
| **mTLS**               | 自动（默认）   | 需要配置 | 需要配置  |
| **流量管理** | 基础（SMI）           | 非常丰富              | 基础                   |
| **可观测性**      | 良好（内置）       | 卓越              | 良好（Hubble）           |
| **多集群**      | Service Mirroring     | 复杂设置          | ClusterMesh             |
| **CNI 集成**    | 独立              | 独立               | 原生                  |
| **CNCF 状态**        | 毕业             | 毕业              | 毕业              |
| **学习曲线**     | 平缓                | 陡峭                  | 中                  |
| **社区**          | 活跃                | 非常活跃            | 活跃                  |

## 何时选择 Linkerd

### 适用场景

1. **注重简洁性时**
   * 相比复杂的流量管理功能，更需要基础服务网格能力时
   * 运维团队规模较小，或团队的服务网格经验有限
   * 优先考虑快速采用和较低学习曲线时
2. **资源效率至关重要时**
   * 每个节点运行大量 Pod 的环境
   * 需要尽量减少 sidecar 开销时
   * 对延迟敏感的应用程序
3. **应默认提供安全性时**
   * 需要无需配置即可自动启用 mTLS 时
   * 实现零信任网络
   * 满足合规性的加密要求
4. **需要简化运维时**
   * 偏好简单的升级流程
   * 尽可能少的 CRD 和配置
   * 直观的 CLI 工具

### 不太适用的场景

1. **需要高级流量管理时**
   * 复杂路由规则、header 操作
   * 高级负载均衡算法
   * 广泛的协议支持（超出 gRPC 的范围）
2. **VM workload 集成**
   * 与 Kubernetes 外部 workload 集成
   * 混合 VM 和容器环境
3. **大规模多协议环境**
   * 需要支持多种协议（Kafka、MongoDB 等）
   * 复杂的 Wasm 扩展需求

## 文档结构

本节涵盖 Linkerd 的主要功能和运维方法：

| 文档                                       | 描述                                                                         |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| [安装和设置](01-installation.md)   | CLI 安装、control plane 安装、HA 配置、扩展          |
| [架构](02-architecture.md)             | control plane、data plane、证书层级结构详情                            |
| [流量管理](03-traffic-management.md) | ServiceProfile、TrafficSplit、重试、超时、金丝雀 Deployment                 |
| [安全](04-security.md)                     | mTLS、授权策略、证书管理、外部 CA 集成       |
| [可观测性](05-observability.md)           | 指标、dashboard、CLI 工具、Prometheus/Grafana 集成、分布式追踪 |
| [多集群](06-multi-cluster.md)           | Service 镜像、集群连接、故障转移                                        |
| [最佳实践](07-best-practices.md)         | 生产环境检查清单、性能调优、故障排除                           |

## 快速开始

### 1. 安装 Linkerd CLI

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$HOME/.linkerd2/bin:$PATH

# Verify installation
linkerd version
```

### 2. 飞行前集群验证

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

### 4. 将应用程序加入网格

```bash
# Enable automatic injection for namespace
kubectl annotate namespace my-app linkerd.io/inject=enabled

# Restart existing deployments to inject proxy
kubectl rollout restart deployment -n my-app

# Or manually inject
kubectl get deploy -n my-app -o yaml | linkerd inject - | kubectl apply -f -
```

### 5. 安装并访问 Dashboard

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

### Data Plane Proxy

Linkerd 会向每个 Pod 注入一个名为 `linkerd-proxy` 的 sidecar 容器。该 proxy：

* 使用 Rust 编写，以保障内存安全和高性能
* 仅使用约 \~10MB 内存
* 增加的延迟低于 1ms
* 处理所有入站/出站流量
* 自动应用 mTLS 加密

### 服务发现

Destination 组件监控 Kubernetes Service 并向 proxy 提供 endpoint 信息：

* 实时 endpoint 更新
* 基于 ServiceProfile 的路由信息
* 流量分割策略分发

### 自动 mTLS

Linkerd 无需配置即可自动加密所有网格流量：

1. Identity 组件向每个 proxy 签发证书
2. proxy 之间进行 mutual TLS 身份验证
3. 自动续订证书（默认 24 小时）

## 后续步骤

1. [**安装和设置**](01-installation.md)：在集群中安装 Linkerd 的详细指南
2. [**架构**](02-architecture.md)：了解 Linkerd 的内部结构
3. [**测验**](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/service-mesh/linkerd/README.md)：测试你的知识

## 参考资料

* [Linkerd 官方文档](https://linkerd.io/2/overview/)
* [Linkerd GitHub](https://github.com/linkerd/linkerd2)
* [CNCF Linkerd 项目页面](https://www.cncf.io/projects/linkerd/)
* [Linkerd Slack 社区](https://slack.linkerd.io/)
* [Buoyant 博客](https://buoyant.io/blog)
