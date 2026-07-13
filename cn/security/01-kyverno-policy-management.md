# 使用 Kyverno 进行策略管理

> **支持的版本**: Kubernetes 1.31, 1.32, 1.33 **最后更新**: February 19, 2026

Kyverno 是一个 Kubernetes 原生的策略引擎，用于在集群内管理和执行策略。在本章中，我们将学习如何使用 Kyverno 管理 EKS 集群中的策略。

## 实验环境设置

要跟随本文档中的示例进行操作，你需要以下工具和环境：

### 所需工具

* kubectl v1.31 或更高版本
* Helm v3.10 或更高版本
* 一个可用的 Kubernetes 集群（EKS、minikube、kind 等）

### 安装 Kyverno

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/

# Update Helm repository
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
```

## Kyverno 简介

Kyverno 是一个策略引擎，允许你将策略定义和管理为 Kubernetes 资源。Kyverno 提供以下能力：

1. **验证**: 验证资源是否符合策略。
2. **变更**: 自动修改资源。
3. **生成**: 自动创建相关资源。
4. **清理**: 自动删除不再需要的资源。

> **关键概念**: Kyverno 采用 Kubernetes 原生方式，因此无需学习单独的语言或工具。策略被定义为 Kubernetes 资源，并可以使用 kubectl 进行管理。

### Kyverno 架构及其工作方式

### Kyverno vs OPA Gatekeeper

Kyverno 和 OPA Gatekeeper 都是用于 Kubernetes 策略管理的工具，但它们之间有一些重要区别：

| 功能                | Kyverno                            | OPA Gatekeeper                 |
| ------------------- | ---------------------------------- | ------------------------------ |
| 策略语言            | Kubernetes YAML                    | Rego（专用语言）               |
| 学习曲线            | 低（Kubernetes 用户熟悉）          | 高（需要学习 Rego）            |
| 变更策略            | 原生支持                           | 支持有限                       |
| 资源生成            | 支持                               | 不支持                         |
| 镜像验证            | 原生支持                           | 需要自定义实现                 |
| 策略例外            | 简单                               | 复杂                           |
| 性能                | 良好                               | 非常好（适用于大型集群）       |

Kyverno 作为 Kubernetes Admission Controller 运行，会拦截所有发往 API server 的请求，并根据定义的策略执行验证、变更、生成或清理操作。它还会通过后台扫描器验证现有资源的策略合规性，并通过报告控制器报告策略违规情况。

## 安装 Kyverno

### 使用 Helm 安装

以下是使用 Helm 安装 Kyverno 的方法：

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
```

### 使用 YAML 清单安装

以下是使用 YAML manifests 安装 Kyverno 的方法：

```bash
# Create namespace
kubectl create namespace kyverno

# Install Kyverno
kubectl apply -f https://github.com/kyverno/kyverno/releases/download/v1.10.0/install.yaml
```

## 策略类型

Kyverno 支持以下策略类型：

### 1. 验证策略

验证策略会验证资源是否满足特定条件。如果不满足条件，则会拒绝创建或更新资源。

示例：确保所有 pods 都设置了资源限制的策略

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 2. 变更策略

变更策略会自动修改资源。这允许你设置默认值或添加特定字段。

示例：向所有 pods 添加默认 labels 的策略

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-labels
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        metadata:
          labels:
            environment: "{{request.namespace}}"
            app.kubernetes.io/managed-by: kyverno
```

### 3. 生成策略

生成策略会在创建资源时自动创建相关资源。

示例：创建 namespace 时自动创建 NetworkPolicy 的策略

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

## EKS 中的 Kyverno 使用场景

在 EKS 集群中使用 Kyverno，可以在安全、成本优化和合规性等多个方面应用策略。

### EKS 与 Kyverno 集成架构

下图展示了 Kyverno 如何在 EKS 集群中集成和运行：

在此架构中，Kyverno 作为 EKS 集群内的 Admission Webhook 运行，拦截所有发往 API server 的请求，并根据定义的策略处理这些请求。策略违规可以发送到 CloudWatch 进行监控和告警。

### 1. 安全加固

#### 防止特权容器

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed."
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
```

#### 防止以 Root 用户执行

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-root-user
spec:
  validationFailureAction: enforce
  rules:
  - name: check-runAsNonRoot
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Running as root is not allowed. Set runAsNonRoot to true."
      pattern:
        spec:
          containers:
          - securityContext:
              runAsNonRoot: true
