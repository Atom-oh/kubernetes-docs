# 策略测验

本测验检查你对 Kubernetes 策略概念的理解，包括资源配额、限制范围、Pod 安全策略和网络策略。

## 选择题

1. Kubernetes 中 ResourceQuota 的主要目的是什么？
   - A) 限制 Pod 的 CPU 和内存使用量
   - B) 限制命名空间内可创建的资源
   - C) 监控整个集群的资源使用情况
   - D) 管理节点资源分配

<details>
<summary>显示答案</summary>

**答案：B) 限制命名空间内可创建的资源**

**解析：**
ResourceQuota 限制一个命名空间内可创建资源的总量。这不仅包括 CPU 和内存等计算资源，也包括 Pod、Service、ConfigMap 等对象的数量。使用 ResourceQuota 可以防止某个团队独占集群的全部资源。
</details>

2. LimitRange 的主要功能是什么？
   - A) 限制命名空间的总资源使用量
   - B) 为单个容器设置默认资源 requests 和 limits
   - C) 在集群节点之间分配资源
   - D) 限制 Pod 之间的网络通信

<details>
<summary>显示答案</summary>

**答案：B) 为单个容器设置默认资源 requests 和 limits**

**解析：**
LimitRange 为命名空间内的 Pod 或容器定义资源约束，可设置默认资源 requests 和 limits，或强制执行资源用量的最小值/最大值。LimitRange 针对单个资源，而 ResourceQuota 作用于整个命名空间。
</details>

3. PodSecurityPolicy (PSP) 在 Kubernetes v1.25 中移除后，由什么机制取代？
   - A) PodSecurityStandards
   - B) PodSecurityContext
   - C) PodSecurityAdmission
   - D) SecurityContextConstraints

<details>
<summary>显示答案</summary>

**答案：C) PodSecurityAdmission**

**解析：**
PodSecurityPolicy (PSP) 在 Kubernetes v1.25 中移除后，由 PodSecurityAdmission 取代。它是基于 Pod Security Standards 的内置准入控制器，提供 Privileged、Baseline 和 Restricted 三个策略级别。PodSecurityContext 用于配置 Pod 级别的安全设置；SecurityContextConstraints 则是 OpenShift 使用的类似机制。
</details>

4. 使用 NetworkPolicy 无法完成什么操作？
   - A) 仅允许来自特定命名空间的 Pod 流量
   - B) 仅允许来自特定 IP CIDR 范围的流量
   - C) 仅允许发往特定端口的流量
   - D) 检查特定协议的负载内容

<details>
<summary>显示答案</summary>

**答案：D) 检查特定协议的负载内容**

**解析：**
NetworkPolicy 提供 L3/L4 防火墙策略，用于控制 Pod 之间的通信，可基于特定命名空间、标签、IP CIDR 范围、端口等限制流量。但 NetworkPolicy 无法执行 L7 检查（例如检查 HTTP header 或负载内容）。如需此类功能，应使用 service mesh（例如 Istio）或 API gateway。
</details>

5. Kubernetes 中 RBAC（基于角色的访问控制）的主要目的是什么？
   - A) 控制 Pod 之间的网络通信
   - B) 管理用户和 ServiceAccount 的权限
   - C) 限制资源使用量
   - D) 设置 Pod 调度策略

<details>
<summary>显示答案</summary>

**答案：B) 管理用户和 ServiceAccount 的权限**

**解析：**
RBAC（基于角色的访问控制）用于控制对 Kubernetes API 的访问。通过 RBAC，可以定义用户、组或 ServiceAccount 在集群中能够执行哪些操作，并使用 Role、ClusterRole、RoleBinding 和 ClusterRoleBinding 等资源管理权限。
</details>

6. Pod Security Standards 的三个策略级别中，限制最严格的是哪一个？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced

<details>
<summary>显示答案</summary>

**答案：C) Restricted**

**解析：**
Pod Security Standards 定义三个策略级别：
- Privileged：不设限制，允许所有权限。
- Baseline：阻止已知的权限提升路径。
- Restricted：限制最严格，应用增强的安全设置。

Restricted 遵循最小权限原则并落实安全最佳实践，会禁止特权容器、共享主机命名空间、挂载主机路径等。
</details>

