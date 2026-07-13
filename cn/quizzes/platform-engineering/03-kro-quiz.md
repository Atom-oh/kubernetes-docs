# KRO Helm 迁移测验

> **相关文档**: [Kubernetes Resource Operator (KRO)](../../platform-engineering/03-kro.md)

## 选择题

### 1. 以下哪一项不是 Kubernetes Resource Operator (KRO) 的核心概念？

- A) 声明式 resource 关系
- B) 基于状态的 reconciliation
- C) 命令式脚本执行
- D) Resource graph

<details>
<summary>显示答案</summary>

**答案：C) 命令式脚本执行**

**解释：**
KRO 以声明式方式管理 resources。声明式 resource 关系、基于状态的 reconciliation、resource graph 和自动化 lifecycle management 都是核心概念，而命令式脚本执行不是 KRO 核心概念的一部分。

</details>

### 2. `childResources` 在 ResourceGraphDefinition (RGD) 中的作用是什么？

- A) 定义 parent resource metadata
- B) 定义要从 parent resource 创建的 child resources 列表
- C) 定义 cluster-wide settings
- D) 定义 namespace policies

<details>
<summary>显示答案</summary>

**答案：B) 定义要从 parent resource 创建的 child resources 列表**

**解释：**
`childResources` 定义将从 parent custom resource 创建的 child Kubernetes resources（Deployment、Service、Ingress 等）的列表和模板。

</details>

### 3. 与 Helm 相比，KRO 的主要差异化点是什么？

- A) 使用 Go template
- B) Chart archive packaging
- C) 显式 resource 关系建模和自动 state propagation
- D) Release history management

<details>
<summary>显示答案</summary>

**答案：C) 显式 resource 关系建模和自动 state propagation**

**解释：**
KRO 将 resources 之间的关系建模为显式 graph，并自动将 child resource 状态传播到 parent resource。

</details>

### 4. RGD templates 中的 `.parent` 引用什么？

- A) Kubernetes cluster
- B) Parent custom resource
- C) Namespace
- D) Controller pod

<details>
<summary>显示答案</summary>

**答案：B) Parent custom resource**

**解释：**
在 RGD templates 中，`.parent` 引用应用了 ResourceGraphDefinition 的 parent custom resource。

</details>

### 5. KRO 中哪个字段用于有条件地创建 child resource？

- A) `when`
- B) `if`
- C) `condition`
- D) `enabled`

<details>
<summary>显示答案</summary>

**答案：C) `condition`**

**解释：**
RGD 的 childResources 中的 `condition` 字段可用于有条件地创建 child resources。

</details>

### 6. RGD 中 `statusMappings` 的用途是什么？

- A) 定义 error handling 行为
- B) 将 child resource status 映射到 parent resource status
- C) 配置 logging levels
- D) 设置 resource quotas

<details>
<summary>显示答案</summary>

**答案：B) 将 child resource status 映射到 parent resource status**

**解释：**
`statusMappings` 定义如何从 child resources 提取 status 信息，并将其传播到 parent custom resource 的 status 字段。

</details>

### 7. KRO 如何处理 resource dependencies？

- A) 通过 YAML files 中的手动排序
- B) 通过自动确定创建顺序的 resource graph
- C) 通过数字 priority fields
- D) 通过字母顺序

<details>
<summary>显示答案</summary>

**答案：B) 通过自动确定创建顺序的 resource graph**

**解释：**
KRO 使用 resource graph 来理解 resources 之间的 dependencies，并自动确定 resource 创建和删除的正确顺序。

</details>

### 8. 在 KRO 中删除 parent custom resource 时会发生什么？

- A) Child resources 保持 orphaned 状态
- B) Child resources 会被自动 garbage collected
- C) 需要手动 cleanup
- D) 会抛出 error

<details>
<summary>显示答案</summary>

**答案：B) Child resources 会被自动 garbage collected**

**解释：**
KRO 会在 child resources 上设置 owner references，因此当 parent 被删除时，Kubernetes 的 garbage collector 会自动移除所有 child resources。

</details>

### 9. KRO 中哪个组件会 watch custom resource changes？

- A) API Server
- B) Scheduler
- C) KRO Controller
- D) Kubelet

<details>
<summary>显示答案</summary>

**答案：C) KRO Controller**

**解释：**
KRO Controller 会 watch 由 ResourceGraphDefinitions 定义的 custom resources 的变化，并 reconcile 期望状态。

</details>

### 10. KRO 中与 Helm 的 `helm upgrade --install` 行为等价的是什么？

- A) 对 custom resource 执行 `kubectl apply`
- B) 对 custom resource 执行 `kubectl replace`
- C) 对 custom resource 执行 `kubectl patch`
- D) `kubectl create --save-config`

<details>
<summary>显示答案</summary>

**答案：A) 对 custom resource 执行 `kubectl apply`**

**解释：**
`kubectl apply` 提供类似 `helm upgrade --install` 的幂等行为。如果 resource 不存在，它会创建；如果存在，它会更新。

</details>

## 简答题

### 1. KRO 中定义 custom resources 与 Kubernetes native resources 之间关系的核心 resource 是什么？

<details>
<summary>显示答案</summary>

**答案：ResourceGraphDefinition (RGD)**

**解释：**
ResourceGraphDefinition (RGD) 是 KRO 的核心组件，用于以声明式方式定义 custom resources（parent）与 Kubernetes native resources（children）之间的关系。

