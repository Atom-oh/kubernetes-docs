# 使用 Kyverno 进行策略管理

> **验证基线**：Kyverno/CLI 1.19.1，Helm chart 3.9.1。当前发布指南列出经过测试的 Kubernetes 版本为 1.33–1.35；chart 中更宽松的安装约束并不构成兼容性保证。
> **最后更新**：September 13, 2026

Kyverno 评估 Kubernetes 策略，并执行显式配置的变更（mutation）、生成（generation）与删除（deletion）操作。以下示例均使用真实 CLI 以及已发布的 schema/chart 在本地检查过。未执行任何真实集群安装、准入（admission）、网络隔离、清理或 AWS 集成。

原有的 `ClusterPolicy` 示例已更新为 `policies.kyverno.io/v1` CEL 策略。官方 1.19 迁移指南将 ClusterPolicy/Policy、CleanupPolicy 以及旧版 `kyverno.io` PolicyException 标记为弃用，计划在 1.20 中移除。它们在 1.19 中并非已经不存在；请在升级前完成迁移与测试，而不是仅仅替换 apiVersion 字符串。

## 实验环境准备

### 所需工具

请使用与目标 API server 版本偏差（version skew）受支持的 kubectl、支持 OCI 的受支持 Helm 版本，以及在这些本地测试中经过验证的 Kyverno 1.19.1 CLI。获取与你的操作系统/架构匹配的 CLI 归档文件，并校验其公布的 checksum/签名。不要复用 1.10.0 的归档文件，也不要把未经验证的下载内容通过管道交给 root 权限安装。

从本地文件开始。下面的策略是相互独立的示例，而不是一整套需要全部应用的集合。Pod 示例的目标是 `policy-lab`；生成类策略还额外要求一个显式标签（label）。请限制谁可以修改这些策略、namespace 标签、Role 和 PolicyException。这些选择器本身并不构成 RBAC 安全边界。

### 安装 Kyverno

准备一个专用的 `kyverno` namespace。在改动共享集群之前，请检查所选的 EKS/Kubernetes 版本、API server 到 webhook 的连通性、DNS、准入失败/超时行为以及 CRD 升级流程。Kubernetes ServiceAccount/RBAC 为控制器授权；安装 Kyverno 本身并不需要 AWS 管理员角色。

## Kyverno 简介

### Kyverno 架构与工作原理

| 组件 | 职责 |
|---|---|
| Admission controller | 匹配准入请求，执行策略校验/变更/镜像检查；并非处理每个 GET/list 请求 |
| Background controller | 生成（generate）以及显式启用的 mutate-existing 工作 |
| Reports controller | 策略结果聚合/报告 |
| Cleanup controller | 定时删除策略以及被允许的清理操作 |

校验类（validating）策略不会删除或修复已存在的不合规资源。后台报告、mutate-existing、generate-existing 和定时删除是彼此独立的机制，所需权限各不相同。生成可能是异步的；namespace 创建与生成的 NetworkPolicy 生效并不是一个原子操作。

### Kyverno 与 OPA Gatekeeper 对比

Kyverno 当前的策略在 YAML/JSON 清单中使用 CEL；旧版策略还会使用 pattern 和 JMESPath。Kubernetes 原生的打包方式并不能免去学习策略表达式的需要。Gatekeeper 使用 ConstraintTemplate/Constraint 以及其版本所支持的策略引擎，具备独立的准入/审计/变更能力。请比较所需特性、表达式语言、策略测试、控制器可用性以及实测的工作负载影响。旧的“简单/复杂”和“性能良好/非常好”的评级是缺乏依据的比较，而非基准测试结果。

## 安装 Kyverno

### 使用 Helm 安装

将以下内容保存为 `kyverno-values.yaml`。这是一个单副本的**实验**配置。ServiceMonitor CRD 以及能够选中相应 namespace/标签的 Prometheus 安装必须事先存在；请将示例中的 `release: kube-prom` 标签替换为该 Prometheus 安装所使用的选择器，或在准备就绪前禁用 ServiceMonitor。

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

