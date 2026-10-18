# 使用 Kyverno 进行策略管理

> **验证基线**：Kyverno/CLI 1.19.1，Helm chart 3.9.1。当前发布指南列出的已测试 Kubernetes 版本为 1.33–1.35；chart 更宽泛的安装约束并不保证兼容性。
> **最后更新**：2026 年 9 月 13 日

Kyverno 会评估 Kubernetes 策略，并执行显式配置的变更、生成和删除操作。这些示例已在本地使用真实 CLI 和已发布的 schema/chart 进行检查。未执行实时集群安装、准入、网络隔离、清理或 AWS 集成。

原有的 `ClusterPolicy` 示例已更新为 `policies.kyverno.io/v1` CEL 策略。官方 1.19 迁移指南已将 ClusterPolicy/Policy、CleanupPolicy 和旧版 `kyverno.io` PolicyException 标记为弃用，并计划在 1.20 中移除。它们在 1.19 中尚未消失；请在升级前迁移并测试，不要只替换 apiVersion 字符串。

## 实验环境设置

### 必需工具

使用与目标 API Server 版本偏差处于支持范围内的 kubectl、受支持且能处理 OCI 的 Helm 版本，以及经验证的 Kyverno 1.19.1 CLI 来执行这些本地测试。获取与 CLI 匹配的操作系统/架构归档，并验证已发布的校验和/签名。不要重复使用 1.10.0 归档，也不要将未经验证的下载内容通过管道直接交给 root 安装。

从本地文件开始。下面的策略是彼此独立的示例，并非一套应整体应用的策略。Pod 示例针对 `policy-lab`；生成策略还要求显式标签。限制能够更改这些策略、命名空间标签、Role 和 PolicyException 的人员。单靠这些选择器并不能构成 RBAC 安全边界。

### 安装 Kyverno

准备专用的 `kyverno` 命名空间。更改共享集群前，请检查所选 EKS/Kubernetes 版本、API Server 到 webhook 的连通性、DNS、准入失败/超时行为以及 CRD 升级流程。Kubernetes ServiceAccount/RBAC 用于授权控制器；安装 Kyverno 本身并不需要 AWS 管理员角色。

## Kyverno 简介

### Kyverno 的架构和工作原理

| 组件 | 职责 |
|---|---|
| 准入控制器 | 匹配准入请求并执行策略验证/变更/镜像检查；并非针对每个 GET/list 请求 |
| 后台控制器 | 执行生成操作以及显式启用的 mutate-existing 工作 |
| 报告控制器 | 汇总/报告策略结果 |
| 清理控制器 | 定时删除策略和获准的清理操作 |

验证策略不会删除或修复现有的不合规资源。后台报告、mutate-existing、generate-existing 和定时删除是不同的机制，所需权限也各不相同。生成操作可能是异步的；命名空间创建与生成 NetworkPolicy 的执行并非原子操作。

### Kyverno 与 OPA Gatekeeper 的比较

Kyverno 当前的策略使用 CEL 编写在 YAML/JSON 清单中；旧版策略也使用模式和 JMESPath。采用 Kubernetes 原生打包方式，并不意味着无需学习策略表达式。Gatekeeper 使用 ConstraintTemplates/Constraints，并针对其版本采用受支持的策略引擎，同时提供独立的准入/审计/变更能力。比较所需功能、表达式语言、策略测试、控制器可用性以及实测工作负载影响。旧有的“简单/复杂”和“良好/非常好的性能”评级缺乏依据，并非基准测试结果。

## 安装 Kyverno

### 使用 Helm 安装

将以下内容保存为 `kyverno-values.yaml`。这是一个单副本的**实验环境**配置。ServiceMonitor CRD 和能够选择实际命名空间/标签的 Prometheus 安装必须已存在；将示例中的 `release: kube-prom` 标签替换为该安装所用的选择器，或者在准备就绪前禁用 ServiceMonitor。

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

