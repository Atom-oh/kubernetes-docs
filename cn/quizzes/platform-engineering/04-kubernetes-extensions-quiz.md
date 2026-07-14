# Kubernetes 扩展机制测验

> **相关文档**: [Kubernetes 扩展机制](../../platform-engineering/04-kubernetes-extensions.md)

## 选择题

### 1. CRD (Custom Resource Definition) 的主要目的是什么？

- A) 修改现有的 Kubernetes 资源
- B) 使用自定义资源类型扩展 Kubernetes API
- C) 配置 pod 网络
- D) 预置存储卷

<details>
<summary>显示答案</summary>

**答案: B) 使用自定义资源类型扩展 Kubernetes API**

**解释:**
CRD 允许你通过定义像原生 Kubernetes 资源一样工作的自定义资源类型来扩展 Kubernetes API。

</details>

### 2. custom controller 的 reconciliation loop 主要执行什么任务？

- A) 立即删除资源
- B) 调和当前状态与期望状态之间的差异
- C) 向 API server 注册新的 API
- D) 应用网络策略

<details>
<summary>显示答案</summary>

**答案: B) 调和当前状态与期望状态之间的差异**

**解释:**
custom controller 的 reconciliation loop 会观察资源的当前状态，将其与期望状态 (spec) 进行比较，并在存在差异时采取操作以达到期望状态。

</details>

### 3. Operator pattern 的核心组件是什么？

- A) Deployment 和 Service
- B) CRD 和 Custom Controller
- C) ConfigMap 和 Secret
- D) Ingress 和 NetworkPolicy

<details>
<summary>显示答案</summary>

**答案: B) CRD 和 Custom Controller**

**解释:**
Operator pattern 使用 CRD 定义应用配置，并使用 custom controller 自动化部署、升级和恢复等运维知识。

</details>

### 4. MutatingAdmissionWebhook 的主要用途是什么？

- A) 拒绝 API 请求
- B) 修改 API 请求
- C) 记录 API 响应
- D) 升级 API 版本

<details>
<summary>显示答案</summary>

**答案: B) 修改 API 请求**

**解释:**
MutatingAdmissionWebhook 可以在 API 请求被持久化之前修改这些请求。常见用途包括：sidecar container 注入、设置默认值等。

</details>

### 5. scheduler framework 中 Filter plugin 的作用是什么？

- A) 为 node 分配分数
- B) 排除无法运行 pod 的 node
- C) 将 pod 绑定到 node
- D) 预留 node 资源

<details>
<summary>显示答案</summary>

**答案: B) 排除无法运行 pod 的 node**

**解释:**
Filter plugin 会过滤掉不满足 pod 要求的 node，将它们从候选范围中排除。

</details>

### 6. Aggregated API Server 和 CRD 之间有什么区别？

- A) 没有区别，它们是相同的
- B) Aggregated API 提供更多控制能力，但需要运行单独的 server
- C) CRD 提供的功能比 Aggregated API 更多
- D) Aggregated API 已弃用

<details>
<summary>显示答案</summary>

**答案: B) Aggregated API 提供更多控制能力，但需要运行单独的 server**

**解释:**
Aggregated API Server 提供对 API 行为、自定义存储后端和高级功能的完全控制，但需要部署和维护单独的 API server。CRD 更简单，但存在限制。

</details>

### 7. Kubernetes 中 Finalizer 的目的是什么？

- A) 加快资源删除
- B) 在清理完成前阻止资源删除
- C) 自动重启失败的 pod
- D) 验证资源创建

<details>
<summary>显示答案</summary>

**答案: B) 在清理完成前阻止资源删除**

**解释:**
Finalizer 会阻塞资源删除，直到 controller 执行必要的清理操作（例如删除外部资源）并移除 finalizer。

</details>

### 8. 哪个 scheduler extension point 在 pod 已绑定到 node 后运行？

- A) PreFilter
- B) PostBind
- C) Reserve
- D) Score

<details>
<summary>显示答案</summary>

**答案: B) PostBind**

**解释:**
PostBind plugin 会在 pod 成功绑定到 node 后被调用。它们用于信息通知，并用于清理或通知。

</details>

### 9. 在 Istio 中，通过 admission webhook 注入 sidecar 使用哪个 annotation？

- A) istio.io/inject
- B) sidecar.istio.io/inject
- C) istio-injection
- D) auto-inject.istio.io

<details>
<summary>显示答案</summary>

**答案: B) sidecar.istio.io/inject**

**解释:**
`sidecar.istio.io/inject` annotation 控制 Istio 的 mutating webhook 是否将 Envoy sidecar 注入到 pod 中。Namespace 级别的控制使用 `istio-injection` label。

</details>

### 10. scheduler framework 中 Score plugin 的目的是什么？

