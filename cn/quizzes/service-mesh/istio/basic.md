# 基础测验

> **审阅版本**：Istio 1.31.0 **EKS 版本**：1.34–1.36 **最后更新**：2026 年 9 月 11 日

本测验用于检验你对 Istio 基本概念和架构的理解。

## 选择题（1–5）

### 问题 1：Service Mesh 的定义

关于 Service Mesh，以下哪项说法**不正确**？

A. 它是负责处理微服务之间通信的基础设施层\
B. 只有修改应用程序代码后才能使用\
C. 它提供服务间的流量控制和可观测性\
D. 它在网络层应用安全策略和策略规则

<details>

<summary>显示答案</summary>

**答案：B**

Service Mesh 的核心优势之一，是**无需修改应用代码**，就能控制并观测服务之间的通信。

**说明：**

* A（正确）：Service Mesh 是微服务架构中专门负责服务间通信的基础设施层。
* B（错误）：它通过 Sidecar 代理或 Ambient Mode 透明地实现，无需修改应用代码。
* C（正确）：它通过 VirtualService、DestinationRule 等资源控制流量并暴露指标；日志和追踪需要配置，应用还必须传递追踪上下文。
* D（正确）：它通过 mTLS、Authorization Policy 等在网络层应用安全策略。

**参考资料：**

* [Istio 核心概念](../../../service-mesh/istio/02-basic-concepts.md)
* [什么是 Service Mesh？](../../../service-mesh/istio/README.md)

</details>

***

### 问题 2：Istio 架构组件

在 Istio Control Plane 中，哪个**集中式组件**负责服务发现、配置管理和证书管理？

A. Envoy\
B. Istiod\
C. Pilot\
D. Citadel

<details>

<summary>显示答案</summary>

**答案：B**

**Istiod** 是在 Istio 1.5 中引入的单一二进制程序，它整合了原先的 Pilot、Citadel 和 Galley 组件。

**说明：**

* A（错误）：Envoy 是 Data Plane 代理，以 Sidecar 形式运行在每个 Pod 中。
* B（正确）：Istiod 是 Control Plane 的核心，负责：
  * 服务发现
  * 配置管理
  * 证书管理
* C（错误）：Pilot 是 Istio 1.5 之前版本中的组件，现在已整合进 Istiod。
* D（错误）：Citadel 也是 Istio 1.5 之前版本中的组件，现在已整合进 Istiod。

**Istiod 的主要职责：**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**参考资料：**

* [Istio 组件](../../../service-mesh/istio/03-architecture.md)
* [架构概览](../../../service-mesh/istio/README.md)

</details>

***

### 问题 3：Envoy Proxy 的职责

以下哪项**不是** Data Plane 的 Envoy 代理执行的任务？

A. 流量路由和负载均衡\
B. mTLS 加密和身份验证\
C. Kubernetes CRD 的校验和存储\
D. 指标、日志和追踪数据的收集

<details>

<summary>显示答案</summary>

**答案：C**

Kubernetes API Server 存储资源并执行 schema 校验；Istiod 也会通过 admission webhook 校验 Istio 配置。Envoy 不存储 Kubernetes CRD。

**说明：**

* A（正确）：Envoy 根据 VirtualService 规则路由流量并执行负载均衡。
* B（正确）：Envoy 使用 mTLS 自动加密服务间通信并验证证书。
* C（错误）：CRD 的校验和存储由 Kubernetes API Server 和 Istiod 负责。
* D（正确）：Envoy 根据已配置的日志和追踪采样设置收集指标（Prometheus）、日志（Access Log）和追踪数据（Jaeger）。

**参考资料：**