7. AdmissionController 在 Kubernetes 中起什么作用？
   - A) 用户身份验证
   - B) 监控资源使用情况
   - C) 验证和修改 API 请求
   - D) Pod 调度

<details>
<summary>显示答案</summary>

**答案：C) 验证和修改 API 请求**

**解析：**
AdmissionController 是一种插件，会在请求通过身份验证和授权之后、对象写入持久化存储之前拦截 Kubernetes API server 请求，并对其进行验证或修改。集群管理员可借此对资源创建和修改应用策略。例如，PodSecurityAdmission、ResourceQuota 和 LimitRanger 都通过 AdmissionController 实现。
</details>

8. OPA（Open Policy Agent）Gatekeeper 在 Kubernetes 中的主要功能是什么？
   - A) 集群监控和日志记录
   - B) 基于策略管理和验证资源
   - C) 自动扩缩容
   - D) Service mesh 管理

<details>
<summary>显示答案</summary>

**答案：B) 基于策略管理和验证资源**

**解析：**
OPA Gatekeeper 是用于在 Kubernetes 集群中实施策略的可扩展方案。它基于 OPA（Open Policy Agent），并使用 CustomResourceDefinition (CRD) 定义和应用策略。Gatekeeper 作为 AdmissionWebhook 运行，验证集群中创建或修改的资源是否符合已定义的策略，因此可用于安全策略、资源限制、命名约定等场景。
</details>

9. 某命名空间对 CPU/内存 requests 和 limits 设置了 ResourceQuota，且没有准入默认值。若 Pod 的容器都未指定这些资源字段，会怎样？
   - A) Pod 会自动使用默认 requests 和 limits 创建
   - B) Pod 创建会被拒绝
   - C) Pod 会被创建，但无法调度
   - D) Pod 会被创建，并可无限使用资源

<details>
<summary>显示答案</summary>

**答案：B) Pod 创建会被拒绝**

**解析：**
当命名空间对 CPU、内存等计算资源设置了配额时，Pod 在经过准入默认值处理后必须包含该配额所需的资源字段。如果字段仍然缺失，API server 会拒绝创建。LimitRange 可以提供默认值；仅限制对象数量的配额则不要求 CPU/内存字段。这样才能在应用了相关配额的命名空间中准确跟踪并限制资源用量。
</details>

10. Kubernetes 中 PriorityClass 的主要用途是什么？
    - A) 定义 Pod 调度优先级
    - B) 设置命名空间资源分配优先级
    - C) 决定 API 请求处理优先级
    - D) 设置节点重要性级别

<details>
<summary>显示答案</summary>

**答案：A) 定义 Pod 调度优先级**

**解析：**
PriorityClass 定义 Pod 的调度优先级。资源紧张时，高优先级 Pod 会先于低优先级 Pod 调度；必要时也可以抢占低优先级 Pod。
</details>

## 简答题

1. 说明 ResourceQuota 和 LimitRange 的主要区别。

<details>
<summary>显示答案</summary>

**答案：**
ResourceQuota 限制整个命名空间的资源用量，而 LimitRange 为命名空间内的单个容器或 Pod 设置资源约束。

主要区别：
1. **范围**：ResourceQuota 作用于整个命名空间；LimitRange 作用于单个资源（如 Pod、容器等）。
2. **目的**：ResourceQuota 限制命名空间内的资源总量；LimitRange 通过默认值、最小值/最大值等控制单个资源的用量。
3. **强制执行**：设置 ResourceQuota 后，超过配额的资源创建会被拒绝。LimitRange 会在创建资源时应用默认值，或在超出限制时拒绝创建。
4. **资源类型**：ResourceQuota 除了 CPU 和内存，还能限制 Pod、Service、PVC 等对象数量。LimitRange 主要针对 CPU、内存和存储等计算资源。
</details>

2. 说明 Pod Security Standards 的 Privileged、Baseline、Restricted 三个级别及其特点。

<details>
<summary>显示答案</summary>

**答案：**
Pod Security Standards 为 Pod 安全设置定义了三个策略级别：

1. **Privileged**：
   - 限制最少，几乎不施加约束。
   - 允许所有特权操作。
   - 可使用主机命名空间、主机端口、特权容器等。
   - 适用于开发和管理工作，但在生产环境中有显著安全风险。