渲染结果包含四个控制器 Deployment 和四个指标 ServiceMonitor。增加副本数需要规划拓扑、中断（disruption）、资源规格以及 webhook 可用性；每个控制器一个副本并不是高可用（HA）设计。请检查当前 chart 的默认值和实际渲染出的镜像标签，不要把 chart 版本标签当作应用程序版本来理解。

### 使用 YAML 清单安装

如果由 GitOps 管理 YAML，请渲染已固定版本的 chart，并把其中的 CRD、RBAC、证书和 hook 作为一个受管整体来评审。对渲染结果直接执行 `kubectl apply` 不会执行 Helm 的 hook/升级语义。不要把旧的 1.10.0 install.yaml 覆盖应用到更新的版本之上，也不要让同一批控制器存在多个所有者。

## 策略类型

### 1. 校验策略（Validation Policies）

将这个独立示例保存为 `require-limits.yaml`。它检查**普通容器和 init 容器**是否设置了非空的 CPU/内存 limits。临时容器（ephemeral container）不能声明资源 requests/limits；下文的安全检查会单独覆盖它们。这是一项自行选择的按容器策略，并不代表每个 Kubernetes 工作负载都必须采用这种资源策略。

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

`validationActions: [Audit]` 会记录违规但仍允许匹配的准入请求；`[Deny]` 则在完成分阶段发布/影响评估后拒绝这些请求。`Warn` 可以向客户端返回警告。webhook 的 `failurePolicy` 控制评估/传输失败时的行为，是另一项独立设置。离线 CLI 的失败结果并不能证明某个 Audit 策略拒绝了真实请求。

### 2. 变更策略（Mutation Policies）

保存为 `add-default-label.yaml`。已存在的 `environment` 标签会被保留，包括显式设置为空值的情况。这里使用的是 CEL ApplyConfiguration，而不是 Kyverno 内部的 Helm Go 模板 `if`/`hasKey` 语法。

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

该示例禁用了 mutate-existing。准入变更仍然会影响匹配的 CREATE/UPDATE 请求。若改用 JSONPatch 方案，必须先创建缺失的 labels map 再添加子键，并在 JSON Pointer 路径中把 `/` 转义为 `~1`。多个相互独立的策略之间，变更顺序无法保证。

### 3. 生成策略（Generation Policies）

保存为 `generate-networkpolicy.yaml`。只有名为 `policy-lab` 且带有 `training.example.com/managed: "true"` 的 Namespace 才会触发该示例。对于 Namespace 对象，应匹配其**名称/标签**，而不是 `metadata.namespace` 或旧版的 namespace 排除列表。

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

在工作负载依赖该 namespace 之前，请先准备好必要的 DNS/API/应用放行规则。Kubernetes NetworkPolicy 隔离需要具备执行能力的 CNI；其他放行策略是叠加生效的，并且必须考虑 host-network 行为。本地生成的清单并不能证明流量确实被阻断。

这里禁用了同步（synchronization）与 generate-existing。安装该策略时，已经存在的 Namespace 不会被自动回填：请等待后续匹配的触发事件，或在更改该设置前显式评审是否启用 generate-existing。启用同步后，下游资源的生命周期取决于是 data 还是 clone 源、触发资源的变化以及 `orphanDownstreamOnPolicyDelete`；它并不是通用的备份/回滚机制。共享 Secret 需要显式的源/目标允许列表以及 RBAC/凭证生命周期评审，而不是把它复制到每个新建的 namespace。

### 4. 定时删除（Scheduled Deletion）

`DeletingPolicy` 使用 `spec.schedule` 和 CEL 条件；它与校验类策略相互独立，没有 validationActions 的 Audit 开关。cleanup controller 需要显式的删除权限。建议使用范围较窄的 namespace/对象标签以及明确的存留期限/状态保留要求，检查被选中的候选对象，并在启用调度之前测试恢复流程。可选测验中的示例选取的是被标记为已完成的 Pod；它并不表示“超过 24 小时”，并且这里没有执行任何定时删除。