* [Data Plane 结构](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### 问题 4：Istio 安装 Profile

在 Amazon EKS 生产环境中安装 Istio 时，推荐使用哪个 Profile？

A. default\
B. demo\
C. minimal\
D. production

<details>

<summary>显示答案</summary>

**答案：A**

本指南中的 Sidecar 安装以 `default` 作为生产环境的起始 Profile。Istio 没有内置的 `production` Profile。应明确设置副本数、资源请求、调度位置、PDB 和安全策略；仅选择 `default` 并不能保证部署具备高可用性。

| Profile | 用途 |
| --- | --- |
| default | 生产环境的起始设置；需按工作负载定制 |
| demo | 用于演示；遥测数据较详细，不适合性能测试 |
| minimal | 仅包含 Control Plane |
| production | 不是内置 Profile |

```bash
istioctl install --set profile=default
```

**生产环境检查清单：**

* ✅ Control Plane 高可用（副本数 ≥ 3）
* ✅ mTLS STRICT 模式
* ✅ 已配置 PodDisruptionBudget
* ✅ 已配置资源限制和 HPA
* ✅ 监控栈已就绪

**参考资料：**

* [安装指南](../../../service-mesh/istio/01-installation.md)
* [最佳实践](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### 问题 5：Istio CRD（Custom Resource Definition）

以下哪项**不是** Istio 的**流量管理** CRD？

A. VirtualService\
B. DestinationRule\
C. PeerAuthentication\
D. Gateway

<details>

<summary>显示答案</summary>

**答案：C**

**PeerAuthentication** 是与安全相关的 CRD。

**说明：**

**Istio CRD 分类：**

**1. 流量管理：**

* VirtualService：定义路由规则
* DestinationRule：配置负载均衡并定义子集
* Gateway：外部流量入口
* ServiceEntry：定义外部服务
* Sidecar：限制 Envoy 配置作用范围

**2. 安全：**

* PeerAuthentication：服务间身份验证（mTLS）
* RequestAuthentication：终端用户身份验证（JWT）
* AuthorizationPolicy：访问控制

**3. 可观测性：**

* Telemetry：配置指标、日志和追踪

**示例：**

```yaml
# Traffic Management
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1

---
# Security
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**参考资料：**

* [流量管理](../../../service-mesh/istio/traffic-management/README.md)
* [安全](../../../service-mesh/istio/security/README.md)

</details>

***

## 简答题（6–10）

### 问题 6：Sidecar 注入机制

请说明 Istio 中自动向 Pod 注入 Envoy Sidecar 的两种方式，并比较各自的优缺点。

<details>

<summary>显示答案</summary>

**答案：**

Istio 通过两种方式自动注入 Sidecar：

**1. Namespace 级自动注入：**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**优点：**

* 可一次应用于整个 Namespace
* 易于管理
* 遗漏注入的可能性较低

**缺点：**

* 会应用于该 Namespace 中的所有 Pod（需要选择性排除）
* 现有 Pod 需要重启

**2. Pod 级选择性注入：**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**优点：**

* 可选择只为指定 Pod 注入
* 可以进行精细控制
* 无需设置 Namespace 标签

**缺点：**

* 每个 Deployment 都需要配置
* 需要维护更多配置点
* 可能遗漏注入

**比较表：**

| 项目 | Namespace 级 | Pod 级 |
| --------------------- | ----------------------- | ------------------ |
| 范围 | 整个 Namespace | 单个 Pod |
| 管理复杂度 | 低 | 高 |
| 选择性 | 低（需要排除） | 高 |
| 推荐用途 | 生产环境 | 混合环境 |

**生产环境建议：**

* 默认使用 Namespace 级注入
* 只对需要排除的 Pod 设置 `sidecar.istio.io/inject: "false"`

**参考资料：**

* [Sidecar 注入](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### 问题 7：Istio 资源用量优化

在包含 1000 个 Pod 的大型 Kubernetes 集群中使用 Istio 时，请计算并比较 Sidecar Mode 与 Ambient Mode 的**预期资源用量**。（假设 ztunnel 部署在 10 个节点上，并且只有一个 waypoint。）

<details>

<summary>显示答案</summary>

**答案：**

以下数值是算术练习中假设的输入，并非 Istio 的实测需求或资源配置建议。请统一使用十进制 MB/GB。假设每个 Sidecar 使用 0.1 vCPU、每个 ztunnel 使用 0.1 vCPU，waypoint 使用 0.5 vCPU。

**假设条件：**

* Pod 数量：1000
* 节点数量：10
* Sidecar 内存：每个 Pod 50 MB
* ztunnel 内存：每个节点 50 MB
* waypoint 内存：200 MB

**1. Sidecar Mode 资源用量：**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Ambient Mode 资源用量：**

```
Memory Usage = (Number of Nodes × ztunnel Memory) + waypoint Memory
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU Usage = (Number of Nodes × ztunnel CPU) + waypoint CPU
          = (10 × 0.1 vCPU) + 0.5 vCPU
          = 1.5 vCPU
```

**3. 对比和节省量：**

| 项目 | Sidecar Mode | Ambient Mode | 节省量 | 节省比例 |
| ---------- | ------------ | ------------ | --------- | ------------ |
| **内存** | 50 GB | 0.7 GB | 49.3 GB | **98.6%** |
| **CPU** | 100 vCPU | 1.5 vCPU | 98.5 vCPU | **98.5%** |

**解读：**

根据上述假设，代理组件的合计内存和 CPU 用量分别减少 98.6% 和 98.5%。这并不意味着 AWS 账单会减少 96%，也不意味着一个 10 节点、1000 Pod 的集群可以运行在单个实例上。此处未计入应用资源、Pod/IP 限制、高可用性、副本数、吞吐量和 waypoint 容量。请先对实际拓扑进行基准测试，再估算资源配置或成本。Ambient 的核心功能自 Istio 1.24 起已正式发布（GA）。

**参考资料：**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [成本优化](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### 问题 8：mTLS 的工作机制

请逐步说明 Istio 中两个服务（service-a 和 service-b）通信时 mTLS 的工作方式，并说明 Istiod、Envoy 和证书各自的作用。

<details>

<summary>显示答案</summary>

**答案：**

**mTLS（Mutual TLS，双向 TLS）工作流程：**

**步骤 1：签发证书（初始化）**

* Pod 启动时，Istio agent 会创建私钥和 CSR，并使用工作负载凭证向 istiod 进行身份验证；随后本地 agent 通过 SDS 将证书和密钥提供给 Envoy。
* Istiod 验证 Service Account 后签发 X.509 证书。
* 证书中包含 Service Account ID（例如 `cluster.local/ns/default/sa/service-a`）。
* 证书默认有效期为 24 小时，并会自动续期。

**步骤 2：服务间通信（mTLS 握手）**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**详细流程：**

```text
1. The source app sends HTTP; configured redirection sends it through Envoy A.
2. Auto mTLS/DestinationRule determines outbound TLS; destination PeerAuthentication
   determines whether Envoy B requires inbound mTLS.
3. ClientHello and ServerHello negotiate TLS parameters/key exchange.
   Certificates are sent in Certificate messages, not in ClientHello/ServerHello.
   The server requests the client certificate; each peer validates the other
   certificate and proof of key possession against the configured trust chain.
4. Envoy B applies authorization and forwards the decrypted request to Service B.
5. The response travels over the established TLS connection.
```

**各组件的作用：**

**Istiod：**

* 充当 CA（其前面也可以有外部根 CA 下的中间 CA）。
* 根据 Service Account 签发证书。
* 在证书过期前签署续期请求；证书有效期可配置。
* 下发 PeerAuthentication 策略。

**Envoy Sidecar：**

* 通过 SDS 从 Istio agent 接收证书。
* 执行 TLS 握手。
* 加密和解密流量。
* 验证证书。

**证书：**

* 使用 X.509 证书格式。
* Subject Alternative Name（SAN）：Service Account URI。
* 默认有效期：24 小时。
* 自动续期。

**配置示例：**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**证书验证：**

```bash
# Inspect certificate validity/status; private keys are not shown as plaintext
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config secret <pod-name> -n <namespace> -o json
```

**安全优势：**

1. **机密性**：所有通信均经过加密。
2. **完整性**：防止数据被篡改。
3. **身份验证**：双向验证身份。
4. **自动化**：无需修改代码即可应用。

**参考资料：**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [证书管理](../../../service-mesh/istio/03-architecture.md#3-certificate-management-citadel-functionality)

</details>

***

### 问题 9：Istio 调试

请编写逐步调试方法，排查新部署的服务无法在 Istio mesh 中通信的问题。（至少 5 个步骤）

<details>

<summary>显示答案</summary>

**答案：**

**Istio 服务通信排查清单：**

**步骤 1：检查 Pod 和 Sidecar 状态**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}{" "}{.spec.initContainers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**诊断：**

* 检查容器中是否有 istio-proxy，或是否有 native sidecar initContainer；Ambient 工作负载没有注入的 Sidecar。
* 如果 Pod 处于 CrashLoopBackOff，表示应用或 Sidecar 初始化失败。

**解决方法：**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**步骤 2：检查 Service 和 Endpoint**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service-name>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**诊断：**

* 如果 Endpoint 为空，说明 Service Selector 与 Pod Label 不匹配。
* 检查 Service 端口与 Pod 端口是否不一致。

**解决方法：**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**步骤 3：检查 Istio 配置**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateways.networking.istio.io -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**诊断：**

* 检查 `istioctl analyze` 报错。
* 检查 VirtualService 的 host 是否与 Service 名称匹配。
* 检查 DestinationRule 子集标签是否与 Pod 标签匹配。

**解决方法：**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced gateway not found: missing-gateway
```

***

**步骤 4：检查 mTLS 和安全策略**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
istioctl x authz check <pod-name> -n <namespace>

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**诊断：**

* 明文客户端流量到达 STRICT 模式的目标、证书已过期，或信任配置不兼容。
* AuthorizationPolicy 阻止了流量。

**解决方法：**

检查实际生效的策略、工作负载身份、证书和 Envoy 拒绝日志。STRICT 和 PERMISSIVE 模式的服务端都可以接受 mesh mTLS 客户端。请在隔离的测试 Namespace 中验证策略变更；删除线上授权策略或放宽 mTLS 不应作为默认调试步骤。



***

**步骤 5：检查 Envoy 配置**

```bash
# Check Envoy cluster configuration (service discovery)
istioctl proxy-config clusters <pod-name> -n <namespace>

# Check Envoy listener configuration (inbound/outbound)
istioctl proxy-config listeners <pod-name> -n <namespace>

# Check Envoy route configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>
```

**诊断：**

* 如果目标 Service 不在 clusters 中，说明 Istiod 未识别该服务。
* 如果没有 listener，说明端口配置有误。
* 如果 endpoints 状态为 UNHEALTHY，说明 Pod 尚未就绪。

***

**步骤 6：测试网络连接**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Compare Pod-IP routing; this does not bypass the sidecar interception
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
istioctl dashboard envoy <pod-name> -n <namespace>
```

***

**步骤 7：检查 Istiod 日志**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**步骤 8：检查指标和追踪**

Telemetry 插件需要单独安装。每个会阻塞的 port-forward 命令都应在单独的终端中运行；请将示例中的服务和 Namespace 替换为实际 Collector 对应值。

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**故障排查流程图：**

```
1. Pod/Sidecar normal?
   ├─ NO → Check Sidecar injection
   └─ YES → Step 2

2. Service/Endpoint normal?
   ├─ NO → Check Selector
   └─ YES → Step 3

3. Istio configuration normal?
   ├─ NO → Run istioctl analyze
   └─ YES → Step 4

4. mTLS/policies normal?
   ├─ NO → Inspect identity, certificates, and denial logs
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Inspect xDS status and istiod logs
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**参考资料：**

* [Istio 调试指南](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### 问题 10：Istio 升级策略

请说明如何在兼容的 EKS 集群上，将 Istio 1.30.4 以 canary 方式升级到 1.31.0。请包括工作负载迁移、Gateway 处理、验证以及回滚条件。

<details>
<summary>显示答案</summary>

在所有工作负载和 Gateway 都完成迁移且回滚窗口关闭之前，必须保留旧 Control Plane。以下示例通过 istioctl 管理 Sidecar；Helm 和 Ambient 安装有各自的升级流程。下面的 revision 名称仅为示例，必须与实际安装相符。

**1. 准备并备份**

检查 Istio/EKS 支持矩阵和版本升级说明。按照最佳实践章节所述，保留现有安装文件（如适用，也保留 chart 版本）、mesh 资源以及 CA/TLS Secret。下载目标版本的 istioctl 并运行升级前检查：

```bash
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"
istioctl version
istioctl x precheck
```

**2. 安装 canary Control Plane**

根据现有配置准备 `canary-install.yaml`，保留 mesh 身份、信任配置和资源设置。设置 revision 为 `1-31-0`，并使用 `minimal` 安装仅包含 Control Plane 的 canary，不启用任何 Gateway 组件。安装前先渲染并审查：

```bash
istioctl manifest generate -f canary-install.yaml > canary-rendered.yaml
istioctl install -f canary-install.yaml
kubectl rollout status deployment/istiod-1-31-0 -n istio-system
```

Istio 没有 `production` Profile。revision 标签不会选择二进制版本；实际使用的版本由目标 istioctl 和配置决定。

**3. 验证测试 Namespace**

```bash
kubectl create namespace istio-upgrade-test
kubectl label namespace istio-upgrade-test istio.io/rev=1-31-0
kubectl apply -n istio-upgrade-test -f samples/curl/curl.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n istio-upgrade-test
kubectl rollout status deployment/httpbin -n istio-upgrade-test
kubectl exec -n istio-upgrade-test deploy/curl -c curl -- curl -fsS http://httpbin:8000/headers
istioctl proxy-status
istioctl analyze -n istio-upgrade-test
```

继续迁移前，应验证实际 Proxy 镜像版本、同步状态、mTLS 和授权行为、错误率及延迟。

**4. 先迁移 Staging，再逐个迁移 Production Namespace**

移除 `istio-injection` 标签，因为它的优先级高于 revision 标签。重启控制器以创建带有新 Proxy 的 Pod；必要时还应涵盖 StatefulSet、DaemonSet 和后续创建的 Job。

```bash
kubectl label namespace staging istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n staging
kubectl rollout status deployment -n staging
istioctl proxy-status
```

只有在应用冒烟测试成功且观察时间满足工作负载要求后，才能继续下一步。固定等待一段时间不能代替健康检查。

**5. 在移除旧 Control Plane 前迁移 Gateway**

通过 Gateway 所属的 istioctl/Helm 配置升级 Gateway，包括 Proxy 镜像、revision 和外部负载均衡器设置。若 Gateway 显式指定了旧镜像，仅修改 Deployment 标签是不够的。请验证滚动更新、外部请求和 proxy-status。默认 istioctl Profile 可以原地升级共享 Gateway，因此应提前明确规划此行为。

**6. 完成升级或回滚**

确认所有 Proxy（包括 Gateway 和非 Deployment 工作负载）都已离开旧 revision 后，再使用安装工具将其移除。不要手动删除共享的校验 webhook：

```bash
istioctl proxy-status
istioctl uninstall --revision=1-30-4
```

移除旧版本之前，如需回滚，应将受影响的 Namespace 标签改回仍在运行的旧 revision，重启其中的工作负载，使用旧版本发布配置恢复任何已升级的 Gateway，并验证流量。如果旧 revision 已经移除，应先重新安装并验证它，再为工作负载切换标签。

**参考资料：**

- [Canary 升级](https://istio.io/latest/docs/setup/upgrade/canary/)
- [备份和运维指南](../../../service-mesh/istio/best-practices.md)

</details>

***

## 分数计算

* 选择题 1–5：每题 10 分（共 50 分）
* 简答题 6–10：每题 10 分（共 50 分）
* **总分：100 分**

**评价标准：**

* 90–100 分：优秀（完全理解 Istio 基本概念）
* 80–89 分：良好（能够进行基本操作）
* 70–79 分：一般（建议继续学习）
* 60–69 分：较弱（需要复习基本概念）
* 0–59 分：需要重新学习

## 学习资源

* [Istio 安装指南](../../../service-mesh/istio/01-installation.md)
* [核心概念](../../../service-mesh/istio/02-basic-concepts.md)
* [组件](../../../service-mesh/istio/03-architecture.md)
* [Istio 官方文档](https://istio.io/latest/docs/)

* [安装配置 Profile](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Sidecar 安装](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
* [安全](https://istio.io/latest/docs/concepts/security/)
* [互联网工程任务组（IETF）：E. Rescorla](https://www.rfc-editor.org/rfc/rfc8446.html)
* [Canary 升级](https://istio.io/latest/docs/setup/upgrade/canary/)
* [istioctl](https://istio.io/latest/docs/reference/commands/istioctl/)
* [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Istio 1.24.0 发布公告](https://istio.io/latest/news/releases/1.24.x/announcing-1.24/)
* [性能与可扩展性](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
