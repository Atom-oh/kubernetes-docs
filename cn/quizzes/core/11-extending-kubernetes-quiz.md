# 扩展 Kubernetes 测验

本测验考查你对 Kubernetes 扩展机制的概念性和实践性知识。内容涵盖 Custom Resource Definition (CRD)、自定义控制器、API 扩展、webhook 和 Operator 模式等主题。

## 选择题

1. 在 Kubernetes 中定义自定义资源最常见的方式是什么？
   - A) 使用 ConfigMap 定义资源架构
   - B) 创建 CustomResourceDefinition (CRD)
   - C) 直接修改 API server 代码
   - D) 使用 Aggregation Layer

<details>
<summary>显示答案</summary>

**答案：B) 创建 CustomResourceDefinition (CRD)**

**解释：**
在 Kubernetes 中定义自定义资源最常见的方式是创建 CustomResourceDefinition (CRD)。CRD 是一种通过定义新的资源类型来扩展 Kubernetes API 的机制。

使用 CRD 有以下好处：
- 无需修改现有 Kubernetes API server，即可添加新的资源类型。
- 可以使用 `kubectl` 等标准 Kubernetes 工具管理自定义资源。
- 可以利用资源验证、版本控制和 status 子资源等功能。

CRD 示例：
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
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
              properties:
                cronSpec:
                  type: string
                image:
                  type: string
                replicas:
                  type: integer
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

其他选项的问题：
- ConfigMap 用于存储配置数据，不适合用于 API 扩展。
- 直接修改 API server 代码既复杂又难以维护，还可能在升级期间引发问题。
- Aggregation Layer 也是定义自定义资源的一种方式，但它比 CRD 更复杂，因为需要实现单独的 API server。
</details>

2. Kubernetes Operator 的主要用途是什么？
   - A) 优化集群节点的资源使用
   - B) 将复杂应用的运维知识编码到自动化软件中
   - C) 提高 Kubernetes API server 的性能
   - D) 扩展集群网络功能

<details>
<summary>显示答案</summary>

**答案：B) 将复杂应用的运维知识编码到自动化软件中**

**解释：**
Kubernetes Operator 的主要用途是将复杂应用的运维知识编码到自动化软件中。Operator 模式是一种软件实现方式，用来模拟人工操作员管理复杂应用的过程。

Operator 的主要特点：
- 将自定义资源与自定义控制器结合起来，实现特定于应用的逻辑。
- 自动执行应用部署、升级、备份、恢复和扩缩容等运维任务。
- 持续监控应用状态，并将其调整为期望状态。
- 将领域知识编码其中，以便以声明式方式管理复杂应用。

Operator 的常见用例：
- 自动管理数据库（例如 PostgreSQL、MySQL、MongoDB）
- 部署和配置消息系统（例如 Kafka、RabbitMQ）
- 设置和维护监控系统（例如 Prometheus）
- 管理服务网格（例如 Istio）

Operator 示例 - Prometheus Operator：
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

借助这一简单的声明式配置，Prometheus Operator 会自动处理以下复杂任务：
- 部署 Prometheus server
- 创建和管理配置文件
- 自动发现服务监控目标
- 设置高可用性
- 在配置了 storage/volumeClaimTemplate 时管理存储
- 协调升级

其他选项并非 Operator 的主要用途：
- 优化资源使用是 HPA (Horizontal Pod Autoscaler)、VPA (Vertical Pod Autoscaler) 等组件的职责。
- 提高 API server 性能不是 Operator 的主要用途。
- 扩展网络功能是 CNI 插件或服务网格的职责。
</details>

3. Kubernetes 中 Admission Webhook 的主要功能是什么？
   - A) 处理 API server 的身份验证
   - B) 拦截资源创建或修改请求，对其进行验证或修改
   - C) 监控集群事件并发送警报
   - D) 提供用于与外部系统集成的 API

<details>
<summary>显示答案</summary>

**答案：B) 拦截资源创建或修改请求，对其进行验证或修改**

**解释：**
Kubernetes 中 Admission Webhook 的主要功能是拦截资源创建或修改请求，对其进行验证或修改。Admission webhook 提供了一种机制，可在 Kubernetes API server 将请求存储到持久化存储 (etcd) 之前拦截请求。

Admission webhook 分为两种类型：

1. **Validating Webhook**：
   - 验证资源创建、更新和删除请求。
   - 可以允许或拒绝请求，但不能修改请求。
   - 用于策略执行、安全检查、配置验证等。

2. **Mutating Webhook**：
   - 可以验证和修改资源创建及更新请求。
   - 用于设置默认值、注入 sidecar 容器、添加标签等。
   - 在 validating webhook 之前运行。

Admission webhook 配置示例：
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-namespace
      name: webhook-service
      path: "/validate-pods"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

Admission webhook 的常见用例：
- 执行安全策略（例如禁止特权容器）
- 强制设置资源 requests 和 limits
- 自动注入 sidecar 容器（例如 Istio）
- 自动添加标签和注解
- 限制镜像仓库
- 应用基于 namespace 的策略

其他选项的问题：
- 处理 API server 身份验证是 Authentication Plugin 的职责。
- 监控集群事件并发送警报是事件监听器或监控工具的职责。
- 提供用于与外部系统集成的 API 是 API 扩展的一般用途，但不是 Admission Webhook 的主要功能。
</details>

4. Kubernetes API server 中 Aggregation Layer 的主要用途是什么？
   - A) 优化 API server 性能
   - B) 将多个 API server 合并为一个 API server
   - C) 将自定义 API server 集成到主 API server，以扩展 API
   - D) 在集群内提供服务发现

<details>
<summary>显示答案</summary>

**答案：C) 将自定义 API server 集成到主 API server，以扩展 API**

**解释：**
Kubernetes API server 中 Aggregation Layer 的主要用途是将自定义 API server 集成到主 API server，以扩展 API。这是扩展 Kubernetes API 的另一种方式，功能比 CRD 更强大，但也更复杂。

Aggregation Layer 的主要特点：
- 将自定义 API server 集成到 Kubernetes API server 的 URL 空间中。
- 自定义 API server 可以拥有自己的存储、业务逻辑、API 版本等。
- 主 API server 会将请求代理到相应的自定义 API server。
- 主 API server 对用户进行身份验证；扩展端必须验证身份验证代理，并执行委托授权 (SubjectAccessReview)。