- A) 过滤掉不合适的 node
- B) 对 node 排名并选择最佳 node
- C) 将 pod 绑定到选定的 node
- D) 验证 pod 规范

<details>
<summary>显示答案</summary>

**答案: B) 对 node 排名并选择最佳 node**

**解释:**
Score plugin 会为通过过滤的 node 分配分数。scheduler 会从所有 Score plugin 的综合分数中选择得分最高的 node。

</details>

## 简答题

### 1. CRD 中用于 schema 验证的标准是什么？

<details>
<summary>显示答案</summary>

**答案: OpenAPI v3 Schema (openAPIV3Schema)**

**解释:**
CRD 使用 `spec.versions[].schema.openAPIV3Schema` 中的 OpenAPI v3 schema 来定义自定义资源的结构和验证规则。

</details>

### 2. Kubernetes controller 中 Owner Reference 的作用是什么？

<details>
<summary>显示答案</summary>

**答案: 定义资源之间的所有权关系，并管理垃圾回收和事件传播**

**解释:**
Owner Reference 定义父子关系，并在父资源通过 Kubernetes 垃圾回收被删除时自动删除子资源。

</details>

### 3. ValidatingAdmissionPolicy 和 ValidatingAdmissionWebhook 之间有什么区别？

<details>
<summary>显示答案</summary>

**答案: ValidatingAdmissionPolicy 使用 CEL 表达式并在进程内运行，而 ValidatingAdmissionWebhook 调用外部 HTTP endpoint。**

**解释:**
ValidatingAdmissionPolicy（在 1.26 中引入）提供更好的性能，并且不需要外部 webhook 基础设施，但灵活性低于 webhook。

</details>

### 4. controller-runtime 库是什么，为什么常用它？

<details>
<summary>显示答案</summary>

**答案: controller-runtime 是一个提供构建 Kubernetes controller 常用模式的库，包括 client 缓存、leader election 和 reconciliation loop 管理。**

**解释:**
controller-runtime 是 Kubebuilder 项目的一部分，它抽象了样板代码和最佳实践，使构建可靠的 operator 更容易。

</details>

### 5. CRD 中 conversion webhook 的目的是什么？

<details>
<summary>显示答案</summary>

**答案: conversion webhook 在同一 CRD 的不同 API 版本之间转换资源。**

**解释:**
当 CRD 有多个版本（例如 v1alpha1、v1beta1、v1）时，conversion webhook 会处理版本之间的转换，以支持 API 演进。

</details>

## 实践题

### 1. 编写一个满足以下要求的 CRD：

- Name: WebApp
- Group: apps.example.com
- Fields: replicas（integer，最小值 1）、image（string，必填）

