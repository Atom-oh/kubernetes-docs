# Calico 深度解析：企业级 Kubernetes 网络

> **支持的版本**: Calico v3.29+ / Kubernetes 1.28+
> **最后更新**: February 22, 2026

## 概述

本节将帮助您全面理解 Calico 的核心概念和技术。我们将深入探讨 Calico 的架构、网络模式、网络策略、安全功能以及与云提供商的集成。

## 什么是 Calico？

Calico 是面向容器、虚拟机和原生基于主机工作负载的开源网络与网络安全解决方案。Calico 最初由 Tigera 开发，现已成为部署最广泛的 Kubernetes CNI 插件之一，凭借其稳定性、性能和强大的网络策略功能，受到全球企业的信赖。

### 核心优势

1. **久经生产验证的成熟度**：自 2016 年以来，已有数千家组织在生产环境中使用
2. **灵活的数据平面**：可在 iptables、nftables 或 eBPF 数据平面之间选择
3. **原生 BGP 支持**：为本地部署和混合部署提供一流的 BGP 集成
4. **全面的网络策略**：Kubernetes NetworkPolicy 加上扩展的 Calico 策略
5. **Windows 支持**：完整支持 Windows 容器网络
6. **企业级功能**：Tigera Calico Enterprise 提供可观测性、合规性和威胁防御功能
7. **云原生集成**：与 AWS、GCP、Azure 和本地基础设施无缝集成

### 为什么选择 Calico？

- **经大规模验证**：为处理数十亿笔交易的公司提供生产工作负载支持
- **运维简单**：安装和配置直接明了
- **强大的社区**：活跃的开源社区和丰富的文档
- **供应商灵活性**：可在任何 Kubernetes 发行版中保持一致运行
- **合规就绪**：内置审计日志和策略强制执行功能

## 版本亮点：Calico v3.29

Calico v3.29 在网络、安全性和可观测性方面带来了重大改进：

### 网络增强功能
- **eBPF 数据平面 GA**：生产就绪的 eBPF 数据平面，具备完整的功能对等性
- **改进的 BGP 性能**：优化路由收敛并减少内存占用
- **增强的 VXLAN**：通过自动 MTU 检测提供更好的跨子网路由
- **IPv6 双栈**：全面支持双栈网络环境

### 安全性改进
- **DNS 策略增强**：更细粒度的基于 FQDN 的网络策略
- **策略建议**：基于观察到的流量提供 AI 辅助的策略生成
- **加密选项**：简化 WireGuard 配置以实现节点间加密

### 运维功能
- **Calico API Server**：Calico 资源的原生 Kubernetes API 聚合
- **改进的诊断功能**：增强的故障排除工具和健康检查
- **资源优化**：降低 CPU 和内存消耗

## CNI 对比

| 功能 | Calico | Cilium |
|---------|--------|--------|
| **核心技术** | iptables/eBPF | eBPF |
| **成熟度** | 极高 (2016+) | 高 (2017+) |
| **网络策略** | L3-L4 (L7 Enterprise) | L3-L7 |
| **服务网格** | 独立 (Enterprise) | 内置 |
| **BGP 支持** | 强大（原生） | 支持 |
| **可观测性** | 基础（Enterprise：高级） | Hubble（强大） |
| **Windows 支持** | 完整 | Beta |
| **eBPF 数据平面** | 可选 | 必需 |
| **学习曲线** | 中等 | 更陡峭 |
| **资源使用量** | 较低 | 较高 |
| **kube-proxy 替代** | 是（eBPF 模式） | 是 |
| **多集群** | Federation | Cluster Mesh |

## 架构概述

Calico 的架构由多个关键组件组成，它们协同工作以提供网络和网络安全功能。

```mermaid
flowchart TD
    subgraph CP["Control Plane"]
        A[kube-controllers]
        B[Typha]
        C[Calico API Server]
    end

    subgraph DP["Data Plane - Per Node"]
        D[Felix]
        E[BIRD]
        F[confd]
        G[iptables/eBPF]
    end

    subgraph DS["Datastore"]
        H[Kubernetes API]
        I[etcd - optional]
    end

    A -->|Watches| H
    B -->|Fan-out| D
    C -->|Aggregates| H
    D -->|Programs| G
    D -->|Configures| F
    F -->|Templates| E
    E -->|BGP Routes| E
    H -->|Config| B

    classDef controlPlane fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef dataPlane fill:#FA8320,stroke:#333,stroke-width:1px,color:white
    classDef datastore fill:#00C7B7,stroke:#333,stroke-width:1px,color:white

    class A,B,C controlPlane
    class D,E,F,G dataPlane
    class H,I datastore
```