使用 Aggregation Layer 的场景：
- 需要复杂的验证逻辑时
- 需要自定义存储后端时
- 需要不同于现有 API 的行为时
- 需要进行资源转换或特殊状态计算时

APIService 资源示例：
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  caBundle: <base64-encoded-serving-ca>
  groupPriorityMinimum: 100
  versionPriority: 100
```

此配置会将对 `metrics.k8s.io/v1beta1` API 组的请求路由到 `kube-system` namespace 中的 `metrics-server` Service。

使用 Aggregation Layer 的实际示例：
- metrics-server：提供节点和 Pod 的资源使用指标
- service-catalog（已归档）：历史上的 service broker 集成
- custom-metrics-apiserver：为 HPA 提供自定义指标

其他选项的问题：
- Aggregation Layer 并非用于优化 API server 性能。
- 将多个 API server 合并为一个并非准确描述。Aggregation Layer 会将多个 API server 集成到单一 URL 空间中，但这些 server 仍分别运行。
- Aggregation Layer 不提供服务发现。这是 Kubernetes Service 的职责。
</details>

5. Kubernetes 中 Custom Controller 的主要作用是什么？
   - A) 监控集群节点的资源使用情况
   - B) 观察自定义资源的状态，并协调使其达到期望状态
   - C) 处理 API server 请求的身份验证和授权
   - D) 管理集群网络

<details>
<summary>显示答案</summary>

**答案：B) 观察自定义资源的状态，并协调使其达到期望状态**

**解释：**
Kubernetes 中 Custom Controller 的主要作用是观察自定义资源的状态，并协调使其达到期望状态。控制器实现了“协调循环”，这是 Kubernetes 的核心运作模式，用于持续将系统的实际状态调整为期望状态。

自定义控制器的主要特点：
- 监视特定资源类型（通常是通过 CRD 定义的自定义资源）。
- 响应资源变更事件并执行业务逻辑。
- 执行任务，将资源的实际状态调整为期望状态。
- 更新资源的 status 字段，以反映当前状态。

自定义控制器的常见组件：
1. **Informer**：监视 Kubernetes API server 并接收资源变更事件。
2. **Work Queue**：存储和管理待处理的事件。
3. **Reconciler**：比较资源的期望状态与实际状态，并执行必要的任务。
4. **Client**：与 Kubernetes API 交互，以创建、更新和删除资源。

自定义控制器示例 - 简单的协调函数：
```go
func (c *Controller) reconcile(key string) error {
    // Split key into namespace and name
    namespace, name, err := cache.SplitMetaNamespaceKey(key)
    if err != nil {
        return err
    }

    // Get custom resource
    instance, err := c.customResourceLister.CustomResources(namespace).Get(name)
    if errors.IsNotFound(err) {
        // Already deleted. External cleanup must run earlier using a finalizer.
        return nil
    }
    if err != nil {
        return err
    }

    // Check resource state and perform necessary tasks
    // e.g., create sub-resources, integrate with external systems, update status, etc.

    // Update status
    instanceCopy := instance.DeepCopy()
    instanceCopy.Status.Phase = "Reconciled"
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(context.TODO(), instanceCopy, metav1.UpdateOptions{})
    return err
}
```

自定义控制器的常见用例：
- 自动执行复杂应用的部署和管理
- 与外部系统集成（例如预配云资源）
- 自动执行备份和恢复流程
- 实现高级部署策略（例如金丝雀部署、蓝绿部署）

其他选项的问题：
- 监控集群节点的资源使用情况是 metrics-server 或 Prometheus 等监控工具的职责。
- 处理 API server 请求的身份验证和授权是身份验证和授权插件的职责。
- 管理集群网络是 CNI 插件或网络控制器的职责。
</details>

6. Kubernetes 中用于定义 CRD (CustomResourceDefinitions) 验证架构的格式是什么？
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>显示答案</summary>

**答案：C) OpenAPI v3 Schema**

**解释：**
Kubernetes 中用于定义 CRD (CustomResourceDefinitions) 验证架构的格式是 OpenAPI v3 Schema。该架构定义自定义资源的结构和字段类型，API server 会使用它来验证资源创建和更新请求。

CRD 验证架构示例：
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

在此示例中，`openAPIV3Schema` 字段定义了以下验证规则：
- `spec` 字段为必填项。
- 在 `spec` 中，`cronSpec` 和 `image` 字段为必填项。
- `cronSpec` 是一个字符串，必须符合 cron 表达式模式。
- `image` 是一个字符串。
- `replicas` 是一个整数，必须介于 1 到 10 之间。

OpenAPI v3 Schema 提供多种验证功能：
- 指定必填字段
- 数据类型验证（字符串、数字、布尔值、对象、数组等）
- 字符串模式验证（正则表达式）
- 数值范围验证（最小值、最大值）
- 数组长度验证
- 枚举值验证
- 嵌套对象结构定义

其他选项的问题：
- JSON Schema 是 OpenAPI 的基础，但 Kubernetes 特别使用 OpenAPI v3 Schema。
- Kubernetes API 不使用 XML Schema。
- GraphQL Schema 用于 GraphQL API，但不用于 Kubernetes API。
</details>

7. 在 Kubernetes 中为自定义资源启用 status 子资源的主要好处是什么？
   - A) 加快资源创建速度
   - B) 分离 spec 和 status 更新，并支持 RBAC 控制
   - C) 自动备份和恢复功能
   - D) 简化资源版本管理

<details>
<summary>显示答案</summary>

**答案：B) 分离 spec 和 status 更新，并支持 RBAC 控制**

**解释：**
在 Kubernetes 中为自定义资源启用 status 子资源的主要好处是分离 spec 和 status 更新，并可通过 RBAC (Role-Based Access Control) 控制访问权限。

启用 status 子资源的好处：

1. **职责分离**：
   - `spec` 字段定义用户指定的期望状态。
   - `status` 字段报告控制器观察到的实际状态。
   - 这种分离明确了用户和控制器各自的职责。

2. **RBAC 控制**：
   - 可以只向控制器授予 status 更新权限，同时为普通用户授予只读权限。
   - 这可以防止未授权修改状态信息。

3. **防止冲突**：
   - spec 和 status 虽然分开，但会共用 resourceVersion，因此并发写入仍可能返回 409 Conflict。
   - 发生冲突时，应读取最新对象并重试/重新协调。

4. **支持 Scale 子资源**：
   - scale 子资源独立配置，包含 specReplicasPath、statusReplicasPath，以及可选的 labelSelectorPath。
   - 这样就能使用 HPA (Horizontal Pod Autoscaler) 等标准 Kubernetes 扩缩容工具。

在 CRD 中启用 status 子资源的示例：
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
  - name: v1
    served: true
    storage: true
    subresources:
      status: {}
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              cronSpec:
                type: string
              image:
                type: string
          status:
            type: object
            properties:
              phase:
                type: string
              message:
                type: string
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

控制器更新 status 的示例：
```go
// Update status only
statusUpdate := instance.DeepCopy() // Preserve resourceVersion from a current read.
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(ctx, statusUpdate, metav1.UpdateOptions{})
```

其他选项的问题：
- status 子资源不会提高资源创建速度。
- 它不提供自动备份和恢复功能。
- 资源版本管理通过 CRD 的 `versions` 字段处理，与 status 子资源没有直接关系。
</details>

8. Kubernetes 中 Webhook Conversion 的主要用途是什么？
   - A) 将 API 请求路由到外部服务
   - B) 处理不同版本自定义资源之间的转换
   - C) 将身份验证令牌转换为不同格式
   - D) 将日志数据转换为结构化格式

<details>
<summary>显示答案</summary>

**答案：B) 处理不同版本自定义资源之间的转换**

**解释：**
Kubernetes 中 Webhook Conversion 的主要用途是处理不同版本自定义资源之间的转换。此功能支持 CRD 的多个版本，并可在不同版本之间平滑迁移。

Webhook conversion 的主要特点：

1. **多版本支持**：
   - CRD 可以同时支持多个 API 版本（例如 v1alpha1、v1beta1、v1）。
   - 每个版本可以使用不同的架构和字段。

2. **自动转换**：
   - API server 会自动处理客户端请求版本与存储版本之间的转换。
   - conversion webhook 会在此过程中提供自定义转换逻辑。

3. **与存储版本无关**：
   - 即使存储版本发生变化，使用旧版本的客户端也可以继续工作。
   - webhook 会处理已提供服务的版本之间的双向转换；更改 storage:true 不会重写现有数据。移除旧的 status.storedVersions 条目之前，应先迁移已存储的对象。

CRD 中 conversion webhook 配置示例：
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  - name: v1beta1
    served: true
    storage: false
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cron
            - image
            properties:
              cron:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions:
      - v1
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

conversion webhook server 实现示例：
```go
// Include encoding/json, net/http, fmt and the Kubernetes types below in the server.
// apiextensionsv1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1"
// metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
// "k8s.io/apimachinery/pkg/runtime"
func convertCron(raw []byte, desired string) ([]byte, error) {
    var obj map[string]interface{}
    if err := json.Unmarshal(raw, &obj); err != nil { return nil, err }
    source, _ := obj["apiVersion"].(string)
    valid := func(v string) bool { return v == "stable.example.com/v1" || v == "stable.example.com/v1beta1" }
    if !valid(source) || !valid(desired) || obj["kind"] != "CronTab" {
        return nil, fmt.Errorf("unsupported CronTab conversion %q -> %q", source, desired)
    }
    spec, ok := obj["spec"].(map[string]interface{})
    if !ok { return nil, fmt.Errorf("spec object required") }
    if source != desired {
        oldField, newField := "cron", "cronSpec"
        if desired == "stable.example.com/v1beta1" { oldField, newField = newField, oldField }
        value, ok := spec[oldField]
        if !ok { return nil, fmt.Errorf("missing %s", oldField) }
        if _, collision := spec[newField]; collision { return nil, fmt.Errorf("ambiguous cron fields") }
        spec[newField] = value
        delete(spec, oldField)
    }
    obj["apiVersion"] = desired
    // Preserve metadata (including UID/resourceVersion), status and all other fields.
    return json.Marshal(obj)
}