## Kyverno 在 EKS 中的用例

### EKS 与 Kyverno 集成架构

EKS API server 通过配置好的 Kubernetes 网络/RBAC 路径调用匹配的准入 webhook。CloudWatch 导出是一个独立配置的采集器/集成，具有各自的 IAM 与保留策略；安装 Kyverno 并不会自动把每个 PolicyReport 发送到 CloudWatch。避免打印可能包含机密信息的原始准入负载。

### 1. 安全加固

#### 阻止特权容器

缺失的 `privileged` 视为 false。该检查覆盖普通容器、init 容器和临时容器；声明的 `pods/ephemeralcontainers` 匹配仍需在目标环境中进行真实的准入/子资源测试。

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

该策略采用每个容器的覆盖值或 Pod 级别的默认值，要求生效的 runAsNonRoot，并拒绝显式生效的 UID 0。它校验的是声明内容；运行时仍然要考虑 kubelet/镜像的行为。

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

#### 设置资源 limits

保存为 `default-resources.yaml`。这个仅针对 CREATE 的示例避免在普通更新过程中改动正在运行的 Pod 资源，并且只在普通容器**既没有 requests 也没有 limits** 时才提供默认值。它会保留完整或部分已有的资源设置，而不是覆盖工作负载规格，也不会产生大于已有较小 limit 的 request。部分设置的情况请单独评审；它不会填补每一个缺失字段，也不会为 init/临时容器设置默认资源。

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

原文中的实例名称只是示意性的允许列表，并非当前的推荐配置。显式的 nodeSelector 是一项强制性的调度约束。这个仅在准入阶段生效的 CREATE 策略会拒绝已提供的 nodeName；后台扫描被禁用，因为已完成调度的 Pod 本来就会带上 nodeName。对节点标签的信任、调度器/绑定权限以及可用容量是另一回事。对于拥有绑定 Pod 或修改 Node 权限的主体，声明性检查无法保证最终的放置位置。

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

这个需要主动加入（opt-in）的 Deployment 示例要求期望副本数至少为 2，并复制**完整的 spec.selector**（包括 matchExpressions），而不是依赖可能并不存在的顶层 app 标签。它并不能证明有两个副本处于 Ready 状态。在扩缩容或选择器变化之后，这个静态的实验用 budget 需要单独的归属/评审决策，尤其是在同步被禁用的情况下。PDB 约束的是符合条件的自愿驱逐，而不是所有的滚动更新或非自愿故障。

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

background controller 需要具备创建所生成资源的实际权限。对于渲染出的 `kyverno` release，下面这个额外的 namespace 级 Role/Binding 展示了一个范围很窄的 PDB 授权。chart 本身已经包含其他控制器权限；不要把这里的内容当作该控制器全部的有效 RBAC 策略。请把 ServiceAccount 名称调整为与渲染结果一致，并在目标集群中验证授权情况。

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

同样需要显式的 Namespace 主动加入。配额数值属于实验策略，而不是 AWS 预算或成本上限；启用之前请考虑工作负载的 requests、init 容器、limits 以及已有的配额。

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

### 策略应用流程

评审策略的归属与作用范围，在本地测试通过/不通过/跳过等各类情形，检查生成或被变更的对象，然后再分阶段启用真实准入与控制器权限。Audit 只是一种校验动作；它不会让变更、生成或删除变得无害。Pod controller 自动生成（autogeneration）以及原生 ValidatingAdmissionPolicy/MutatingAdmissionPolicy 生成是各自独立的可选项，并且存在兼容性限制；请检查生成的策略状态，不要假定所有控制器模板都已被覆盖。

### 策略模拟

创建 `policy-lab-tests/` 目录并把下面四个文件保存在其中。该测试有意期望 `missing-label` 出现违规；测试套件通过意味着期望与实际相符，而不是说每个输入都合规。

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

`pod.yaml`（本地测试固件；其镜像不会被拉取）：

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

### 策略校验