### 关键组件

| 组件 | 作用 | 运行位置 |
|-----------|------|---------|
| **Felix** | 在每台主机上配置路由和 ACL | 每个节点 |
| **BIRD** | 用于路由分发的 BGP 守护进程 | 每个节点 |
| **confd** | 监视数据存储并生成 BIRD 配置 | 每个节点 |
| **Typha** | 用于降低 API Server 负载的缓存代理 | 专用 Pod |
| **kube-controllers** | 将 Kubernetes 资源与 Calico 同步 | 控制平面 |
| **Calico API Server** | Kubernetes API 聚合层 | 控制平面 |

## 网络模式

Calico 支持多种网络模式，以适应不同的基础设施要求：

### 1. IPIP 模式（默认）
- 用于跨子网流量的 IP-in-IP 封装
- MTU：1480 字节
- 最适合：云环境、简单设置

### 2. VXLAN 模式
- VXLAN 封装（UDP 端口 4789）
- MTU：1450 字节
- 最适合：需要标准覆盖网络协议的环境

### 3. 直接/无封装模式
- 无封装，使用原生路由
- MTU：1500 字节（完整）
- 最适合：使用 BGP 的本地环境、性能关键型工作负载

### 模式选择指南

```mermaid
flowchart TD
    A[Choose Networking Mode] --> B{BGP Available?}
    B -->|Yes| C{L2 Adjacency?}
    B -->|No| D[VXLAN Mode]
    C -->|Yes| E[Direct Mode]
    C -->|No| F{Cross-Subnet?}
    F -->|Yes| G[IPIP CrossSubnet]
    F -->|No| E
    D --> H[Configure IPPool]
    E --> H
    G --> H
```

## Amazon EKS 集成

Calico 与 Amazon EKS 无缝集成，提供增强的网络策略功能。

### 在 EKS 上快速安装

```bash
# Install Calico operator
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml

# Configure Calico for EKS (VXLAN mode)
cat <<EOF | kubectl apply -f -
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    ipPools:
    - blockSize: 26
      cidr: 10.244.0.0/16
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
EOF

# Verify installation
kubectl get pods -n calico-system
```

### 使用 VPC CNI 和 Calico Policy 的 EKS

适用于使用 AWS VPC CNI 进行网络连接、但需要高级网络策略的 EKS 环境：

```bash
# Install Calico for network policy only
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

## 安装方法

### 方法 1：Tigera Operator（推荐）

```bash
# Install the operator
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml

# Install Calico with custom configuration
cat <<EOF | kubectl apply -f -
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    ipPools:
    - blockSize: 26
      cidr: 192.168.0.0/16
      encapsulation: IPIP
      natOutgoing: Enabled
      nodeSelector: all()
EOF
```

### 方法 2：Helm 安装

```bash
# Add Calico Helm repository
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update

# Install Calico
helm install calico projectcalico/tigera-operator \
  --version v3.29.0 \
  --namespace tigera-operator \
  --create-namespace \
  --set installation.kubernetesProvider=EKS
```

### 方法 3：基于 Manifest 的安装

```bash
# For clusters with 50 nodes or less
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/calico.yaml

# For larger clusters (enables Typha)
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/calico-typha.yaml
```

## 网络策略示例

### 基础 Kubernetes NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### Calico GlobalNetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: deny-all-egress-except-dns
spec:
  selector: all()
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      ports:
      - 53
  - action: Deny
```

### 带 FQDN 的 Calico NetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-api
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      domains:
      - "api.example.com"
      - "*.amazonaws.com"
      ports:
      - 443
```

## 监控和可观测性

### Prometheus 指标

Calico 通过 Prometheus 暴露指标。需要监控的关键指标：

```yaml
# Felix metrics endpoint configuration
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

