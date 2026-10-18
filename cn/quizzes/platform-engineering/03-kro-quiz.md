# Kube Resource Orchestrator (kro) 测验

[kro](../../platform-engineering/03-kro.md)

这些问题保留了原有的 20 个主题，使用 kro 0.9.4。

## 1. kro 的核心概念是什么？

<details>
<summary>显示答案</summary>

在 RGD 中定义 API 字段模式（schema）和资源图，根据 CEL 引用推断依赖关系，并调谐实例。kro 不是命令式脚本运行器。

</details>

## 2. 在哪里声明受管理资源定义？

<details>
<summary>显示答案</summary>

在 spec.resources 下，使用每个条目的 id 和 template 或 externalRef。旧版的 childResources 不是当前 RGD 字段。

</details>

## 3. kro 在 Helm 之外补充哪些能力？

<details>
<summary>显示答案</summary>

资源引用图和持续的实例调谐。Helm 提供 Chart 渲染和发布管理；二者可以协同工作。没有一方对所有工作负载都更好。

</details>

## 4. 如何在 CEL 中引用实例输入？

<details>
<summary>显示答案</summary>

使用 schema.spec 或 schema.metadata，例如 `${schema.spec.replicas}`。不要使用 .parent 或 Go 模板语法。

</details>

## 5. 如何按条件决定是否创建或保留资源？

<details>
<summary>显示答案</summary>

在 includeWhen 中使用布尔 CEL 表达式。更改条件可能会添加或移除资源，因此请审查对有状态资源生命周期的影响。

</details>

## 6. 在哪里映射受管理资源的状态值？

<details>
<summary>显示答案</summary>

在 spec.schema.status 下定义 CEL 表达式，例如 `${deployment.status.availableReplicas}`。statusMappings 不是当前字段。

</details>

## 7. 如何确定依赖关系和就绪顺序？

<details>
<summary>显示答案</summary>

对其他资源 ID 的 CEL 引用会推断出一个有向无环图（DAG）。如果设置了 readyWhen 条件，依赖其他资源的下游资源还须等待相应条件满足。循环依赖会被拒绝；YAML 中的排列顺序不能替代依赖关系。

</details>

## 8. 删除实例时会发生什么？

<details>
<summary>显示答案</summary>

当前版本的 kro 使用 ApplySet 资源清单和分批删除机制，先删除依赖其他资源的下游资源，并保留一个 finalizer。子资源上的 finalizer 可能会阻止删除进度。外部引用的目标不会被删除。

</details>

## 9. 什么会监视实例变更？

<details>
<summary>显示答案</summary>

kro 的动态实例控制器会观察变更并调谐资源图。RGD/GraphRevision 的验证和编译会影响实例进度。

</details>

## 10. kubectl apply 会做什么？

<details>
<summary>显示答案</summary>

它会创建或更新 CR 的期望状态，之后由控制器进行调谐。apply 成功不代表资源图已编译或应用已就绪，也不能保证外部操作具有事务性。

</details>

## 11. 什么是 RGD？

<details>
<summary>显示答案</summary>

ResourceGraphDefinition 定义生成的 API 字段模式、受管理资源和状态关系。它不同于应用实例 CR。

</details>

## 12. 什么提供了类似 Helm values 的输入？

<details>
<summary>显示答案</summary>

生成的 API 实例的 spec。其 SimpleSchema 类型、默认值和边界必须与模板实际使用的字段相匹配。

</details>

## 13. 如何引用另一个资源？

<details>
<summary>显示答案</summary>

直接引用其资源 ID，例如 `${deployment.spec.selector.matchLabels}` 或 `${service.metadata.name}`。不要使用 .children。

</details>

## 14. 什么用于跟踪受管理资源并帮助诊断删除问题？

<details>
<summary>显示答案</summary>

检查当前的 ApplySet 资源清单、所有者元数据和用于分批删除的 internal.kro.run/apply-order。不要把臆造的 kro.run/owner 注解视为完整的跟踪约定。

</details>

## 15. 如何验证输入字段模式？

<details>
<summary>显示答案</summary>

SimpleSchema 会成为生成的 CRD 的 OpenAPI 字段模式，Kubernetes 会用它来验证实例。RGD 结构、资源图编译器的 CEL 类型检查和运行时就绪状态是彼此独立的检查。

</details>

## 16. 编写示例 NginxApp 实例。

<details>
<summary>显示答案</summary>

首先确保 RGD 处于 Active 状态，且其生成的 CRD 已达到 Established 状态。此实例会禁用入口访问。

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

</details>

## 17. 编写用于创建 Deployment 的资源条目。

<details>
<summary>显示答案</summary>

这与指南中的模板相同。readyWhen 只引用 Deployment 本身；请在实际环境中核实镜像、命名空间和策略。

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

## 18. 在状态中公开 availableReplicas。

<details>
<summary>显示答案</summary>

这是 RGD spec.schema 下的状态部分。表达式解析可能需要等待缺失的值可用；这并不能全面反映应用健康状况。

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. 设计 dev/staging/prod 策略。

<details>
<summary>显示答案</summary>

共享经过验证的 API 契约和镜像摘要，同时为每个实例分别设置命名空间、副本数、入口访问和策略。在每个集群中准备 kro/RGD/权限，并使用集群管理工具进行同步。未使用的自动扩缩字段不会创建 HPA。

</details>

## 20. Helm 和 kro 在有状态应用方面有哪些限制？

<details>
<summary>显示答案</summary>

二者都不会自动实现数据库备份、恢复、故障转移或数据库模式迁移。请验证专用 Operator/托管服务的行为和数据保留策略。恢复 Git 中的 spec 并不等于数据库回滚；最新的 GraphRevision 失败时也不会自动回退。

</details>
