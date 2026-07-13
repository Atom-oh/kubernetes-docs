# 扩展 Kubernetes 测验

本测验用于测试你对 Kubernetes 扩展机制的概念性和实践性知识。它涵盖 Custom Resource Definitions (CRD)、custom controllers、API 扩展、webhooks 以及 operator pattern 等主题。

## 选择题

1. 在 Kubernetes 中定义 custom resources 最常见的方式是什么？
   - A) 使用 ConfigMap 定义资源 schema
   - B) 创建 CustomResourceDefinition (CRD)
   - C) 直接修改 API server 代码
   - D) 使用 Aggregation Layer

<details>
<summary>显示答案</summary>

**答案：B) 创建 CustomResourceDefinition (CRD)**

**解释：**
在 Kubernetes 中定义 custom resources 最常见的方式是创建 CustomResourceDefinition (CRD)。CRD 是一种机制，允许你通过定义新的资源类型来扩展 Kubernetes API。

使用 CRDs 可带来以下好处：
- 可以在不修改现有 Kubernetes API server 的情况下添加新的资源类型。
- 可以使用 `kubectl` 等标准 Kubernetes 工具管理 custom resources。
- 可以利用资源验证、版本管理和 status subresources 等功能。

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
- ConfigMaps 用于存储配置数据，不适合用于 API 扩展。
- 直接修改 API server 代码很复杂、难以维护，并且可能在升级期间导致问题。
- Aggregation Layer 是定义 custom resources 的另一种方式，但它比 CRDs 更复杂，因为它需要实现单独的 API server。
</details>

2. Kubernetes Operator 的主要目的是什么？
   - A) 优化 cluster nodes 的资源使用
   - B) 将复杂应用程序的运维知识编码到自动化软件中
   - C) 提高 Kubernetes API server 性能
   - D) 扩展 cluster networking 功能

<details>
<summary>显示答案</summary>

**答案：B) 将复杂应用程序的运维知识编码到自动化软件中**

**解释：**
Kubernetes Operator 的主要目的是将复杂应用程序的运维知识编码到自动化软件中。operator pattern 是人类操作员管理复杂应用程序方式的软件实现。

operators 的关键特征：
- 将 custom resources 与 custom controllers 结合起来，实现特定于应用程序的逻辑。
- 自动化应用程序部署、升级、备份、恢复和扩缩容等运维任务。
- 持续监控应用程序状态，并调整到期望状态。
- 将领域知识编码化，以支持复杂应用程序的声明式管理。

operators 的常见使用场景：
- 数据库的自动化管理（例如 PostgreSQL、MySQL、MongoDB）
- 消息系统的部署和配置（例如 Kafka、RabbitMQ）
- 监控系统的设置和维护（例如 Prometheus）
- service meshes 的管理（例如 Istio）

Operator 示例 - Prometheus Operator：
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  version: v2.35.0
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

通过这个简单的声明式配置，Prometheus Operator 会自动处理以下复杂任务：
- 部署 Prometheus servers
- 创建和管理配置文件
- 自动发现 service monitoring targets
- 高可用设置
- 存储管理
- 升级协调

其他选项不是 operators 的主要目的：
- 资源使用优化是 HPA (Horizontal Pod Autoscaler)、VPA (Vertical Pod Autoscaler) 等的职责。
- 提高 API server 性能不是 operators 的主要目的。
- 扩展 networking 功能是 CNI plugins 或 service meshes 的职责。
</details>

3. Kubernetes 中 Admission Webhooks 的主要功能是什么？
   - A) 处理 API server 的身份认证
   - B) 拦截资源创建或修改请求，以验证或修改它们
   - C) 监控 cluster events 并发送告警
   - D) 提供用于与外部系统集成的 APIs

<details>
<summary>显示答案</summary>

**答案：B) 拦截资源创建或修改请求，以验证或修改它们**

**解释：**
Kubernetes 中 Admission Webhooks 的主要功能是拦截资源创建或修改请求，以验证或修改它们。Admission webhooks 提供一种机制，可在 Kubernetes API server 将请求存储到持久化存储（etcd）之前拦截请求。

两种 admission webhooks：

1. **Validating Webhook**:
   - 验证资源创建、更新和删除请求。
   - 可以允许或拒绝请求，但不能修改请求。
   - 用于策略强制、安全检查、配置验证等。

2. **Mutating Webhook**:
   - 可以验证和修改资源创建与更新请求。
   - 用于设置默认值、注入 sidecar containers、添加 labels 等。
   - 在 validating webhooks 之前运行。

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
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

admission webhooks 的常见使用场景：
- 强制执行安全策略（例如禁止 privileged containers）
- 强制设置 resource requests 和 limits
- 自动注入 sidecar containers（例如 Istio）
- 自动添加 labels 和 annotations
- 限制 image registries
- 应用基于 namespace 的策略

