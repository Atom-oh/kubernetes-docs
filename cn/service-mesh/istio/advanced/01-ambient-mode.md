# Ambient Mode

> **最后更新**: October 12, 2026 · Istio 1.31。本实验假定使用兼容的 Linux 节点、具备 node-agent/CNI 权限，并使用全新的演示命名空间。本次审计未运行任何部署命令。

Ambient 于 2022 年作为实验性预览版推出，首次在 Istio 1.18 中以 Alpha 形式发布，在 1.22 达到 Beta，并在 1.24 实现核心 GA。该预览版并非主版本 1.15 中已正式发布的功能。资源节省和迁移安全性取决于实际拓扑、策略和流量。

## 目录

1. [概述](#overview)
2. [Sidecar Mode 与 Ambient Mode](#sidecar-mode-vs-ambient-mode)
3. [架构](#architecture)
4. [安装和配置](#installation-and-configuration)
5. [迁移](#migration)
6. [性能比较](#performance-comparison)
7. [使用场景](#use-cases)
8. [故障排除](#troubleshooting)

## 概述


Ambient Mode 是一种无需向应用 Pod 注入 Sidecar 代理即可提供 Service Mesh 功能的新方法。Ambient Mode 采用**分层架构**：

1. **安全覆盖层（L4）**：通过 ztunnel 提供 mTLS 和基本遥测
2. **L7 处理层**：通过 Waypoint Proxy 提供高级流量管理

### 为什么需要 Ambient Mode？

传统 Sidecar 模型的局限性：
- **高资源开销**：每个 Pod 都需要一个 Envoy 代理（应测量实际代理资源占用）
- **运维复杂性**：Pod 重启、版本管理和滚动更新较为复杂
- **启动协调**：必须协调代理和应用的就绪状态
- **功能过剩**：某些工作负载仅需要 L4 mesh 功能

Ambient Mode 的解决方案：
- 共享节点代理加上所需的 waypoint：测量总体资源使用量
- 注册可避免重启未加入 mesh 的 Pod；移除 sidecar 和修改策略需要受控发布
- 渐进式采用：按需从 L4 扩展到 L7
- L4 传输可以透明；追踪上下文以及应用超时/幂等性约定仍然很重要

### 核心概念

这些图中的可选 waypoint 由配置/注册决定。ztunnel 不会解析每个 HTTP 请求并决定是否采用 L7 绕行路径。现有连接、就绪状态和策略转换仍需验证。


![对比 Sidecar Mode 和 Ambient Mode 的图示：在 Sidecar Mode 中，每个 pod 都将应用与 Envoy sidecar 配对；在 Ambient Mode 中，pod 透明地将流量发送到节点级 ztunnel，并可选地通过已配置的 Waypoint 路径进行 L7 处理。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-0.html)

### Ambient Mode 的优势

1. **共享资源模型**：节点代理加上所需的 waypoint 副本
2. **简单部署**：未加入 mesh 的 Pod 注册无需重启 Pod；移除 sidecar 则需要
3. **透明的 L4 传输**：应用追踪/截止时间/幂等性要求仍然存在
4. **灵活的 L7 功能**：仅在需要时使用 waypoint

## Sidecar Mode 与 Ambient Mode

### 架构比较

#### Sidecar Mode

![架构图展示三个 pod，每个 pod 都将应用容器与自己的 Envoy sidecar 代理配对，sidecar 之间直接协商双向 TLS。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-1.html)

**特性**：
- Envoy 代理注入到每个 pod
- 成熟的 L4/L7 功能；验证所选版本
- 资源使用量高
- 需要重启 Pod

#### Ambient Mode

![架构图展示许多应用 pod 将流量透明地发送到一个节点级 ztunnel，该 ztunnel 直接为目标服务处理 L4 流量，并在资源注册使用 waypoint 时走可选的 waypoint 路径。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-2.html)

**特性**：
- 每个节点一个 ztunnel
- 默认提供 L4 功能
- L7 功能需要 waypoint
- 未加入 mesh 的 Pod 注册无需重启 Pod；移除 sidecar 则需要

### 详细比较表

| 项目 | Sidecar Mode | Ambient Mode |
|------|-------------|--------------|
| **部署方式** | 向 pod 注入 Sidecar | 节点级 ztunnel + 可选 waypoint |
| **资源核算** | 每个 Pod 的 Envoy + 控制平面 | 节点 ztunnel + 所有 waypoint 副本 + 控制平面；在负载下测量 |
| **Pod 重建** | 添加/移除注入的代理时需要 | 未加入 mesh 的注册通常不需要；移除 sidecar 时需要 |
| **启动协调** | 代理/应用生命周期和就绪状态 | CNI 捕获和 ztunnel 就绪状态 |
| **L4 功能** | 支持 | 支持 |
| **L7 功能** | 与版本相关的支持 | 需要 waypoint 和受支持的 API；并非每项扩展都是 GA |
| **mTLS** | 自动 | 自动 |
| **遥测** | 详细 | 基本（L4）、详细（使用 waypoint 的 L7） |
| **熔断器** | 支持 | 需要 Waypoint |
| **重试/超时** | 支持 | 需要 Waypoint |
| **标头操作** | 支持 | 需要 Waypoint |
| **性能开销** | 取决于工作负载/配置 | 取决于路径/身份/waypoint/负载；比较等效策略 |
| **运维范围** | 每个工作负载的代理生命周期 | 节点/CNI 和共享 waypoint 生命周期 |
| **生产就绪性** | 成熟 | GA（Istio 1.24+） |

### 资源使用量比较

下面的 100-Pod 计算是假设性的规划示例，并非官方基准测试。估算资源或账单节省前，请计算所有节点/waypoint 副本，并比较等效的安全性、遥测和路由要求。

## 架构


Ambient Mode 数据平面由两个核心组件组成：**ztunnel** 和 **Waypoint Proxy**。

### ztunnel（Zero Trust Tunnel）


ztunnel 是 Ambient Mode 的核心组件，是一个**运行在节点级别的轻量级 L4 代理**。它作为 DaemonSet 运行在符合条件的 Linux 节点上，并处理已注册工作负载的受支持流量。这并非来自每个 Pod 的全部流量；需要检查 host-network/排除的工作负载和非 TCP 应用协议的当前支持情况。

#### ztunnel 的工作方式

1. **流量捕获**：通过 Istio CNI 在 pod 内的 netfilter/iptables 规则和网络命名空间交接透明地拦截 pod 网络流量
2. **mTLS 应用**：使用基于 SPIFFE 的 Identity 自动应用 mTLS 加密
3. **负载均衡**：在端点之间执行 L4 负载均衡
4. **遥测收集**：收集连接指标和日志
5. **转发**：将流量转发到目标 ztunnel 或 Waypoint

**ztunnel 技术栈**：
- **语言**：Rust（高性能、低内存使用）
- **协议**：HBONE（HTTP-Based Overlay Network Environment）
- **身份**：SPIFFE 工作负载身份；默认使用 Istiod CA，SPIRE 需单独集成
- **CNI**：与 Istio CNI 插件紧密集成

#### ztunnel 的角色

![图示展示一个 TCP 连接从应用 pod 出发，经过 ztunnel 内置的 mTLS 加密、L4 遥测收集、身份验证和 L4 负载均衡，随后到达目标服务。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-3.html)

**ztunnel 特性**：
- 使用 Rust 编写（性能优化）
- 以 DaemonSet 部署
- 与 CNI 插件集成
- 由 Istio CNI 协调的 pod 内 netfilter/iptables 重定向

#### ztunnel 部署

请使用已发布的 ambient 安装方式/charts。原始的最小 DaemonSet 缺少 token/CA/socket 挂载，并使用了错误的 hostNetwork/privileged 设置。1.31 chart 提供特定能力和 pod 内命名空间访问；它不会设置 `hostNetwork: true` 或 `privileged: true`。在未了解完整 chart/平台上下文的情况下，请勿复制或降低权限。

```bash
# Offline inspection; use the same reviewed values as the actual installation
istioctl manifest generate --set profile=ambient > ambient-rendered.yaml
# Inspect a deployed resource if a mesh already exists
kubectl get daemonset ztunnel -n istio-system -o yaml
```

### Waypoint Proxy


Waypoint 是一个**在需要 L7 功能时使用的可选代理**。已配置的 waypoint 会放置在已注册资源的流量路径中，以提供高级流量管理功能。

#### Waypoint 的关键特性

1. **选择性部署**：仅用于需要 L7 功能的服务，而非所有服务
2. **共享代理**：多个工作负载共享一个 Waypoint（根据 namespace/Service/Pod 注册）
3. **基于 Envoy**：使用与传统 Sidecar 相同的 Envoy 代理，并提供与版本相关的 L7 API 支持
4. **按需使用**：可以在运行时动态添加/移除

#### Waypoint 部署单元

ServiceAccount 提供工作负载身份；为其添加标签**不会**选择 waypoint。在 Namespace、Service 或 Pod 上使用 `istio.io/use-waypoint`，并使用 Gateway，其 `istio.io/waypoint-for` 流量类型应与预期流量匹配。

| 注册 | 范围 |
|---|---|
|Namespace|该 namespace 中符合条件资源的默认 waypoint 选择|
|Service|到该 Service 的流量；默认 waypoint 类型是 `service`|
|Pod|使用 `workload` 或 `all` waypoint 的直接工作负载/Pod-IP 流量|

仅部署标签不会为现有 Pod 添加标签；请使用 Pod-template 标签进行工作负载注册。`service` waypoint 不会自动覆盖直接 Pod-IP 流量。

#### Waypoint 的角色


**Waypoint 特性**：
- 以 Gateway 部署，随后由受支持的资源注册进行选择
- 基于 Envoy 代理
- 验证每个 API 的支持情况；任意 EnvoyFilter 补丁不是受支持的 waypoint API
- 仅为所需服务选择性使用

#### Waypoint 部署

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: ambient-demo
  labels:
    istio.io/waypoint-for: service
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

默认的 `istio-waypoint` class 使用 Envoy。核心 ambient GA 并不意味着所有 API 都是 GA：当前文档将 ambient VirtualService 描述为 Alpha，并禁止将其与 Gateway API routes 混用。此处请使用 HTTPRoute。EnvoyFilter 不是受支持的 waypoint 扩展。L7 策略保护到达 waypoint 的流量；强制经过 waypoint 还需要已记录的 ztunnel 授权防护以及正确的注册/就绪状态。

### 完整流量流向

以下是一张综合图，展示 Ambient Mode 中**不使用 Sidecars**时的流量流向：

![序列图跟踪一个请求：无 sidecar 的客户端应用通过客户端和服务端 ztunnel 走纯 L4 路径；在可选分支中，请求在到达服务端应用前通过 waypoint 代理进行 L7 路由。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-6.html)

**流量流向分析**：

1. **仅 L4 路径**（仅使用 ztunnel）：
   - 在具有代表性的负载下测量路径延迟
   - 自动应用 mTLS
   - 基本遥测
   - 适用于实际需求仅为 L4 的场景

2. **L7 路径**（ztunnel + Waypoint）：
   - 基于标头的路由
   - 熔断
   - 重试/超时
   - 适用于需要复杂流量策略时

### HBONE 协议


**HBONE（HTTP-Based Overlay Network Environment）** 是 Ambient Mode 中使用的隧道协议：

- **基于 HTTP/2**：与现有基础设施兼容
- **内置 mTLS**：安全通信
- **多路复用**：TCP 流为相同源/目标身份对共享隧道
- **网络策略**：HBONE 通常使用 TCP15008；请显式允许所需 mesh 路径

![图示展示来自应用的纯 TCP 流量由源 ztunnel 封装进 HTTP/2 mTLS HBONE 隧道，通过网络传输，并由目标 ztunnel 解封装回纯 TCP，随后到达目标应用。](../../../.gitbook/assets/en-service-mesh-istio-advanced-01-ambient-mode-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-01-ambient-mode-7.html)

本指南中的 HBONE 传输 TCP 流。应用 UDP 不会由该隧道承载；DNS 捕获/代理是独立功能。本地应用流可以保持明文，而代理之间的 mesh 传输会加密。

## 安装和配置

本实验需要兼容的 Linux 节点以及所需的 Istio CNI/ztunnel DaemonSet。EKS Fargate 无法运行这些节点 DaemonSet；请使用受支持的、由 EC2 支撑的部署位置，并审查实际的节点/CNI 平台。[平台先决条件](https://istio.io/latest/docs/ambient/install/platform-prerequisites/)涵盖 CNI 路径、权限和健康检查。使用 SecurityGroupPolicy 的 VPC CNI Pod ENI trunking 可能需要标准 enforcing mode 或适当的 exec probes；请评估策略影响。GKE、OpenShift、k3s 和其他平台可能需要不同设置。

Istio1.31 支持 Kubernetes1.32–1.37；请参阅 [安装指南](../01-installation.md)以了解 EKS 兼容性。下方的 Gateway API1.6.0 与 Istio1.31 的依赖项和官方 ambient 教程一致。请检查现有 bundle 的兼容性；不要仅为复制示例而降级较新的兼容 bundle。

### 1. Istio 安装（Ambient Mode）

仅在审查安装程序和平台设置后，对全新的实验 mesh 使用此安装命令。对于现有 mesh，请通过迁移流程保留其安装方法/values。

```bash
curl -fsSL https://istio.io/downloadIstio -o download-istio.sh
ISTIO_VERSION=1.31.0 sh download-istio.sh
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"

# Fresh cluster without Gateway API; review an existing bundle separately
if ! kubectl get crd gateways.gateway.networking.k8s.io >/dev/null 2>&1; then
  kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.0/experimental-install.yaml
fi
kubectl wait --for=condition=Established crd/gateways.gateway.networking.k8s.io --timeout=60s
kubectl get crd httproutes.gateway.networking.k8s.io

# Fresh lab mesh only; include required platform-specific values
istioctl install --set profile=ambient -y
kubectl get pods,daemonsets -n istio-system
```

### 2. 启用 Ambient Mode 并部署应用

请使用一个没有 sidecar-injection/revision 覆盖的新一次性 namespace。现有 Sidecar Pod 不会仅因添加 ambient 标签而转换。1.31 发行版中的完整 Bookinfo manifest 提供了旧单 Deployment 示例中缺失的 reviews Service、版本标签、ServiceAccounts 和 ratings 依赖项；它使用 Bookinfo1.20.3 images。

```bash
kubectl create namespace ambient-demo
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient
kubectl get namespace ambient-demo -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl apply -n ambient-demo -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl apply -n ambient-demo -f samples/curl/curl.yaml
for deployment in reviews-v1 reviews-v2 ratings-v1 curl; do
  kubectl rollout status "deployment/$deployment" -n ambient-demo --timeout=120s
done
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

### 3. 部署并选择 Waypoint

当前 CLI 接受 waypoint 名称和流量类型，而非 ServiceAccount 注册标志。等待就绪，并显式注册 Service。

```bash
istioctl waypoint apply --name reviews-waypoint --for service -n ambient-demo --wait
kubectl label service reviews -n ambient-demo istio.io/use-waypoint=reviews-waypoint --overwrite
kubectl get gateways.gateway.networking.k8s.io reviews-waypoint -n ambient-demo
kubectl get service reviews -n ambient-demo --show-labels
```

### 4. 使用 L7 功能

创建特定版本的后端 Services，并将 HTTPRoute 附加到已注册的 reviews Service。此示例展示 GET/标头路由；标头不是经过认证的身份。不要将旧 VirtualService 与此 Gateway API route 组合使用。对其他 Service/Pod IP 的直接调用是独立路径。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: ambient-demo
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: ambient-demo
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews
  namespace: ambient-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: reviews
    port: 9080
  rules:
  - matches:
    - method: GET
      headers:
      - name: end-user
        type: Exact
        value: jason
    backendRefs:
    - name: reviews-v2
      port: 9080
  - matches:
    - method: GET
    backendRefs:
    - name: reviews-v1
      port: 9080
```

```bash
kubectl describe httproutes.gateway.networking.k8s.io reviews -n ambient-demo
kubectl exec -n ambient-demo deploy/curl -c curl -- \
  curl -sS --max-time 5 -H "end-user: jason" http://reviews:9080/reviews/0
```

检查 Accepted/ResolvedRefs conditions 以及通过日志/遥测确定的所选后端。仅 HTTP 成功既不能证明 mTLS，也不能证明强制经过 waypoint。L7 授权需要适当的 `targetRefs`；强制经过 waypoint 还需要已记录的 ztunnel 授权防护。请参阅 [waypoint 策略附加](https://istio.io/latest/docs/ambient/usage/l7-features/)。

## 迁移

### 从 Sidecar Mode 迁移到 Ambient Mode

迁移是一项策略/工作负载发布，而非仅修改标签。保留已安装的 revision、CA/trust、gateways、CNI 选项和声明式工作负载配置。现有 sidecar 优先于 ambient 注册。对于需要这些策略的工作负载，请在移除 sidecar 前准备兼容的 L7 路由/授权和就绪的 waypoints。

#### 第 1 步：安装 Ambient 组件

使用现有安装方法和已审查的 values，以兼容版本添加 ambient 支持。不要使用无关的裸 `istioctl install --set profile=ambient` 命令覆盖由 Helm 管理的 mesh。渲染/比较预期配置，并验证 CNI/ztunnel 节点代理。

#### 第 2 步：应用到测试 Namespace

此独立 ambient 测试从 1.31 发行版部署客户端和服务端。httpbin Service 暴露8000并目标为8080。

```bash
kubectl create namespace test-ambient
kubectl label namespace test-ambient istio.io/dataplane-mode=ambient
kubectl apply -n test-ambient -f samples/curl/curl.yaml
kubectl apply -n test-ambient -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n test-ambient --timeout=120s
kubectl rollout status deployment/httpbin -n test-ambient --timeout=120s
kubectl exec -n test-ambient deploy/curl -c curl -- \
  curl -sS --max-time 5 http://httpbin:8000/headers
```

#### 第 3 步：验证

HBONE workload 列显示预期传输。对于实际流量，请在正确节点的 ztunnel 日志中检查预期的源/目标身份，或检查带有 `connection_security_policy="mutual_tls"` 的 TCP 指标。仅 HTTP 成功不是 mTLS 的证据。HBONE 注册不会拒绝每个明文调用方；如有需要请使用 PeerAuthentication STRICT。请参阅 [mTLS 验证](https://istio.io/latest/docs/ambient/usage/verify-mtls-enabled/)。

```bash
istioctl ztunnel-config workloads --workload-namespace test-ambient
source_pod=$(kubectl get pod -n test-ambient -l app=curl -o jsonpath='{.items[0].metadata.name}')
source_node=$(kubectl get pod "$source_pod" -n test-ambient -o jsonpath='{.spec.nodeName}')
ztunnel_pod=$(kubectl get pod -n istio-system -l app=ztunnel \
  --field-selector "spec.nodeName=$source_node" -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$ztunnel_pod" -n istio-system --since=5m
```

#### 第 4 步：切换选定工作负载

下一个示例假定存在一个独立的现有 `migration-demo` namespace，其中仅包含经审查、由 namespace 注入的 curl/httpbin Deployments，且只需要 L4。检查 Pod-template 注入覆盖或手动注入的代理；这些命令不会移除它们。对于 L7 工作负载，首先验证 waypoint 注册和策略转换，包括 `targetRefs` 以及任何强制经过的防护。在迁移期间规划策略共存；由 ztunnel 强制执行的基于 selector 的 L7 策略可能会失败关闭。

```bash
# Reference snapshots, not manifests to blindly reapply with stale server metadata
kubectl get namespace migration-demo -o json > migration-namespace-before.json
kubectl get deployment curl httpbin -n migration-demo -o yaml > migration-workloads-before.yaml

kubectl label namespace migration-demo istio.io/dataplane-mode=ambient --overwrite
kubectl label namespace migration-demo istio-injection- istio.io/rev-
kubectl get namespace migration-demo -L istio-injection,istio.io/rev,istio.io/dataplane-mode
for deployment in curl httpbin; do
  kubectl rollout restart "deployment/$deployment" -n migration-demo
  kubectl rollout status "deployment/$deployment" -n migration-demo --timeout=120s
done

# Check both classic containers and native-sidecar initContainers
kubectl get pods -n migration-demo -o json | jq -r '
  .items[] | [.metadata.name,
    any((.spec.containers + (.spec.initContainers // []))[]; .name == "istio-proxy")] | @tsv'
istioctl ztunnel-config workloads --workload-namespace migration-demo
```

#### 第 5 步：验证所选数据路径

对指定工作负载重复进行就绪状态、连通性、身份和策略测试。对于 L7 队列，请检查实际的 Namespace/Service/Pod 注册、Gateway 流量类型/就绪状态以及 route/策略附加；不要为每个 ServiceAccount 创建一个 waypoint。使用工作负载特定的停止/回滚标准。此实验流程并不保证生产环境零停机。

### 回滚策略

恢复记录的注入模式和原始 Pod-template/策略配置。以下代码只处理上述 namespace 注入情形；旧 revision 必须仍然存在且健康。带有 waypoints 的队列需要将其注册/路由策略作为审查后回滚的一部分进行恢复。仅删除为该队列创建、且已明确识别为未被引用的 waypoint——绝不能删除 namespace 中的所有 Gateway。

```bash
original_revision=$(jq -r '.metadata.labels["istio.io/rev"] // ""' migration-namespace-before.json)
original_injection=$(jq -r '.metadata.labels["istio-injection"] // ""' migration-namespace-before.json)

# Restore the recorded namespace-injection mode; do not invent a revision
if [ "$original_injection" = "enabled" ]; then
  kubectl label namespace migration-demo istio-injection=enabled --overwrite
elif [ -n "$original_revision" ]; then
  kubectl label namespace migration-demo "istio.io/rev=$original_revision" --overwrite
else
  echo "No supported namespace-injection mode recorded; restore the original workload configuration." >&2
  exit 1
fi
kubectl label namespace migration-demo istio.io/dataplane-mode-
for deployment in curl httpbin; do
  kubectl rollout restart "deployment/$deployment" -n migration-demo
  kubectl rollout status "deployment/$deployment" -n migration-demo --timeout=120s
done
```

## 性能比较

### 基准测试结果

已移除的 `perf.png` URL 返回404，且无法证实旧的“官方基准测试”表。没有来源能确定其每个 Pod 的 CPU/内存、延迟或吞吐量百分比。请使用[已发布的性能结果](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)，并保留其原始版本、负载、有效负载、硬件和策略条件；不要将历史测量结果重新标示为当前版本测试。

| 衡量项 | 保持可比性 |
|---|---|
|内存/CPU|应用数量、身份/连接数、节点数量、所有 waypoint 副本和等效策略|
|P50/P99 延迟|请求大小/速率、连接复用、mTLS、L7 策略、遥测和过载条件|
|吞吐量|相同的应用/后端容量和错误定义|
|成本|实际配置的容量、利用率和计费；仅降低 requests/使用量并不等于账单减少|

### 资源节省计算

原始的 100-Pod 算术仅作为**假设预算模型**保留在下方。其50MB/0.1CPU 和 waypoint 值为假设输入，并非建议的 requests/limits 或测量成本。实际比较中请包含每个 waypoint/ztunnel 副本、HA 部署和控制平面资源。增加 waypoint 副本会改变结果。

```python
# Hypothetical planning inputs, not measured resource consumption or billing
sidecar_memory = 100 * 50       # MB, decimal
sidecar_cpu = 100 * 0.1        # vCPU
ambient_memory = 10 * 50 + 200  # 10 ztunnels + one assumed waypoint budget
ambient_cpu = 10 * 0.1 + 0.5

memory_saved = sidecar_memory - ambient_memory  # 4300 MB, 86% of assumed baseline
cpu_saved = sidecar_cpu - ambient_cpu           # 8.5 vCPU, 85% of assumed baseline
```

## 使用场景

### 何时应选择 Ambient Mode？


**Ambient Mode 的推荐场景**：
- 数百个或更多微服务
- 重视资源成本优化
- 大多数服务仅需简单通信
- 仅部分服务需要高级路由
- 希望最小化运维复杂性

**Sidecar Mode 的推荐场景**：
- 所需 API/扩展或平台行为仅由所选 sidecar 设置支持
- 需要经过验证的成熟解决方案
- 需要对每个服务进行细粒度控制
- 每个 pod 独立进行代理版本管理

### 1. 仅需 L4 功能时

对于兼容的现有 TCP 工作负载，在验证平台、策略和捕获先决条件后注册 namespace。此 Namespace 并非完整的数据库部署；必须单独设计数据库复制/存储/HA。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: backend
  labels:
    istio.io/dataplane-mode: ambient
```

### 2. 选择性使用 L7 功能

该演示在 Service 级别选择已就绪的 reviews waypoint。Namespace 和直接工作负载注册是独立的受支持范围；ServiceAccount 标签不是选择器。

```bash
kubectl label service reviews -n ambient-demo istio.io/use-waypoint=reviews-waypoint --overwrite
```

L7 要求不会自动要求使用 sidecars：请将受支持的 waypoint API 和扩展与应用的实际需求比较。反之，核心 GA 并不意味着每个高级 API 都具有功能对等性。

### 3. 渐进式迁移

先清点注入和注册，然后使用明确的就绪状态/安全性/回滚标准迁移经审查的队列。不要盲目为每个 dev/staging/production namespace 添加标签，也不要假定该变更会转换现有 sidecars。

```bash
kubectl get namespaces -L istio-injection,istio.io/rev,istio.io/dataplane-mode,istio.io/use-waypoint
```

## 故障排除

### ztunnel 未正常工作

```bash
# Check ztunnel status
kubectl get daemonset -n istio-system ztunnel
kubectl logs -n istio-system -l app=ztunnel

# Check CNI
kubectl get daemonset -n istio-system istio-cni-node
kubectl logs -n istio-system -l k8s-app=istio-cni-node
```

### 流量未发送至 Waypoint

```bash
# Check Waypoint status
kubectl get gateways.gateway.networking.k8s.io -n <namespace>

# Check supported enrollment scopes and Gateway readiness
kubectl get namespace <namespace> -L istio.io/use-waypoint
kubectl get services -n <namespace> -L istio.io/use-waypoint
istioctl waypoint list -n <namespace>
istioctl ztunnel-config services

# Check Envoy configuration
istioctl proxy-config clusters <waypoint-pod> -n <namespace>
```

## 参考资料

### 当前官方文档

- [Ambient 概览](https://istio.io/latest/docs/ambient/overview/)
- [入门指南](https://istio.io/latest/docs/ambient/getting-started/)
- [Pod 内流量重定向](https://istio.io/latest/docs/ambient/architecture/traffic-redirection/)
- [HBONE](https://istio.io/latest/docs/ambient/architecture/hbone/)
- [Waypoint 注册](https://istio.io/latest/docs/ambient/usage/waypoint/)
- [L7 API 支持和策略附加](https://istio.io/latest/docs/ambient/usage/l7-features/)
- [性能方法论/结果](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [ztunnel 源代码](https://github.com/istio/ztunnel)
- [Istio 社区和 Slack 访问](https://istio.io/latest/get-involved/)

### 历史介绍

这些2022 页面描述的是实验性预览，而非当前安装或 ServiceAccount-waypoint 命令。

- [Ambient mesh 简介（2022）](https://istio.io/latest/blog/2022/introducing-ambient-mesh/)
- [实验性安全架构（2022）](https://istio.io/latest/blog/2022/ambient-security/)
- [实验性入门指南（2022）](https://istio.io/latest/blog/2022/get-started-ambient/)

### 已验证的里程碑和当前限制

| 里程碑 | 证据 |
|---|---|
|2022 预览版|已宣布实验性实现；不是主版本1.15功能发布的一部分|
|1.18 Alpha（2023）|首个随 Istio 发布 ambient 的版本|
|1.22 Beta（2024）|Beta 里程碑|
|1.24 核心 GA（2024）|核心 ztunnel/waypoint/API 里程碑；各项功能仍保留各自状态|

当前的 [ambient multicluster 文档](https://istio.io/latest/docs/ambient/install/multicluster/)描述**Beta multi-primary、multi-network**支持。Primary/remote 不受支持，且 single-network 部署未经测试；必须跨集群协调 waypoint 命名/配置和服务范围。旧的1.26/1.27 路线图和未署名的企业节省数据，不能作为受支持行为或保证成本降低的证据。

## 总结

Ambient 将共享 L4 传输与选定的 L7 waypoint 处理分离。它可以简化未加入 mesh 的工作负载注册和代理生命周期管理，但资源节省、策略保留和可用性需要等效策略测量及经过验证的迁移计划。请考虑 Linux/CNI/平台约束、TCP15008 连通性以及每个 API 的功能状态。