func serveConvert(w http.ResponseWriter, r *http.Request) {
    var review apiextensionsv1.ConversionReview
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest); return
    }
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8<<20)).Decode(&review); err != nil ||
        review.APIVersion != "apiextensions.k8s.io/v1" || review.Kind != "ConversionReview" ||
        review.Request == nil || review.Request.UID == "" {
        http.Error(w, "Invalid ConversionReview v1", http.StatusBadRequest); return
    }
    response := &apiextensionsv1.ConversionResponse{
        UID: review.Request.UID, Result: metav1.Status{Status: "Success"},
    }
    for _, obj := range review.Request.Objects {
        raw, err := convertCron(obj.Raw, review.Request.DesiredAPIVersion)
        if err != nil {
            response.Result = metav1.Status{Status: "Failure", Message: err.Error()}
            response.ConvertedObjects = nil
            break
        }
        response.ConvertedObjects = append(response.ConvertedObjects, runtime.RawExtension{Raw: raw})
    }
    out := apiextensionsv1.ConversionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "apiextensions.k8s.io/v1", Kind: "ConversionReview"},
        Response: response,
    }
    w.Header().Set("Content-Type", "application/json")
    _ = json.NewEncoder(w).Encode(out)
}
```

其他选项的问题：
- 将 API 请求路由到外部服务是 API aggregation 的职责。
- 转换身份验证令牌是身份验证插件的职责。
- 转换日志数据是日志系统的职责。
</details>

9. 以下哪一项不是用于帮助开发 Kubernetes Operator 的框架？
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>显示答案</summary>

**答案：D) Kubespray**

**解释：**
Kubespray 不是用于帮助开发 Kubernetes Operator 的框架。Kubespray 是一种使用 Ansible playbook 部署和管理 Kubernetes 集群的工具。它专注于集群安装和配置，与 Operator 开发无关。

用于 Kubernetes Operator 开发的实际框架包括：

1. **Operator Framework**：
   - 由 Red Hat 开发的 Operator 开发工具包
   - 主要组件：
     - Operator SDK：用于搭建 Operator 项目和进行开发的工具
     - Operator Lifecycle Manager (OLM)：Operator 安装和升级管理
     - Operator Metering：Operator 使用情况报告
   - 支持使用 Go、Ansible 和 Helm 开发 Operator

2. **Kubebuilder**：
   - 由 Kubernetes SIG (Special Interest Group) 开发的框架
   - 用于使用 Go 开发控制器的 SDK
   - 提供代码生成、CRD 管理和测试工具
   - 基于 controller-runtime 库

3. **Metacontroller**：
   - 轻量级、基于 webhook 的 Operator 框架
   - 可以使用多种语言实现控制器逻辑
   - 声明式控制器定义
   - 适合快速开发简单控制器

各框架的功能对比：

| 框架 | 主要语言 | 复杂度 | 功能 |
|-----------|------------------|------------|----------|
| Operator Framework | Go、Ansible、Helm | 中到高 | 全面的工具包、多种开发选项 |
| Kubebuilder | Go | 中 | 标准化模式、代码生成工具 |
| Metacontroller | 与语言无关 | 低 | 基于 webhook、实现简单 |

Operator 开发示例（使用 Kubebuilder）：
```bash
# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Implement controller (edit controller.go file)