其他选项的问题：
- 处理 API server 的身份认证是 Authentication Plugins 的职责。
- 监控 cluster events 并发送告警是 event listeners 或监控工具的职责。
- 提供用于与外部系统集成的 APIs 是 API 扩展的一般目的，但不是 admission webhooks 的主要功能。
</details>

4. Kubernetes API server 中 Aggregation Layer 的主要目的是什么？
   - A) 优化 API server 性能
   - B) 将多个 API servers 合并为单个 API server
   - C) 将 custom API servers 集成到 main API server 中以扩展 API
   - D) 在 cluster 内提供 service discovery

<details>
<summary>显示答案</summary>

**答案：C) 将 custom API servers 集成到 main API server 中以扩展 API**

**解释：**
Kubernetes API server 中 Aggregation Layer 的主要目的是将 custom API servers 集成到 main API server 中以扩展 API。这提供了另一种扩展 Kubernetes API 的方式，虽然更复杂，但比 CRDs 提供更强大的功能。

Aggregation Layer 的关键特征：
- 将 custom API servers 集成到 Kubernetes API server 的 URL 空间中。
- Custom API servers 可以拥有自己的存储、业务逻辑、API 版本等。
- Main API server 将请求代理到适当的 custom API server。
- 身份认证和授权由 main API server 处理。

使用 Aggregation Layer 的场景：
- 需要复杂验证逻辑时
- 需要自定义存储后端时
- 需要与现有 APIs 不同的行为时
- 需要资源转换或特殊状态计算时

APIService 资源示例：
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1alpha1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1alpha1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
```

此配置会将针对 `metrics.k8s.io/v1alpha1` API group 的请求路由到 `kube-system` namespace 中的 `metrics-server` service。

使用 Aggregation Layer 的真实示例：
- metrics-server：提供 node 和 pod resource usage metrics
- service-catalog：与外部 service brokers 集成
- custom-metrics-apiserver：为 HPA 提供 custom metrics

其他选项的问题：
- Aggregation Layer 不是用于优化 API server 性能的。
- 将多个 API servers 合并为一个并不是准确描述。Aggregation Layer 将多个 API servers 集成到单个 URL 空间中，但这些 servers 是分别运行的。
- Aggregation Layer 不提供 service discovery。那是 Kubernetes Services 的职责。
</details>

5. Kubernetes 中 Custom Controller 的主要角色是什么？
   - A) 监控 cluster nodes 的资源使用
   - B) 观察 custom resources 的状态并协调到期望状态
   - C) 处理 API server 请求的身份认证和授权
   - D) 管理 cluster networking

<details>
<summary>显示答案</summary>

**答案：B) 观察 custom resources 的状态并协调到期望状态**

**解释：**
Kubernetes 中 Custom Controller 的主要角色是观察 custom resources 的状态并协调到期望状态。Controllers 实现“reconciliation loop”，这是 Kubernetes 中的核心运维模式，用于持续将系统的实际状态调整到期望状态。

custom controllers 的关键特征：
- Watch 特定资源类型（通常是通过 CRDs 定义的 custom resources）。
- 对资源变更事件作出响应并执行业务逻辑。
- 执行任务，将资源的实际状态调整为期望状态。
- 更新资源的 status 字段以反映当前状态。

custom controllers 的常见组件：
1. **Informer**: Watch Kubernetes API server 并接收资源变更事件。
2. **Work Queue**: 存储和管理待处理事件。
3. **Reconciler**: 比较资源的期望状态和实际状态，并执行必要任务。
4. **Client**: 与 Kubernetes API 交互以创建、更新和删除资源。

Custom controller 示例 - 简单 reconcile 函数：
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
        // Resource deleted - perform cleanup
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
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(instanceCopy)
    return err
}
```

custom controllers 的常见使用场景：
- 自动化复杂应用程序的部署和管理
- 与外部系统集成（例如 cloud resource provisioning）
- 自动化备份和恢复流程
- 实现高级部署策略（例如 canary deployments、blue-green deployments）

其他选项的问题：
- 监控 cluster nodes 的资源使用是 metrics-server 或 Prometheus 等监控工具的职责。
- 处理 API server 请求的身份认证和授权是 authentication 和 authorization plugins 的职责。
- 管理 cluster networking 是 CNI plugins 或 network controllers 的职责。
</details>

6. 在 Kubernetes 中，CRDs (CustomResourceDefinitions) 使用什么格式来定义验证 schemas？
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>显示答案</summary>

**答案：C) OpenAPI v3 Schema**

**解释：**
在 Kubernetes 中，用于定义 CRDs (CustomResourceDefinitions) 验证 schemas 的格式是 OpenAPI v3 Schema。此 schema 定义 custom resources 的结构和字段类型，并由 API server 用于验证资源创建和更新请求。

CRD 验证 schema 示例：
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