渲染结果包含四个控制器 Deployment 和四个指标 ServiceMonitor。增加副本需要规划拓扑、故障中断、资源规格和 webhook 可用性；每个控制器一个副本并非高可用设计。请检查当前 chart 的默认值和实际渲染出的镜像标签，不要将 chart 版本标签误解为应用版本。

### 使用 YAML 清单安装

如果 YAML 由 GitOps 管理，请渲染固定版本的 chart，并将其 CRD、RBAC、证书和钩子作为一组进行审查。对渲染结果直接执行 `kubectl apply` 不会执行 Helm 钩子/升级语义。不要将旧版 1.10.0 install.yaml 应用到较新版本上，也不要让多个所有者管理相同的控制器。

## 策略类型

### 1. 验证策略

将此独立示例保存为 `require-limits.yaml`。它会检查**普通容器和 init 容器**是否设置了非空 CPU/内存限制。临时容器不能声明资源请求/限制；下方的安全检查会单独涵盖它们。这是针对每个容器所选用的策略，并不意味着每个 Kubernetes 工作负载都必须采用这种资源策略。

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

`validationActions: [Audit]` 会记录违规情况，同时允许匹配的准入请求通过；`[Deny]` 会在分阶段部署/影响审查后拒绝请求。`Warn` 可向客户端发出警告。Webhook 的 `failurePolicy` 控制评估/传输失败时的行为，是另一项独立设置。离线 CLI 的失败结果不能证明 Audit 策略拒绝了实时请求。

### 2. 变更策略

保存为 `add-default-label.yaml`。现有的 `environment` 标签（包括显式设置为空值的标签）都会保留。此处使用的是 CEL ApplyConfiguration，而不是 Kyverno 中的 Helm Go 模板 `if`/`hasKey` 语法。

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

此示例禁用了 mutate-existing。准入变更仍可影响匹配的 CREATE/UPDATE 请求。使用 JSONPatch 时，必须先创建缺失的 labels 映射，再添加子键；在 JSON Pointer 路径中，`/` 必须转义为 `~1`。不同策略之间的变更顺序不受保证。

### 3. 生成策略

将此示例保存为 `generate-networkpolicy.yaml`。只有名称为 `policy-lab` 且带有 `training.example.com/managed: "true"` 标签的 Namespace 才会触发此示例。对于 Namespace 对象，应匹配其**名称/标签**，而不是 `metadata.namespace` 或旧式的命名空间排除列表。

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

在工作负载依赖此命名空间之前，先准备好所需的 DNS/API/应用放行规则。NetworkPolicy 隔离需要由支持该功能的 CNI 执行；其他放行策略采用累加方式，且必须考虑 host-network 行为。本地生成的清单不能证明流量已被阻断。

此处禁用了同步和 generate-existing。安装此策略时，已存在的 Namespace 不会自动补充生成资源：请使用之后的匹配触发，或者在更改该设置前明确审查是否启用 generate-existing。启用同步后，下游资源的生命周期取决于数据与克隆源、触发器更改以及 `orphanDownstreamOnPolicyDelete`；它并非通用的备份/回滚机制。共享 Secret 需要明确的源/目标允许列表以及 RBAC/凭据生命周期审查，而不是将 Secret 复制到每个新命名空间。

### 4. 定时删除

`DeletingPolicy` 使用 `spec.schedule` 和 CEL 条件；它独立于验证策略，也没有 validationActions 的 Audit 开关。清理控制器需要显式的删除权限。应优先选择范围狭窄的命名空间/对象标签和明确的资源保留期限或状态要求，检查所选目标，并在启用定时任务前测试恢复流程。可选的测验示例会选择带有标记且已完成的 Pod；它并不表示“超过 24 小时”，且此处没有执行任何定时删除。

## Kyverno 在 EKS 中的应用场景

### EKS 与 Kyverno 集成架构

