# 基础测验

> **支持版本**: Istio 1.28.0 **EKS 版本**: 1.34 (Kubernetes 1.28+) **最后更新**: February 23, 2026

本测验用于检验您对 Istio 基础概念和架构的理解。

## 多项选择题（1-5）

### 问题 1: Service Mesh 的定义

关于 Service Mesh，以下哪项说法**不正确**？

A. 它是处理微服务之间通信的基础设施层 B. 只能通过修改应用程序代码来使用它 C. 它在服务之间提供流量控制和可观测性 D. 它在网络层应用安全性和策略

<details>

<summary>显示答案</summary>

**答案: B**

Service Mesh 的核心优势之一是，无需更改应用程序代码即可控制和观测服务之间的通信。

**说明:**

* A (O): Service Mesh 是负责微服务架构中服务间通信的专用基础设施层
* B (X): 它通过 Sidecar proxy 或 Ambient Mode 透明地应用，无需更改应用程序代码
* C (O): 它使用 VirtualService、DestinationRule 等控制流量，并自动收集指标/日志/追踪
* D (O): 它使用 mTLS、Authorization Policy 等在网络层应用安全策略

**参考资料:**

* [Istio 核心概念](../../../service-mesh/istio/02-basic-concepts.md)
* [什么是 Service Mesh？](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#introduction)

</details>

***

### 问题 2: Istio 架构组件

在 Istio 的 Control Plane 中，哪个是负责服务发现、配置管理和证书管理的**集中式组件**？

A. Envoy B. Istiod C. Pilot D. Citadel

<details>

<summary>显示答案</summary>

**答案: B**

**Istiod** 是 Istio 1.5 中引入的单一二进制文件，集成了之前的 Pilot、Citadel 和 Galley 组件。

**说明:**

* A (X): Envoy 是运行在每个 Pod 中作为 Sidecar 的 Data Plane proxy
* B (O): Istiod 是 Control Plane 的核心，负责：
  * 服务发现
  * 配置管理
  * 证书管理
* C (X): Pilot 是 Istio 1.5 之前版本中的组件，现已集成到 Istiod 中
* D (X): Citadel 也是 Istio 1.5 之前版本中的组件，现已集成到 Istiod 中

**Istiod 的关键职责:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**参考资料:**

* [Istio 组件](../../../service-mesh/istio/03-architecture.md)
* [架构概览](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#architecture-overview)

</details>

***

### 问题 3: Envoy Proxy 的职责

以下哪项**不是** Data Plane 中 Envoy proxy 执行的任务？

A. 流量路由和负载均衡 B. mTLS 加密和认证 C. Kubernetes CRD 验证和存储 D. 指标、日志和追踪收集

<details>

<summary>显示答案</summary>

**答案: C**

Kubernetes CRD 验证和存储是 Control Plane（Istiod）的职责。

**说明:**

* A (O): Envoy 根据 VirtualService 规则路由流量并执行负载均衡
* B (O): Envoy 使用 mTLS 自动加密服务间通信并验证证书
* C (X): CRD 验证和存储是 Kubernetes API Server 和 Istiod 的职责
* D (O): Envoy 为所有请求收集指标（Prometheus）、日志（Access Log）和追踪（Jaeger）

**参考资料:**

* [Data Plane 结构](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### 问题 4: Istio 安装 Profile

在 Amazon EKS 生产环境中安装 Istio 时，推荐使用哪个 Profile？

A. default B. demo C. minimal D. production

<details>

<summary>显示答案</summary>

**答案: D**

对于生产环境，应使用 **production** Profile。

**说明:**

**Istio 安装 Profile 对比:**

| Profile        | 用途             | 特征                           |
| -------------- | ------------------- | ----------------------------------------- |
| **default**    | 开发/测试 | 默认配置，中等资源   |
| **demo**       | 演示/学习       | 启用所有功能，资源使用量高 |
| **minimal**    | 最小化设置       | 仅 Control Plane                        |
| **production** | 生产环境          | HA 配置，高可用性       |

**Production Profile 特征:**

```bash
# Production profile installation
istioctl install --set profile=production -y

# Key characteristics:
# - Istiod replica: 3 (HA)
# - PodDisruptionBudget configured
# - Resource limits properly set
# - Ingress/Egress Gateway included
```

**生产环境检查清单:**

* ✅ Control Plane HA（replica ≥ 3）
* ✅ mTLS STRICT 模式
* ✅ 已配置 PodDisruptionBudget
* ✅ 已配置资源限制和 HPA
* ✅ 监控栈已就绪

**参考资料:**

* [安装指南](../../../service-mesh/istio/01-installation.md)
* [最佳实践](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### 问题 5: Istio CRD（Custom Resource Definition）

以下哪项**不是** Istio 用于**流量管理**的 CRD？

A. VirtualService B. DestinationRule C. PeerAuthentication D. Gateway

<details>

<summary>显示答案</summary>

**答案: C**

**PeerAuthentication** 是与安全相关的 CRD。

**说明:**

**Istio CRD 分类:**

**1. 流量管理:**

* VirtualService: 定义路由规则
* DestinationRule: 负载均衡、子集定义
* Gateway: 外部流量入口点
* ServiceEntry: 外部服务定义
* Sidecar: 限制 Envoy 配置范围

**2. 安全:**

* PeerAuthentication: 服务间认证（mTLS）
* RequestAuthentication: 终端用户认证（JWT）
* AuthorizationPolicy: 访问控制

**3. 可观测性:**

* Telemetry: 指标、日志、追踪配置

**示例:**

```yaml
# Traffic Management
apiVersion: networking.istio.io/v1beta1
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
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**参考资料:**

* [流量管理](../../../service-mesh/istio/traffic-management/README.md)
* [安全](../../../service-mesh/istio/security/README.md)

</details>

***

## 简答题（6-10）

### 问题 6: Sidecar 注入机制

请说明在 Istio 中向 Pod 自动注入 Envoy Sidecar 的两种方法，并比较各自的优缺点。

<details>

<summary>显示答案</summary>

**答案:**

Istio 使用两种方法自动注入 Sidecar：

**1. Namespace 级自动注入:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**优点:**

* 可一次应用于整个 Namespace
* 易于管理
* 意外遗漏的可能性低

**缺点:**

* 应用于 Namespace 中的所有 Pod（需要选择性排除）
* 现有 Pod 需要重启

**2. Pod 级选择性注入:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**优点:**

* 仅可选择性注入特定 Pod
* 可实现细粒度控制
* 无需 Namespace label

**缺点:**

* 每个 Deployment 都需要配置
* 管理点增加
* 可能意外遗漏

**对比表:**

| 项目                  | Namespace 级别         | Pod 级别          |
| --------------------- | ----------------------- | ------------------ |
| 范围                 | 整个 Namespace        | 单个 Pod     |
| 管理复杂度 | 低                     | 高               |
| 选择性           | 低（需要排除）  | 高               |
| 推荐用途       | 生产环境 | 混合环境 |

**生产环境建议:**

* 默认使用 Namespace 级别
* 仅为需要排除的 Pod 设置 `sidecar.istio.io/inject: "false"`

**参考资料:**

* [Sidecar 注入](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### 问题 7: Istio 资源使用优化

计算并比较在拥有 1000 个 Pod 的大规模 Kubernetes 集群中使用 Istio 时，Sidecar Mode 和 Ambient Mode 的**预期资源使用量**。（假设 ztunnel 部署在 10 个节点上，且有 1 个 waypoint）

<details>

<summary>显示答案</summary>

**答案:**

**假设条件:**

* Pod 数量: 1000
* Node 数量: 10
* Sidecar 内存: 50MB/Pod
* ztunnel 内存: 50MB/Node
* waypoint 内存: 200MB

**1. Sidecar Mode 资源使用量:**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Ambient Mode 资源使用量:**

```
Memory Usage = (Number of Nodes × ztunnel Memory) + waypoint Memory
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU Usage = (Number of Nodes × ztunnel CPU) + waypoint CPU
          = (10 × 0.1 vCPU) + 0.5 vCPU
          = 1.5 vCPU
```

**3. 对比和节省量:**

| 项目       | Sidecar Mode | Ambient Mode | 节省量   | 节省比例 |
| ---------- | ------------ | ------------ | --------- | ------------ |
| **内存** | 50GB         | 0.7GB        | 49.3GB    | **98.6%**    |
| **CPU**    | 100 vCPU     | 1.5 vCPU     | 98.5 vCPU | **98.5%**    |

**成本计算（基于 AWS EKS）:**

```
# r5.xlarge: 4 vCPU, 32GB RAM, $0.252/hour

Sidecar Mode:
- CPU: 100 vCPU → 25 instances needed
- Memory: 50GB → 2 instances needed
- Required instances: max(25, 2) = 25
- Monthly cost: 25 × $0.252 × 24 × 30 = $4,536

Ambient Mode:
- CPU: 1.5 vCPU → 1 instance sufficient
- Memory: 0.7GB → 1 instance sufficient
- Required instances: 1
- Monthly cost: 1 × $0.252 × 24 × 30 = $181

Monthly cost savings: $4,536 - $181 = $4,355 (96%)
```

**结论:**

* Ambient Mode 在大规模集群中可节省**至少 96% 的成本**
* 在 1000 Pod 规模下，每月大约可节省 **$4,300**
* 资源使用量减少**超过 98%**

**注意事项:**

* 需要 L7 功能时需增加 waypoint
* Ambient Mode 是 Istio 1.28+ 中的 beta 功能

**参考资料:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [成本优化](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### 问题 8: mTLS 工作机制

请逐步说明当两个服务（service-a 和 service-b）在 Istio 中通信时 mTLS 如何工作。请包含 Istiod、Envoy 和 Certificate 的职责。

<details>

<summary>显示答案</summary>

**答案:**

**mTLS（Mutual TLS）工作流程:**

**第 1 步: 证书签发（Bootstrap）**

* 当 Pod 启动时，Envoy 使用其 Service Account 向 Istiod 请求证书（CSR）
* Istiod 验证 Service Account 并签发 X.509 Certificate
* Certificate 包含 Service Account ID（例如，`cluster.local/ns/default/sa/service-a`）
* Certificate 有效期: 默认为 24 小时（自动续期）

**第 2 步: 服务间通信（mTLS Handshake）**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**详细流程:**

```yaml
# Service A calls Service B
1. Service A → Envoy A (localhost:outbound)
   - Application sends plaintext HTTP request

2. Envoy A: Outbound Processing
   - Check configuration received from Istiod
   - Check PeerAuthentication policy (STRICT mTLS)
   - Start connection to Service B's Envoy B

3. TLS Handshake (Envoy A ↔ Envoy B)
   a. Envoy A → Envoy B: ClientHello
      - Present own certificate
      - Present supported encryption algorithms

   b. Envoy B → Envoy A: ServerHello
      - Present own certificate
      - Selected encryption algorithm

   c. Mutual Certificate Validation
      - Envoy A: Validate Service B's certificate
      - Envoy B: Validate Service A's certificate
      - Verify signature with Istiod's Root CA

   d. Generate Encrypted Session Key
      - Create TLS 1.3 encrypted channel

4. Envoy B → Service B (localhost:inbound)
   - Deliver decrypted plaintext HTTP request

5. Service B → Envoy B → [mTLS] → Envoy A → Service A
   - Response uses same encrypted channel
```

**各组件的职责:**

**Istiod:**

* 充当 Root CA（证书签名）
* 基于 Service Account 签发证书
* 自动续期证书（每 24 小时）
* 分发 PeerAuthentication 策略

**Envoy Sidecar:**

* 请求和续期证书
* 执行 TLS Handshake
* 加密/解密流量
* 验证证书

**Certificate:**

* X.509 Certificate 格式
* Subject Alternative Name（SAN）: Service Account URI
* 有效期: 24 小时（默认）
* 自动续期

**配置示例:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**证书验证:**

```bash
# Check Pod's certificate
istioctl proxy-config secret <pod-name> -o json

# Example output:
{
  "name": "default",
  "tlsCertificate": {
    "certificateChain": "...",
    "privateKey": "...",
    "subjectAltNames": [
      "spiffe://cluster.local/ns/default/sa/service-a"
    ]
  }
}
```

**安全优势:**

1. **机密性**: 所有通信均经过加密
2. **完整性**: 防止数据篡改
3. **认证**: 双向身份验证
4. **自动化**: 无需更改代码即可应用

**参考资料:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [证书管理](../../../service-mesh/istio/03-architecture.md#certificate-management)

</details>

***

### 问题 9: Istio 调试

请编写一种逐步调试方法，用于诊断新部署的服务无法在 Istio mesh 中通信的问题。（至少 5 个步骤）

<details>

<summary>显示答案</summary>

**答案:**

**Istio 服务通信调试检查清单:**

**第 1 步: 检查 Pod 和 Sidecar 状态**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**诊断:**

* 如果只有 1 个 container → 未注入 Sidecar
* 如果 Pod 处于 CrashLoopBackOff → 应用程序或 Sidecar 初始化失败

**解决方法:**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**第 2 步: 检查 Service 和 Endpoint**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpoints <service-name> -n <namespace>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**诊断:**

* 如果 Endpoint 为空 → Service Selector 与 Pod Label 不匹配
* Service port 与 Pod port 不匹配

**解决方法:**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**第 3 步: 检查 Istio 配置**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateway -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**诊断:**

* 检查 `istioctl analyze` 错误消息
* VirtualService host 是否与 Service 名称匹配
* DestinationRule subset label 是否与 Pod label 匹配

**解决方法:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced host not found: reviews
```

***

**第 4 步: 检查 mTLS 和安全策略**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl authn tls-check <pod-name>.<namespace> <service-name>.<namespace>.svc.cluster.local

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**诊断:**

* mTLS 模式不匹配（STRICT 与 PERMISSIVE）
* AuthorizationPolicy 阻止流量

**解决方法:**

```bash
# Temporarily change to PERMISSIVE mode (for debugging)
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: <namespace>
spec:
  mtls:
    mode: PERMISSIVE
EOF

# Temporarily delete AuthorizationPolicy
kubectl delete authorizationpolicy <policy-name> -n <namespace>
```

***

**第 5 步: 检查 Envoy 配置**

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

**诊断:**

* 如果 clusters 中没有目标 Service → Istiod 未识别该服务
* 如果没有 listener → port 配置错误
* 如果 endpoints 为 UNHEALTHY → Pod 未就绪

***

**第 6 步: 网络连接测试**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Test directly without going through Envoy (by Pod IP)
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- curl localhost:15000/stats | grep <service-name>
```

***

**第 7 步: 检查 Istiod 日志**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**第 8 步: 检查指标和追踪**

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**故障排查流程图:**

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
   ├─ NO → Test PERMISSIVE mode
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Restart Istiod
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**参考资料:**

* [Istio 调试指南](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### 问题 10: Istio 升级策略

请说明在生产环境中将 Istio 从 1.27.0 升级到 1.28.0 的 **Canary Upgrade** 策略。请包含逐步命令和验证方法。

<details>

<summary>显示答案</summary>

**答案:**

**Istio Canary Upgrade 策略:**

Canary Upgrade 是一种安全的升级方法，可同时运行旧版和新版 Control Plane，并逐步迁移 workload。

***

**准备工作:**

```bash
# 1. Check current version
istioctl version

# 2. Create backup
kubectl get istiooperator -A -o yaml > istio-1.27-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 3. Download new version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 4. Check compatibility
istioctl x precheck
```

***

**第 1 步: 安装新的 Control Plane（使用 revision）**

```bash
# Install new version Control Plane using Revision
istioctl install --set revision=1-28-0 --set profile=production -y

# Verify installation
kubectl get pods -n istio-system -l app=istiod
# Example output:
# istiod-1-27-0-xxxx  (old version)
# istiod-1-28-0-xxxx  (new version)

# Check Revision
kubectl get mutatingwebhookconfigurations | grep istio
# Output:
# istio-sidecar-injector-1-27-0
# istio-sidecar-injector-1-28-0
```

**重要提示:** 此时，**两个 Control Plane** 正在同时运行。

***

**第 2 步: 使用测试 Namespace 进行 Canary 验证**

```bash
# Create test namespace
kubectl create namespace istio-upgrade-test

# Label for new version
kubectl label namespace istio-upgrade-test istio.io/rev=1-28-0

# Deploy test application
kubectl apply -n istio-upgrade-test -f samples/sleep/sleep.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml

# Check Sidecar version (should be 1.28.0)
kubectl get pods -n istio-upgrade-test -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'

# Test communication
kubectl exec -n istio-upgrade-test deploy/sleep -- curl http://httpbin:8000/headers

# Check Envoy configuration
istioctl proxy-config clusters deploy/sleep.istio-upgrade-test
```

**验证检查清单:**

* ✅ 是否已注入 1.28.0 版本的 Sidecar？
* ✅ 服务间通信是否正常？
* ✅ mTLS 是否正常工作？
* ✅ 是否正在收集指标？

***

**第 3 步: 迁移 Staging Namespace**

```bash
# Switch staging namespace to new version
kubectl label namespace staging istio.io/rev=1-28-0 --overwrite

# Remove existing label (if present)
kubectl label namespace staging istio-injection-

# Restart Pods (inject new version Sidecar)
kubectl rollout restart deployment -n staging

# Monitor restart status
kubectl rollout status deployment -n staging

# Verify version
kubectl get pods -n staging -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

**验证:**

```bash
# Check metrics
kubectl exec -n staging <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_build

# Test communication
kubectl exec -n staging <pod-name> -- curl http://<service-name>

# Visual confirmation with Kiali
istioctl dashboard kiali
```

**监控 24-48 小时:**

* 检查 Prometheus 指标
* 对比错误率和延迟
* 检查 Istiod 资源使用情况

***

**第 4 步: 逐步迁移生产 Namespace**

```bash
# List of production Namespaces
PROD_NAMESPACES="prod-api prod-web prod-worker"

# Migrate one at a time gradually
for ns in $PROD_NAMESPACES; do
  echo "Upgrading namespace: $ns"

  # Update label
  kubectl label namespace $ns istio.io/rev=1-28-0 --overwrite

  # Restart Pods
  kubectl rollout restart deployment -n $ns

  # Wait for completion
  kubectl rollout status deployment -n $ns

  # Verify
  echo "Verifying namespace: $ns"
  kubectl exec -n $ns <pod-name> -- curl http://<service-name>

  # Wait before next Namespace migration (observation)
  echo "Waiting 1 hour before next namespace..."
  sleep 3600
done
```

**逐步验证:**

```bash
# After each Namespace migration
# 1. Golden Signals
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query in Prometheus:
# - istio_requests_total
# - istio_request_duration_milliseconds
# - istio_request_bytes

# 2. Control Plane status
istioctl proxy-status | grep $ns

# 3. Error logs
kubectl logs -n istio-system -l app=istiod,istio.io/rev=1-28-0 --tail=100
```

***

**第 5 步: 移除旧版本**

```bash
# Verify all Namespaces have migrated to new version
kubectl get namespace -L istio.io/rev

# Verify no Pods using old version
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}' | grep 1.27

# Remove old version Control Plane
istioctl uninstall --revision=1-27-0 -y

# Verify removal
kubectl get pods -n istio-system -l app=istiod

# Cleanup
kubectl delete mutatingwebhookconfigurations istio-sidecar-injector-1-27-0
kubectl delete validatingwebhookconfigurations istio-validator-1-27-0-istio-system
```

***

**第 6 步: Gateway 升级（可选）**

```bash
# Upgrade Gateway separately
kubectl patch deployment istio-ingressgateway -n istio-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"istio.io/rev":"1-28-0"}}}}}'

kubectl rollout restart deployment istio-ingressgateway -n istio-system
kubectl rollout status deployment istio-ingressgateway -n istio-system
```

***

**回滚计划:**

```bash
# Immediate rollback if issues occur
# 1. Change Namespace label to old version
kubectl label namespace <namespace> istio.io/rev=1-27-0 --overwrite

# 2. Restart Pods
kubectl rollout restart deployment -n <namespace>

# 3. Remove new version Control Plane
istioctl uninstall --revision=1-28-0 -y
```

***

**最佳实践:**

1. **分阶段方法:**
   * 按阶段推进: Test → Staging → Prod
   * 每次迁移一个 Namespace
   * 在每个阶段留出充足的观察时间
2. **监控:**
   * 监控 Golden Signals（Latency、Traffic、Errors、Saturation）
   * 检查 Istiod 资源使用情况
   * 在每个阶段观察 24-48 小时
3. **自动化:**
   * 集成到 CI/CD pipeline
   * 自动化 Smoke Tests
   * 准备回滚脚本
4. **沟通:**
   * 与团队共享升级计划
   * 审查 release notes
   * 记录变更

**参考资料:**

* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [升级策略](../../../service-mesh/istio/best-practices.md#upgrade-strategy)

</details>

***

## 分数计算

* 多项选择题 1-5: 每题 10 分（共 50 分）
* 简答题 6-10: 每题 10 分（共 50 分）
* **总分: 100 分**

**评价标准:**

* 90-100 分: 优秀（完全理解 Istio 基础概念）
* 80-89 分: 良好（能够进行基本操作）
* 70-79 分: 一般（建议进一步学习）
* 60-69 分: 低于平均水平（需要复习基础概念）
* 0-59 分: 需要重新学习

## 学习资源

* [Istio 安装指南](../../../service-mesh/istio/01-installation.md)
* [核心概念](../../../service-mesh/istio/02-basic-concepts.md)
* [组件](../../../service-mesh/istio/03-architecture.md)
* [Istio 官方文档](https://istio.io/latest/docs/)