在此示例中，`openAPIV3Schema` 字段定义以下验证规则：
- `spec` 字段是必需的。
- 在 `spec` 中，`cronSpec` 和 `image` 字段是必需的。
- `cronSpec` 是字符串，并且必须遵循 cron 表达式模式。
- `image` 是字符串。
- `replicas` 是整数，并且必须在 1 到 10 之间。

OpenAPI v3 Schema 提供多种验证功能：
- 指定必需字段
- 数据类型验证（string、number、boolean、object、array 等）
- 字符串模式验证（正则表达式）
- 数值范围验证（minimum、maximum）
- 数组长度验证
- Enum 值验证
- 嵌套 object 结构定义

其他选项的问题：
- JSON Schema 是 OpenAPI 的基础，但 Kubernetes 明确使用 OpenAPI v3 Schema。
- XML Schema 不用于 Kubernetes API。
- GraphQL Schema 用于 GraphQL APIs，但不用于 Kubernetes API。
</details>

7. 在 Kubernetes 中为 custom resources 启用 status subresource 的主要好处是什么？
   - A) 更快的资源创建
   - B) 分离 spec 和 status 更新，并进行 RBAC 控制
   - C) 自动备份和恢复功能
   - D) 简化资源版本管理

<details>
<summary>显示答案</summary>

**答案：B) 分离 spec 和 status 更新，并进行 RBAC 控制**

**解释：**
在 Kubernetes 中为 custom resources 启用 status subresource 的主要好处是分离 spec 和 status 更新，并能够通过 RBAC (Role-Based Access Control) 控制访问。

启用 status subresource 的好处：

1. **关注点分离**:
   - `spec` 字段定义用户指定的期望状态。
   - `status` 字段报告 controllers 观察到的实际状态。
   - 这种分离明确了用户和 controllers 的职责。

2. **RBAC 控制**:
   - 可以只向 controllers 授予 status 更新权限，同时给普通用户只读权限。
   - 这可以防止未经授权修改 status 信息。

3. **冲突预防**:
   - 即使用户更新 `spec` 的同时 controller 更新 `status`，也不会发生冲突。
   - 这是因为这两个字段通过单独的 API 请求更新。

4. **Scale Subresource 支持**:
   - 启用 status subresource 也允许启用 scale subresource。
   - 这使得可以使用 HPA (Horizontal Pod Autoscaler) 等标准 Kubernetes 扩缩容工具。

在 CRD 中启用 status subresource 的示例：
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
        status: {}  # Enable status subresource
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                # Spec field definitions...
            status:
              type: object
              properties:
                # Status field definitions...
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

controller 更新 status 的示例：
```go
// Update status only
statusUpdate := &v1alpha1.MyResource{}
statusUpdate.Name = instance.Name
statusUpdate.Namespace = instance.Namespace
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(statusUpdate)
```

其他选项的问题：
- status subresource 不会提高资源创建速度。
- 它不提供自动备份和恢复功能。
- 资源版本管理通过 CRD 的 `versions` 字段处理，并不直接与 status subresource 相关。
</details>

8. Kubernetes 中 Webhook Conversion 的主要目的是什么？
   - A) 将 API 请求路由到外部 services
   - B) 处理 custom resources 不同版本之间的转换
   - C) 将身份认证 tokens 转换为不同格式
   - D) 将日志数据转换为结构化格式

<details>
<summary>显示答案</summary>

**答案：B) 处理 custom resources 不同版本之间的转换**

**解释：**
Kubernetes 中 Webhook Conversion 的主要目的是处理 custom resources 不同版本之间的转换。此功能支持 CRDs 的多个版本，并支持版本之间的平滑迁移。

webhook conversion 的关键特征：

1. **多版本支持**:
   - CRDs 可以同时支持多个 API 版本（例如 v1alpha1、v1beta1、v1）。
   - 每个版本可以有不同的 schemas 和字段。

2. **自动转换**:
   - API server 会自动处理客户端请求版本与存储版本之间的转换。
   - conversion webhook 在此过程中提供自定义转换逻辑。

3. **存储版本独立性**:
   - 即使存储版本发生变化，使用旧版本的 clients 也可以继续工作。
   - webhook 负责处理旧版本与新版本之间的双向转换。

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
          # v1 schema definition...
    - name: v1beta1
      served: true
      storage: false
      schema:
        openAPIV3Schema:
          # v1beta1 schema definition...
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions: ["v1", "v1beta1"]
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

