# Kube Resource Orchestrator (kro) 测验

[kro](../../platform-engineering/03-kro.md)

这些问题保留了使用 kro 0.9.4 的原始 20 个主题。

## 1. kro 的核心概念是什么？

<details>
<summary>显示答案</summary>

在 RGD 中定义 API schema 和资源图，通过 CEL 引用推断依赖关系并协调实例。kro 不是命令式脚本运行器。

</details>

## 2. 受管资源定义在哪里声明？

<details>
<summary>显示答案</summary>

在 spec.resources 下，使用每个条目的 id 以及 template 或 externalRef。以前的 childResources 已不是当前的 RGD 字段。

</details>

## 3. kro 与 Helm 一起提供什么？

<details>
<summary>显示答案</summary>

资源引用图和持续的实例协调。Helm 提供 chart 渲染和 release 管理；它们可以协同工作。对于每一种工作负载，没有任何一个能普遍优于另一个。

</details>

## 4. 如何在 CEL 中引用实例输入？

<details>
<summary>显示答案</summary>

使用 schema.spec 或 schema.metadata，例如 `${schema.spec.replicas}`。不要使用 .parent 或 Go-template 语法。

</details>

## 5. 如何配置条件性资源包含？

<details>
<summary>显示答案</summary>

在 includeWhen 中使用 Boolean CEL 表达式。更改条件可能会添加或清理资源，因此请审查对有状态资源的生命周期影响。

</details>

## 6. 受管资源 status 值投射到哪里？

<details>
<summary>显示答案</summary>

在 spec.schema.status 下定义 CEL 表达式，例如 `${deployment.status.availableReplicas}`。statusMappings 不是当前字段。

</details>

## 7. 如何排序依赖关系和就绪状态？

<details>
<summary>显示答案</summary>

对其他资源 ID 的 CEL 引用会推断出一个 DAG。存在 readyWhen 条件时，依赖资源也会等待这些条件。循环会被拒绝；YAML 列出顺序不能替代依赖关系。

</details>

## 8. 删除实例时会发生什么？

<details>
<summary>显示答案</summary>

当前 kro 使用 ApplySet inventory 和删除波次，先移除依赖其他资源的对象（依赖方），并保留 finalizer。子资源的 finalizer 可能会阻塞进度。外部引用目标不会被删除。

</details>

## 9. 什么会监视实例变更？

<details>
<summary>显示答案</summary>

kro 的动态实例 controllers 会观察变更并协调图。RGD/GraphRevision 验证和编译会影响实例进度。

</details>

## 10. kubectl apply 做什么？

<details>
<summary>显示答案</summary>

它会创建或更新 CR 的期望状态，随后 controllers 进行协调。apply 成功并不表示图编译完成或应用已就绪，也不保证外部影响具有事务性。

</details>

## 11. 什么是 RGD？

<details>
<summary>显示答案</summary>

ResourceGraphDefinition 定义生成的 API schema、受管资源和 status 关系。它不同于应用实例 CR。

</details>

## 12. 什么提供了类似 Helm values 的输入？

<details>
<summary>显示答案</summary>

生成的 API 实例的 spec。它的 SimpleSchema 类型、默认值和边界必须与 template 实际使用的字段相匹配。

</details>

## 13. 如何引用另一个资源？

<details>
<summary>显示答案</summary>

直接引用其资源 ID，例如 `${deployment.spec.selector.matchLabels}` 或 `${service.metadata.name}`。不要使用 .children。

</details>

## 14. 什么会跟踪受管资源并支持删除诊断？

<details>
<summary>显示答案</summary>

检查当前 ApplySet inventory、owner metadata 和 internal.kro.run/apply-order 删除波次。不要把虚构的 kro.run/owner annotation 视为完整的跟踪契约。

</details>

## 15. 如何验证输入 schema？

<details>
<summary>显示答案</summary>

SimpleSchema 会成为生成的 CRD 的 OpenAPI schema，Kubernetes 使用它来验证实例。RGD 结构、图编译器的 CEL 类型检查和运行时就绪状态是独立的检查。

</details>

## 16. 编写示例 NginxApp 实例。

<details>
<summary>显示答案</summary>

首先确保 RGD 为 Active 且其生成的 CRD 为 Established。此实例禁用了 ingress。

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

</details>

## 17. 编写创建 Deployment 的资源条目。

<details>
<summary>显示答案</summary>

这与指南中的 template 相同。readyWhen 仅引用 Deployment 本身；请在实际环境中验证 image、namespace 和 policies。

```yaml
resources:
- id: deployment
  readyWhen:
  - ${deployment.status.availableReplicas >= deployment.spec.replicas}
  - ${deployment.status.observedGeneration >= deployment.metadata.generation}
  template:
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ${schema.metadata.name}
      namespace: ${schema.metadata.namespace}
      labels:
        app.kubernetes.io/name: ${schema.metadata.name}
    spec:
      replicas: ${schema.spec.replicas}
      selector:
        matchLabels:
          app.kubernetes.io/name: ${schema.metadata.name}
      template:
        metadata:
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 101
            runAsGroup: 101
            fsGroup: 101
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: web
            image: ${schema.spec.image}
            ports:
            - name: http
              containerPort: 8080
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            readinessProbe:
              httpGet:
                path: /
                port: http
            volumeMounts:
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir:
              sizeLimit: 64Mi
```

</details>

## 18. 在 status 中公开 availableReplicas。

<details>
<summary>显示答案</summary>

这是 RGD spec.schema 下的 status 部分。解析可能会等待缺失的值；它并不代表全面的应用健康状况。

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. 设计一个 dev/staging/prod 策略。

<details>
<summary>显示答案</summary>

共享经过验证的 API 契约和 image digests，同时按实例分离 namespace、replicas、ingress 和 policies。在每个 cluster 中准备 kro/RGD/permissions，并使用 fleet tooling 进行同步。未使用的 autoscaling 字段不会创建 HPA。

</details>

## 20. Helm 和 kro 对有状态应用的限制是什么？

<details>
<summary>显示答案</summary>

两者都不会自动实现数据库备份、恢复、failover 或 schema migration。请验证专用 operator/managed-service 的行为和数据保留。恢复 Git spec 不等于数据库回滚；失败的最新 GraphRevision 不会自动回退。

</details>
