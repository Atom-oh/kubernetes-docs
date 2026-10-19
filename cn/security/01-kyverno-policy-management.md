# 使用 Kyverno 管理策略

> **验证基线**：Kyverno/CLI 1.19.1，Helm Chart 3.9.1。当前发布指南列出的已测试 Kubernetes 版本为 1.33–1.35；Chart 更宽泛的安装约束并不构成兼容性保证。
> **最后更新**：2026 年 10 月 19 日

Kyverno 会评估 Kubernetes 策略，并执行明确配置的变更、生成和删除操作。本文中的示例已使用真实 CLI 和已发布的 Schema/Chart 在本地检查。未执行实时集群安装、准入、网络隔离、清理或 AWS 集成操作。

原有的 `ClusterPolicy` 示例已更新为 `policies.kyverno.io/v1` CEL 策略。官方 1.19 迁移指南将 ClusterPolicy/Policy、CleanupPolicy 和旧版 `kyverno.io` PolicyException 标记为已弃用，并计划在 1.20 中移除。它们并非已在 1.19 中消失；请在升级前迁移并测试，而不要只替换 apiVersion 字符串。

## 实验环境设置

### 所需工具

本地测试请使用与目标 API 服务器版本偏差受支持的 kubectl、受支持且兼容 OCI 的 Helm 版本，以及经过验证的 Kyverno 1.19.1 CLI。获取与 CLI 匹配的操作系统/架构归档，并验证其已发布的校验和/签名。不要重复使用 1.10.0 归档，也不要将未经验证的下载内容通过管道传入需要 root 权限的安装过程。

从本地文件开始。以下策略是彼此独立的示例，并非一组可以整体应用的策略。Pod 示例面向 `policy-lab`；生成策略还要求显式标签。限制有权修改这些策略、命名空间标签、Roles 和 PolicyExceptions 的人员。这些选择器本身并不是 RBAC 安全边界。

### 安装 Kyverno

准备专用的 `kyverno` 命名空间。在更改共享集群之前，检查所选 EKS/Kubernetes 版本、API 服务器与 webhook 之间的连通性、DNS、准入失败/超时行为以及 CRD 升级流程。Kubernetes ServiceAccount/RBAC 用于授权控制器；安装 Kyverno 本身不需要 AWS 管理员角色。

## Kyverno 简介

### Kyverno 架构及其工作原理

| 组件 | 职责 |
|---|---|
| 准入控制器 | 匹配准入请求并执行策略验证/变更/镜像检查；并非处理每个 GET/list 请求 |
| 后台控制器 | 生成以及明确启用的 mutate-existing 工作 |
| 报告控制器 | 汇总/报告策略结果 |
| 清理控制器 | 定时删除策略和获准的清理操作 |

验证策略不会删除或修复现有的不合规资源。后台报告、mutate-existing、generate-existing 和定时删除是权限要求各不相同的独立机制。生成操作可能是异步的；创建命名空间与强制执行生成的 NetworkPolicy 并非原子操作。

### Kyverno 与 OPA Gatekeeper 对比

Kyverno 当前的策略在 YAML/JSON 清单中使用 CEL；旧版策略还使用模式和 JMESPath。采用 Kubernetes 原生封装并不意味着无需学习策略表达式。Gatekeeper 使用 ConstraintTemplates/Constraints，并使用其对应版本支持的策略引擎，同时具备独立的准入/审计/变更能力。请比较所需功能、表达式语言、策略测试、控制器可用性和实测工作负载影响。旧有的“简单/复杂”和“性能良好/非常好”评级缺乏依据，并非基准测试结果。

### 2026 年 10 月更新：将运行时强制执行扩展至准入之外

在 [10 月 15 日 CNCF 博文](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/)中，Kyverno 的创建者 Nirmata 描述了准入控制的局限——它只能回答“这个 spec 看起来是否正确”，无法发现正在运行的工作负载偏离其 spec 的情况（例如启动后拉取第二阶段有效载荷、向未经批准的目标发送流量）——并介绍了 **Nirmata Runtime for Kyverno**，这是一种使用 eBPF 和 Linux 安全模块 (LSM) 在内核级别强制执行策略的开源实现。该方案面向 AI Agent 等非确定性工作负载的运行时安全。它是一个独立组件，拥有自己的权限，与本章中的准入/后台策略不同；而且这篇博文是供应商（Nirmata）的介绍。采用前请核实其功能范围以及内核/平台要求。