2. **Baseline**：
   - 中等严格度，阻止已知的权限提升路径。
   - 为大多数工作负载提供基础安全级别。
   - 限制特权容器和主机命名空间的使用。
   - Baseline 同样禁止 HostPath 卷；Restricted 还会增加非 root 运行、seccomp 和 capability 限制等要求。

3. **Restricted**：
   - 限制最严格，采用增强安全设置。
   - 遵循最小权限原则并强制落实安全最佳实践。
   - 禁止特权容器、主机命名空间、主机路径挂载和权限提升。
   - 强制容器以非 root 用户运行。
   - 适用于安全要求严格的生产工作负载。
</details>

3. 说明如何用 NetworkPolicy 限制某命名空间中的 Pod，使其只能与另一个命名空间中的特定 Pod 通信。

<details>
<summary>显示答案</summary>

**答案：**
要用 NetworkPolicy 限制一个命名空间中的 Pod，使其只能与另一个命名空间中的特定 Pod 通信：

1. **在源命名空间应用 NetworkPolicy：**
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

2. **在目标命名空间应用 NetworkPolicy：**
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

要使上述方法生效，命名空间必须具有适当的标签：
```bash
kubectl label namespace source-namespace name=source-namespace
kubectl label namespace destination-namespace name=destination-namespace
```

这些策略只隔离所选择的通信方向。其他 NetworkPolicy 会将允许的流量叠加起来，不能用来收紧一个更宽泛的允许规则。若使用 DNS 名称，应另行允许 DNS 出站流量，并分别测试源端和目标端规则。
</details>

4. 说明可以用 OPA Gatekeeper 在 Kubernetes 中实现的策略示例。

<details>
<summary>显示答案</summary>

**答案：**
可以使用 OPA Gatekeeper 实现以下策略示例：

请先从官方 Gatekeeper library 安装每种策略对应的 ConstraintTemplate。这些 kind 由模板生成，并非 Kubernetes 内置 API；library 中 K8sRequiredLabels 的 schema 与本章简化版 K8sRequiredLabelKeys 不同。

1. **限制镜像注册表：**
   - 强制镜像只能从获批的注册表拉取。
   - 例如只允许公司内部注册表或指定的可信公共注册表。
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

2. **强制设置资源 requests 和 limits：**
   - 要求所有容器都设置资源 requests 和 limits。
   - 以防资源耗尽，并确保合理分配资源。
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

3. **禁止特权容器：**
   - 禁止运行特权容器。
   - 降低安全风险并确保容器隔离。
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

4. **限制主机文件系统访问**（需要 library 中匹配的模板）：
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPHostFilesystem
   metadata:
     name: prevent-host-filesystem-mount
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
     parameters:
       allowedHostPaths: []
   ```

5. **要求标签值符合约束：**
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredLabels
   metadata:
     name: require-team-label
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod", "Service"]
       - apiGroups: ["apps"]
         kinds: ["Deployment"]
     parameters:
       labels:
       - key: team
         allowedRegex: "^(frontend|backend|infra)$"
       - key: environment
         allowedRegex: "^(dev|staging|prod)$"
   ```

（以上示例中只需解释三个。）
</details>

5. 说明如何使用 Kubernetes PriorityClass 提高重要工作负载的可用性。

<details>
<summary>显示答案</summary>

**答案：**
可通过以下方式使用 PriorityClass 提高重要工作负载的可用性：