</details>

### 2. Helm 的 values.yaml 在 KRO 中的等价物是什么？

<details>
<summary>显示答案</summary>

**答案：Custom Resource (CR) 的 spec 字段**

**解释：**
正如 Helm 通过 values.yaml 自定义配置一样，KRO 通过 custom resource 的 spec 字段定义应用配置。

</details>

### 3. 如何在 RGD template 中引用 sibling child resource 的输出？

<details>
<summary>显示答案</summary>

**答案：使用 `.children.<resourceId>` 语法**

**解释：**
在 RGD templates 中，你可以使用 `.children.<resourceId>` 引用其他 child resources，以访问其 metadata、spec 或 status 字段，从而实现 cross-resource 引用。

</details>

### 4. KRO 使用哪个 annotation 来跟踪 managed resources？

<details>
<summary>显示答案</summary>

**答案：`kro.run/owner` annotation**

**解释：**
KRO 使用 `kro.run/owner` annotation 以及 Kubernetes owner references 来跟踪哪些 resources 由哪个 parent custom resource 管理。

</details>

### 5. KRO 如何处理 custom resources 的 schema validation？

<details>
<summary>显示答案</summary>

**答案：通过 RGD 的 spec.schema 字段中定义的 OpenAPI v3 Schema**

**解释：**
KRO 会从 RGD 生成 CRD，并使用 ResourceGraphDefinition 中定义的 OpenAPI v3 Schema 执行 schema validation。

</details>

## 实践题

### 1. 将以下 Helm values.yaml 转换为 KRO custom resource instance。

```yaml
# Helm values.yaml
replicaCount: 2
image:
  repository: myapp
  tag: "1.0.0"
service:
  type: ClusterIP
  port: 8080
```

<details>
<summary>显示答案</summary>

```yaml
apiVersion: kro.example.com/v1
kind: MyApp
metadata:
  name: my-application
spec:
  replicas: 2
  image:
    repository: myapp
    tag: "1.0.0"
  service:
    type: ClusterIP
    port: 8080
```

</details>

### 2. 编写一个基于 parent spec 创建 Deployment 的 RGD childResource 定义。

<details>
<summary>显示答案</summary>

```yaml
childResources:
  - id: deployment
    resource:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{.parent.metadata.name}}"
      spec:
        replicas: "{{.parent.spec.replicas}}"
        selector:
          matchLabels:
            app: "{{.parent.metadata.name}}"
        template:
          metadata:
            labels:
              app: "{{.parent.metadata.name}}"
          spec:
            containers:
              - name: app
                image: "{{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}"
                ports:
                  - containerPort: "{{.parent.spec.service.port}}"
```

</details>

### 3. 编写一个 statusMappings 配置，将 Deployment 的 available replicas 暴露到 parent status。

<details>
<summary>显示答案</summary>

```yaml
statusMappings:
  - childResourceId: deployment
    fieldPath: status.availableReplicas
    parentFieldPath: status.availableReplicas
  - childResourceId: deployment
    fieldPath: status.conditions
    parentFieldPath: status.deploymentConditions
```

**解释：**
statusMappings 从 child resource status 中提取特定字段，并将其映射到 parent custom resource 的 status，使用户能够通过 parent resource 检查应用状态。

</details>

## 进阶题

### 1. 使用 KRO 设计一个多环境（dev/staging/production）部署策略。

<details>
<summary>显示答案</summary>

**特定于环境的 Custom Resource Instances：**

```yaml
# dev/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-dev
spec:
  replicas: 1
  image:
    tag: "dev-latest"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
---
# staging/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-staging
spec:
  replicas: 2
  image:
    tag: "rc-1.0.0"
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
---
# production/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-prod
spec:
  replicas: 3
  image:
    tag: "v1.0.0"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
```

**GitOps 集成：**
使用 ArgoCD ApplicationSet，通过单个 RGD 在所有环境中自动化特定于环境的部署。

</details>

### 2. 比较 Helm 和 KRO 在管理类似 database cluster 这样的 stateful application 时的运维差异。

<details>
<summary>显示答案</summary>

**Helm 方法：**
- 基于 templating：在安装时生成静态 manifests
- Release management：通过 Secrets/ConfigMaps 跟踪版本
- Upgrade process：需要 `helm upgrade` command
- State tracking：初始部署后没有内置 reconciliation
- Rollback：使用存储的 release history

**KRO 方法：**
- 基于 reconciliation：持续监控并修正 drift
- Native Kubernetes：使用标准 kubectl 和 CRDs
- Upgrade process：修改 CR spec，controller 进行 reconcile
- State tracking：controller 持续 watch 并 reconcile
- Rollback：将 CR spec 还原到之前的状态

**Stateful Applications 的关键差异：**

| Aspect | Helm | KRO |
|--------|------|-----|
| Drift Detection | Manual | Automatic |
| Self-healing | No | Yes |
| Status Visibility | External (helm status) | Native (kubectl get) |
| Dependency Management | Chart dependencies | Resource graph |
| Lifecycle Hooks | pre/post hooks | Controller logic |

**建议：**
KRO 更适合需要持续 reconciliation、自动 drift correction 和复杂 lifecycle management 的 stateful applications。对于部署简单直接的 stateless applications，Helm 更简单。

</details>