# Create CRD and deploy controller
make install
make deploy
```

其他选项的说明：
- Operator Framework 是 Red Hat 的综合 Operator 开发工具包。
- Kubebuilder 是 Kubernetes SIG 开发的基于 Go 的控制器开发框架。
- Metacontroller 是轻量级、基于 webhook 的 Operator 框架。
</details>

10. Kubernetes 中 Custom Resource Definition (CRD) 与 Aggregated API 的主要区别是什么？
    - A) CRD 不支持版本控制，但 Aggregated API 支持
    - B) CRD 不支持验证架构，但 Aggregated API 支持
    - C) CRD 易于实现但灵活性有限，而 Aggregated API 实现复杂但灵活性更高
    - D) CRD 仅支持集群作用域资源，而 Aggregated API 仅支持 namespace 作用域资源

<details>
<summary>显示答案</summary>

**答案：C) CRD 易于实现但灵活性有限，而 Aggregated API 实现复杂但灵活性更高**

**解释：**
Kubernetes 中 Custom Resource Definition (CRD) 与 Aggregated API 的主要区别在于实现复杂度和灵活性之间的权衡。CRD 易于实现但灵活性有限，而 Aggregated API 实现复杂但灵活性更高。

**CRD (CustomResourceDefinitions) 的特点：**
- **实现简单**：只需一个 YAML 文件即可定义新的 API 资源。
- **使用现有 API server**：无需实现单独的 API server。
- **灵活性有限**：
  - 存储方式仅限 etcd。
  - 继承默认 API server 的行为。
  - 支持 CEL 验证以及 admission/conversion webhook；自定义存储和非标准 API 行为仍是两者的主要区别。
- **通过 webhook 扩展**：可以通过 validating webhook、conversion webhook 等扩展部分功能。

**Aggregated API 的特点：**
- **实现复杂**：必须开发和部署单独的 API server。
- **灵活性高**：
  - 可以使用自定义存储后端
  - 可以实现复杂的业务逻辑
  - 可以实现自定义身份验证和授权逻辑
  - 可以实现特殊的状态计算和转换逻辑
- **完整的 API server 功能**：可以利用标准 Kubernetes API server 的所有功能。

**选择标准：**

| 标准 | 选择 CRD | 选择 Aggregated API |
|----------|------------|----------------------|
| 实现复杂度 | 低 - 简单的 YAML 定义 | 高 - 需要开发单独的 API server |
| 开发时间 | 短 - 几分钟内即可实现 | 长 - 需要完整开发 API server |
| 维护 | 简单 - 由现有 API server 管理 | 困难 - 需要维护单独的服务 |
| 存储选项 | 仅 etcd | 可以使用自定义存储后端 |
| 业务逻辑 | 有限 - 通过控制器实现 | 灵活 - 可直接在 API server 中实现 |
| 性能 | 通常良好 | 可以进行自定义优化 |
| 用例 | 简单 CRUD 操作、标准模式 | 复杂 API 行为、特殊验证/转换 |

**示例场景：**

适合使用 CRD 的场景：
- 简单的应用配置管理
- 主要需求是基本 CRUD 操作
- 快速原型设计和开发

适合使用 Aggregated API 的场景：
- 与外部数据库集成
- 复杂的数据转换和验证
- 需要特殊的身份验证机制
- 高性能或特殊用途的 API

其他选项的问题：
- CRD 支持版本控制（A 错误）。
- CRD 通过 OpenAPI v3 Schema 支持验证架构（B 错误）。
- CRD 和 Aggregated API 都支持集群作用域和 namespace 作用域资源（D 错误）。
</details>

> cronSpec 正则表达式只检查一种受限的五字段形式，仅包含数字、星号和步长。它不会验证范围、列表、名称或所有合法的时间值。请在控制器/webhook 中添加真正的 cron 解析器。CRD 本身不会执行定时任务。

## 简答题

1. 说明如何使用 CustomResourceDefinition (CRD) 定义自定义资源，以及如何为这些资源设置验证规则。

<details>
<summary>显示答案</summary>

**答案：**

**如何定义 CustomResourceDefinition (CRD)：**

CRD 是一种用于扩展 Kubernetes API、定义新资源类型的机制。创建 CRD 后，会创建一个新的 RESTful API 端点，你可以使用 `kubectl` 等标准工具管理该资源。

**1. CRD 基本结构：**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>
spec:
  group: <api-group>
  names:
    kind: <kind-name>
    plural: <plural-name>
    singular: <singular-name>
    shortNames:
    - <short-name>
  scope: Namespaced
  versions:
  - name: <version>
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
```

**2. 设置验证规则：**

CRD 的验证规则通过 `openAPIV3Schema` 字段设置。此架构遵循 OpenAPI v3 格式，用于定义资源的结构和字段类型。

**基本验证规则示例：**

```yaml
schema:
  openAPIV3Schema:
    type: object
    required: ["spec"]
    properties:
      spec:
        type: object
        required: ["cronSpec", "image"]
        properties:
          cronSpec:
            type: string
            pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
          image:
            type: string
          replicas:
            type: integer
            minimum: 1
            maximum: 10
            default: 1
```

**3. 高级验证功能：**

OpenAPI v3 Schema 提供多种验证功能：

- **必填字段**：将字段名称添加到 `required` 数组中
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **数据类型**：使用 `type` 字段指定数据类型
  ```yaml
  type: string  # Choose one supported type, not a pipe-separated union.
  ```