## 安装 Kyverno

### 使用 Helm 安装

将以下内容保存为 `kyverno-values.yaml`。这是一个单副本的**实验环境**规格。ServiceMonitor CRD 和能选中实际命名空间/标签的 Prometheus 安装必须已存在；将示例标签 `release: kube-prom` 替换为该安装使用的选择器，或者在准备就绪前禁用 ServiceMonitor。

```yaml
admissionController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
backgroundController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
cleanupController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
reportsController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
```

```bash
# Use an approved context; this changes real cluster resources.
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm template kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --values kyverno-values.yaml > kyverno-rendered.yaml
# Inspect the render, CRD migration and webhook reachability before installation.
helm upgrade --install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace --kube-context "$KUBE_CONTEXT" \
  --values kyverno-values.yaml
```

渲染结果包含四个控制器 Deployment 和四个指标 ServiceMonitor。增加副本需要规划拓扑、干扰预算、资源规格和 webhook 可用性；每个控制器一个副本并非高可用设计。请检查当前 Chart 的默认值和实际渲染出的镜像标签，不要将 Chart 版本标签误解为应用版本。

### 使用 YAML 清单安装

如果由 GitOps 管理 YAML，请渲染固定版本的 Chart，并将其 CRD、RBAC、证书和钩子作为一组进行审查和管理。对渲染结果直接执行 `kubectl apply` 不会执行 Helm 钩子/升级语义。不要将旧版 1.10.0 install.yaml 应用到较新版本，也不要让多个管理方同时管理相同的控制器。

## 策略类型

### 1. 验证策略

将以下独立示例保存为 `require-limits.yaml`。它会检查**常规容器和 init 容器**是否设置了非空的 CPU/内存限制。临时容器不能声明资源请求/限制；下文的安全检查会单独涵盖它们。这是选定的逐容器策略，并不表示每个 Kubernetes 工作负载都必须采用此资源策略。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-container-limits
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, has(c.resources) && has(c.resources.limits) && ['cpu', 'memory'].all(k, k in c.resources.limits
      && string(c.resources.limits[k]) != ''))
    message: Normal and init containers need nonempty CPU and memory limits.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([])
```

`validationActions: [Audit]` 会记录违规情况，同时允许匹配的准入请求通过；`[Deny]` 会在分阶段实施/影响审查后拒绝这些请求。`Warn` 可以向客户端发出警告。Webhook 的 `failurePolicy` 用于控制评估/传输失败时的行为，是另一项独立设置。离线 CLI 失败结果不能证明 Audit 策略拒绝了实时请求。

### 2. 变更策略

保存为 `add-default-label.yaml`。现有的 `environment` 标签（包括显式设置为空值的标签）会保留。此处使用 CEL ApplyConfiguration，而不是在 Kyverno 中使用 Helm Go 模板的 `if`/`hasKey` 语法。

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: add-default-label
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        has(object.metadata.labels) && 'environment' in object.metadata.labels
        ? Object{}
        : Object{metadata: Object.metadata{labels: {"environment": object.metadata.namespace}}}
```

此示例禁用了 mutate-existing。准入变更仍可能影响匹配的 CREATE/UPDATE 请求。JSONPatch 替代方案必须先创建缺失的 labels 映射，再添加子键；在 JSON Pointer 路径中，`/` 必须转义为 `~1`。独立策略之间的变更顺序没有保证。

### 3. 生成策略

保存为 `generate-networkpolicy.yaml`。只有名称为 `policy-lab` 且具有 `training.example.com/managed: "true"` 标签的 Namespace 才会触发此示例。对于 Namespace 对象，应匹配其**名称/标签**，而不是 `metadata.namespace` 或旧版命名空间排除列表。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-networkpolicy
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("networking.k8s.io/v1"),
        "kind": dyn("NetworkPolicy"),
        "metadata": dyn({"name": "lab-default-deny", "namespace": object.metadata.name}),
        "spec": dyn({"podSelector": {}, "policyTypes": ["Ingress", "Egress"]})
      }])