1. **定义 PriorityClass：**
   - 根据工作负载的重要程度创建多个优先级。
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000  # Higher value means higher priority
   globalDefault: false
   description: "This priority class should be used for critical production workloads."
   ```

2. **为重要工作负载指定 PriorityClass：**
   - 在重要 Pod 中引用相应的 PriorityClass。
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

3. **利用抢占：**
   - 资源紧张时，高优先级 Pod 可以抢占（驱逐）低优先级 Pod 并进入调度。
   - 这会提高调度优先级，但若约束条件或可用容量仍不允许放置，就无法保证 Pod 成功调度。

4. **考虑系统优先级类：**
   - Kubernetes 提供 system-cluster-critical (2000000000) 和 system-node-critical (2000001000) 等系统优先级类。
   - 用户自定义 PriorityClass 的值最多为 1,000,000,000；更高值保留给系统类。

5. **设计优先级层次：**
   - 根据工作负载重要性定义多个级别。
   - 例如：生产服务 (900000)、内部工具 (500000)、开发/测试 (100000)。
</details>

## 实践题

1. 创建一个满足以下要求的 ResourceQuota：
   - 命名空间：team-a
   - 最多 10 个 Pod
   - 最多 5 个 Service
   - CPU requests 总量：4 核
   - 内存 requests 总量：8Gi

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

应用方法：
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
   - 命名空间：team-b
   - 容器默认 request：CPU 100m、内存 256Mi
   - 容器默认 limit：CPU 200m、内存 512Mi
   - 容器最大 limit：CPU 1 核、内存 2Gi

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

应用方法：
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
   - 命名空间：web
   - app 标签为 frontend 的 Pod 只能与 app 标签为 backend 的 Pod 通信
   - Backend Pod 只允许使用端口 8080 通信

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

应用方法：
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

4. 创建一个 PriorityClass 和一个使用该类别的 Pod，并满足以下要求：
   - PriorityClass 名称：high-priority
   - 优先级值：100000
   - 说明："For critical production workloads"
   - Pod 名称：critical-app
   - 镜像：nginx

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

应用方法：
```bash
kubectl apply -f high-priority-pod.yaml
```

检查 PriorityClass 和 Pod 状态：
```bash
kubectl get priorityclass high-priority
kubectl get pod critical-app
```
</details>

5. 应用以下 Pod Security 设置：
   - 命名空间：restricted-ns
   - 模式：enforce
   - 级别：restricted

<details>
<summary>显示答案</summary>

**答案：**

在 Kubernetes 1.25 及更高版本中，可以通过为命名空间添加标签来应用 Pod Security Standards：

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

应用方法：
```bash
kubectl apply -f restricted-namespace.yaml
```

也可以为现有命名空间添加标签：
```bash
kubectl create namespace restricted-ns
kubectl label namespace restricted-ns \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```
</details>

## 高级主题

1. 说明 Kubernetes 中 OPA Gatekeeper 与 Kyverno 的区别，以及二者各自的优缺点。

<details>
<summary>显示答案</summary>

**答案：**

**OPA Gatekeeper 与 Kyverno 对比：**

1. **架构和方法：**
   - **OPA Gatekeeper：** 基于 Open Policy Agent (OPA)，使用 Rego 策略语言。通过两个 CRD 定义策略：ConstraintTemplate 和 Constraint。
   - **Kyverno：** 使用自身的策略引擎，通过 YAML/JSON 定义策略。它提供多种策略类型，包括 Policy/ClusterPolicy；具体版本还可能提供专用的清理策略/CEL 策略 API。

2. **策略语言：**
   - **OPA Gatekeeper：** 使用 Rego，表达能力强，但学习曲线较陡。
   - **Kyverno：** 使用类似 Kubernetes 资源的 YAML 语法定义策略，Kubernetes 用户更容易上手。

3. **功能：**
   - **OPA Gatekeeper：**
     - 能表达复杂策略的强大策略语言。
     - 可集成外部数据源，根据外部数据进行决策。
     - 支持策略库和可复用模板。
   - **Kyverno：**
     - 内置资源创建、修改和验证功能。
     - 支持镜像验证和修改。
     - 创建资源时可以自动创建其他资源。
     - 支持策略例外处理。

4. **优点：**
   - **OPA Gatekeeper：**
     - Rego 生态成熟，拥有可复用的模板。
     - 更适合表达复杂策略。
     - 针对多种用例提供丰富文档和示例。
     - OPA 生态也可用于 Kubernetes 以外的场景。
   - **Kyverno：**
     - 使用熟悉的 YAML 语法，学习曲线较平缓。
     - 无需额外学习独立的策略语言。
     - 内置资源创建和修改功能。
     - 设置和配置较简单。

5. **缺点：**
   - **OPA Gatekeeper：**
     - 需要学习 Rego。
     - 设置和配置较复杂。
     - 资源修改还需要额外配置。
   - **Kyverno：**
     - 需要按版本检查 CRD 和功能兼容性。
     - 对非常复杂的策略表达可能有局限。
     - 应使用有代表性的策略和准入负载进行基准测试；不存在普遍适用的引擎性能排名。

6. **选择标准：**
   - **适合选择 OPA Gatekeeper 的情况：**
     - 需要复杂的策略逻辑。
     - 已经使用 OPA 或熟悉 Rego。
     - 需要在多种系统中一致地实施策略。
   - **适合选择 Kyverno 的情况：**
     - 快速上手和易学性很重要。
     - 团队熟悉 Kubernetes 资源语法。
     - 需要资源创建和修改功能。
     - Kubernetes 原生的变更、生成、验证或校验方式符合策略要求。
</details>

2. 说明 Pod Security Admission 与 Kubernetes 以前的 PodSecurityPolicy (PSP) 之间的主要区别。

<details>
<summary>显示答案</summary>

**答案：**

**Pod Security Admission 与 PodSecurityPolicy (PSP) 对比：**

1. **实现方式：**
   - **PodSecurityPolicy：** 以 Kubernetes 内置 API 资源实现（不是 CRD），通过准入控制器应用。
   - **Pod Security Admission：** 以 Kubernetes 内置准入控制器实现，通过命名空间标签配置。

2. **配置方法：**
   - **PodSecurityPolicy：** 集群管理员必须创建 PSP 资源，并通过 RBAC 将其绑定到用户/ServiceAccount。
   - **Pod Security Admission：** 通过命名空间标签指定强制执行模式（enforce、audit、warn）和策略级别（privileged、baseline、restricted）。

3. **策略粒度：**
   - **PodSecurityPolicy：** 可进行非常细粒度的控制，分别配置多种安全上下文设置。
   - **Pod Security Admission：** 只提供三个预定义策略级别（privileged、baseline、restricted），不能单独调整具体设置。

4. **易用性：**
   - **PodSecurityPolicy：** 配置复杂，需要 RBAC 绑定，也容易出现配置错误。
   - **Pod Security Admission：** 只需通过简单的命名空间标签应用，易用得多。

5. **作用范围：**
   - **PodSecurityPolicy：** 作用于整个集群或特定用户/ServiceAccount。
   - **Pod Security Admission：** 按命名空间应用。

6. **模式：**
   - **PodSecurityPolicy：** 只有启用或不启用两种状态。
   - **Pod Security Admission：** 提供 enforce、audit、warn 三种渐进式模式：
     - enforce：违规时拒绝创建 Pod。
     - audit：将违规记录到审计日志。
     - warn：违规时显示警告。

7. **迁移和支持：**
   - **PodSecurityPolicy：** 已在 Kubernetes v1.25 中移除。
   - **Pod Security Admission：** 从 Kubernetes v1.23 起以 beta 形式提供，并在 v1.25 中完全取代 PSP。

8. **可扩展性：**
   - **PodSecurityPolicy：** 可通过自定义设置实现较高的扩展性。
   - **Pod Security Admission：** 扩展性有限；要实现更细粒度的控制，可能需要 OPA Gatekeeper 或 Kyverno 等附加工具。
</details>

3. 说明外部授权 webhook 如何补充 Kubernetes RBAC，以及为什么授权顺序很重要。

<details>
<summary>显示答案</summary>

**答案：**

对于自管理 API server，应配置通过 TLS 身份验证的 webhook，并使用提供 endpoint、CA、客户端证书和密钥的 kubeconfig。以下是通过标志配置的示例：

```text
--authorization-mode=Node,RBAC,Webhook
--authorization-webhook-config-file=/path/to/webhook-config.yaml
--authorization-webhook-version=v1
```

Webhook 会接收 `authorization.k8s.io/v1` SubjectAccessReview，其中包含经过身份验证的用户/组和请求属性，并返回 SubjectAccessReview 状态，例如 `allowed: true` 或明确拒绝。它必须验证传输凭证、谨慎处理错误/超时，并避免记录 bearer token 或机密请求数据。

**授权器链会在首次允许或拒绝时停止。** 在 `Node,RBAC,Webhook` 配置中，如果 RBAC 先允许请求，后续 webhook 就不会运行；后续 webhook 不能否决该权限。强制执行外部拒绝策略时，需要合适的顺序/失败策略，或采用适当的准入控制。结构化 AuthorizationConfiguration 支持额外的 webhook 控制。EKS 不开放任意 API server 授权标志的配置。

OPA adapter 可以用 Rego 评估该 review。以下 OPA 1.x 示例使用了当前规则语法：

```rego
package kubernetes.authz