- **字符串约束**：验证字符串长度和模式
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **数值约束**：验证数值范围
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **数组约束**：验证数组长度和元素
  ```yaml
  minItems: 1
  maxItems: 10
  x-kubernetes-list-type: set
  items:
    type: string
  ```

- **枚举值**：指定允许值列表
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **默认值**：为字段指定默认值
  ```yaml
  default: "default-value"
  ```

- **Map 值**：定义类型化的 map 条目；CRD 中禁止使用 additionalProperties: false。通常会修剪未知字段。
  ```yaml
  additionalProperties:
    type: string
  ```

**4. 完整 CRD 示例：**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                  default: 1
            status:
              type: object
              properties:
                active:
                  type: boolean
                lastScheduleTime:
                  type: string
                  format: date-time
      subresources:
        status: {}  # Enable status subresource
      additionalPrinterColumns:
        - name: Schedule
          type: string
          description: The cron schedule
          jsonPath: .spec.cronSpec
        - name: Image
          type: string
          description: The image to use
          jsonPath: .spec.image
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

**5. 应用和使用 CRD：**

```bash
# Apply CRD
kubectl apply -f crontab-crd.yaml

# Create custom resource
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: my-crontab
spec:
  cronSpec: "* * * * */5"
  image: my-cron-image
  replicas: 3
EOF

# View custom resources
kubectl get crontabs
kubectl get ct  # Using short name
```

**6. 测试验证规则：**

使用无效值创建资源会导致验证错误：

```bash
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: invalid-crontab
spec:
  cronSpec: "invalid-cron-spec"  # Pattern mismatch
  image: my-cron-image
  replicas: 20  # Exceeds maximum
EOF
```

此命令会返回类似以下错误：
API server 会通过 CRD 架构验证拒绝无效的 cronSpec/replicas。此示例中没有安装单独的 admission webhook；具体错误措辞会因版本而异。

**7. 最佳实践：**

- 定义清晰、详尽的架构
- 明确指定必填字段
- 提供适当的默认值
- 限制字符串模式和数值范围
- 启用 status 子资源
- 配置额外的打印列
- 制定版本控制策略
</details>

2. 说明 Kubernetes Operator 模式的核心概念，以及实现 Operator 的常见方法。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes Operator 模式的核心概念：**

Operator 模式是一种 Kubernetes 扩展机制，它将特定于应用的运维知识编码到软件中，以自动管理复杂应用。此模式模仿人工操作员管理复杂系统的方式。

**1. 核心概念：**

- **声明式管理**：用户声明期望状态，Operator 将当前状态调整为期望状态。
- **编码领域知识**：将特定应用的运维知识和最佳实践编码其中。
- **协调循环**：持续观察实际状态并将其调整为期望状态。
- **自定义资源**：用于存储特定于应用的配置和状态。
- **控制器**：监视自定义资源的变更，并执行必要的任务。

**2. Operator 的常见功能：**

- **安装和升级**：部署应用组件并升级版本
- **自动恢复**：检测故障并执行恢复任务
- **备份和恢复**：自动执行数据备份和恢复流程
- **扩缩容**：根据工作负载需求自动扩容和缩容
- **配置管理**：处理特定于应用的配置变更
- **运维自动化**：自动执行日常运维任务（例如数据库压缩、索引重建）

**实现 Operator 的方法：**

**1. 使用 Operator SDK：**

[Operator SDK](https://sdk.operatorframework.io/) 是 Red Hat Operator Framework 的一部分，是一种可简化 Operator 开发的工具。

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push IMG="$OPERATOR_IMAGE"
make deploy IMG="$OPERATOR_IMAGE"
```

**2. 使用 Kubebuilder：**

[Kubebuilder](https://book.kubebuilder.io/) 是由 Kubernetes SIG 开发的框架，可提供控制器开发工具。

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy IMG="$OPERATOR_IMAGE"
```

**3. 控制器实现：**

Operator 的核心是协调函数。该函数会观察自定义资源的当前状态并执行必要的任务。

```go
// Uses the scaffold's client.Client and Scheme. Import controllerutil and sort.
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    if !myApp.DeletionTimestamp.IsZero() { return ctrl.Result{}, nil }
    deployment := &appsv1.Deployment{ObjectMeta: metav1.ObjectMeta{Name: myApp.Name, Namespace: myApp.Namespace}}
    _, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
        if deployment.UID != "" && !metav1.IsControlledBy(deployment, &myApp) {
            return fmt.Errorf("refusing to modify Deployment owned by another actor")
        }
        labels := map[string]string{"myapp.example.com/owner-uid": string(myApp.UID)}
        if deployment.Spec.Selector == nil {
            deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
        }
        if deployment.Spec.Template.Labels == nil { deployment.Spec.Template.Labels = map[string]string{} }
        deployment.Spec.Template.Labels["myapp.example.com/owner-uid"] = string(myApp.UID)
        size := myApp.Spec.Size
        deployment.Spec.Replicas = &size
        keys := []string{}
        for key := range myApp.Spec.Config { keys = append(keys, key) }
        sort.Strings(keys) // Stable output avoids unnecessary updates.
        env := []corev1.EnvVar{}
        for _, key := range keys { env = append(env, corev1.EnvVar{Name: key, Value: myApp.Spec.Config[key]}) }
        // This operator owns its application container; update image as well as replicas.
        deployment.Spec.Template.Spec.Containers = []corev1.Container{{
            Name: "myapp", Image: myApp.Spec.Image, Env: env,
            Ports: []corev1.ContainerPort{{ContainerPort: 8080, Name: "http"}},
        }}
        return ctrl.SetControllerReference(&myApp, deployment, r.Scheme)
    })
    if err != nil { return ctrl.Result{}, err }
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil { return ctrl.Result{}, err }
    }
    return ctrl.Result{}, nil
}

func (r *MyAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&appsv1alpha1.MyApp{}).
        Owns(&appsv1.Deployment{}).
        Complete(r)
}
```

**4. Custom Resource Definition：**

为 Operator 管理的自定义资源定义 API。

```go
// MyApp API
type MyAppSpec struct {
    // Application image
    Image string `json:"image"`

    // Number of replicas
    Size int32 `json:"size"`

    // Configuration options
    Config map[string]string `json:"config,omitempty"`
}

type MyAppStatus struct {
    // Number of available replicas
    AvailableReplicas int32 `json:"availableReplicas"`

    // Last update time
    LastUpdateTime metav1.Time `json:"lastUpdateTime,omitempty"`

    // Status message
    Message string `json:"message,omitempty"`
}

// MyApp resource
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.size`
// +kubebuilder:printcolumn:name="Available",type=integer,JSONPath=`.status.availableReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`
type MyApp struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   MyAppSpec   `json:"spec,omitempty"`
    Status MyAppStatus `json:"status,omitempty"`
}
```

**5. 基于 Ansible 或 Helm 的 Operator：**

除了 Go，Operator SDK 还支持使用 Ansible 或 Helm 开发 Operator。

**基于 Ansible 的 Operator：**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**基于 Helm 的 Operator：**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. 部署和测试 Operator：**

```bash
# Deploy operator
make deploy