```

### 2. 成本优化

#### 设置资源限制

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: set-default-resources
spec:
  rules:
  - name: set-default-resources
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        spec:
          containers:
          - (name): "*"
            resources:
              limits:
                memory: "512Mi"
                cpu: "500m"
              requests:
                memory: "256Mi"
                cpu: "250m"
```

#### 强制使用特定实例类型

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-node-types
spec:
  validationFailureAction: enforce
  rules:
  - name: check-node-type
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Pod must be scheduled on approved node types."
      pattern:
        spec:
          nodeSelector:
            node.kubernetes.io/instance-type: "?*"
          affinity:
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: node.kubernetes.io/instance-type
                    operator: In
                    values:
                    - m5.large
                    - c5.large
                    - r5.large
```

### 3. 合规性

#### 自动生成 PodDisruptionBudget

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-pdb
spec:
  rules:
  - name: generate-pdb-for-deployment
    match:
      resources:
        kinds:
        - Deployment
    generate:
      kind: PodDisruptionBudget
      name: "{{request.object.metadata.name}}-pdb"
      namespace: "{{request.object.metadata.namespace}}"
      synchronize: true
      data:
        spec:
          minAvailable: 1
          selector:
            matchLabels:
              app: "{{request.object.metadata.labels.app}}"
```

#### 自动生成 Namespace ResourceQuota

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-resourcequota
spec:
  rules:
  - name: generate-resourcequota
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: ResourceQuota
      name: default-resourcequota
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      data:
        spec:
          hard:
            requests.cpu: "10"
            requests.memory: 10Gi
            limits.cpu: "20"
            limits.memory: 20Gi
            pods: "50"
```

## 策略测试与验证

Kyverno 提供用于测试和验证策略的工具。

### 策略应用工作流

下图展示了 Kyverno 策略的典型开发和应用工作流：

### 策略模拟

你可以使用 `kyverno test` 命令模拟策略：

```bash
# Install Kyverno CLI
curl -LO https://github.com/kyverno/kyverno/releases/download/v1.10.0/kyverno-cli_v1.10.0_linux_x86_64.tar.gz
tar -xvf kyverno-cli_v1.10.0_linux_x86_64.tar.gz
sudo mv kyverno /usr/local/bin/

# Test policy
kyverno test ./policy.yaml --resource=./resource.yaml
```

### 策略验证

你可以使用 `kubectl kyverno` 插件验证策略：

```bash
# Install kubectl kyverno plugin
kubectl krew install kyverno

# Validate policy
kubectl kyverno apply ./policy.yaml --cluster
```

## 策略监控和报告

Kyverno 提供用于监控和报告策略违规的工具。

### 策略报告

Kyverno 会创建以下报告资源：

1. **ClusterPolicyReport**: 报告集群级策略违规。
2. **PolicyReport**: 报告 namespace 级策略违规。

```bash
# View cluster policy reports
kubectl get clusterpolicyreport

# View namespace policy reports
kubectl get policyreport -n <namespace>
```

### Prometheus 指标

Kyverno 提供 Prometheus 指标，用于监控策略违规：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kyverno-svc-metrics
  namespace: kyverno
  labels:
    app: kyverno
spec:
  ports:
  - port: 8000
    targetPort: 8000
    name: metrics
  selector:
    app: kyverno
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kyverno-svc-metrics
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: kyverno
  endpoints:
  - port: metrics
```

## 最佳实践

### 1. 渐进式推出

引入新策略时，建议先设置 `validationFailureAction: audit` 模式来监控违规情况，准备就绪后再切换到 `enforce` 模式。

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: audit  # Start with audit mode first
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 2. 例外处理

要处理特定 namespaces 或资源的例外情况，请使用 `exclude` 部分：

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    exclude:
      resources:
        namespaces:
        - kube-system
        - kyverno
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 3. 策略组织

建议按用途组织策略，并使用清晰的名称：

```
policies/
├── security/
│   ├── disallow-privileged-containers.yaml
│   ├── require-pod-probes.yaml
│   └── restrict-image-registries.yaml
├── cost-optimization/
│   ├── require-resource-limits.yaml
│   └── restrict-node-types.yaml
└── compliance/
    ├── generate-pdb.yaml
    └── generate-resourcequota.yaml
```

## 结论

Kyverno 是一个强大的工具，可以使用 Kubernetes 原生方式管理策略。在 EKS 集群中使用 Kyverno，可以在安全、成本优化和合规性等多个方面应用策略。以渐进方式引入策略、处理例外情况并良好组织策略非常重要。

## 测验

要测试你在本章中学到的内容，请尝试 [Kyverno 策略管理测验](../quizzes/security/01-kyverno-policy-management-quiz.md)。