<details>
<summary>显示答案</summary>

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames:
      - wa
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["image"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  default: 1
                image:
                  type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Available
          type: integer
          jsonPath: .status.availableReplicas
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

</details>

### 2. 编写一个 ValidatingAdmissionWebhook 配置，用于验证 "production" namespace 中的所有 Deployment。

<details>
<summary>显示答案</summary>

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: deployment-validator
webhooks:
  - name: validate-deployment.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: webhook-system
        path: /validate-deployment
      caBundle: <base64-encoded-ca-cert>
    rules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
        scope: Namespaced
    namespaceSelector:
      matchLabels:
        environment: production
    failurePolicy: Fail
    sideEffects: None
    admissionReviewVersions: ["v1"]
    timeoutSeconds: 10
```

**解释:**
- `namespaceSelector` 将 webhook 限制到带有 `environment: production` label 的 namespace
- `failurePolicy: Fail` 会在 webhook 不可用时拒绝请求
- `sideEffects: None` 表示 webhook 没有副作用

</details>

### 3. 为 custom controller 编写一个简单的 reconciliation loop 伪代码。

<details>
<summary>显示答案</summary>

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. Fetch the WebApp resource
    var webapp appsv1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted, nothing to do
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. Check if being deleted (handle finalizers)
    if !webapp.DeletionTimestamp.IsZero() {
        if containsFinalizer(webapp, finalizerName) {
            // Perform cleanup
            if err := r.cleanupExternalResources(&webapp); err != nil {
                return ctrl.Result{}, err
            }
            // Remove finalizer
            removeFinalizer(&webapp, finalizerName)
            if err := r.Update(ctx, &webapp); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // 3. Add finalizer if not present
    if !containsFinalizer(webapp, finalizerName) {
        addFinalizer(&webapp, finalizerName)
        if err := r.Update(ctx, &webapp); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Create or update Deployment
    deployment := r.constructDeployment(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, deployment); err != nil {
        return ctrl.Result{}, err
    }

    // 5. Create or update Service
    service := r.constructService(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, service, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, service); err != nil {
        return ctrl.Result{}, err
    }

    // 6. Update status
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
    if err := r.Status().Update(ctx, &webapp); err != nil {
        return ctrl.Result{}, err
    }

    // 7. Requeue after interval for periodic reconciliation
    return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}
```

**要点:**
- 始终处理资源未找到的情况（可能已被删除）
- 使用 finalizer 清理外部资源
- 为垃圾回收设置 owner reference
- 单独更新 status subresource
- 考虑为定期检查设置 requeue interval

</details>

## 进阶题

### 1. 为复杂的分布式系统设计一个 Kubernetes Operator。

<details>
<summary>显示答案</summary>

**CRD 设计:**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.database.example.com
spec:
  group: database.example.com
  names:
    kind: PostgresCluster
    plural: postgresclusters
    shortNames:
      - pg
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["replicas", "version"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                version:
                  type: string
                  enum: ["14", "15", "16"]
                storage:
                  type: object
                  properties:
                    size:
                      type: string
                      default: "10Gi"
                    storageClass:
                      type: string
                backup:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      default: true
                    schedule:
                      type: string
                      default: "0 2 * * *"
                    retention:
                      type: integer
                      default: 7
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: ["Creating", "Running", "Upgrading", "Failed", "Deleting"]
                primaryEndpoint:
                  type: string
                replicaEndpoints:
                  type: array
                  items:
                    type: string
                currentVersion:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      reason:
                        type: string
                      message:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
```

**Controller 核心逻辑:**
- **基于阶段的状态管理**（Creating、Running、Upgrading、Failed）
- **自动故障恢复**（Primary 失败时进行 Failover）
- **滚动升级策略**（先升级 replica，然后升级 primary）
- **Backup 管理**（用于定时 backup 的 CronJob）

**架构:**
```
PostgresCluster CR
       |
       v
   Controller
       |
       +---> StatefulSet (PostgreSQL pods)
       +---> Service (Primary endpoint)
       +---> Service (Replica endpoint)
       +---> Secret (Credentials)
       +---> ConfigMap (PostgreSQL config)
       +---> CronJob (Backups)
       +---> PodDisruptionBudget
```

</details>

### 2. 解释如何使用 scheduler framework 实现 custom scheduler。

<details>
<summary>显示答案</summary>

**Scheduler Plugin 实现:**

```go
// Plugin implementing multiple extension points
type CustomSchedulerPlugin struct {
    handle framework.Handle
}

// Implement PreFilter - check pod requirements
func (p *CustomSchedulerPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    // Validate pod has required annotations
    if _, ok := pod.Annotations["custom-scheduler/zone"]; !ok {
        return nil, framework.NewStatus(framework.Unschedulable, "missing zone annotation")
    }
    return nil, framework.NewStatus(framework.Success, "")
}

// Implement Filter - exclude unsuitable nodes
func (p *CustomSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    requiredZone := pod.Annotations["custom-scheduler/zone"]
    nodeZone := nodeInfo.Node().Labels["topology.kubernetes.io/zone"]
    
    if requiredZone != nodeZone {
        return framework.NewStatus(framework.Unschedulable, "zone mismatch")
    }
    return framework.NewStatus(framework.Success, "")
}

// Implement Score - rank suitable nodes
func (p *CustomSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    
    // Score based on available resources
    allocatable := nodeInfo.Node().Status.Allocatable
    requested := nodeInfo.Requested
    
    cpuScore := calculateResourceScore(allocatable.Cpu(), requested.Cpu)
    memScore := calculateResourceScore(allocatable.Memory(), requested.Memory)
    
    return (cpuScore + memScore) / 2, framework.NewStatus(framework.Success, "")
}

// Register the plugin
func New(_ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &CustomSchedulerPlugin{handle: h}, nil
}
```

**Scheduler 配置:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: custom-scheduler
    plugins:
      preFilter:
        enabled:
          - name: CustomSchedulerPlugin
      filter:
        enabled:
          - name: CustomSchedulerPlugin
      score:
        enabled:
          - name: CustomSchedulerPlugin
        disabled:
          - name: NodeResourcesBalancedAllocation
```

**Extension Point 摘要:**

| Extension Point | 目的 | 运行时机 |
|----------------|---------|-----------|
| PreFilter | Pod 级检查 | 过滤前 |
| Filter | Node 排除 | 对每个 node |
| PostFilter | 处理不可调度情况 | 没有合适的 node 时 |
| PreScore | 为打分做准备 | 打分前 |
| Score | Node 排名 | 对过滤后的 node |
| NormalizeScore | 分数归一化 | 所有分数计算后 |
| Reserve | 资源预留 | node 选择后 |
| Permit | 最终批准 | 绑定前 |
| PreBind | 绑定前操作 | API 绑定前 |
| Bind | 实际绑定 | API server 更新 |
| PostBind | 绑定后清理 | 绑定后 |

</details>