```

在工作负载依赖此命名空间之前，请准备好所需的 DNS/API/应用放行规则。Kubernetes NetworkPolicy 隔离需要由支持强制执行的 CNI 实现；其他放行策略具有累加效果，并且必须考虑 host-network 行为。本地生成清单并不能证明流量已被阻断。

此处禁用了同步和 generate-existing。安装此策略时，如果 Namespace 已存在，不会自动为其补充资源：请通过后续匹配触发，或在更改此设置前明确审查是否启用 generate-existing。启用同步后，下游资源的生命周期取决于数据与克隆源、触发器变更以及 `orphanDownstreamOnPolicyDelete`；它并非通用的备份/回滚机制。共享 Secrets 需要明确的来源/目标允许列表，并审查 RBAC/凭据生命周期，而不是将其复制到每个新命名空间。

### 4. 定时删除

`DeletingPolicy` 使用 `spec.schedule` 和 CEL 条件；它与验证策略分开，也没有 `validationActions` 的 Audit 开关。清理控制器需要明确的删除权限。应优先采用范围狭窄的命名空间/对象标签以及清晰的保留期限要求（基于对象年龄/状态），检查选中的候选对象，并在启用定时任务前测试恢复流程。可选测验示例选择带标记的已完成 Pod；这并不表示“超过 24 小时”，此处也未执行任何定时删除。

## 在 EKS 中使用 Kyverno

### EKS 与 Kyverno 集成架构

EKS API 服务器会通过配置的 Kubernetes 网络/RBAC 路径调用匹配的准入 webhook。CloudWatch 导出是另一项独立配置的采集器/集成，具有自己的 IAM 和保留设置；安装 Kyverno 并不会自动将每个 PolicyReport 发送到 CloudWatch。避免输出可能含有 Secret 的原始准入有效载荷。

### 1. 加固安全

#### 禁止特权容器

缺少 `privileged` 字段时按 false 处理。此检查涵盖常规容器、init 容器和临时容器；即使声明匹配 `pods/ephemeralcontainers`，仍需要在目标环境中测试实时准入/子资源行为。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, !c.?securityContext.privileged.orValue(false))
    message: Privileged normal, init and ephemeral containers are not allowed.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

#### 禁止以 Root 用户运行

该策略使用每个容器的覆盖值或 Pod 级默认值，要求最终生效的 `runAsNonRoot` 为 true，并拒绝最终生效的 UID 显式设置为 0 的情况。此策略验证的是声明；kubelet/镜像在运行时的行为仍然相关。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-non-root
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, c.?securityContext.runAsNonRoot.orValue(object.spec.?securityContext.runAsNonRoot.orValue(false))
      && c.?securityContext.runAsUser.orValue(object.spec.?securityContext.runAsUser.orValue(-1)) != 0)
    message: Use effective runAsNonRoot=true and do not select UID 0.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

### 2. 成本优化

#### 设置资源限制

保存为 `default-resources.yaml`。此示例仅处理 CREATE，避免在普通更新期间更改运行中的 Pod 资源；只有在常规容器**既没有 requests 也没有 limits** 时才提供默认值。它会保留完整或部分已有的资源设置，不会覆盖工作负载的资源规格，也不会生成大于现有限制值的请求。请单独审查部分设置；此策略不会填充每个缺失字段，也不会为 init/临时容器设置默认值。

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: default-unset-resources
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        Object{spec: Object.spec{containers: object.spec.containers.map(c,
          (!has(c.resources) || ((!has(c.resources.requests) || c.resources.requests.size() == 0) &&
            (!has(c.resources.limits) || c.resources.limits.size() == 0)))
          ? Object.spec.containers{name: c.name, resources: Object.spec.containers.resources{
              requests: {"cpu": "250m", "memory": "256Mi"},
              limits: {"cpu": "500m", "memory": "512Mi"}
            }}
          : Object.spec.containers{name: c.name}
        )}}
```

#### 强制使用指定实例类型