default allow := false

allow if {
    input.spec.resourceAttributes.namespace == "default"
    input.spec.resourceAttributes.resource == "deployments"
    input.spec.resourceAttributes.verb == "get"
    input.spec.user == "jane"
    "developers" in input.spec.groups
}
```

部署兼容版本的 OPA、加载策略 bundle，并实现 adapter，将 review 作为 OPA 输入提交，再将结果映射为 SubjectAccessReview 状态。单独部署 OPA 并不构成完整的授权 webhook。集中式策略、外部属性和可审计性是其优点；可用性、延迟、缓存 TTL 和拒绝行为都必须经过测试。
</details>

4. 设计多租户网络隔离方案，使用 NetworkPolicy 实现租户间隔离。

<details>
<summary>显示答案</summary>

**答案：**

在每个租户命名空间中先应用默认拒绝入站/出站流量的策略。之后可选择允许租户内部广泛互通，或按角色编写细粒度规则。由于策略是累加的，如果同时应用“允许同一命名空间内通信”的宽泛规则，它会抵消更窄的角色限制。

对于允许租户内部广泛互通的方案，需要同时允许两个方向；只有入站策略并不能解除默认拒绝出站流量的限制：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
```

若要实现更细粒度隔离，请改用 `role: backend` 或 `tier: web` 等标签。要仅向其他租户开放指定 API，请在同一个 peer 中组合命名空间选择器和 Pod 选择器，并明确指定目标端口。可以使用内置的 `kubernetes.io/metadata.name` 命名空间标签，或维护受保护的租户标签约定。