conversion webhook server 实现示例：
```go
func (s *WebhookServer) ServeConvert(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // Decode ConversionReview request
    convertReview := v1.ConversionReview{}
    if err := json.Unmarshal(body, &convertReview); err != nil {
        // Error handling
        return
    }

    // Perform conversion logic
    if convertReview.Request.DesiredAPIVersion == "stable.example.com/v1" {
        // v1beta1 -> v1 conversion
        for i, obj := range convertReview.Request.Objects {
            v1beta1Obj := &v1beta1.CronTab{}
            if err := json.Unmarshal(obj.Raw, v1beta1Obj); err != nil {
                // Error handling
                return
            }

            // Conversion logic
            v1Obj := &v1.CronTab{
                Spec: v1.CronTabSpec{
                    CronSpec: v1beta1Obj.Spec.Cron,  // Field name change
                    Image: v1beta1Obj.Spec.Image,
                    Replicas: v1beta1Obj.Spec.Replicas,
                },
            }

            // Encode converted object
            raw, err := json.Marshal(v1Obj)
            if err != nil {
                // Error handling
                return
            }

            convertReview.Response.ConvertedObjects = append(
                convertReview.Response.ConvertedObjects,
                runtime.RawExtension{Raw: raw},
            )
        }
    } else {
        // v1 -> v1beta1 conversion
        // Similar logic...
    }

    // Set response
    convertReview.Response.UID = convertReview.Request.UID
    convertReview.Response.Result.Status = "Success"

    // Send response
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(convertReview)
}
```

其他选项的问题：
- 将 API 请求路由到外部 services 是 API aggregation 的职责。
- 转换身份认证 tokens 是 authentication plugins 的职责。
- 转换日志数据是 logging systems 的职责。
</details>

9. 以下哪一项不是帮助开发 Kubernetes operators 的框架？
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>显示答案</summary>

**答案：D) Kubespray**

**解释：**
Kubespray 不是帮助开发 Kubernetes operators 的框架。Kubespray 是一个使用 Ansible playbooks 部署和管理 Kubernetes clusters 的工具。它专注于 cluster 安装和配置，与 operator 开发无关。

实际用于 Kubernetes operator 开发的框架包括：

1. **Operator Framework**:
   - Red Hat 开发的 operator 开发工具包
   - 关键组件：
     - Operator SDK：Operator 脚手架和开发工具
     - Operator Lifecycle Manager (OLM)：Operator 安装和升级管理
     - Operator Metering：Operator 使用情况报告
   - 支持 Go、Ansible 和基于 Helm 的 operator 开发

2. **Kubebuilder**:
   - Kubernetes SIG (Special Interest Group) 开发的框架
   - 用于以 Go 开发 controllers 的 SDK
   - 提供代码生成、CRD 管理和测试工具
   - 基于 controller-runtime 库

3. **Metacontroller**:
   - 轻量级、基于 webhook 的 operator 框架
   - 可以使用多种语言实现 controller 逻辑
   - 声明式 controller 定义
   - 适合快速开发简单 controllers

各框架的功能比较：

| 框架 | 主要语言 | 复杂度 | 功能 |
|-----------|------------------|------------|----------|
| Operator Framework | Go、Ansible、Helm | 中高 | 综合工具包，多种开发选项 |
| Kubebuilder | Go | 中 | 标准化模式，代码生成工具 |
| Metacontroller | 语言无关 | 低 | 基于 Webhook，简单实现 |

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

其他选项说明：
- Operator Framework 是 Red Hat 的综合 operator 开发工具包。
- Kubebuilder 是 Kubernetes SIG 开发的基于 Go 的 controller 开发框架。
- Metacontroller 是轻量级、基于 webhook 的 operator 框架。
</details>

10. Kubernetes 中 Custom Resource Definitions (CRD) 与 Aggregated APIs 的主要区别是什么？
    - A) CRDs 不支持版本管理，但 Aggregated APIs 支持
    - B) CRDs 不支持验证 schemas，但 Aggregated APIs 支持
    - C) CRDs 实现简单但灵活性有限，而 Aggregated APIs 实现复杂但提供更多灵活性
    - D) CRDs 只支持 cluster-scoped resources，而 Aggregated APIs 只支持 namespace-scoped resources

<details>
<summary>显示答案</summary>

**答案：C) CRDs 实现简单但灵活性有限，而 Aggregated APIs 实现复杂但提供更多灵活性**

**解释：**
Kubernetes 中 Custom Resource Definitions (CRD) 与 Aggregated APIs 的主要区别在于实现复杂度和灵活性之间的权衡。CRDs 实现简单但灵活性有限，而 Aggregated APIs 实现复杂但提供更多灵活性。

**CRDs (CustomResourceDefinitions) 的特征：**
- **实现简单**：可以通过单个 YAML 文件定义新的 API 资源。
- **使用现有 API server**：无需实现单独的 API server。
- **灵活性有限**：
  - 存储限制为 etcd。
  - 继承默认 API server 的行为。
  - 难以实现复杂验证或转换逻辑。
- **通过 webhooks 扩展**：某些功能可以通过 validating webhooks、conversion webhooks 等扩展。

**Aggregated APIs 的特征：**
- **实现复杂**：必须开发并部署单独的 API server。
- **高灵活性**：
  - 可以使用自定义存储后端
  - 可以实现复杂业务逻辑
  - 可以实现自定义身份认证和授权逻辑
  - 可以实现特殊状态计算和转换逻辑
