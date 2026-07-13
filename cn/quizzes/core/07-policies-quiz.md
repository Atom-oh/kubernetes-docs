# 策略测验

本测验用于测试你对 Kubernetes 策略概念的理解，包括 resource quotas、limit ranges、pod security policies 和 network policies。

## 选择题

1. Kubernetes 中 ResourceQuota 的主要目的是什么？
   - A) 限制 pod 的 CPU 和内存使用量
   - B) 限制 namespace 内的资源创建
   - C) 监控整个集群的资源使用情况
   - D) 管理 node 资源分配
   
<details>
<summary>显示答案</summary>

**答案：B) 限制 namespace 内的资源创建**

**解析：**
ResourceQuota 限制 namespace 内可创建的资源总量。这不仅包括 CPU 和内存等计算资源，还包括 pods、services 和 configmaps 等对象的数量。使用 ResourceQuota 可以防止某个团队独占所有集群资源。
</details>

2. LimitRange 的主要功能是什么？
   - A) 限制 namespace 的总资源使用量
   - B) 为单个 containers 设置默认 resource requests 和 limits
   - C) 在集群 nodes 之间分配资源
   - D) 限制 pods 之间的网络通信
   
<details>
<summary>显示答案</summary>

**答案：B) 为单个 containers 设置默认 resource requests 和 limits**

**解析：**
LimitRange 为 namespace 内的 pods 或 containers 定义资源约束。这可以设置默认的 resource requests 和 limits，或强制执行最小/最大资源使用量。LimitRange 适用于单个资源，而 ResourceQuota 适用于整个 namespace。
</details>

3. PodSecurityPolicy (PSP) 在 Kubernetes v1.25 中被移除后，什么机制取代了它？
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints
   
<details>
<summary>显示答案</summary>

**答案：C) PodSecurityAdmission**

**解析：**
PodSecurityPolicy (PSP) 在 Kubernetes v1.25 中被移除，并由 PodSecurityAdmission 取代。这是一个基于 Pod Security Standards 的内置 admission controller，提供三个策略级别：Privileged、Baseline 和 Restricted。PodSecurityContext 用于在 pod 级别配置安全设置，而 SecurityContextConstraints 是 OpenShift 中使用的类似机制。
</details>

4. 使用 NetworkPolicy 无法完成什么？
   - A) 仅限制来自特定 namespace 的 pods 的流量
   - B) 仅限制到特定 IP CIDR 范围的流量
   - C) 仅限制到特定端口的流量
   - D) 检查特定协议的 payload 内容
   
<details>
<summary>显示答案</summary>

**答案：D) 检查特定协议的 payload 内容**

**解析：**
NetworkPolicy 提供 L3/L4 级别的防火墙策略，用于控制 pods 之间的通信。它可以基于特定 namespaces、labels、IP CIDR 范围、ports 等限制流量。但是，NetworkPolicy 无法执行 L7 级别的检查（例如 HTTP headers、payload 内容）。若需要此类功能，需要使用 service mesh（例如 Istio）或 API gateway。
</details>

5. Kubernetes 中 RBAC (Role-Based Access Control) 的主要目的是什么？
   - A) 控制 pods 之间的网络通信
   - B) 管理 users 和 service accounts 的权限
   - C) 限制资源使用量
   - D) 设置 pod 调度策略
   
<details>
<summary>显示答案</summary>

**答案：B) 管理 users 和 service accounts 的权限**

**解析：**
RBAC (Role-Based Access Control) 是一种控制 Kubernetes API 访问的机制。通过它，你可以定义 users、groups 或 service accounts 在集群内可以执行哪些操作。RBAC 使用 Role、ClusterRole、RoleBinding 和 ClusterRoleBinding 等资源来管理权限。
</details>

6. Pod Security Standards 中三个策略级别里限制最严格的是哪一个？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>显示答案</summary>

**答案：C) Restricted**

**解析：**
Pod Security Standards 定义了三个策略级别：
- Privileged：无限制，允许所有权限
- Baseline：防止已知的权限提升路径
- Restricted：应用增强安全设置的最严格策略

