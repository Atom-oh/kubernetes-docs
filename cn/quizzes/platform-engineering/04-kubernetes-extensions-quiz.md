# Kubernetes 扩展机制测验

[Kubernetes 扩展](../../platform-engineering/04-kubernetes-extensions.md)

最初的 20 个问题主题已根据当前 API 和行为进行了审查。

## 1. CRD 的用途是什么？

<details>
<summary>显示答案</summary>

在 Kubernetes API 中注册自定义资源类型和输入字段模式（schema）。CRD 本身并不实现工作负载行为。

</details>

## 2. 调谐循环的作用是什么？

<details>
<summary>显示答案</summary>

在处理重复事件、重启和冲突的同时，调谐观测状态与期望状态。当状态已经一致时，应避免不必要的更新。

</details>

## 3. Operator 的定义是什么，其限制有哪些？

<details>
<summary>显示答案</summary>

Operator 使用自定义 API 和控制器实现领域知识。仅仅创建它们并不能让备份、故障转移或升级变得安全。

</details>

## 4. 变更准入 Webhook 可以返回什么？

<details>
<summary>显示答案</summary>

允许或拒绝请求的 AdmissionReview 响应，并可选地携带 JSONPatch。保留请求 UID 和版本；补丁字节采用 Base64 编码。

</details>

## 5. Filter 插件的作用是什么？

<details>
<summary>显示答案</summary>

排除无法满足 Pod 要求的节点。通过过滤并不意味着已完成绑定或执行。

</details>

## 6. 聚合与 CRD 有何不同？

<details>
<summary>显示答案</summary>

CRD 使用现有 API 服务器的自定义资源存储和验证机制。聚合将请求委托给独立的服务器，后者需要处理 TLS、身份验证、授权、API 发现和存储操作。

</details>

## 7. finalizer 提供什么能力？

<details>
<summary>显示答案</summary>

它让控制器有机会在删除完成前完成清理。该字符串本身不会执行任何清理；未经调查就将其移除可能会遗留外部资源。

</details>

## 8. PostBind 在何时运行？

<details>
<summary>显示答案</summary>

它是在成功绑定后执行的通知阶段，而非通用错误恢复机制。应实现 Unreserve 等处理路径，以应对失败或取消的预留。

</details>

## 9. 当前 Istio 的每 Pod 注入如何控制？

<details>
<summary>显示答案</summary>

在 Pod 或工作负载的 Pod 模板标签中设置 sidecar.istio.io/inject。检查命名空间的注入标签、修订版本标签及其优先级，而不是默认使用旧注解。

</details>

## 10. Score 结果如何使用？

<details>
<summary>显示答案</summary>

结合归一化和插件权重，对可行节点进行排序。并列评分节点的选择和失败处理也由调度器负责。

</details>

## 11. CRD 字段模式和必填字段应定义在哪里？

<details>
<summary>显示答案</summary>

定义在 spec.versions[].schema.openAPIV3Schema 下。顶层的 required: [spec] 与 spec 内的 required: [image] 强制执行不同的条件。

</details>

## 12. 对 ownerReferences 必须检查什么？

<details>
<summary>显示答案</summary>

检查所有者 UID、命名空间/作用域以及现有的控制器归属。垃圾回收（GC）依赖传播策略和 finalizer；名称匹配并不授权接管另一个工作负载。

</details>

## 13. VAP 与验证准入 Webhook 有何不同？

<details>
<summary>显示答案</summary>

ValidatingAdmissionPolicy 自 1.30 起已稳定，并在进程内执行 CEL。Webhook 需要远程调用、TLS 和可用性管理。VAP 还需要绑定来定义作用域和 validationActions。

</details>

## 14. controller-runtime 提供什么？

<details>
<summary>显示答案</summary>

管理器、客户端/缓存、调谐设置和领导者选举。它不提供自定义 API 类型、类型注册方案（scheme）、RBAC 或领域逻辑；应对齐所用库与 Kubernetes Go 模块的版本。

</details>

## 15. 转换 Webhook 的用途是什么？

<details>
<summary>显示答案</summary>

在 CRD 的不同 API 版本之间转换表示形式。检查对外提供服务（served）和用于存储（storage）的版本、storedVersions 以及语义是否保留。并非每个 CRD 都需要转换 Webhook。

</details>

## 16. 编写一个要求 image 且 replicas 介于 1 到 5 的 WebApp CRD。

<details>
<summary>显示答案</summary>

这还要求 spec 字段本身存在，并分离 status/scale 路径。控制器必须填充实际的 status.replicas 和 selector。

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
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

</details>

## 17. 应如何将 Deployment 验证 Webhook 限定到 production？

<details>
<summary>显示答案</summary>

匹配 apps/v1 deployments 的 CREATE/UPDATE，并通过 kubernetes.io/metadata.name: production 选择命名空间。配置实际的验证服务器、Service、路径、CA 证书包、failurePolicy、timeoutSeconds、sideEffects 和 admissionReviewVersions。指南中的 /mutate 处理程序不是 Deployment 验证器。若仅限制副本数，请使用其 VAP/绑定示例，并同时匹配 `deployments` 和 `deployments/scale`，以避免 HPA 和 `kubectl scale` 更新绕过限制。

</details>

## 18. 描述一个健壮的调谐序列。

<details>
<summary>显示答案</summary>

将 NotFound 视为成功完成。删除期间，应先完成幂等清理，再仅移除自己的 finalizer。创建外部资源前先持久化 finalizer，检查子资源所有权并调谐受管理字段。发生冲突时重试，并通过补丁更新已变更的观测状态。不要将伪代码标注为可运行的控制器。

</details>

## 19. 设计分布式数据库 Operator 时需要什么？

<details>
<summary>显示答案</summary>

除字段模式和工作负载创建外，还应设计阻止旧主节点继续写入的隔离机制、法定数量（quorum）机制、副本同步、备份/WAL 恢复测试、存储生命周期、迁移兼容性和故障处理。创建 Service、StatefulSet 和 CronJob 并不能确立数据安全性。

</details>

## 20. 应如何实现和验证自定义调度器？

<details>
<summary>显示答案</summary>

针对所用 Kubernetes 次要版本的准确框架接口编译/注册插件。对齐配置名称（profile names）和 Pod 的 schedulerName；测试 Filter/Score 以及预留、许可和绑定失败的情况。仅靠 YAML 无法安装插件。对于简单的可用区要求，先考虑节点亲和性。

</details>