- **完整 API server 功能**：可以利用标准 Kubernetes API server 的所有功能。

**选择标准：**

| 标准 | 选择 CRD | 选择 Aggregated API |
|----------|------------|----------------------|
| 实现复杂度 | 低 - 简单 YAML 定义 | 高 - 需要开发单独的 API server |
| 开发时间 | 短 - 可以在几分钟内实现 | 长 - 需要完整的 API server 开发 |
| 维护 | 容易 - 由现有 API server 管理 | 困难 - 需要维护单独服务 |
| 存储选项 | 仅 etcd | 可使用自定义存储后端 |
| 业务逻辑 | 有限 - 通过 controllers 实现 | 灵活 - 可直接在 API server 中实现 |
| 性能 | 通常良好 | 可自定义优化 |
| 使用场景 | 简单 CRUD 操作、标准模式 | 复杂 API 行为、特殊验证/转换 |

**示例场景：**

适合 CRDs 的场景：
- 简单应用程序配置管理
- 基本 CRUD 操作是主要需求
- 快速原型设计和开发

适合 Aggregated APIs 的场景：
- 与外部数据库集成
- 复杂数据转换和验证
- 需要特殊身份认证机制
- 高性能或特殊用途 APIs

其他选项的问题：
- CRDs 支持版本管理（A 不正确）。
- CRDs 通过 OpenAPI v3 Schema 支持验证 schemas（B 不正确）。
- CRDs 和 Aggregated APIs 都支持 cluster-scoped 和 namespace-scoped resources（D 不正确）。
</details>

## 简答题

1. 说明如何使用 CustomResourceDefinition (CRD) 定义 custom resources，以及如何为这些资源设置验证规则。

<details>
<summary>显示答案</summary>

**答案：**

**如何定义 CustomResourceDefinition (CRD)：**

CRD 是一种扩展 Kubernetes API 以定义新资源类型的机制。当你创建 CRD 时，会创建一个新的 RESTful API endpoint，并且可以使用 `kubectl` 等标准工具管理该资源。

**1. 基本 CRD 结构：**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>  # e.g., crontabs.stable.example.com
spec:
  group: <api-group>      # e.g., stable.example.com
  names:
    kind: <kind-name>     # e.g., CronTab
    plural: <plural-name> # e.g., crontabs
    singular: <singular-name>  # e.g., crontab
    shortNames:           # optional
    - <short-name>        # e.g., ct
  scope: Namespaced       # or Cluster
  versions:
    - name: <version>     # e.g., v1
      served: true        # whether to serve via API server
      storage: true       # whether this is the storage version
      schema:
        openAPIV3Schema:
          # schema definition
```

**2. 设置验证规则：**

CRDs 的验证规则通过 `openAPIV3Schema` 字段设置。此 schema 遵循 OpenAPI v3 格式，并定义资源的结构和字段类型。

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

- **必需字段**：将字段名添加到 `required` 数组
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **数据类型**：使用 `type` 字段指定数据类型
  ```yaml
  type: string | number | integer | boolean | array | object
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
  uniqueItems: true
  items:
    type: string
  ```

- **Enum 值**：指定允许的值列表
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **默认值**：为字段指定默认值
  ```yaml
  default: "default-value"
  ```

- **Additional properties**：控制是否允许额外属性
  ```yaml
  additionalProperties: false
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

此命令将返回类似以下的错误：
```
Error from server (Invalid): error when creating "STDIN": admission webhook "validate-crontab.example.com" denied the request:
- spec.cronSpec: Invalid value: "invalid-cron-spec": does not match pattern '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
- spec.replicas: Invalid value: 20: must be less than or equal to 10
```

**7. 最佳实践：**

- 清晰且详细的 schema 定义
- 明确指定必需字段
- 提供适当的默认值
- 限制字符串模式和数值范围
- 启用 status subresource
- 配置 additional printer columns
- 建立版本管理策略
</details>

2. 说明 Kubernetes Operator Pattern 的核心概念以及实现 operators 的常见方法。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes Operator Pattern 的核心概念：**

operator pattern 是一种 Kubernetes 扩展机制，它将特定于应用程序的运维知识编码到软件中，以自动管理复杂应用程序。此模式模仿人类操作员管理复杂系统的方式。

**1. 核心概念：**

- **声明式管理**：用户声明期望状态，operator 将当前状态调整为期望状态。
- **编码领域知识**：将特定应用程序的运维知识和最佳实践编码化。
- **Reconciliation Loop**：持续观察实际状态并调整到期望状态。
- **Custom Resources**：用于存储特定于应用程序的配置和状态。
- **Controllers**：Watch custom resources 的变更并执行必要任务。

**2. Operators 的常见功能：**