Restricted 策略限制最严格，遵循最小权限原则并应用安全最佳实践。该策略禁止 privileged containers、host namespace 共享、host path 挂载等。
</details>

7. AdmissionController 在 Kubernetes 中的作用是什么？
   - A) 用户身份验证
   - B) 监控资源使用情况
   - C) 验证和修改 API 请求
   - D) Pod 调度
   
<details>
<summary>显示答案</summary>

**答案：C) 验证和修改 API 请求**

**解析：**
AdmissionController 是一种 plugin，在请求通过身份验证和授权之后、对象存储到持久化存储之前，拦截并验证或修改发送到 Kubernetes API server 的请求。这允许集群管理员对资源创建和修改应用策略。例如，PodSecurityAdmission、ResourceQuota 和 LimitRanger 都是作为 AdmissionControllers 实现的。
</details>

8. Kubernetes 中 OPA (Open Policy Agent) Gatekeeper 的主要功能是什么？
   - A) 集群监控和日志记录
   - B) 基于策略的资源管理和验证
   - C) Auto scaling
   - D) Service mesh 管理
   
<details>
<summary>显示答案</summary>

**答案：B) 基于策略的资源管理和验证**

**解析：**
OPA Gatekeeper 是一种用于向 Kubernetes clusters 应用策略的可扩展解决方案。它基于 OPA (Open Policy Agent)，并使用 CustomResourceDefinitions (CRDs) 定义和应用策略。Gatekeeper 作为 AdmissionWebhook 运行，用于验证集群中创建或修改的资源是否符合已定义的策略。这使得应用各种策略成为可能，例如安全策略、资源限制和命名约定。
</details>

9. 在已应用 ResourceQuota 的 namespace 中创建 pod，但未指定 resource requests 和 limits 时，会发生什么？
   - A) Pod 会使用默认 resource requests 和 limits 创建
   - B) Pod 创建会被拒绝
   - C) Pod 会被创建但不会被调度
   - D) Pod 会被创建并可使用无限资源
   
<details>
<summary>显示答案</summary>

**答案：B) Pod 创建会被拒绝**

**解析：**
当 ResourceQuota 应用于 namespace，并且为 CPU 和内存等计算资源设置了配额时，该 namespace 中的所有 containers 都必须显式指定 resource requests 和 limits。否则，API server 会拒绝 pod 创建请求。这是为了在应用了配额的 namespaces 中准确跟踪和限制资源使用量。
</details>

10. Kubernetes 中 PriorityClass 的主要目的是什么？
    - A) 定义 pod 调度优先级
    - B) 设置 namespace 资源分配优先级
    - C) 确定 API 请求处理优先级
    - D) 设置 node 重要性级别
    
<details>
<summary>显示答案</summary>

**答案：A) 定义 pod 调度优先级**

**解析：**
PriorityClass 定义 pods 的调度优先级。当资源不足时，高优先级 pods 会先于低优先级 pods 被调度，并且在必要时可以抢占低优先级 pods。
</details>

## 简答题

1. 说明 ResourceQuota 和 LimitRange 的主要区别。

<details>
<summary>显示答案</summary>

**答案：**
ResourceQuota 限制整个 namespace 的资源使用量，而 LimitRange 为 namespace 内的单个 containers 或 pods 设置资源约束。

主要区别：
1. **范围**：ResourceQuota 适用于整个 namespace，LimitRange 适用于单个资源（pods、containers 等）。
2. **目的**：ResourceQuota 限制 namespace 的总资源使用量，而 LimitRange 通过默认设置、最小/最大限制等控制单个资源使用量。
3. **强制执行**：设置 ResourceQuota 后，超过配额的资源创建会被拒绝。LimitRange 在创建资源时应用默认值，或在超出限制时拒绝创建。
4. **资源类型**：ResourceQuota 不仅可以限制 CPU 和内存，还可以限制 pods、services 和 PVCs 等对象数量。LimitRange 主要关注 CPU、内存和存储等计算资源。
</details>