EKS API Server 会通过配置的 Kubernetes 网络/RBAC 路径调用匹配的准入 webhook。导出到 CloudWatch 是单独配置的采集器/集成，有其自身的 IAM 和保留期限；安装 Kyverno 不会自动将每个 PolicyReport 发送到 CloudWatch。避免打印可能包含 Secret 的原始准入负载。

### 1. 安全强化

#### 阻止特权容器

如果未设置 `privileged`，则按 false 处理。此检查涵盖普通容器、init 容器和临时容器；在目标环境中仍需对 `pods/ephemeralcontainers` 的匹配进行实时准入/子资源测试。

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

#### 阻止以 root 用户运行

该策略会使用每个容器的覆盖值或 Pod 级默认值，要求有效的 runAsNonRoot，并拒绝显式的有效 UID 0。此策略验证的是声明；运行时仍需考虑 kubelet/镜像的行为。

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

将此示例保存为 `default-resources.yaml`。此示例仅适用于 CREATE，可避免在普通更新期间更改运行中的 Pod 资源；并且只有在普通容器**既没有请求也没有限制**时才提供默认值。它会保留已有的完整或部分资源设置，而不会覆盖工作负载资源规格，也不会产生大于现有限制的小请求。请单独审查部分设置；此策略不会填充每个缺失字段，也不会为 init/临时资源设置默认值。

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

#### 强制使用特定实例类型

原有实例名称仅为示意性允许列表，并非当前建议。显式的 nodeSelector 是强制调度约束。此准入策略仅适用于 CREATE，并会拒绝已提供 nodeName 的请求；后台扫描已禁用，因为已调度的 Pod 会正常获得 nodeName。对节点标签的信任、调度器/绑定权限以及可用容量需要另行考虑。声明检查无法保证 Pod 会被放置到指定位置，尤其是当某个主体有权绑定 Pod 或修改 Node 时。

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

### 3. 合规性

#### 自动生成 PodDisruptionBudget

此 Deployment 示例需显式启用，要求期望副本数至少为两个，并复制**完整的 spec.selector**（包括 matchExpressions），而不是可能不存在的顶层 app 标签。它不能证明两个副本都处于 Ready 状态。在扩容或选择器更改后，需要另行决定是否继续使用此静态实验环境 PDB，尤其是在禁用同步时。PDB 只约束符合条件的主动驱逐，不涵盖每次滚动更新或意外故障。

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

后台控制器必须拥有创建生成资源的实际权限。对于渲染出的 `kyverno` release，以下额外的命名空间 Role/Binding 展示了范围狭窄的 PDB 授权。chart 已包含其他控制器权限；不要将此配置称为控制器的全部有效 RBAC 策略。请根据渲染结果调整 ServiceAccount 名称，并在目标集群中验证授权。

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

#### 自动生成命名空间 ResourceQuota

同样需要对 Namespace 进行显式启用。这些配额值仅用于实验环境策略，并非 AWS 预算或成本上限；启用前请考虑工作负载请求、init 容器、限制以及现有配额。

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

审查策略所有权和作用范围，在本地测试正向/负向/跳过情况，检查生成/变更后的对象，然后分阶段部署实时准入和控制器权限。Audit 是一种验证操作；它不会让变更、生成或删除变得无害。Pod 控制器自动生成和原生 ValidatingAdmissionPolicy/MutatingAdmissionPolicy 生成是不同的可选功能，且存在兼容性限制；请检查生成的策略状态，不要假定所有控制器模板都已涵盖。

### 策略模拟

创建 `policy-lab-tests/`，并将以下四个文件保存在其中。该测试有意对 `missing-label` 预期违规；测试套件通过表示预期结果相符，而不是每个输入都合规。

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

`pod.yaml`（本地测试样例；不会拉取其中的镜像）：

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