# Create custom resource
kubectl apply -f config/samples/

# Check operator logs
kubectl logs -f deployment/my-operator-controller-manager -n my-operator-system

# Check resource status
kubectl get myapps
kubectl describe myapp my-app
```

**7. Operator 成熟度级别：**

Operator 成熟度模型定义了 Operator 的能力级别：

1. **基本安装**：应用安装和配置
2. **无缝升级**：版本之间自动升级
3. **完整生命周期**：备份、恢复、故障恢复等
4. **深入洞察**：自动扩缩容、调优等
5. **自动驾驶**：基于监控的自动优化

**8. 最佳实践：**

- 逐步实现功能（从简单功能开始）
- 完善错误处理和日志记录
- 确保幂等性（相同输入产生相同结果）
- 设置 owner reference（资源层级和垃圾回收）
- 通过 status 更新报告进度
- 编写单元测试和集成测试
- 提供清晰的文档
</details>

3. 说明 Kubernetes 中 Admission Webhook 的类型及各自的用例。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes Admission Webhook 的类型和用例：**

Admission webhook 是一种机制，可在 Kubernetes API server 将请求存储到持久化存储 (etcd) 之前拦截请求，并对其进行修改或验证。Admission webhook 大致分为两种类型：Mutating webhook 和 Validating webhook。

**1. Mutating Webhook：**

Mutating webhook 可以修改进入 API server 的请求对象。这类 webhook 会在 validating webhook 之前运行。

**主要特点：**
- 可以修改请求对象
- 多个 mutating webhook 会按链式顺序运行
- 每个 webhook 接收前一个 webhook 修改后的对象

**配置示例：**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-server
      path: "/mutate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**常见用例：**

1. **注入 sidecar 容器：**
   - 在 Istio 和 Linkerd 等服务网格中自动注入代理 sidecar
   - 添加日志和监控 sidecar
   - 示例：Istio 的 sidecar injector 会在创建 Pod 时自动添加 Envoy 代理容器

2. **设置默认值：**
   - 自动设置资源 requests 和 limits
   - 应用默认的安全上下文
   - 自动添加标签和注解
   - 示例：为所有 Pod 设置默认 CPU 和内存 requests

3. **应用镜像策略：**
   - 修改镜像仓库 URL
   - 将镜像标签转换为摘要
   - 示例：将 `nginx:latest` 更改为 `internal-registry.example.com/nginx:1.30.6`

4. **卷修改：**
   - 添加默认的卷挂载
   - 自动挂载 ConfigMap 或 Secret
   - 示例：除非 automountServiceAccountToken 为 false，否则 ServiceAccount admission 已会注入投射令牌；不要覆盖这一禁用设置

5. **Pod 网络配置：**
   - 添加默认网络设置
   - 修改 DNS 配置
   - 示例：为特定 namespace 中的所有 Pod 应用特定 DNS 设置

**2. Validating Webhook：**

Validating webhook 可以验证进入 API server 的请求，并允许或拒绝请求。这类 webhook 会在 mutating webhook 之后运行。

**主要特点：**
- 不能修改请求对象
- 只能允许或拒绝请求
- 多个 validating webhook 会并行运行
- 每个匹配的 webhook 都必须允许请求；调用错误/超时会遵循 failurePolicy，因此 Ignore 可能会在没有响应的情况下允许请求

**配置示例：**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-server
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**常见用例：**

1. **执行安全策略：**
   - 禁止特权容器
   - 禁止以 root 用户身份运行
   - 限制 host network/PID/IPC 的使用
   - 示例：拒绝以特权模式运行的 Pod

2. **验证资源约束：**
   - 强制设置资源 requests 和 limits
   - 应用资源上限
   - 强制实施 QoS 类别
   - 示例：拒绝没有内存 limits 的 Pod

3. **验证镜像策略：**
   - 仅允许经过批准的仓库
   - 禁止使用 latest 标签
   - 验证漏洞扫描结果
   - 示例：仅允许使用来自官方仓库的镜像

4. **验证标签和注解：**
   - 检查必需标签
   - 验证标签格式
   - 示例：要求所有 Pod 都必须设置 `app` 和 `environment` 标签

5. **基于 namespace 的策略：**
   - 按 namespace 设置资源限制
   - 按 namespace 设置功能限制
   - 示例：在生产 namespace 中应用更严格的策略

**3. Webhook 实现方法：**

Admission webhook 以提供 HTTPS 端点的 Service 形式实现。这些 Service 接收 `AdmissionReview` 请求、处理请求，并返回 `AdmissionResponse`。

**基本 Webhook Server 实现示例 (Go)：**

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"
    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/api/resource"
)

func readPodReview(w http.ResponseWriter, r *http.Request) (*admissionv1.AdmissionRequest, *corev1.Pod, bool) {
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest)
        return nil, nil, false
    }
    var review admissionv1.AdmissionReview
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 2<<20)).Decode(&review); err != nil {
        http.Error(w, "Invalid AdmissionReview JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    req := review.Request
    if review.APIVersion != "admission.k8s.io/v1" || review.Kind != "AdmissionReview" || req == nil || req.UID == "" {
        http.Error(w, "AdmissionReview v1 request and UID required", http.StatusBadRequest)
        return nil, nil, false
    }
    if req.Kind.Group != "" || req.Kind.Version != "v1" || req.Kind.Kind != "Pod" ||
        (req.Operation != admissionv1.Create && req.Operation != admissionv1.Update) {
        http.Error(w, "Only Pod CREATE/UPDATE is supported", http.StatusBadRequest)
        return nil, nil, false
    }
    var pod corev1.Pod
    if err := json.Unmarshal(req.Object.Raw, &pod); err != nil {
        http.Error(w, "Invalid Pod JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    return req, &pod, true
}

func writeReview(w http.ResponseWriter, response admissionv1.AdmissionResponse) {
    review := admissionv1.AdmissionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "admission.k8s.io/v1", Kind: "AdmissionReview"},
        Response: &response,
    }
    data, err := json.Marshal(review)
    if err != nil {
        http.Error(w, "Response encoding failed", http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    _, _ = w.Write(data)
}

func writePatch(w http.ResponseWriter, req *admissionv1.AdmissionRequest, patches []map[string]interface{}) {
    response := admissionv1.AdmissionResponse{UID: req.UID, Allowed: true}
    if len(patches) > 0 {
        data, err := json.Marshal(patches)
        if err != nil {
            http.Error(w, "Patch encoding failed", http.StatusInternalServerError)
            return
        }
        patchType := admissionv1.PatchTypeJSONPatch
        response.PatchType, response.Patch = &patchType, data
    }
    writeReview(w, response)
}

func deny(w http.ResponseWriter, req *admissionv1.AdmissionRequest, message string) {
    writeReview(w, admissionv1.AdmissionResponse{
        UID: req.UID, Allowed: false,
        Result: &metav1.Status{Status: "Failure", Reason: metav1.StatusReasonForbidden, Code: 403, Message: message},
    })
}
var sidecarImage string

func mutateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    // This example targets explicitly declared Linux Pods on CREATE only.
    if req.Operation != admissionv1.Create || pod.Spec.OS == nil || pod.Spec.OS.Name != corev1.Linux {
        writePatch(w, req, nil)
        return
    }
    if sidecarImage == "" {
        deny(w, req, "Configure a tested SIDE_CAR_IMAGE first")
        return
    }
    changed, foundVolume, foundSidecar := false, false, false
    for _, volume := range pod.Spec.Volumes {
        if volume.Name == "shared-data" {
            if volume.EmptyDir == nil {
                deny(w, req, "shared-data is reserved for an emptyDir volume")
                return
            }
            foundVolume = true
        }
    }
    if !foundVolume {
        pod.Spec.Volumes = append(pod.Spec.Volumes, corev1.Volume{
            Name: "shared-data", VolumeSource: corev1.VolumeSource{EmptyDir: &corev1.EmptyDirVolumeSource{}},
        })
        changed = true
    }
    for i := range pod.Spec.Containers {
        c := &pod.Spec.Containers[i]
        if c.Name == "monitoring-sidecar" {
            if c.Image != sidecarImage {
                deny(w, req, "monitoring-sidecar name is reserved")
                return
            }
            foundSidecar = true
        }
        mounted := false
        for _, mount := range c.VolumeMounts {
            if mount.MountPath == "/var/monitoring" {
                if mount.Name != "shared-data" || mount.SubPath != "" || mount.SubPathExpr != "" {
                    deny(w, req, "/var/monitoring is reserved for shared-data")
                    return
                }
                mounted = true
            }
        }
        if !mounted {
            c.VolumeMounts = append(c.VolumeMounts, corev1.VolumeMount{Name: "shared-data", MountPath: "/var/monitoring"})
            changed = true
        }
    }
    if !foundSidecar {
        pod.Spec.Containers = append(pod.Spec.Containers, corev1.Container{
            Name: "monitoring-sidecar", Image: sidecarImage,
            VolumeMounts: []corev1.VolumeMount{{Name: "shared-data", MountPath: "/var/monitoring", ReadOnly: true}},
            Resources: corev1.ResourceRequirements{
                Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("50m"), corev1.ResourceMemory: resource.MustParse("50Mi")},
                Limits: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("100m"), corev1.ResourceMemory: resource.MustParse("100Mi")},
            },
        })
        changed = true
    }
    if !changed { writePatch(w, req, nil); return }
    // Whole-array add also works when volumes was absent; preserve all existing entries.
    writePatch(w, req, []map[string]interface{}{
        {"op": "add", "path": "/spec/volumes", "value": pod.Spec.Volumes},
        {"op": "add", "path": "/spec/containers", "value": pod.Spec.Containers},
    })
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    contexts := []*corev1.SecurityContext{}
    for _, c := range pod.Spec.Containers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.InitContainers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.EphemeralContainers { contexts = append(contexts, c.SecurityContext) }
    for _, sc := range contexts {
        if sc != nil && sc.Privileged != nil && *sc.Privileged {
            deny(w, req, "Privileged containers are not allowed")
            return
        }
    }
    writeReview(w, admissionv1.AdmissionResponse{UID: req.UID, Allowed: true})
}

func main() {
    sidecarImage = os.Getenv("SIDE_CAR_IMAGE")
    if sidecarImage == "" { log.Fatal("Set SIDE_CAR_IMAGE to a tested Linux image tag/digest") }
    mux := http.NewServeMux()
    mux.HandleFunc("/mutate", mutateHandler)
    mux.HandleFunc("/validate", validateHandler)
    server := &http.Server{Addr: ":8443", Handler: mux, ReadHeaderTimeout: 5*time.Second}
    log.Fatal(server.ListenAndServeTLS("/etc/webhook/certs/tls.crt", "/etc/webhook/certs/tls.key"))
}
```