- **安装和升级**：部署应用程序组件并升级版本
- **自动恢复**：检测故障并执行恢复任务
- **备份和还原**：自动化数据备份和还原流程
- **扩缩容**：根据 workload 需求自动扩展和收缩
- **配置管理**：处理特定于应用程序的配置变更
- **运维自动化**：自动化日常运维任务（例如数据库压缩、索引重建）

**实现 Operators 的方法：**

**1. 使用 Operator SDK：**

[Operator SDK](https://sdk.operatorframework.io/) 是 Red Hat Operator Framework 的一部分，是简化 operator 开发的工具。

```bash
# Install Operator SDK
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push
make deploy
```

**2. 使用 Kubebuilder：**

[Kubebuilder](https://book.kubebuilder.io/) 是 Kubernetes SIG 开发的框架，提供 controller 开发工具。

```bash
# Install Kubebuilder
curl -L https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH) | tar -xz -C /tmp/
sudo mv /tmp/kubebuilder_*/bin/kubebuilder /usr/local/bin/

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy
```

**3. Controller 实现：**

operator 的核心是 reconciliation 函数。此函数观察 custom resources 的当前状态并执行必要任务。

```go
// Reconcile function example
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := r.Log.WithValues("myapp", req.NamespacedName)

    // Get custom resource
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted - perform cleanup
            return ctrl.Result{}, nil
        }
        // Error occurred
        return ctrl.Result{}, err
    }

    // 1. Check if required resources exist
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, types.NamespacedName{Name: myApp.Name, Namespace: myApp.Namespace}, deployment)
    if errors.IsNotFound(err) {
        // Create deployment if it doesn't exist
        deployment = r.deploymentForMyApp(&myApp)
        log.Info("Creating a new Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
        if err := r.Create(ctx, deployment); err != nil {
            log.Error(err, "Failed to create new Deployment")
            return ctrl.Result{}, err
        }
        // Deployment creation successful
        return ctrl.Result{Requeue: true}, nil
    } else if err != nil {
        log.Error(err, "Failed to get Deployment")
        return ctrl.Result{}, err
    }

    // 2. Check if deployment is in desired state
    size := myApp.Spec.Size
    if *deployment.Spec.Replicas != size {
        deployment.Spec.Replicas = &size
        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }
        // Deployment update successful
        return ctrl.Result{Requeue: true}, nil
    }

    // 3. Update status
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil {
            log.Error(err, "Failed to update MyApp status")
            return ctrl.Result{}, err
        }
    }

    return ctrl.Result{}, nil
}

// Deployment creation function
func (r *MyAppReconciler) deploymentForMyApp(m *appsv1alpha1.MyApp) *appsv1.Deployment {
    ls := labelsForMyApp(m.Name)
    replicas := m.Spec.Size

    dep := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      m.Name,
            Namespace: m.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: ls,
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: ls,
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{{
                        Image: m.Spec.Image,
                        Name:  "myapp",
                        Ports: []corev1.ContainerPort{{
                            ContainerPort: 8080,
                            Name:          "http",
                        }},
                    }},
                },
            },
        },
    }

    // Set owner reference
    ctrl.SetControllerReference(m, dep, r.Scheme)
    return dep
}
```

**4. Custom Resource Definition：**

定义由 operator 管理的 custom resources 的 API。

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

**5. 基于 Ansible 或 Helm 的 Operators：**

Operator SDK 除了 Go 之外，也支持使用 Ansible 或 Helm 开发 operators。

**基于 Ansible 的 operator：**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**基于 Helm 的 operator：**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. 部署和测试 Operators：**

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

operator 成熟度模型定义 operators 的能力级别：

1. **Basic Install**：应用程序安装和配置
2. **Seamless Upgrades**：版本之间的自动升级
3. **Full Lifecycle**：备份、还原、故障恢复等
4. **Deep Insights**：自动扩缩容、调优等
5. **Auto Pilot**：基于监控的自动优化

**8. 最佳实践：**

- 增量实现功能（从简单功能开始）
- 彻底的错误处理和日志记录
- 确保幂等性（相同输入得到相同结果）
- 设置 owner references（资源层次结构和垃圾回收）
- 通过 status updates 报告进度
- 编写 unit tests 和 integration tests
- 清晰的文档
</details>

3. 说明 Kubernetes 中 Admission Webhooks 的类型以及各自的使用场景。

<details>
<summary>显示答案</summary>

**答案：**

**Kubernetes Admission Webhooks 的类型和使用场景：**

Admission webhooks 是一种机制，可以在 Kubernetes API server 将请求存储到持久化存储（etcd）之前拦截并修改或验证请求。Admission webhooks 大体分为两类：Mutating webhooks 和 Validating webhooks。

**1. Mutating Webhook：**

Mutating webhooks 可以修改进入 API server 的请求对象。这些 webhooks 在 validating webhooks 之前运行。

**关键特征：**
- 可以修改请求对象
- 多个 mutating webhooks 以链式方式运行
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
      name: sidecar-injector
      path: "/inject"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**常见使用场景：**

1. **Sidecar Container 注入：**
   - 在 Istio 和 Linkerd 等 service meshes 中自动注入 proxy sidecar
   - 添加 logging 和 monitoring sidecars
   - 示例：Istio 的 sidecar injector 会在 pods 创建时自动添加 Envoy proxy containers

2. **设置默认值：**
   - 自动设置 resource requests 和 limits
   - 应用 security context 默认值
   - 自动添加 labels 和 annotations
   - 示例：为所有 pods 设置默认 CPU 和 memory requests

3. **应用 Image Policies：**
   - 修改 image registry URLs
   - 将 image tags 转换为 digests
   - 示例：将 `nginx:latest` 改为 `internal-registry.example.com/nginx:v1.19.0`

4. **Volume 修改：**
   - 添加默认 volume mounts
   - 自动挂载 ConfigMap 或 Secret
   - 示例：为所有 pods 自动挂载 service account token volume

5. **应用 Network Policies：**
   - 添加默认 network settings
   - 修改 DNS 配置
   - 示例：对特定 namespace 中的所有 pods 应用特定 DNS 设置

**2. Validating Webhook：**

Validating webhooks 可以验证进入 API server 的请求并允许或拒绝它们。这些 webhooks 在 mutating webhooks 之后运行。

**关键特征：**
- 不能修改请求对象
- 只能允许或拒绝请求
- 多个 validating webhooks 并行运行
- 所有 webhooks 都必须允许请求，请求才会被处理

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
      name: pod-policy-validator
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**常见使用场景：**

1. **强制执行安全策略：**
   - 禁止 privileged containers
   - 禁止 root user 执行
   - 限制 host network/PID/IPC 使用
   - 示例：拒绝以 privileged mode 运行的 pods

2. **验证资源约束：**
   - 强制要求 resource requests 和 limits
   - 应用 resource caps
   - 强制执行 QoS classes
   - 示例：拒绝没有 memory limits 的 pods

3. **验证 Image Policies：**
   - 仅允许 approved registries
   - 禁止使用 latest tag
   - 验证 vulnerability scan 结果
   - 示例：只允许来自 official registries 的 images

4. **验证 Labels 和 Annotations：**
   - 检查 required labels
   - 验证 label formats
   - 示例：要求所有 pods 必须包含 `app` 和 `environment` labels

5. **基于 Namespace 的策略：**
   - 每个 namespace 的 resource limits
   - 每个 namespace 的 feature restrictions
   - 示例：在 production namespaces 中应用更严格的策略

**3. Webhook 实现方法：**

Admission webhooks 实现为提供 HTTPS endpoints 的 services。这些 services 接收 `AdmissionReview` 请求，处理它们，并返回 `AdmissionResponse`。

**基本 Webhook Server 实现示例 (Go)：**

```go
package main

import (
    "encoding/json"
    "io/ioutil"
    "net/http"

    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/runtime/serializer"
)

var (
    runtimeScheme = runtime.NewScheme()
    codecs        = serializer.NewCodecFactory(runtimeScheme)
    deserializer  = codecs.UniversalDeserializer()
)

// Mutating webhook handler
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Create patch (add sidecar container)
    patch := []map[string]interface{}{
        {
            "op": "add",
            "path": "/spec/containers/-",
            "value": map[string]interface{}{
                "name": "sidecar",
                "image": "sidecar-image:latest",
                "resources": map[string]interface{}{
                    "limits": map[string]interface{}{
                        "cpu": "100m",
                        "memory": "100Mi",
                    },
                    "requests": map[string]interface{}{
                        "cpu": "50m",
                        "memory": "50Mi",
                    },
                },
            },
        },
    }

    // Convert patch to JSON
    patchBytes, err := json.Marshal(patch)
    if err != nil {
        http.Error(w, "Failed to marshal patch", http.StatusInternalServerError)
        return
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: true,
        Patch:   patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

// Validating webhook handler
func validateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Validation logic
    allowed := true
    var message string

    // Check for privileged containers
    for _, container := range pod.Spec.Containers {
        if container.SecurityContext != nil && container.SecurityContext.Privileged != nil && *container.SecurityContext.Privileged {
            allowed = false
            message = "Privileged containers are not allowed"
            break
        }
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: allowed,
    }

    if !allowed {
        admissionResponse.Result = &metav1.Status{
            Message: message,
            Status:  "Failure",
            Reason:  metav1.StatusReasonForbidden,
            Code:    403,
        }
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

func main() {
    http.HandleFunc("/mutate", mutateHandler)
    http.HandleFunc("/validate", validateHandler)

    fmt.Println("Starting webhook server on :8443")
    http.ListenAndServeTLS(":8443", "tls.crt", "tls.key", nil)
}
```

**4. Webhook 部署和配置：**

Webhook servers 通常部署在 Kubernetes cluster 内，并且需要 service 和 TLS certificates。

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
        image: webhook-server:latest
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

- **性能优化**：Webhooks 位于 API server 请求路径中，因此必须快速响应。
- **错误处理**：考虑 webhook server 失败时的行为，并适当设置 `failurePolicy`。
- **范围限制**：仅将 webhooks 应用于必要的资源和操作。
- **测试**：在各种场景中彻底测试 webhook 行为。
- **监控**：监控 webhook server 性能和错误。
- **版本管理**：支持多个 AdmissionReview 版本，为 API 版本变化做准备。
</details>

## 实践题

1. 编写一个满足以下要求的 CustomResourceDefinition (CRD)：
   - API Group: webapp.example.com
   - Version: v1
   - Kind: WebApp
   - Scope: Namespaced
   - Required fields: spec.image, spec.replicas
   - Validation rules: replicas must be an integer between 1 and 10
   - Enable status subresource

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

此 CRD 具有以下特征：

1. **基本信息**：
   - API Group: `webapp.example.com`
   - Version: `v1`
   - Kind: `WebApp`
   - Scope: `Namespaced`

2. **Schema 验证**：
   - `spec` 字段是必需的。
   - `spec.image` 和 `spec.replicas` 是必需字段。
   - `spec.replicas` 必须是 1 到 10 之间的整数。
   - `spec.port` 是可选字段，默认值为 80。
   - `spec.env` 是可选字段，定义环境变量数组。

3. **Status Subresource**：
   - 启用 `status` subresource，以便 controllers 可以更新 status。
   - 定义了 `status.availableReplicas` 和 `status.phase` 字段。

4. **Additional Printer Columns**：
   - 运行 `kubectl get webapps` 时，会显示 Replicas、Image 和 Age 列。

5. **名称配置**：
   - Plural: `webapps`
   - Singular: `webapp`
   - Kind: `WebApp`
   - Short name: `wa`

可以使用此 CRD 创建如下 custom resources：

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.19
  replicas: 3
  port: 8080
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

Controllers 可以 watch 此资源并更新 status：

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. 编写一个满足以下要求的 Mutating Admission Webhook 配置：
   - Add sidecar container to all pod creation requests
   - Apply only to a specific namespace (monitoring)
   - Webhook service: webhook-service.webhook-system.svc
   - Path: /mutate

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
      monitoring-injection: enabled
  admissionReviewVersions: ["v1", "v1beta1"]
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
    monitoring-injection: enabled
```

此配置具有以下特征：

1. **Webhook 配置**：
   - Name: `sidecar-injector`
   - Webhook service: `webhook-service.webhook-system.svc`
   - Path: `/mutate`

2. **范围**：
   - API Group: `""`（core API group）
   - API Version: `v1`
   - Operation: `CREATE`（仅在 pod 创建时应用）
   - Resource: `pods`
   - Scope: `Namespaced`

3. **Namespace Selector**：
   - 仅应用于带有 `monitoring-injection: enabled` label 的 namespaces
   - 将此 label 添加到 `monitoring` namespace

4. **其他设置**：
   - `admissionReviewVersions`：支持的 AdmissionReview API 版本
   - `sideEffects`：webhook 无副作用
   - `timeoutSeconds`：webhook 响应等待时间
   - `failurePolicy`：webhook 失败时拒绝请求

webhook server 应实现如下逻辑：

```go
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    // Decode request
    body, _ := ioutil.ReadAll(r.Body)
    admissionReview := admissionv1.AdmissionReview{}
    deserializer.Decode(body, nil, &admissionReview)

    // Decode pod object
    pod := corev1.Pod{}
    json.Unmarshal(admissionReview.Request.Object.Raw, &pod)

    // Define sidecar container
    sidecarContainer := corev1.Container{
        Name:  "monitoring-sidecar",
        Image: "monitoring-agent:latest",
        Resources: corev1.ResourceRequirements{
            Limits: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("100m"),
                corev1.ResourceMemory: resource.MustParse("100Mi"),
            },
            Requests: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("50m"),
                corev1.ResourceMemory: resource.MustParse("50Mi"),
            },
        },
        VolumeMounts: []corev1.VolumeMount{
            {
                Name:      "shared-data",
                MountPath: "/var/monitoring",
            },
        },
    }

    // Create patch
    patch := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/spec/containers/-",
            "value": sidecarContainer,
        },
        {
            "op":   "add",
            "path": "/spec/volumes/-",
            "value": map[string]interface{}{
                "name": "shared-data",
                "emptyDir": map[string]interface{}{},
            },
        },
    }

    // Convert patch to JSON
    patchBytes, _ := json.Marshal(patch)

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:       admissionReview.Request.UID,
        Allowed:   true,
        Patch:     patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

此 webhook 会自动向在 `monitoring` namespace 中创建的所有 pods 添加一个 monitoring sidecar container。该 sidecar container 使用 monitoring agent image，并挂载共享 volume 以与 main container 共享数据。
</details>