原有实例名称仅为允许列表示例，并非当前建议。显式设置的 nodeSelector 是强制调度约束。此策略仅在准入时检查 CREATE 请求，并拒绝提供了 nodeName 的请求；它会禁用后台扫描，因为已调度的 Pod 会正常获得 nodeName。对节点标签的信任、调度器/绑定权限和可用容量需要单独考虑。声明检查无法保证调度结果不受有权绑定 Pod 或修改 Node 的主体影响。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-node-selector
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.spec.?nodeName.orValue('') == '' && object.spec.?nodeSelector['node.kubernetes.io/instance-type'].orValue('')
      in ['m5.large', 'c5.large', 'r5.large']
    message: Use an approved instance-type nodeSelector and do not bypass the scheduler with nodeName.
  evaluation:
    background:
      enabled: false
```

### 3. 合规

#### 自动生成 PodDisruptionBudget

此可选 Deployment 示例要求期望副本数至少为 2，并复制**完整的 spec.selector**（包括 matchExpressions），而不是可能不存在的顶层 app 标签。它不能证明两个副本都已就绪。由于禁用了同步，此静态实验环境预算在扩容或选择器更改后需要单独决定是否继续使用并进行审查。PDB 限制符合条件的主动驱逐，但不限制每次滚动更新或非主动故障。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-pdb
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - deployments
  matchConditions:
  - name: approved-deployment
    expression: object.metadata.namespace == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true' && object.spec.?replicas.orValue(1) >= 2
  generate:
  - expression: |-
      generator.Apply(object.metadata.namespace, [{
        "apiVersion": dyn("policy/v1"), "kind": dyn("PodDisruptionBudget"),
        "metadata": dyn({"name": object.metadata.name + "-pdb", "namespace": object.metadata.namespace}),
        "spec": dyn({"minAvailable": 1, "selector": object.spec.selector})
      }])
```

后台控制器必须拥有创建生成资源的实际权限。对于渲染出的 `kyverno` release，以下额外的命名空间 Role/Binding 演示了范围有限的 PDB 授权。Chart 已包含其他控制器权限；不要将此配置称为控制器完整的有效 RBAC 策略。请根据渲染结果调整 ServiceAccount 名称，并在目标集群中验证授权。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
rules:
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
subjects:
- kind: ServiceAccount
  name: kyverno-background-controller
  namespace: kyverno
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kyverno-lab-pdb-writer
```

#### 自动生成 Namespace ResourceQuota

同样需要显式选择加入 Namespace。配额值是实验环境策略，并非 AWS 预算或成本上限；启用前请考虑工作负载请求、init 容器、限制以及现有配额。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-quota
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("v1"), "kind": dyn("ResourceQuota"),
        "metadata": dyn({"name": "lab-resource-quota", "namespace": object.metadata.name}),
        "spec": dyn({"hard": {"requests.cpu": "10", "requests.memory": "10Gi",
          "limits.cpu": "20", "limits.memory": "20Gi", "pods": "50"}})
      }])
```

## 策略测试与验证

### 策略应用工作流

审查策略的管理责任和作用范围，在本地测试正例/反例/跳过场景，检查生成/变更后的对象，然后分阶段测试实时准入和控制器权限。Audit 是一种验证操作；它不会让变更、生成或删除操作变得无害。Pod 控制器自动生成策略以及原生 ValidatingAdmissionPolicy/MutatingAdmissionPolicy 的生成是需要分别选择启用的功能，并且存在兼容性限制；请检查生成策略的状态，不要假定所有控制器模板都已覆盖。

### 策略模拟

创建 `policy-lab-tests/`，并将以下四个文件保存在其中。测试有意期望 `missing-label` 发生违规；测试套件通过意味着测试期望与结果相符，并不表示每个输入都合规。

`require-team.yaml`：

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

`pod.yaml`（本地测试样例；不会拉取其镜像）：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good
  namespace: policy-lab
  labels:
    team: platform
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`pod-missing.yaml`：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: missing-label
  namespace: policy-lab
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`kyverno-test.yaml`：

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: team-label-local-test
policies:
- require-team.yaml
resources:
- pod.yaml
- pod-missing.yaml
results:
- policy: require-team
  kind: Pod
  resources:
  - good
  result: pass
- policy: require-team
  kind: Pod
  resources:
  - missing-label
  result: fail