2. 说明 Pod Security Standards 的三个策略级别（Privileged、Baseline、Restricted）及其特征。

<details>
<summary>显示答案</summary>

**答案：**
Pod Security Standards 为 pod 安全设置定义了三个策略级别：

1. **Privileged**：
   - 最开放的策略，几乎没有限制。
   - 允许所有 privileged operations。
   - 可以使用 host namespaces、host ports、privileged containers 等。
   - 适合开发和管理工作，但在生产环境中存在显著安全风险。

2. **Baseline**：
   - 防止已知权限提升路径的中等级别策略。
   - 提供适用于大多数 workloads 的 baseline 安全级别。
   - 限制 privileged containers 和 host namespace 使用。
   - 但是，某些 privileged operations（例如 host path mounts）仍被允许。

3. **Restricted**：
   - 具有增强安全设置的最严格策略。
   - 遵循最小权限原则并强制执行安全最佳实践。
   - 禁止 privileged containers、host namespaces、host path mounts 和权限提升。
   - 强制 containers 以非 root users 身份运行。
   - 适合对安全要求严格的生产 workloads。
</details>

3. 说明如何使用 NetworkPolicy 将特定 namespace 中的 pods 限制为只能与另一个 namespace 中的特定 pods 通信。

<details>
<summary>显示答案</summary>

**答案：**
要使用 NetworkPolicy 将特定 namespace 中的 pods 限制为只能与另一个 namespace 中的特定 pods 通信：

1. **将 NetworkPolicy 应用于源 namespace**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-communication
  namespace: source-namespace  # Source namespace
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: destination-namespace  # Destination namespace label
      podSelector:
        matchLabels:
          app: specific-app  # Destination pod label
```

2. **将 NetworkPolicy 应用于目标 namespace**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-specific-namespace
  namespace: destination-namespace  # Destination namespace
spec:
  podSelector:
    matchLabels:
      app: specific-app  # Destination pod label
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: source-namespace  # Source namespace label
```

要使此方法生效，namespaces 必须具有适当的 labels：
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

NetworkPolicy 默认以 allow-list 模式运行，因此一旦应用这些策略，就只有显式允许的通信才可行，其他所有通信都会被阻止。
</details>

4. 说明可以在 Kubernetes 中使用 OPA Gatekeeper 实现的三个策略示例。

<details>
<summary>显示答案</summary>

**答案：**
可以使用 OPA Gatekeeper 实现的策略示例：

1. **Image Registry 限制**：
   - 强制 images 只能从已批准的 registries 拉取的策略
   - 示例：仅允许公司内部 registries 或特定受信任的公共 registries
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/trusted-project/"
   ```

2. **强制设置 Resource Requests 和 Limits**：
   - 强制所有 containers 都设置 resource requests 和 limits 的策略
   - 防止资源耗尽并确保正确的资源分配
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits-and-requests
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
       requests:
         - cpu
         - memory
   ```

3. **防止 Privileged Containers**：
   - 禁止运行 privileged containers 的策略
   - 降低安全风险并确保 container 隔离
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

（只需说明以上三个中的任意三个）
</details>

5. 说明如何使用 Kubernetes 中的 PriorityClass 确保重要 workloads 的可用性。

<details>
<summary>显示答案</summary>

**答案：**
使用 PriorityClass 确保重要 workloads 可用性的方法：