允许访问共享服务时，源端出站规则和目标端入站规则必须匹配。允许租户访问端口 9090 上的 Prometheus，会暴露其 API/UI；这并不授权 Prometheus 抓取租户 Pod。抓取需要反向流量路径。对外部出站流量，应限制适当的 IP 范围和 TCP 端口；若 IP 不适用，则需要支持域名策略的实现。

DNS 出站流量通常需要以下规则（如使用 NodeLocal DNS 或不同标签，请相应调整）：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

使用能够强制执行策略的 CNI，通过 RBAC 和准入规则保护命名空间/Pod 标签，为策略做版本管理，并测试允许和拒绝的流量。标准 NetworkPolicy 不提供 L7 身份验证，并且对节点/host-network 有文档说明的限制。
</details>

5. 说明如何组合使用 ResourceQuota 和 LimitRange 制定资源管理策略。

<details>
<summary>显示答案</summary>

**答案：**

- 在集群层规划节点容量、自动扩缩容和工作负载隔离；在命名空间层限制计算/存储请求和对象数量；在工作负载层设置经测量的资源 requests 和 Pod 优先级。
- 为 PVC 分配存储时使用 `requests.storage` 和 `<class>.storageclass.storage.k8s.io/requests.storage`。统计任意对象数量时使用 `count/deployments.apps`、`count/statefulsets.apps` 等键；裸写 `deployments.apps` 并不是对象计数语法。
- 针对每个 PriorityClass，使用 `scopeSelector` 和 `hard.pods` 设置单独的配额。PriorityClass 属于 Pod，而不是直接属于命名空间。
- 使用 Container 类型的 LimitRange 条目设置默认值和最小/最大校验。Pod 条目限制汇总资源；PVC 条目限制存储请求；这两类条目都不会提供默认值。

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: object-counts
  namespace: team-a
spec:
  hard:
    pods: "50"
    services: "10"
    services.loadbalancers: "2"
    services.nodeports: "5"
    secrets: "20"
    configmaps: "20"
    count/deployments.apps: "10"
    count/statefulsets.apps: "5"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: storage-limits
  namespace: team-a
spec:
  limits:
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 100Gi
```

ResourceQuota 和 LimitRange 没有内置的仅审计模式；应在测试命名空间中评估更改，并在适用时使用 dry-run。分别监控配额分配和实际用量，在达到限制前告警，并根据测量结果调整 requests。动态配额更改、借用、共享资源池和成本分摊需要额外的控制器/自动化；原生硬性配额不允许临时超额。配额限制准入，并不保证工作负载性能。
</details>