```

```bash
kyverno version
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
# Offline evaluation; this does not install a policy or modify cluster resources:
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
# For mutation/generation, --output takes a file/directory path, not a format name:
kyverno apply add-default-label.yaml --resource ./policy-lab-tests/pod.yaml --output ./mutated/
```

### 策略验证

`kyverno test` 接收包含测试清单的目录；`kyverno apply` 会针对提供的资源评估策略。`--cluster` 会从所选集群读取资源用于评估；它不是安装策略的命令。安装经过审查的策略需要使用 kubectl/GitOps，并会更改集群。请参阅固定版本 CLI 的帮助信息：通用的 `kyverno validate` 或 `kyverno create disallow-latest-tag` 工作流并非经过测试的接口。对于受支持的 Kyverno 辅助资源，确实存在 `create` 命令。

## 策略监控与报告

### 策略报告

默认规格使用 Policy WG 的 `PolicyReport`/`ClusterPolicyReport` API。PolicyReport 具有命名空间作用域；ClusterPolicyReport 用于集群范围的资源，并非简单地合并所有命名空间。报告配置和支持的规则类型很重要。后台扫描会报告验证结果；它们不会追溯性地拒绝、变更或删除现有对象。即使禁用了后台扫描，现有对象在更新时仍需接受匹配的准入检查。

这是一个**合成 Schema 示例**，并非从集群采集的报告。结果使用 `resources` 和 `result`，而不是 `resource`/`status`；如果提供时间戳，应使用整数秒/纳秒。汇总计数必须与条目相符。

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: example-report
  namespace: policy-lab
summary:
  pass: 1
  fail: 1
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: good
    namespace: policy-lab
  result: pass
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: missing-label
    namespace: policy-lab
  result: fail
  message: A nonempty team label is required.
```

使用 `kubectl get policyreports -n policy-lab` 和 `kubectl get clusterpolicyreports` 查询实际报告。Reports Server/OpenReports 是单独的可选安装/配置；在假定后端已就绪之前，请先确认实际安装的 API。

### Prometheus 指标

请使用上述经过测试的值创建的指标 Service，以及每个控制器对应的 ServiceMonitor。其 Service 端口名称为 `metrics-port`，端口号为 8000，选择器使用组件/实例/part-of 标签，而不是 `app: kyverno`。渲染结果会将它们放在 `kyverno` 中，并配置 `namespaceSelector.matchNames: [kyverno]`。Prometheus 必须选中这些 monitor 和命名空间。资源存在并不能证明指标已被抓取或已导出到 CloudWatch。

## 最佳实践

### 1. 逐步推出

先以 Audit 分阶段启用新的验证策略，审查实际报告和例外，然后在适当时选择 Deny。检查 webhook 故障策略、超时、副本可用性和紧急恢复措施。对生成、mutate-existing 和破坏性删除分别进行审查。

### 2. 例外处理

范围狭窄的 matchConstraints/matchConditions 并不等同于不受限制的豁免。请审查命名空间范围、名称、类型以及准入/用户信息的可用性。不能假定依赖用户/角色信息的经典规则在后台扫描中也可评估。CEL PolicyException 使用 `policies.kyverno.io/v1`、显式的 policyRefs/matchConditions，并可选用 expiresAt；请限制能够创建它的人员，并确认安装/配置支持情况。例外是一种涉及授权的重要对象，不应成为每个应用团队都能获得的准入绕过手段。

### 3. 策略组织

对经过版本管理的验证、变更、生成和删除策略进行统一管理，并配套测试和负责人。旧版 ClusterPolicy 模式/JMESPath 与 CEL 不同；请逐条迁移并比较输出。当前 API 中，镜像签名验证使用 `ImageValidatingPolicy`；有关 attestor/仓库/信任前置条件，请参阅[镜像安全指南](./07-image-security.md)。签名验证并非漏洞扫描，也不是通用的仓库允许列表。

## 结论

本地验证涵盖了真实 Kyverno 1.19.1 策略评估和输出保留、已发布的 API Schema 以及 Chart 渲染。实时 webhook 顺序/自动生成、控制器 RBAC、网络、镜像信任和破坏性生命周期操作均未执行。这些仍属于部署验收检查。

- [Kyverno 发布版本和已测试的 Kubernetes 版本](https://kyverno.io/docs/installation/releases/)
- [安装和控制器职责](https://kyverno.io/docs/installation/installation/)
- [迁移到 CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## 测验

试试 [Kyverno 策略管理测验](../quizzes/security/01-kyverno-policy-management-quiz.md)。