1. **定义 PriorityClass**：
   - 根据重要性创建具有不同优先级级别的 PriorityClasses
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **为重要 workloads 分配 PriorityClass**：
   - 向重要 pods 添加 PriorityClass 引用
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: critical-service
   spec:
     priorityClassName: high-priority
     containers:
     - name: app
       image: critical-service:latest
   ```

3. **利用抢占**：
   - 当资源不足时，高优先级 pods 可以抢占（驱逐）低优先级 pods 并被调度
   - 这可确保重要 workloads 始终能够运行

4. **考虑 System Priority Classes**：
   - Kubernetes 提供 system-cluster-critical (2000000000) 和 system-node-critical (2000001000) 等 system priority classes
   - 用户定义的 priority classes 通常应使用低于这些值的数值

5. **设计优先级层次结构**：
   - 根据 workload 重要性定义多个优先级级别
   - 示例：生产 services (900000)、内部工具 (500000)、开发/测试 (100000)
</details>

## 实践题

1. 创建一个满足以下要求的 ResourceQuota：
   - Namespace：team-a
   - 最多 10 个 pods
   - 最多 5 个 services
   - 总 CPU requests：4 cores
   - 总 memory requests：8Gi

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "10"
    services: "5"
    requests.cpu: "4"
    requests.memory: 8Gi
```

如何应用：
```bash
# Create namespace
kubectl create namespace team-a

# Apply ResourceQuota
kubectl apply -f team-a-quota.yaml
```

检查 ResourceQuota 状态：
```bash
kubectl describe resourcequota team-a-quota -n team-a
```
</details>

2. 创建一个满足以下要求的 LimitRange：
   - Namespace：team-b
   - Container 默认 request：CPU 100m，Memory 256Mi
   - Container 默认 limit：CPU 200m，Memory 512Mi
   - Container 最大 limit：CPU 1 core，Memory 2Gi

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: team-b-limits
  namespace: team-b
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    max:
      cpu: "1"
      memory: 2Gi
    type: Container
```

如何应用：
```bash
# Create namespace
kubectl create namespace team-b

# Apply LimitRange
kubectl apply -f team-b-limits.yaml
```

检查 LimitRange 状态：
```bash
kubectl describe limitrange team-b-limits -n team-b
```
</details>

3. 创建一个满足以下要求的 NetworkPolicy：
   - Namespace：web
   - 带有 app label 'frontend' 的 Pods 只能与带有 app label 'backend' 的 pods 通信
   - Backend pods 只允许在 port 8080 上通信

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend-only
  namespace: web
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend-only
  namespace: web
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

如何应用：
```bash
# Create namespace
kubectl create namespace web

# Apply NetworkPolicy
kubectl apply -f web-network-policies.yaml
```

检查 NetworkPolicy 状态：
```bash
kubectl describe networkpolicy -n web
```
</details>

4. 创建一个 PriorityClass 和一个使用它的 pod，满足以下要求：
   - PriorityClass name：high-priority
   - Priority value：100000
   - Description："For critical production workloads"
   - Pod name：critical-app
   - Image：nginx

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "For critical production workloads"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx
```

如何应用：
```bash
kubectl apply -f high-priority-pod.yaml
```

检查 PriorityClass 和 pod 状态：
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. 应用以下 Pod Security 设置：
   - Namespace：restricted-ns
   - Mode：enforce
   - Level：restricted

<details>
<summary>显示答案</summary>

**答案：**

在 Kubernetes 1.25 及以上版本中，可以通过向 namespace 添加 labels 来应用 Pod Security Standards：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

如何应用：
```bash
kubectl apply -f restricted-namespace.yaml
```

或向现有 namespace 添加 labels：
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## 高级主题

1. 说明 Kubernetes 中 OPA Gatekeeper 和 Kyverno 的区别，以及它们各自的优缺点。

<details>
<summary>显示答案</summary>

**答案：**

**OPA Gatekeeper 与 Kyverno 对比：**

1. **架构和方法**：
   - **OPA Gatekeeper**：基于 Open Policy Agent (OPA)，使用 Rego policy language。使用两个 CRDs 定义策略：ConstraintTemplate 和 Constraint。
   - **Kyverno**：使用自己的 policy engine，提供基于 YAML/JSON 的策略定义。使用单个 Policy CRD 定义策略。

2. **策略语言**：
   - **OPA Gatekeeper**：使用 Rego 语言，功能强大但学习曲线陡峭。
   - **Kyverno**：使用类似 Kubernetes resources 的 YAML 语法定义策略，对 Kubernetes users 更熟悉。

