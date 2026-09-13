# Kubernetes 扩展机制测验

[Kubernetes extensions](../../platform-engineering/04-kubernetes-extensions.md)

最初的 20 个问题主题已根据当前 API 和行为进行了审查。

## 1. CRD 的用途是什么？

<details>
<summary>显示答案</summary>

在 Kubernetes API 中注册自定义资源类型和输入 schema。CRD 本身并不实现工作负载行为。

</details>

## 2. 调谐循环的作用是什么？

<details>
<summary>显示答案</summary>

在处理重复事件、重启和冲突的同时，调谐观测状态与期望状态。当状态已经一致时，应避免不必要的更新。

</details>

## 3. Operator 的定义是什么，其限制有哪些？

<details>
<summary>显示答案</summary>

Operator 使用自定义 API 和 controller 实现领域知识。仅仅创建它们并不能让备份、故障转移或升级变得安全。

</details>

## 4. 变更 webhook 可以返回什么？

<details>
<summary>显示答案</summary>

允许或拒绝请求的 AdmissionReview 响应，并可选地携带 JSONPatch。保留请求 UID/version；patch 字节采用 Base64 编码。

</details>

## 5. Filter plugin 的作用是什么？

<details>
<summary>显示答案</summary>

排除无法满足 Pod 要求的节点。通过过滤并不意味着已完成绑定或执行。

</details>

## 6. 聚合与 CRD 有何不同？

<details>
<summary>显示答案</summary>

CRD 使用现有 API server 的自定义资源存储和验证。聚合将请求委托给独立的 server，后者需要 TLS、身份验证、授权、发现和存储操作。

</details>

## 7. finalizer 提供什么能力？

<details>
<summary>显示答案</summary>

它让 controller 有机会在删除完成前完成清理。该字符串本身不会执行任何清理；未经调查就将其移除可能会遗留外部资源。

</details>

## 8. PostBind 在何时运行？

<details>
<summary>显示答案</summary>

它是在成功绑定后执行的信息性阶段，而非通用错误恢复机制。应为失败或取消的预留实现诸如 Unreserve 的路径。

</details>

## 9. 当前 Istio 的每 Pod 注入如何控制？

<details>
<summary>显示答案</summary>

在 Pod 或工作负载的 Pod-template labels 中设置 sidecar.istio.io/inject。检查 namespace 注入/revision labels 及其优先级，而不是将旧 annotations 用作默认值。

</details>

## 10. Score 结果如何使用？

<details>
<summary>显示答案</summary>

对可行节点进行排序，并结合归一化和 plugin 权重。平局选择和失败处理也是 scheduler 的行为。

</details>

## 11. CRD schema 和必填字段应定义在哪里？

<details>
<summary>显示答案</summary>

定义在 spec.versions[].schema.openAPIV3Schema 下。顶层的 required: [spec] 与 spec 内的 required: [image] 强制执行不同的条件。

</details>

## 12. 对 ownerReferences 必须检查什么？

<details>
<summary>显示答案</summary>

检查 owner UID、namespace/scope 以及现有的 controller 所有权。GC 依赖传播策略/finalizers；名称匹配并不授权接管另一个工作负载。

</details>

## 13. VAP 与验证 webhook 有何不同？

<details>
<summary>显示答案</summary>

ValidatingAdmissionPolicy 自 1.30 起已稳定，并在进程内执行 CEL。webhook 需要远程调用、TLS 和可用性管理。VAP 还需要 binding 来定义 scope 和 validationActions。

</details>

## 14. controller-runtime 提供什么？

<details>
<summary>显示答案</summary>

Managers、clients/caches、调谐设置和 leader election。它不提供自定义 API types、schemes、RBAC 或领域逻辑；应对齐 library 与 Kubernetes Go module 的版本。

</details>

## 15. conversion webhook 的用途是什么？

<details>
<summary>显示答案</summary>

在 CRD 的 API versions 之间转换表示形式。审查 served/storage versions、storedVersions 和语义保留。并非每个 CRD 都需要 conversion webhook。

</details>

## 16. 编写一个要求 image 且 replicas 介于 1 到 5 的 WebApp CRD。

<details>
<summary>显示答案</summary>

这还要求 spec 本身存在，并分离 status/scale 路径。controller 必须填充实际的 status.replicas 和 selector。

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

## 17. 应如何将 Deployment 验证 webhook 限定到 production？

<details>
<summary>显示答案</summary>

匹配 apps/v1 deployments 的 CREATE/UPDATE，并选择 kubernetes.io/metadata.name: production。配置实际的验证 server/Service/path、CA bundle、failurePolicy、timeoutSeconds、sideEffects 和 admissionReviewVersions。指南中的 /mutate handler 不是 Deployment validator。若仅限制 replica，请使用其 VAP/binding 示例，并同时匹配 `deployments` 和 `deployments/scale`，以避免 HPA 和 `kubectl scale` 更新绕过限制。

</details>

## 18. 描述一个健壮的调谐序列。

<details>
<summary>显示答案</summary>

将 NotFound 视为成功完成。删除期间，应在仅移除自己的 finalizer 前完成幂等清理。创建外部资源前先持久化 finalizer，检查子资源所有权并调谐受管理字段。重试冲突并 patch 已变更的观测 status。不要将伪代码标注为可运行的 controller。

</details>

## 19. 设计分布式数据库 Operator 时需要什么？

<details>
<summary>显示答案</summary>

除 schema 和工作负载创建外，还应设计主节点隔离、quorum、副本同步、备份/WAL 恢复测试、存储生命周期、迁移兼容性和故障处理。创建 Services、StatefulSets 和 CronJobs 并不能建立数据安全性。

</details>

## 20. 应如何实现和验证自定义 scheduler？

<details>
<summary>显示答案</summary>

针对对应 Kubernetes minor 版本的精确 framework interfaces 编译/注册 plugins。对齐 profile names 和 Pod schedulerName；测试 Filter/Score 以及预留、permit 和绑定失败。仅靠 YAML 无法安装 plugin。对于简单的 zone 要求，先考虑 node affinity。

</details>