**4. Webhook Deployment 和配置：**

构建上述完整 server，替换 server/sidecar 镜像占位符，并创建 webhook-system 和 webhook-server-tls。服务证书必须涵盖 webhook-server.webhook-system.svc（以及使用的任何其他 Service 名称），且 caBundle 必须包含其签名 CA。sidecar 镜像必须兼容应用的文件系统权限。这是一个普通 sidecar 示例；对于 Job，请单独配置关闭行为/native-sidecar 行为。

```yaml
# Webhook server deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-server
  template:
    metadata:
      labels:
        app: webhook-server
    spec:
      containers:
      - name: server
        image: example/webhook-server:REPLACE_WITH_TESTED_RELEASE
        env:
        - name: SIDE_CAR_IMAGE
          value: example/monitoring-agent:REPLACE_WITH_TESTED_RELEASE
        ports:
        - containerPort: 8443
        volumeMounts:
        - name: tls
          mountPath: "/etc/webhook/certs"
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: webhook-server-tls

---
# Webhook server service
apiVersion: v1
kind: Service
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  selector:
    app: webhook-server
  ports:
  - port: 443
    targetPort: 8443
```

**5. 最佳实践：**

- **性能优化**：Webhook 位于 API server 请求路径中，因此必须快速响应。
- **错误处理**：考虑 webhook server 故障时的行为，并适当设置 `failurePolicy`。
- **限制作用范围**：仅对必要的资源和操作应用 webhook。
- **测试**：在各种场景中全面测试 webhook 行为。
- **监控**：监控 webhook server 的性能和错误。
- **版本管理**：仅声明实际实现的 AdmissionReview 版本，并返回与请求相同的版本。
</details>