3. **功能**：
   - **OPA Gatekeeper**： 
     - 用于表达复杂策略的强大 policy language
     - 可以集成 data sources，用于基于外部数据的决策
     - 支持 policy libraries 和 reusable templates
   - **Kyverno**： 
     - 内置资源创建、修改和验证功能
     - Image 验证和修改功能
     - 创建资源时可以自动创建其他资源
     - Policy exception 处理功能

4. **优点**：
   - **OPA Gatekeeper**：
     - 更成熟且被广泛采用
     - 更适合复杂策略表达
     - 针对各种使用场景有丰富的文档和示例
     - OPA ecosystem 可在 Kubernetes 之外使用
   - **Kyverno**：
     - 使用熟悉的 YAML 语法，学习曲线更平缓
     - 不需要学习单独的 policy language
     - 内置资源创建和修改功能
     - 设置和配置更简单

5. **缺点**：
   - **OPA Gatekeeper**：
     - 需要学习 Rego 语言
     - 设置和配置复杂
     - 资源修改需要额外配置
   - **Kyverno**：
     - 相对不够成熟
     - 对于非常复杂的策略表达可能存在限制
     - 与 OPA 相比，性能可能较低

6. **选择标准**：
   - **选择 OPA Gatekeeper 的情况**：
     - 需要复杂策略逻辑
     - 已经使用 OPA 或熟悉 Rego
     - 需要在各种系统中一致地应用策略
   - **选择 Kyverno 的情况**：
     - 快速上手和低学习曲线很重要
     - 团队熟悉 Kubernetes resource 语法
     - 需要资源创建和修改功能
     - 只需要简单策略
</details>

2. 说明 Kubernetes 中 Pod Security Admission 和之前的 PodSecurityPolicy (PSP) 的主要区别。

<details>
<summary>显示答案</summary>

**答案：**

**Pod Security Admission 与 PodSecurityPolicy (PSP) 对比：**

1. **实现方式**：
   - **PodSecurityPolicy**：作为 API resource (CRD) 实现，通过 admission controller 应用。
   - **Pod Security Admission**：作为内置 admission controller 实现，通过 namespace labels 配置。

2. **配置方法**：
   - **PodSecurityPolicy**：Cluster admin 必须创建 PSP resources，并通过 RBAC 将它们绑定到 users/service accounts。
   - **Pod Security Admission**：通过向 namespaces 添加 labels 来应用，指定 enforcement level（enforce、audit、warn）和 policy level（privileged、baseline、restricted）。

3. **策略粒度**：
   - **PodSecurityPolicy**：可以进行非常细粒度的控制，能够单独配置各种 security context settings。
   - **Pod Security Admission**：只提供三个预定义 policy levels（privileged、baseline、restricted），无法单独调整详细设置。

4. **易用性**：
   - **PodSecurityPolicy**：设置复杂，需要 RBAC bindings，配置错误很常见。
   - **Pod Security Admission**：通过简单的 namespace labeling 应用，使用起来容易得多。

5. **范围**：
   - **PodSecurityPolicy**：适用于整个 cluster 或特定 users/service accounts。
   - **Pod Security Admission**：按 namespace 应用。

6. **模式**：
   - **PodSecurityPolicy**：采用应用或不应用的二元方式。
   - **Pod Security Admission**：提供三种模式（enforce、audit、warn），用于逐步应用。
     - enforce：违规时拒绝 pod 创建
     - audit：将违规记录到 audit log
     - warn：违规时显示 warning message

7. **迁移和支持**：
   - **PodSecurityPolicy**：已在 Kubernetes v1.25 中移除。
   - **Pod Security Admission**：自 Kubernetes v1.23 起以 beta 形式可用，并在 v1.25 中完全取代 PSP。

8. **可扩展性**：
   - **PodSecurityPolicy**：通过自定义设置具有高可扩展性。
   - **Pod Security Admission**：可扩展性有限，可能需要 OPA Gatekeeper 或 Kyverno 等额外工具来实现更细粒度控制。
</details>