### 关键指标

| 指标 | 描述 |
|--------|-------------|
| `felix_active_local_endpoints` | 节点上的活跃端点数量 |
| `felix_iptables_rules` | 已配置的 iptables 规则数量 |
| `felix_ipsets_calico` | 维护的 IP 集合数量 |
| `felix_int_dataplane_failures` | 数据平面配置失败次数 |
| `felix_cluster_num_hosts` | 集群中的主机总数 |

### 健康检查端点

```bash
# Check Felix health
curl -s http://localhost:9099/liveness
curl -s http://localhost:9099/readiness

# Check Typha health
curl -s http://localhost:9098/liveness
```

## 故障排除快速参考

### 常用命令

```bash
# Check Calico system status
kubectl get pods -n calico-system

# View Calico node status
kubectl get nodes -o custom-columns=NAME:.metadata.name,CALICO:.status.conditions[*].type

# Check IP pools
kubectl get ippools -o wide

# View network policies
kubectl get networkpolicies -A
kubectl get globalnetworkpolicies

# Felix logs
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node

# BIRD status (BGP)
kubectl exec -n calico-system calico-node-xxxxx -c calico-node -- birdcl show protocols
```

### 常见问题与解决方案

| 问题 | 诊断 | 解决方案 |
|-------|-----------|----------|
| Pod 卡在 ContainerCreating | 检查 Felix 日志中的 IPAM 错误 | 验证 IPPool 配置 |
| 跨节点连接失败 | 检查封装模式 | 确保已启用 IPIP/VXLAN |
| 未强制执行网络策略 | 检查策略顺序和选择器 | 使用 `calicoctl` 验证策略 |
| Felix CPU 使用率高 | iptables 规则过多 | 考虑使用 eBPF 数据平面 |

## 深度解析目录

**[第 1 部分：Calico 简介](01-introduction.md)**
- 什么是 Calico 以及项目历史
- 实验环境设置
- 核心功能概述
- 使用案例和部署场景
- 社区与治理

**[第 2 部分：Calico 架构深度解析](02-architecture.md)**
- 组件架构概述
- Felix：Calico Agent
- BIRD：BGP 路由守护进程
- confd：配置管理
- Typha：扩展组件
- kube-controllers：Kubernetes 集成
- 数据存储选项
- 数据包流分析

**[第 3 部分：网络模式](03-networking-modes.md)**
- IPIP 封装模式
- VXLAN 封装模式
- 直接/无封装模式
- 模式对比与选择
- 性能基准测试
- 云提供商兼容性
- MTU 优化

## 选择指南：Calico 与 Cilium

### 以下情况选择 Calico：
- 您需要经生产验证的稳定性和成熟度
- 需要 Windows 容器支持
- 与现有网络基础设施进行 BGP 集成至关重要
- 相较于高级功能，您更偏好运维简单性
- 资源效率是优先事项
- 您已熟悉基于 iptables 的网络

### 以下情况选择 Cilium：
- 您需要高级 L7 网络策略
- 希望具备内置服务网格功能
- 使用 Hubble 进行深度可观测性很重要
- 您希望利用前沿 eBPF 功能
- 需要使用 Cluster Mesh 进行多集群连接

### 混合方法
一些组织会同时使用两者：
- Calico 用于需要稳定性的生产工作负载
- Cilium 用于探索新功能的开发/预发布环境

## 参考资料

- [Calico 官方文档](https://docs.tigera.io/calico/latest/about/)
- [Calico GitHub 仓库](https://github.com/projectcalico/calico)
- [Tigera Calico Enterprise](https://www.tigera.io/tigera-products/calico-enterprise/)
- [Calico 网络策略指南](https://docs.tigera.io/calico/latest/network-policy/)
- [Amazon EKS Calico 集成](https://docs.aws.amazon.com/eks/latest/userguide/calico.html)
- [calicoctl 参考](https://docs.tigera.io/calico/latest/reference/calicoctl/)
- [Calico eBPF 数据平面](https://docs.tigera.io/calico/latest/operations/ebpf/)

## 测验

如需测试您在本节中学到的内容，请尝试 [Calico 深度解析测验](../../quizzes/networking/calico/01-introduction-quiz.md)。
