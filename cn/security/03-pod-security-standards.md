# Pod 安全标准（PSS）

> **验证基线**：Kubernetes PSA 库 `k8s.io/pod-security-admission` v0.36.2；示例 PSS 策略 v1.35
> **最后更新**：2026年11月16日

Pod 安全标准（PSS）是 Kubernetes 中用于 Pod 安全的标准化策略框架。本文介绍 PSS 的概念、配置方法，以及在 EKS 环境中的实施方式。

PSS 定义策略；PSA 是应用这些策略的内置准入实现。除非另有说明，本指南均以**不使用用户命名空间的普通 Linux Pod**为前提。上游本地策略评估与 Schema/命令检查，和部署是不同的事情：未对实时集群、EKS 或容器执行进行测试。示例中的 `v1.35` 是固定版本的策略定义，并不表示 Kubernetes/EKS 当前支持的最新版本。API 服务器升级后，`latest` 所代表的版本也会随之变化。

## 目录

1. [从 PSP 到 PSS 的演进](#evolution-from-psp-to-pss)
2. [Pod Security Admission（PSA）控制器](#pod-security-admission-psa-controller)
3. [安全级别](#security-levels)
4. [强制执行模式](#enforcement-modes)
5. [命名空间级配置](#namespace-level-configuration)
6. [从 PSP 迁移到 PSS](#migration-from-psp-to-pss)
7. [EKS 默认设置与配置](#eks-defaults-and-configuration)
8. [安全配置文件详情](#security-profile-details)
9. [例外配置](#exemptions-configuration)
10. [逐步采用的最佳实践](#best-practices-for-gradual-adoption)

---

## 从 PSP 到 PSS 的演进 {#evolution-from-psp-to-pss}

### PodSecurityPolicy（PSP）的历史

PodSecurityPolicy（PSP）最初于 Kubernetes 1.3 中引入，作为 Pod 安全机制。然而，由于以下问题，它在 Kubernetes 1.21 中被弃用，并在 1.25 中被彻底移除：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Key Issues with PSP                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. Complex RBAC binding requirements                             │
│ 2. Implicit policy application (unclear which policy applies)    │
│ 3. User vs workload permission confusion                         │
│ 4. No warn/audit rollout modes                                               │
│ 5. Limited audit capabilities                                    │
└─────────────────────────────────────────────────────────────────┘
```

### PSS 的引入

Pod 安全标准（PSS）和 Pod Security Admission（PSA）在 Kubernetes 1.22 中以 Alpha 形式引入，在 1.23 中达到 Beta 阶段，并于 1.25 正式 GA（普遍可用）。

![路线图区分了 PSP 弃用、PSP 移除和 PSA 在 1.25 中 GA，以及之后按版本演进的策略。](../.gitbook/assets/en-security-03-pod-security-standards-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-0.html)

> 图表解读：PSA 在 1.25 中达到 GA；1.28 并非单独的稳定化里程碑。

### PSP 与 PSS 对比

| 特性 | PodSecurityPolicy（PSP） | Pod 安全标准（PSS） |
|---------|------------------------|------------------------------|
| **启用方式** | 以前的准入插件 | 由内置 PSA 插件强制执行 PSS 定义 |
| **策略定义** | 自定义 PSP 资源 | 三种预定义配置文件 |
| **策略绑定** | 复杂的 RBAC 绑定 | 简单的命名空间标签 |
| **作用范围** | 集群级或命名空间级 | 命名空间级 |
| **策略预览** | 无 PSA 风格的 warn/audit 模式；API dry-run 是另一项功能 | warn/audit 模式以及 API dry-run |
| **审计** | 有限 | 内置审计支持 |
| **灵活性** | 高（精细控制） | 中（标准化配置文件） |
| **复杂度** | 高 | 低 |

---

## Pod Security Admission（PSA）控制器 {#pod-security-admission-psa-controller}

### PSA 架构

PSA **在 API 服务器内部、验证准入期间运行**，并且在变更准入之后执行。身份验证、授权、Schema 验证和其他准入检查也同样适用。PSA 不是外部 Webhook，图表也不应暗示 PSA 与所有其他验证器之间存在普遍固定的顺序。

```text
Request → authentication / authorization → mutating admission
        → validating admission (PSA + other checks) → persistence if accepted
```

### PSA 的工作方式

![经过身份验证和授权的简化 Pod CREATE。PSA 在 API 服务器内部运行；只有其他准入检查和存储都成功后，201 才会成立。](../.gitbook/assets/en-security-03-pod-security-standards-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-1.html)

> 图表范围：PSA 在 API 服务器内部运行。只有通过所有适用检查后，成功的 Pod CREATE 才会被持久化；仅获 PSA 批准并不能保证返回 201 Created。

### 验证 PSA 状态

PSA 在 Kubernetes 1.23 中达到 Beta 阶段并默认启用，随后在 1.25 中达到 GA。未显式设置 `--enable-admission-plugins=PodSecurity` 标志，并不意味着 PSA 已禁用。对于自管理的 API 服务器，应检查其配置中是否显式禁用了 PSA；EKS 不会公开此配置。指标显示的是评估结果，而不是功能门控设置。访问 `/metrics` 需要授权，而且未使用的时间序列可能不存在。

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" get --raw /metrics
```

使用下方的正向/负向 Pod dry-run 控制来测试实际准入路径。切勿仅凭 Deployment dry-run 成功就推断其符合要求。

---

## 安全级别 {#security-levels}

PSS 定义了三个安全级别（配置文件）。每个级别都会逐步施加更严格的安全约束。

### 1. Privileged

此配置文件不增加任何 PSS 限制。它既不会自动启用容器特权，也不会绕过 RBAC、API 验证或其他准入策略。

```yaml
# Privileged profile: PSS imposes no controls; API/RBAC/other policies still apply
# Use cases: System daemons, CNI plugins, monitoring agents

apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: pss-privileged-lab
spec:
  hostNetwork: true      # Allowed
  hostPID: true          # Allowed
  hostIPC: true          # Allowed
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true   # Allowed
      runAsUser: 0    # Allowed
```

**Privileged 级别允许：**
- 主机网络、PID、IPC 命名空间
- 特权容器
- 所有 capabilities
- HostPath 挂载
- 任意用户/组 ID

### 2. Baseline

施加最低限度的限制，以防止已知的特权提升。适用于大多数通用工作负载。

```yaml
# Baseline level: Prevents known privilege escalations
# Use cases: General applications, web servers, API servers

apiVersion: v1
kind: Pod
metadata:
  name: baseline-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      # The following are prohibited in Baseline:
      # privileged: true        ❌
      # allowPrivilegeEscalation is not constrained by Baseline

      # The following are allowed in Baseline:
      runAsNonRoot: false      # ✓ (allowed but not recommended)
      readOnlyRootFilesystem: false  # ✓ (allowed)
    ports:
    - containerPort: 80
```

**Baseline 级别限制：**

| 字段 | 限制 |
|-------|------------|
| HostProcess | 禁止 Windows HostProcess 容器 |
| 主机命名空间 | 禁止 hostNetwork、hostPID、hostIPC |
| 特权容器 | 禁止 privileged: true |
| Capabilities | 显式添加的项目仅限于列出的 Baseline 允许列表；其中不包含 `NET_RAW` |
| HostPath 卷 | 禁止 hostPath 卷 |
| 主机端口 | 内置 PSA 允许未设置或为 0；它没有自定义端口允许列表 |
| AppArmor | 未设置，或为 RuntimeDefault/Localhost；旧版注解使用 runtime/default 或 localhost/* |
| SELinux | 仅允许受限的类型值；禁止设置用户/角色 |
| /proc 挂载类型 | 仅允许默认值 |
| Seccomp | 允许未设置；若已指定，则必须为 RuntimeDefault 或 Localhost（不能是 Unconfined） |
| Sysctls | 仅允许该 PSS 版本明确列出的 sysctl 允许列表；并非所有 kubelet 安全的 sysctl 都允许 |

### 3. Restricted

限制最严格的策略，应用 Pod 安全加固最佳实践。适用于对安全要求较高的工作负载。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

**Restricted 级别的附加限制：**

| 字段 | 限制 |
|-------|------------|
| 卷类型 | 仅允许 configMap、csi、downwardAPI、emptyDir、ephemeral、persistentVolumeClaim、projected、secret |
| 特权提升 | 必须设置 allowPrivilegeEscalation: false |
| 以非 root 身份运行 | 必须设置 runAsNonRoot: true |
| 以非 root 用户运行 | 禁止显式设置 runAsUser: 0（v1.23+）；可省略该字段 |
| Seccomp | 必须为 RuntimeDefault 或 Localhost |
| Capabilities | 必须丢弃所有 capabilities；仅允许添加 NET_BIND_SERVICE |



这些控制适用于所有符合条件的常规容器、init 容器和临时容器。Pod 级别的非 root/seccomp 值可以继承；冲突的容器级覆盖值不符合要求。v1.34+ 的策略还禁止在 HTTP/TCP 探针和生命周期钩子中使用非空的 `host`。在 v1.35 中，`hostUsers: false` 会放宽非 root 检查；Baseline 也会放宽 `procMount`，但 Restricted 仍禁止 `Unmasked`。这要求实际支持用户命名空间，而不仅仅是添加标签。针对 Windows 的特权提升、seccomp 和 Linux capabilities 放宽规则，与此 Linux 示例相互独立。

#### 2026年11月更新：AWS Batch 对 EKS 上安全上下文的支持

2026年11月13日，AWS 宣布 AWS Batch 在 Amazon EKS 作业定义中支持更多 Kubernetes 安全上下文设置，包括 Linux capabilities、seccomp 配置文件和 Pod 级设置。因此，在强制执行 Pod 安全标准 **restricted** 配置文件的 EKS 集群上，AWS Batch 作业现在可以仅使用所需的权限运行。详情请参阅[公告](https://aws.amazon.com/about-aws/whats-new/2026/11/aws-batch-eks-security-context/)。

### 安全级别对比图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Security Level Comparison                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Restriction  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶       │
│               Low                                           High          │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Privileged  │    │   Baseline   │    │  Restricted  │               │
│  │              │    │              │    │              │               │
│  │ No           │    │ Prevent      │    │ Security     │               │
│  │ restrictions │    │ known        │    │ best         │               │
│  │              │    │ escalations  │    │ practices    │               │
│  │              │    │              │    │              │               │
│  │ Use cases:   │    │ Use cases:   │    │ Use cases:   │               │
│  │ - CNI        │    │ - General    │    │ - Financial  │               │
│  │ - CSI        │    │   apps       │    │   apps       │               │
│  │ - Monitoring │    │ - Web        │    │ - Healthcare │               │
│  │              │    │   servers    │    │ - Multi-     │               │
│  │              │    │ - API        │    │   tenant     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 强制执行模式 {#enforcement-modes}

PSA 提供三种强制执行模式。这些模式可以单独使用，也可以组合使用。

### 1. enforce

拒绝违反策略的 Pod 创建和相关 Pod 更新。工作负载模板会接受 warn/audit 检查；实际强制执行发生在生成的 Pod 上。更改命名空间标签不会驱逐已经运行的 Pod。

```yaml
# enforce mode: Block Pod creation on violation
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
```

**响应示例片段（并非记录的集群执行结果）：**
```text
# Attempting to create a policy-violating Pod
$ kubectl apply --dry-run=server -f privileged-pod.yaml -n production
Error from server (Forbidden): error when creating "privileged-pod.yaml":
pods "privileged-pod" is forbidden: violates PodSecurity "restricted:v1.35":
privileged (container "app" must not set securityContext.privileged=true),
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false)
```

### 2. audit

向审计事件添加违规注解；此模式本身不会拒绝请求。是否保留这些事件取决于审计策略/日志传送配置。其他模式和准入检查仍可能拒绝请求。

```yaml
# audit mode: Record violations in audit logs
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
```

**合成审计事件片段（并非完整的已捕获事件）：**
```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "Metadata",
  "auditID": "00000000-0000-4000-8000-000000000001",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/staging/pods",
  "verb": "create",
  "user": {
    "username": "developer@example.com"
  },
  "objectRef": {
    "resource": "pods",
    "namespace": "staging",
    "name": "my-pod"
  },
  "annotations": {
    "pod-security.kubernetes.io/audit-violations": "privileged (container \"app\" must not set securityContext.privileged=true)"
  }
}
```

### 3. warn

向客户端返回可见警告，但本身不会拒绝请求；enforce 模式或其他准入检查仍可能拒绝请求。

```yaml
# warn mode: Display warning messages on violation
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

**警告示例片段（并非记录的执行结果）：**
```text
$ kubectl apply --dry-run=server -f non-compliant-pod.yaml -n development
Warning: would violate PodSecurity "restricted:v1.35":
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false),
unrestricted capabilities (container "app" must set
securityContext.capabilities.drop=["ALL"])
pod/my-pod created (server dry run)
```

### 模式组合策略

初始的 Privileged 阶段仅适用于尚无更严格既有策略的命名空间。切勿为了遵循此图而降低现有的 Baseline/Restricted 强制级别。

在生产环境中，建议组合使用多种模式：

```yaml
# Recommended configuration: Use mode combinations
apiVersion: v1
kind: Namespace
metadata:
  name: app-namespace
  labels:
    # Current enforcement level
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    # Audit next level
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    # Warn next level
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mode Combination Strategy                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Assess Current State                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: privileged                                      │   │
│  │ audit: baseline                                          │   │
│  │ warn: baseline                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 2: Gradual Hardening                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: baseline                                        │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 3: Final Goal                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: restricted                                      │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 命名空间级配置 {#namespace-level-configuration}

### 基本标签配置

通过命名空间标签配置 PSS：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    # Format: pod-security.kubernetes.io/<MODE>: <LEVEL>
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### 版本指定

可以使用特定 Kubernetes 版本中的 PSS 定义：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: versioned-namespace
  labels:
    # Use PSS definitions from a specific version
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35  # Specific version

    # Using 'latest' applies PSS from current cluster version
    # pod-security.kubernetes.io/enforce-version: latest
```

### 环境特定配置示例

```yaml
---
# Development environment: Relaxed policy
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: development
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/warn: restricted
---
# Staging environment: Intermediate policy
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# Production environment: Strict policy
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 为现有命名空间添加标签

```bash
# Add labels using kubectl
kubectl label namespace my-namespace \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Verify labels
kubectl get namespace my-namespace -o yaml | grep pod-security
```

---

## 从 PSP 迁移到 PSS {#migration-from-psp-to-pss}

### 迁移概述

从 PSP 迁移到 PSS 应谨慎规划并分阶段进行。

![迁移过程在评估差距、观察 warn/audit、修正并验证目标策略的同时保留现有强制策略。PSP API 清理仅适用于历史上的 1.24 或更早版本环境。](../.gitbook/assets/en-security-03-pod-security-standards-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-03-pod-security-standards-2.html)

> 图表范围：PSP 分析/移除属于历史操作。观察期间切勿降低现有更严格的 enforce 策略；readOnlyRootFilesystem 是建议项，不是 Restricted 的要求。

### 步骤 1：分析当前 PSP

**仅适用于历史流程**：以下 PSP 命令/资源适用于仍提供 `policy/v1beta1` 的旧集群（Kubernetes 1.24 及更早版本），或已保存的清单。不要将此 PSP 应用于当前集群。还应盘点此前由 PSP 默认填充/变更的字段；PSA 不会填充这些字段。

```bash
# List current PSPs
kubectl get psp

# Get PSP details
kubectl get psp <psp-name> -o yaml

# Check Pods with PSP applied
kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.metadata.annotations.kubernetes\.io/psp}{"\n"}{end}'
```

### 步骤 2：将 PSP 映射到 PSS 配置文件

```yaml
# Example: Existing PSP
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
```

**映射结果**：Restricted 是一个候选目标，而非等效策略。此 PSP 缺少所需的 seccomp 控制，并允许设置 PSS 可能会拒绝的 SELinux 选项。请比较每项控制和每个生成的 Pod；仅凭选出的三个字段无法证明两者等效。

### PSP 到 PSS 映射表

| 工作负载需求 | 候选 PSS 配置文件 | 必须审查的内容 |
|---|---|---|
| 主机命名空间、特权容器或 hostPath | Privileged | 隔离例外并施加额外控制 |
| 不访问主机，但需要 root 进程 | Baseline | 检查所有 Baseline 控制，包括 capabilities 和 seccomp |
| 非 root、无特权提升、丢弃 ALL | Restricted | 还需检查卷、seccomp、覆盖设置和特定版本的控制 |

### 步骤 3：在测试环境中验证

```bash
# Create test namespace
kubectl create namespace pss-test

# Apply restricted in warn mode
kubectl label namespace pss-test \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/warn-version=v1.35

# Test existing workload deployment
kubectl apply -f my-deployment.yaml -n pss-test

# Check warnings and modify workloads
```

### 步骤 4：逐步应用

```yaml
# Staged migration namespace configuration
apiVersion: v1
kind: Namespace
metadata:
  name: migrating-namespace
  labels:
    # Phase 1: New namespace without a previous stronger enforce policy
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline

    # Phase 2: Apply baseline, monitor restricted
    # pod-security.kubernetes.io/enforce: baseline
    # pod-security.kubernetes.io/audit: restricted
    # pod-security.kubernetes.io/warn: restricted

    # Phase 3: Final restricted enforcement
    # pod-security.kubernetes.io/enforce: restricted
```

### 步骤 5：修改工作负载

修改前：未设置安全上下文的普通 `nginx` Pod 无法通过 Restricted 检查。仅添加 `runAsNonRoot` 并不足够：镜像用户、监听端口和可写路径也必须兼容。修正后的 Pod 使用上游非特权镜像（UID/GID 101）、端口 8080，并在只读根文件系统中提供可写的 `/tmp`。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: new-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### 迁移自动化脚本

此脚本有意仅针对**一个经过审查的命名空间**，只添加此前不存在的 warn/audit 标签，保留 enforce，并使用观测到的资源版本来拒绝并发编辑。运行时会实际修改命名空间；请先检查目标。若标签已存在，脚本会报错以便人工比较，而不会自动降级。警告会在后续请求中出现，不会追溯扫描所有正在运行的 Pod。

```python
#!/usr/bin/env python3
# add-pss-observation.py CONTEXT NAMESPACE
import json, subprocess, sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: add-pss-observation.py CONTEXT NAMESPACE")
context, namespace = sys.argv[1:]
if namespace in {"kube-system", "kube-public", "kube-node-lease"}:
    raise SystemExit("Refusing system namespace; review its workload requirements separately")
base = ["kubectl", "--context", context, "--request-timeout=30s"]
obj = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = obj["metadata"].get("labels", {})
new = {
    "pod-security.kubernetes.io/warn": "restricted",
    "pod-security.kubernetes.io/warn-version": "v1.35",
    "pod-security.kubernetes.io/audit": "restricted",
    "pod-security.kubernetes.io/audit-version": "v1.35",
}
if any(key in labels for key in new):
    raise SystemExit("Existing observation policy: review it; do not overwrite automatically")
subprocess.run(base + [
    "label", "namespace", namespace,
    "--resource-version=" + obj["metadata"]["resourceVersion"],
] + [key + "=" + value for key, value in new.items()], check=True)
```

---

## EKS 默认设置与配置 {#eks-defaults-and-configuration}

### EKS 中的 PSA 默认设置

AWS 文档说明，EKS 1.23 起默认启用 PSA；集群默认值为所有模式使用 `privileged/latest`，且没有静态例外。这些宽松的默认值并不是工作负载加固策略。平台工具或管理员创建的命名空间标签可以覆盖默认值；应检查实际命名空间，而不要假设每个命名空间都没有标签。

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
```

### 在 EKS 中配置 PSS

```yaml
# Apply PSS to EKS namespace
apiVersion: v1
kind: Namespace
metadata:
  name: eks-app-namespace
  labels:
    # Example rollout choice, not a universal AWS requirement
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

    # EKS-related labels
    app.kubernetes.io/managed-by: eks
```

### EKS 系统命名空间注意事项

需要访问主机的代理无法满足 Baseline，但这并不意味着 `kube-system` 中的每个 Pod 都需要完整特权。应检查具体的附加组件版本和渲染后的 Pod 规格。避免通过一刀切的覆盖操作，禁用整个系统命名空间的 warn/audit。尽可能将获准的主机代理与普通应用隔离，并限制可以向其中部署工作负载的人员。以下是专用示例命名空间，并非要求重新标记现有系统命名空间。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### EKS 附加组件与 PSS 兼容性

| 组件/典型部署 | PSS 审查要点 |
|---|---|
| VPC CNI `aws-node`、kube-proxy | 主机网络或特权节点操作可能超出 Baseline 允许范围 |
| EBS/EFS CSI 节点 DaemonSet | 主机挂载可能超出 Baseline 允许范围；控制器 Pod 的需求不同 |
| 节点级 CloudWatch Agent/Fluent Bit | 对主机日志/文件系统的访问取决于实际配置 |
| CoreDNS、AWS Load Balancer Controller、Cluster Autoscaler | 根据渲染后的规格检查其是否符合 Baseline/Restricted；仅凭组件名称无法证明其合规 |

EKS Auto Mode 内置节点组件与自管理附加组件有所不同。此表仅供审查参考，不是经过测试的兼容性矩阵，也不表示必须安装列出的所有附加组件。

### EKS Terraform 示例

此代码片段管理一个应用命名空间。Kubernetes Provider 及其目标上下文需单独配置和审查；未运行 Provider 初始化、plan 或 apply。应由现有所有者通过认领/导入来管理已有命名空间，而不是另建相互冲突的 Terraform/GitOps 所有权。策略有意固定版本，且不会更改任何系统命名空间标签。

```hcl
# Provider authentication/context and ownership must be configured separately.
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = "my-app"
    labels = {
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "v1.35"
      "pod-security.kubernetes.io/audit"           = "restricted"
      "pod-security.kubernetes.io/audit-version"   = "v1.35"
      "pod-security.kubernetes.io/warn"            = "restricted"
      "pod-security.kubernetes.io/warn-version"    = "v1.35"
      "environment"                              = "production"
    }
  }
}
```

---

## 安全配置文件详情 {#security-profile-details}

### Privileged 配置文件详情

Privileged 配置文件不施加任何 PSS 限制；API 验证、RBAC 和其他准入检查仍然有效。以下主机 root 示例仅用于策略分析，并非建议部署的工作负载。

```yaml
# All options allowed in Privileged profile
apiVersion: v1
kind: Pod
metadata:
  name: privileged-example
spec:
  hostNetwork: true
  hostPID: true
  hostIPC: true
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true
      allowPrivilegeEscalation: true
      runAsUser: 0
      capabilities:
        add:
          - ALL
    volumeMounts:
    - name: host-root
      mountPath: /host
  volumes:
  - name: host-root
    hostPath:
      path: /
      type: Directory
```

### Baseline 配置文件详情

```yaml
# Baseline profile restrictions (v1.35)
#
# Prohibited fields and values:
#
# spec.hostNetwork: true prohibited
# spec.hostPID: true prohibited
# spec.hostIPC: true prohibited
#
# spec.containers[*].securityContext.privileged: true prohibited
# spec.initContainers[*].securityContext.privileged: true prohibited
# spec.ephemeralContainers[*].securityContext.privileged: true prohibited
#
# spec.containers[*].securityContext.capabilities.add restricted
#   - Allowed: NET_BIND_SERVICE (only this in Restricted)
#   - Additionally allowed in Baseline: AUDIT_WRITE, CHOWN, DAC_OVERRIDE,
#     FOWNER, FSETID, KILL, MKNOD, NET_BIND_SERVICE,
#     SETFCAP, SETGID, SETPCAP, SETUID, SYS_CHROOT
#
# spec.volumes[*].hostPath prohibited
#
# spec.containers[*].ports[*].hostPort prohibited (except 0)
#
# spec.securityContext.appArmorProfile.type restricted
#   - Allowed: profile omitted, or type RuntimeDefault/Localhost
#   - Prohibited: Unconfined
#
# spec.securityContext.seLinuxOptions.type restricted
#   - Prohibited: Custom types (container_t etc. allowed)
#
# spec.securityContext.seccompProfile.type restricted
#   - Prohibited: Unconfined
#
# spec.securityContext.sysctls restricted
#   - Only the explicit versioned PSS sysctl allowlist

apiVersion: v1
kind: Pod
metadata:
  name: baseline-compliant
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    ports:
    - containerPort: 8080
    securityContext:
      capabilities:
        drop: [ALL]
```

### Restricted 配置文件详情

Restricted 在 Baseline 的基础上增加卷允许列表、非 root 执行、显式 seccomp、禁止特权提升以及丢弃 ALL capabilities 等要求。仅允许添加 `NET_BIND_SERVICE`，但此处的 8080 监听器不需要它。`readOnlyRootFilesystem` 是建议的加固措施，不是 PSS 要求。设置 `containerPort` 只是元数据，不会重新配置 Nginx。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-compliant
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### 完整的 Restricted 合规 Nginx 示例

已根据上游 OCI 元数据检查该摘要适用于 Linux amd64/arm64（Nginx 1.30.4，用户 101）；未拉取镜像层，也未执行容器。上游文档说明使用端口 8080、`/tmp/nginx.pid`，以及 `/tmp` 下的临时路径。下方 ConfigMap 提供匹配的监听器和健康检查端点。请先在同一命名空间中创建 ConfigMap，再创建 Deployment。上线前，应在获准的环境中验证启动和就绪状态。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-restricted
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101  # nginx user
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: nginx
        image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 101
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: production
data:
  default.conf: |
    server {
        listen 8080;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /healthz {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
```

---

## 例外配置 {#exemptions-configuration}

### 集群级例外配置

自管理的 API 服务器可以通过 `--admission-control-config-file` 加载此配置。示例中的所有例外列表均为空。例外会跳过 **所有 PSA 模式**。`usernames` 匹配完全相同的已认证请求用户名，而不是组、通配符或未来 Pod 的 ServiceAccount。将控制器账户列为例外，会绕过其代表许多用户创建 Pod 时所需的检查。命名空间和 RuntimeClass 名称也必须完全匹配。只有在单独限制了例外的使用权限后，才应配置例外。

```yaml
# Self-managed API server configuration; not an EKS control-plane setting
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: baseline
      enforce-version: v1.35
      audit: restricted
      audit-version: v1.35
      warn: restricted
      warn-version: v1.35
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: []
```

### EKS 中的例外配置

EKS 不允许编辑其托管 API 服务器的 AdmissionConfiguration。命名空间 `enforce: privileged` 是一个宽松配置文件，**不是静态例外**：warn/audit 仍可评估请求。应限制命名空间写入/部署权限，并将主机代理与普通应用分开。例如，配置了 hostNetwork/hostPID/hostPath 的 node-exporter 无法通过 Baseline；设置 Baseline 并不会让这些主机访问变得安全或获准。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### 基于 RuntimeClass 的例外

RuntimeClass 用于选择已配置的 CRI 运行时处理程序。创建此资源不会安装 gVisor/Kata，也不会授予 PSA 例外。所有目标节点都必须支持该处理程序（或使用适当的调度约束）。仅凭以下定义，PSA 仍会完整适用：

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
```

只有在自管理 API 服务器上单独配置 `runtimeClasses: ["gvisor"]` 例外，才会跳过 PSA。任何获准选择该类的请求都可能因此绕过 PSA；运行时隔离不能取代准入授权。EKS 不提供这种托管控制平面配置。

### 使用 Kyverno 配置精细例外

Kyverno 无法将 PSA 拒绝的请求转换为允许。如果主机代理需要例外，应先设计命名空间的 PSA 配置文件和部署权限，然后再添加一个带有严格限定例外、且独立执行的策略。仅排除 HostPath 并不会排除 hostNetwork/hostPID 检查；仅匹配镜像标签或可变 Pod 标签并不能构成授权。

有关经过审查的策略 API 和版本/弃用限制，请参阅 [Kyverno 策略管理](./01-kyverno-policy-management.md)。不要复制旧版 `ClusterPolicy` 并使用小写的 `validationFailureAction: enforce`；这不是有效值，而且 ClusterPolicy 已在 Kyverno 1.19 中弃用。替代方案必须针对普通工作负载和例外工作负载进行测试。

---

## 逐步采用的最佳实践 {#best-practices-for-gradual-adoption}

### 步骤 1：分析当前状态

预览对 **enforce** 的更改，而不是 warn：只有 enforce 级别/版本更改才会触发对现有 Pod 的检查。此服务器端 dry-run 不会保存标签或驱逐 Pod。如果有效的 enforce 策略没有变化，就不会触发新的扫描。扫描尽力而为，可能会限制/去重警告；没有警告并不表示已完成完整的工作负载审计。命令/身份验证失败仍然属于失败。

```bash
#!/usr/bin/env bash
# preview-pss.sh: no namespace mutation
set -euo pipefail
: "${PSS_CONTEXT:?Set the approved test context}"
: "${PSS_NAMESPACE:?Set one namespace to inspect}"
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  label namespace "$PSS_NAMESPACE" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  --overwrite --dry-run=server
```

### 步骤 2：逐步推出策略

日期范围仅为示例性规划安排，并非实测的迁移时长。应使用明确的命名空间清单，切勿降低现有更严格的策略；只有在测试替代 Pod 和回滚能力后，才继续推进。

```yaml
# Gradual rollout using GitOps

# Phase 1: Monitoring (Day 1-7)
# - Apply warn: baseline to all namespaces
# - Collect and analyze violations

# Phase 2: Development Environment (Day 8-14)
# - Apply enforce: baseline to development namespaces
# - Apply warn: baseline to staging namespaces

# Phase 3: Staging Environment (Day 15-21)
# - Apply enforce: baseline to staging namespaces
# - Apply warn: baseline to production namespaces

# Phase 4: Production Environment (Day 22-28)
# - Apply enforce: baseline to production namespaces
# - Apply warn: restricted to all environments

# Phase 5: Restricted Hardening (Day 29+)
# - Apply enforce: restricted as default for new namespaces
# - Gradually migrate existing namespaces
```

### 步骤 3：设置监控和告警

这些规则需要 Prometheus Operator CRD、包含此 PrometheusRule 的选择器，以及能够暴露 `pod_security_evaluations_total` 的授权 API 服务器抓取端点。内置 PSA 并不是名为 `pod-security-webhook` 的 Webhook。评估标签包括 decision、policy_level、policy_version、mode、request_operation、resource 和 subresource；**没有 namespace 标签**。请关联保留的审计事件，以获取命名空间/请求详情。缺少指标不能证明违规次数为零；audit 模式中的 deny 表示评估发现违规，不一定表示 API 请求已被拒绝。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pss-violations
  namespace: monitoring
spec:
  groups:
  - name: pod-security-standards
    rules:
    - alert: PSSViolationDetected
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="enforce",decision="deny"}[5m])
        ) > 0
      labels:
        severity: warning
      annotations:
        summary: "PSA denied a Pod request"
        description: "Policy {{ $labels.policy_level }}:{{ $labels.policy_version }}. Correlate audit logs for namespace and request identity."
    - alert: PSSAuditViolation
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="audit",decision="deny"}[5m])
        ) > 10
      for: 5m
      labels:
        severity: info
      annotations:
        summary: "PSA audit violations increasing"
        description: "{{ $value }} violating evaluations over five minutes; not a count of unique Pods."
```

### 步骤 4：自动化合规检查

将此脚本保存为工作负载所属项目中的 `check-pss.py`。前置条件：Python 3 和 PyYAML、兼容的 kubectl、获准的集群凭证、支持策略 v1.35 的 Kubernetes API 服务器，以及一个已存在且显式强制执行 `restricted:v1.35` 的测试命名空间。即使使用服务器端 dry-run，调用者也需要命名空间读取权限和 Pod 创建授权。不要将集群凭证暴露给不可信的拉取请求代码。

```python
#!/usr/bin/env python3
# check-pss.py CONTEXT NAMESPACE pod.yaml [pod2.yaml ...]
# Requires Python 3 + PyYAML and a preconfigured, authorized kubectl.
import copy, json, subprocess, sys
from pathlib import Path
import yaml

if len(sys.argv) < 4:
    raise SystemExit("Usage: check-pss.py CONTEXT NAMESPACE pod.yaml [...]")
context, namespace, *files = sys.argv[1:]
pods = []
for filename in files:
    docs = list(yaml.safe_load_all(Path(filename).read_text()))
    if not docs or any(not isinstance(p, dict) for p in docs):
        raise SystemExit(f"{filename}: empty/non-object YAML")
    for pod in docs:
        if (pod.get("apiVersion"), pod.get("kind")) != ("v1", "Pod"):
            raise SystemExit(f"{filename}: only explicit v1 Pod test inputs are supported")
        meta = pod.setdefault("metadata", {})
        if meta.get("namespace", namespace) != namespace:
            raise SystemExit(f"{filename}: namespace mismatch")
        meta["namespace"] = namespace
        pods.append(pod)
base = ["kubectl", "--context", context, "--request-timeout=30s"]
ns = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = ns["metadata"].get("labels", {})
if (labels.get("pod-security.kubernetes.io/enforce"),
    labels.get("pod-security.kubernetes.io/enforce-version")) != ("restricted", "v1.35"):
    raise SystemExit("Test namespace must explicitly enforce restricted:v1.35")

def dry_run(pod):
    return subprocess.run(
        base + ["create", "--dry-run=server", "--validate=strict",
                "--namespace", namespace, "-f", "-"],
        input=json.dumps(pod), text=True, capture_output=True)

control = {
    "apiVersion": "v1", "kind": "Pod",
    "metadata": {"generateName": "pss-control-", "namespace": namespace},
    "spec": {
        "automountServiceAccountToken": False,
        "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                            "seccompProfile": {"type": "RuntimeDefault"}},
        "containers": [{"name": "probe", "image": "registry.k8s.io/pause:3.10",
                        "securityContext": {"allowPrivilegeEscalation": False,
                                            "capabilities": {"drop": ["ALL"]}}}],
    },
}
good = dry_run(control)
if good.returncode:
    raise SystemExit("Positive control failed; no compliance result:\n" + good.stderr)
bad = copy.deepcopy(control)
bad["spec"]["hostPID"] = True
denied = dry_run(bad)
if denied.returncode == 0 or 'violates PodSecurity "restricted:v1.35"' not in denied.stderr:
    raise SystemExit("Negative control did not confirm PSA rejection:\n" + denied.stderr)
for pod in pods:
    result = dry_run(pod)
    if result.returncode:
        raise SystemExit("Pod dry-run failed:\n" + result.stderr)
print(f"{len(pods)} explicit Pod inputs passed server dry-run in {namespace}")
```

```bash
python3 check-pss.py "$PSS_CONTEXT" "$PSS_NAMESPACE" ./pss-inputs/web-pod.yaml
```

显式输入列表必须涵盖每个工作负载的 Pod 模板，包括 init 容器。此示例会拒绝 Deployment、空文件、命名空间错误、查询失败、缺少强制策略，以及例外/未启用的负向控制路径。模板提取、变更 Webhook、调度、镜像启动和未来的运行时行为需要单独检查。负向控制必须被 PSA 拒绝；任何其他错误都无法得出结论，因此检查会失败。候选 Pod 选择的其他例外（例如被豁免的 RuntimeClass）也必须禁止，或由测试集群所有者单独测试。

### 步骤 5：文档和培训

```markdown
# Pod Security Standards Guidelines

## Checklist for Developers

### When Writing Restricted-Level Pods:

- [ ] Set `spec.securityContext.runAsNonRoot: true`
- [ ] Set `spec.securityContext.seccompProfile.type: RuntimeDefault`
- [ ] Set `allowPrivilegeEscalation: false` on all containers
- [ ] Set `capabilities.drop: ["ALL"]` on all containers
- [ ] Set `readOnlyRootFilesystem: true` (recommended)
- [ ] Use unprivileged images (e.g., nginxinc/nginx-unprivileged)
- [ ] Mount emptyDir for writable paths

### Common Problem Solutions:

1. **nginx fails to bind port 80**
   → Add `NET_BIND_SERVICE` capability or use port 8080

2. **File write failures**
   → Mount emptyDir volumes to required paths

3. **Process runs as root**
   → Use unprivileged base image or add USER directive in Dockerfile
```

---

## 故障排除

### 常见错误及解决方法

#### 1. “allowPrivilegeEscalation != false”错误

错误示例片段；此 YAML 是**部分 Pod 规格修正内容**，不是独立清单。请保留现有容器镜像/配置。也应对 init 容器和临时容器应用相关的容器级控制。

```text
allowPrivilegeEscalation != false
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
```

#### 2. “unrestricted capabilities”错误

错误示例片段；此 YAML 是**部分 Pod 规格修正内容**，不是独立清单。请保留现有容器镜像/配置。也应对 init 容器和临时容器应用相关的容器级控制。

```text
unrestricted capabilities
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      capabilities:
        drop: [ALL]
```

#### 3. “runAsNonRoot != true”错误

错误示例片段；此 YAML 是**部分 Pod 规格修正内容**，不是独立清单。请保留现有容器镜像/配置。也应对 init 容器和临时容器应用相关的容器级控制。

```text
runAsNonRoot != true
```

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
```

#### 4. “seccompProfile”错误

错误示例片段；此 YAML 是**部分 Pod 规格修正内容**，不是独立清单。请保留现有容器镜像/配置。也应对 init 容器和临时容器应用相关的容器级控制。

```text
seccompProfile must be RuntimeDefault or Localhost
```

```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
```

### PSS 违规检查工具

Polaris、kube-score 和 Trivy 可提供额外的静态检查，但不能精确替代集群的版本化 PSA 策略、例外和变更行为。请安装经过审查的版本，并查阅其 CLI 帮助。服务器端 dry-run 成功仅适用于该请求、身份、命名空间和执行时点；请使用上文的显式 Pod 控制。

```bash
# Dry-run check with kubectl
kubectl apply -f my-pod.yaml --dry-run=server

# Check with Polaris
polaris audit --audit-path ./k8s/ --format pretty

# Check with kube-score
kube-score score my-deployment.yaml

# Configuration check with Trivy
trivy config ./k8s/
```

---

## 总结

Pod 安全标准（PSS）为管理 Kubernetes 中的 Pod 安全提供了标准化方法：

1. **三个安全级别**：Privileged（所有特权）、Baseline（防止已知的特权提升）、Restricted（最小权限）
2. **三种强制执行模式**：enforce（阻止）、audit（记录日志）、warn（警告）
3. **命名空间标签**：没有 PSP 风格的用户绑定；仍须通过 RBAC 限制命名空间标签和工作负载创建
4. **支持逐步采用**：通过 warn/audit 模式安全迁移

### 建议

- 从一开始就在新集群中启用 PSS
- 对现有集群从 warn 模式开始，逐步加强策略
- 在生产环境中至少应用 Baseline 级别
- 对敏感工作负载应用 Restricted 级别

---

## 参考资料

- [Kubernetes Pod 安全标准官方文档](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission 官方文档](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [EKS 最佳实践指南 - Pod 安全](https://docs.aws.amazon.com/eks/latest/best-practices/pod-security.html)
- [从 PSP 迁移到 PSS 指南](https://kubernetes.io/docs/tasks/configure-pod-container/migrate-from-psp/)

- [PSA 命名空间标签预览和现有 Pod 检查](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/)
- [PSA 配置和例外](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/)
- [Nginx 非特权镜像和可写路径](https://github.com/nginx/docker-nginx-unprivileged)