`kyverno test` 接收一个包含测试清单的目录；`kyverno apply` 针对给定资源评估策略。`--cluster` 会从所选集群读取资源用于评估；它不是安装策略的命令。安装经过评审的策略要使用 kubectl/GitOps，并且会改动集群。请查阅固定版本 CLI 的帮助信息：通用的 `kyverno validate` 或 `kyverno create disallow-latest-tag` 这类流程并不是经过测试的接口。`create` 确实存在，用于受支持的 Kyverno 辅助资源。

## 策略监控与报告

### 策略报告（Policy Reports）

默认配置使用 Policy WG 的 `PolicyReport`/`ClusterPolicyReport` API。PolicyReport 是 namespace 级的；ClusterPolicyReport 覆盖集群范围（cluster-scoped）的资源，而不是简单地把所有 namespace 合并起来。报告配置以及受支持的规则类型很关键。后台扫描会报告校验结果；它们不会追溯地拒绝、变更或删除已有对象。即使后台扫描被禁用，已有对象在更新时仍然要接受匹配的准入检查。

以下是一个**人为构造的 schema 示例**，不是从集群中采集到的报告。结果使用 `resources` 和 `result`，而不是 `resource`/`status`；如果提供时间戳，则使用整数形式的秒/纳秒。摘要计数必须与条目保持一致。

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

使用 `kubectl get policyreports -n policy-lab` 和 `kubectl get clusterpolicyreports` 查询实际的报告。Reports Server/OpenReports 是彼此独立的可选安装/配置项；在假定后端之前，请先确认相应 API 确实已安装。

### Prometheus 指标

请使用上面测试过的 values 所创建的指标 Service 以及各控制器对应的 ServiceMonitor。它们的 Service 端口名为 `metrics-port`，端口号 8000，并带有 component/instance/part-of 选择器——而不是 `app: kyverno`。渲染结果会把它们放在 `kyverno` 中，并配置 `namespaceSelector.matchNames: [kyverno]`。Prometheus 必须能够选中这些 monitor 和该 namespace。资源存在并不能证明抓取或 CloudWatch 导出已经生效。

## 最佳实践

### 1. 渐进式推广

新的校验策略先以 Audit 方式分阶段上线，评审实际报告与例外情况，然后在合适的地方选择 Deny。检查 webhook 的 failure policy、超时、副本可用性以及紧急恢复方案。把生成、mutate-existing 与破坏性删除的评审分开进行。

### 2. 例外处理

范围较窄的 matchConstraints/matchConditions 并不等同于无限制的豁免。请评审 namespace 范围、名称、kind 以及准入/用户信息的可用性。依赖用户/角色信息的传统规则不能假定在后台扫描中同样可以求值。CEL 版 PolicyException 使用 `policies.kyverno.io/v1`、显式的 policyRefs/matchConditions，并可选地设置 expiresAt；请限制谁可以创建它，并验证安装/配置是否支持。例外是一种对授权敏感的对象，而不是每个应用团队都应获得的准入绕过手段。

### 3. 策略组织

对校验、变更、生成和删除策略进行版本管理，并配套测试与负责人。旧版 ClusterPolicy 的 pattern/JMESPath 与 CEL 不同；请逐条规则迁移并比较输出结果。在当前 API 中，镜像签名验证由 `ImageValidatingPolicy` 负责；关于 attestor/registry/信任等前提条件，请参见[镜像安全指南](./07-image-security.md)。签名验证既不是漏洞扫描，也不是一份笼统的 registry 允许列表。

## 结论

本地验证覆盖了真实 Kyverno 1.19.1 的策略评估与输出保留、已发布的 API schema 以及 chart 渲染。真实环境的 webhook 排序/自动生成、控制器 RBAC、网络、镜像信任以及破坏性生命周期操作均未执行。这些仍属于部署验收检查项。

- [Kyverno releases and tested Kubernetes versions](https://kyverno.io/docs/installation/releases/)
- [Installation and controller responsibilities](https://kyverno.io/docs/installation/installation/)
- [Migration to CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## 测验

请尝试[Kyverno 策略管理测验](../quizzes/security/01-kyverno-policy-management-quiz.md)。