`kyverno test` 接受包含测试清单的目录；`kyverno apply` 会针对提供的资源评估策略。`--cluster` 会读取所选集群中的资源用于评估；它不是安装策略的命令。安装经审查的策略应使用 kubectl/GitOps，并会更改集群。请查阅固定版本 CLI 的帮助信息：通用的 `kyverno validate` 或 `kyverno create disallow-latest-tag` 工作流并非经过测试的接口。受支持的 Kyverno 辅助资源确实可以使用 `create` 创建。

## 策略监控与报告

### 策略报告

默认配置使用 Policy WG 的 `PolicyReport`/`ClusterPolicyReport` API。PolicyReport 是命名空间级资源；ClusterPolicyReport 用于集群范围的资源，并非简单地汇总所有命名空间。报告配置和受支持的规则类型都很重要。后台扫描会报告验证结果；它们不会追溯性地拒绝、变更或删除现有对象。即使禁用了后台扫描，现有对象在更新时仍会接受匹配的准入检查。

以下是一个**合成 schema 示例**，并非从集群采集的报告。结果字段使用 `resources` 和 `result`，而不是 `resource`/`status`；如果提供时间戳，则使用整数秒/纳秒。汇总计数必须与条目一致。

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

使用 `kubectl get policyreports -n policy-lab` 和 `kubectl get clusterpolicyreports` 查询实际报告。Reports Server/OpenReports 是单独的可选安装/配置；请先验证实际安装的 API，再假定后端可用。

### Prometheus 指标

使用上述已测试配置创建的 chart 指标 Service 和各控制器的 ServiceMonitor。它们在 8000 端口上使用名为 `metrics-port` 的 Service 端口，并通过 component/instance/part-of 选择器进行选择，而不是 `app: kyverno`。渲染结果会将它们放在 `kyverno` 中，并配置 `namespaceSelector.matchNames: [kyverno]`。Prometheus 必须能够选择这些 monitor 及其命名空间。资源存在并不能证明指标正在被采集或已导出到 CloudWatch。

## 最佳实践

### 1. 渐进式推出

先使用 Audit 分阶段部署新的验证策略，审查实际报告和例外情况，然后在适当时选择 Deny。检查 webhook 故障策略、超时、副本可用性和紧急恢复方案。对生成、mutate-existing 和破坏性删除分别进行审查。

### 2. 例外处理

范围狭窄的 matchConstraints/matchConditions 并不等同于无限制豁免。审查命名空间范围、名称、种类以及准入/用户信息的可用性。不能假定依赖用户/角色信息的传统规则可在后台扫描中评估。CEL PolicyException 使用 `policies.kyverno.io/v1`、显式的 policyRefs/matchConditions，并可选用 expiresAt；请限制能够创建它的人员，并验证安装/配置是否支持。例外对象涉及授权敏感性，不应让每个应用团队都能获得它作为准入绕过手段。

### 3. 策略组织

将带有测试和所有者信息的验证、变更、生成和删除策略纳入版本管理。旧版 ClusterPolicy 模式/JMESPath 与 CEL 不同；请逐条迁移并比较输出。当前 API 中的镜像签名验证由 `ImageValidatingPolicy` 实现；有关 attestor/registry/信任前提，请参阅[镜像安全指南](./07-image-security.md)。签名验证不等同于漏洞扫描，也不是对 registry 的一概允许列表。

## 结论

本地验证涵盖了真实 Kyverno 1.19.1 策略评估与输出保留、已发布的 API schema 以及 chart 渲染。未执行实时 webhook 顺序/自动生成、控制器 RBAC、网络、镜像信任和破坏性生命周期操作。这些仍需作为部署验收检查。

- [Kyverno 版本和已测试的 Kubernetes 版本](https://kyverno.io/docs/installation/releases/)
- [安装和控制器职责](https://kyverno.io/docs/installation/installation/)
- [迁移到 CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## 测验

尝试[Kyverno 策略管理测验](../quizzes/security/01-kyverno-policy-management-quiz.md)。
