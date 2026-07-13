# Policy Management with Kyverno

> **サポート対象バージョン**: Kubernetes 1.31, 1.32, 1.33 **最終更新**: February 19, 2026

Kyverno は、cluster 内でポリシーを管理および適用するために使用される Kubernetes-native policy engine です。この章では、Kyverno を使用して EKS cluster のポリシーを管理する方法を学びます。

## Lab Environment Setup

このドキュメントの例を実行するには、以下のツールと環境が必要です。

### Required Tools

* kubectl v1.31 以上
* Helm v3.10 以上
* 動作する Kubernetes cluster（EKS、minikube、kind など）

### Installing Kyverno

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/

# Update Helm repository
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
```

## Introduction to Kyverno

Kyverno は、ポリシーを Kubernetes resource として定義および管理できる policy engine です。Kyverno は以下の機能を提供します。

1. **Validate**: resource がポリシーに準拠していることを検証します。
2. **Mutate**: resource を自動的に変更します。
3. **Generate**: 関連する resource を自動的に作成します。
4. **Clean up**: 不要になった resource を自動的に削除します。

> **重要な概念**: Kyverno は Kubernetes-native なアプローチを使用するため、別の言語やツールを学ぶ必要はありません。ポリシーは Kubernetes resource として定義され、kubectl を使用して管理できます。

### Kyverno Architecture and How It Works

### Kyverno vs OPA Gatekeeper

Kyverno と OPA Gatekeeper はどちらも Kubernetes policy management のためのツールですが、いくつかの重要な違いがあります。

| Feature             | Kyverno                            | OPA Gatekeeper                 |
| ------------------- | ---------------------------------- | ------------------------------ |
| Policy Language     | Kubernetes YAML                    | Rego (dedicated language)      |
| Learning Curve      | Low (familiar to Kubernetes users) | High (requires learning Rego)  |
| Mutation Policies   | Native support                     | Limited support                |
| Resource Generation | Supported                          | Not supported                  |
| Image Verification  | Native support                     | Requires custom implementation |
| Policy Exceptions   | Simple                             | Complex                        |
| Performance         | Good                               | Very good (for large clusters) |

Kyverno は Kubernetes Admission Controller として動作し、API server へのすべてのリクエストをインターセプトして、定義されたポリシーに従って validation、mutation、generation、または cleanup 操作を実行します。また、background scanner を通じて既存 resource のポリシー準拠を検証し、reporting controller を通じてポリシー違反を報告します。

## Installing Kyverno

### Installation Using Helm

Helm を使用して Kyverno をインストールする方法は次のとおりです。

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
```

### Installation Using YAML Manifests

YAML manifest を使用して Kyverno をインストールする方法は次のとおりです。

```bash
# Create namespace
kubectl create namespace kyverno

# Install Kyverno
kubectl apply -f https://github.com/kyverno/kyverno/releases/download/v1.10.0/install.yaml
```

## Policy Types

Kyverno は以下のポリシータイプをサポートしています。

### 1. Validation Policies

Validation policy は、resource が特定の条件を満たしていることを検証します。条件が満たされていない場合、resource の作成または更新は拒否されます。

例: すべての Pod に resource limit が設定されていることを保証するポリシー

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

### 2. Mutation Policies

Mutation policy は resource を自動的に変更します。これにより、default value を設定したり、特定の field を追加したりできます。

例: すべての Pod に default label を追加するポリシー

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

### 3. Generation Policies

Generation policy は、resource が作成されたときに関連する resource を自動的に作成します。

例: namespace が作成されたときに NetworkPolicy を自動的に作成するポリシー

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

## Kyverno Use Cases in EKS

EKS cluster で Kyverno を使用すると、security、cost optimization、compliance など、さまざまな側面にわたってポリシーを適用できます。

### EKS and Kyverno Integration Architecture

次の図は、Kyverno が EKS cluster 内でどのように統合され、動作するかを示しています。

このアーキテクチャでは、Kyverno は EKS cluster 内の Admission Webhook として動作し、API server へのすべてのリクエストをインターセプトして、定義されたポリシーに従って処理します。ポリシー違反は、monitoring と alerting のために CloudWatch に送信できます。

### 1. Security Hardening

#### Preventing Privileged Containers

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

#### Preventing Root User Execution

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

### 2. Cost Optimization

#### Setting Resource Limits

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

#### Enforcing Specific Instance Types

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

### 3. Compliance

#### Automatic PodDisruptionBudget Generation

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

#### Automatic Namespace ResourceQuota Generation

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

## Policy Testing and Validation

Kyverno は、ポリシーのテストと検証のためのツールを提供します。

### Policy Application Workflow

次の図は、Kyverno policy の一般的な開発および適用 workflow を示しています。

### Policy Simulation

`kyverno test` コマンドを使用してポリシーをシミュレートできます。

```bash
# Install Kyverno CLI
curl -LO https://github.com/kyverno/kyverno/releases/download/v1.10.0/kyverno-cli_v1.10.0_linux_x86_64.tar.gz
tar -xvf kyverno-cli_v1.10.0_linux_x86_64.tar.gz
sudo mv kyverno /usr/local/bin/

# Test policy
kyverno test ./policy.yaml --resource=./resource.yaml
```

### Policy Validation

`kubectl kyverno` plugin を使用してポリシーを検証できます。

```bash
# Install kubectl kyverno plugin
kubectl krew install kyverno

# Validate policy
kubectl kyverno apply ./policy.yaml --cluster
```

## Policy Monitoring and Reporting

Kyverno は、ポリシー違反の monitoring と reporting のためのツールを提供します。

### Policy Reports

Kyverno は以下の report resource を作成します。

1. **ClusterPolicyReport**: cluster-level のポリシー違反を報告します。
2. **PolicyReport**: namespace-level のポリシー違反を報告します。

```bash
# View cluster policy reports
kubectl get clusterpolicyreport

# View namespace policy reports
kubectl get policyreport -n <namespace>
```

### Prometheus Metrics

Kyverno は、ポリシー違反を monitoring するための Prometheus metrics を提供します。

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

## Best Practices

### 1. Gradual Rollout

新しいポリシーを導入する際は、まず `validationFailureAction: audit` mode に設定して違反を monitoring し、準備ができたら `enforce` mode に切り替えることをお勧めします。

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

### 2. Exception Handling

特定の namespace または resource の例外を処理するには、`exclude` section を使用します。

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

### 3. Policy Organization

目的別にポリシーを整理し、明確な名前を使用することをお勧めします。

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

## Conclusion

Kyverno は、Kubernetes-native なアプローチを使用してポリシーを管理するための強力なツールです。EKS cluster で Kyverno を使用すると、security、cost optimization、compliance など、さまざまな側面にわたってポリシーを適用できます。ポリシーを段階的に導入し、例外を処理し、適切に整理することが重要です。

## Quiz

この章で学んだ内容を確認するには、[Kyverno Policy Management Quiz](../quizzes/security/01-kyverno-policy-management-quiz.md) に挑戦してください。