## 实践题

1. 编写一个满足以下要求的 CustomResourceDefinition (CRD)：
   - API Group：webapp.example.com
   - Version：v1
   - Kind：WebApp
   - Scope：Namespaced
   - 必填字段：spec.image、spec.replicas
   - 验证规则：replicas 必须是介于 1 到 10 之间的整数
   - 启用 status 子资源

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.webapp.example.com
spec:
  group: webapp.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["image", "replicas"]
              properties:
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                port:
                  type: integer
                  default: 80
                env:
                  type: array
                  items:
                    type: object
                    required: ["name"]
                    properties:
                      name:
                        type: string
                      value:
                        type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                phase:
                  type: string
      subresources:
        status: {}
      additionalPrinterColumns:
      - name: Replicas
        type: integer
        jsonPath: .spec.replicas
      - name: Image
        type: string
        jsonPath: .spec.image
      - name: Age
        type: date
        jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: webapps
    singular: webapp
    kind: WebApp
    shortNames:
    - wa
```

此 CRD 具有以下特点：

1. **基本信息**：
   - API Group：`webapp.example.com`
   - Version：`v1`
   - Kind：`WebApp`
   - Scope：`Namespaced`

2. **架构验证**：
   - `spec` 字段为必填项。
   - `spec.image` 和 `spec.replicas` 为必填字段。
   - `spec.replicas` 必须是介于 1 到 10 之间的整数。
   - `spec.port` 是可选字段，默认值为 80。
   - `spec.env` 是可选字段，用于定义环境变量数组。

3. **Status 子资源**：
   - 已启用 `status` 子资源，以便控制器更新状态。
   - 定义了 `status.availableReplicas` 和 `status.phase` 字段。

4. **额外的打印列**：
   - 运行 `kubectl get webapps` 时，会显示 Replicas、Image 和 Age 列。

5. **名称配置**：
   - 复数形式：`webapps`
   - 单数形式：`webapp`
   - Kind：`WebApp`
   - 简称：`wa`

可以使用此 CRD 创建如下自定义资源：

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.30.6
  replicas: 3
  port: 80
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

控制器可以监视此资源并更新状态：

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. 编写一个满足以下要求的 Mutating Admission Webhook 配置：
   - 对明确声明 spec.os.name: linux 的 Pod 的 CREATE 请求添加 sidecar
   - 仅应用于指定的 namespace (monitoring)
   - Webhook Service：webhook-service.webhook-system.svc
   - Path：/mutate

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-service
      path: "/mutate"
    caBundle: ${CA_BUNDLE}  # Replace with base64-encoded CA certificate in actual environment
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: monitoring
  matchConditions:
  - name: explicit-linux-pod
    expression: "has(object.spec.os) && object.spec.os.name == 'linux'"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
  failurePolicy: Fail
---
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    kubernetes.io/metadata.name: monitoring
```

此配置具有以下特点：

1. **Webhook 配置**：
   - 名称：`sidecar-injector`
   - Webhook Service：`webhook-service.webhook-system.svc`
   - Path：`/mutate`

2. **作用范围**：
   - API Group：`""`（核心 API 组）
   - API Version：`v1`
   - Operation：`CREATE`（仅在创建 Pod 时应用）
   - Resource：`pods`
   - Scope：`Namespaced`

3. **Namespace Selector**：
   - 仅应用于具有 `kubernetes.io/metadata.name: monitoring` 标签的 namespace
   - API server 会为 monitoring namespace 提供此不可变的名称标签

4. **其他设置**：
   - `admissionReviewVersions`：支持的 AdmissionReview API 版本
   - `sideEffects`：webhook 无副作用
   - `timeoutSeconds`：等待 webhook 响应的时间
   - `failurePolicy`：webhook 失败时拒绝请求

Webhook server 应实现类似以下的逻辑：

使用上面完整 server 中的 `mutateHandler` 和通用请求/响应辅助函数。它会创建缺少的 volumes 数组、保留现有条目、防止重复注入，并在应用容器和 sidecar 容器中挂载 shared-data。遇到保留名称/路径冲突时会拒绝请求。

此 webhook 会自动为在 `monitoring` namespace 中创建且声明了 `spec.os.name: linux` 的 Pod 添加 monitoring sidecar 容器。sidecar 容器使用 monitoring agent 镜像，并挂载共享卷，以便与主容器共享数据。
</details>

> 控制器代码片段需要生成的项目类型、client 和 RBAC。它们会检查 Deployment 所有权，协调镜像/replicas/environment 配置，并使用 Owns watch 监视状态变更。删除资源之前，请使用 finalizer 清理外部资源。本次审查期间没有执行 Kubernetes/AWS 部署。

## 验证参考资料

- https://kubernetes.io/releases/
- https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/
- https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/
- https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/
- https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/
- https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/scheduler/apis/config/types.go
- https://github.com/kubernetes/cloud-provider-aws/blob/master/docs/prerequisites.md
- https://github.com/kubernetes/cloud-provider-aws/blob/master/examples/existing-cluster/base/aws-cloud-controller-manager-daemonset.yaml
- https://github.com/kubernetes-sigs/kubebuilder/blob/master/README.md
- https://github.com/operator-framework/operator-sdk/blob/master/README.md
- https://github.com/NVIDIA/k8s-device-plugin/blob/main/README.md
- https://github.com/jaegertracing/jaeger-operator/blob/main/README.md
- https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/
- https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://github.com/aws-controllers-k8s/community/blob/main/docs/content/docs/user-docs/install.md
- https://github.com/aws-controllers-k8s/s3-controller/blob/main/helm/values.yaml
