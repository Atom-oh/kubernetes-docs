# Helm 包管理器测验

> **相关指南**: [Helm](../../platform-engineering/01-helm.md)

以下 20 个问题主题对应 Helm 3.21.3 / 4.3.0 的复习内容。

## 单项选择

### 1. 移除 Tiller 带来了什么变化？

- A) 只有 chart 大小会改变。
- B) 客户端使用其 Kubernetes 凭证和 RBAC。
- C) 每个 chart 都变得安全。
- D) 不再需要 Kubernetes API。

<details>
<summary>显示答案</summary>

**答案：B**

Helm 3 移除了 Tiller，简化了权限路径。仍需审查不安全的 manifest 和权限范围过大的客户端凭证。

</details>

### 2. values.yaml 的用途是什么？

- A) Chart 元数据
- B) 由 template 使用的默认配置数据
- C) Release 历史记录
- D) 自动执行的 template

<details>
<summary>显示答案</summary>

**答案：B**

只有被 template 使用的 values 才会生效。文件和 --set 变体可以覆盖它们；嵌入式 template 字符串不会被自动求值。

</details>

### 3. helm upgrade --install 的作用是什么？

- A) 始终创建新的 release
- B) 始终删除后重新创建
- C) 安装缺失的 release 或升级现有的 release
- D) 保证外部操作的幂等性

<details>
<summary>显示答案</summary>

**答案：C**

它会选择安装或升级。hook、随机值和外部数据库变更不一定是幂等的。

</details>

### 4. Release.Name 是什么？

- A) Chart 名称
- B) Cluster 名称
- C) 所选的 release 名称
- D) Image tag

<details>
<summary>显示答案</summary>

**答案：C**

在 `helm install demo ./chart` 中，名称是 demo。它不同于 chart 名称、appVersion 和 release revision。

</details>

### 5. dependency condition 指定什么？

- A) Image tag
- B) 控制是否启用 dependency 的 values 路径
- C) Registry 密码
- D) Pod 优先级

<details>
<summary>显示答案</summary>

**答案：B**

对于 alias cache，请使用真实的 Boolean 路径，例如 cache.enabled。测试路径不存在时的行为，并将其与传入 subchart 的 values 区分开来。

</details>

### 6. pre-upgrade hook 何时运行？

- A) 删除之后
- B) 渲染之后、常规资源升级之前
- C) 始终在新的 Pod 变为 Ready 后
- D) 仅在 rollback 后

<details>
<summary>显示答案</summary>

**答案：B**

数据库迁移必须考虑数据库可用性、重试、失败情况以及与先前 app 的兼容性。Rollback 不会自动撤销数据库变更。

</details>

### 7. 普通 helm template 的用途是什么？

- A) 安装到 cluster 中
- B) 在本地渲染 manifest
- C) 验证真实的 webhook
- D) 自动 rollback

<details>
<summary>显示答案</summary>

**答案：B**

默认的本地渲染无法证明 admission、RBAC、image 执行或连通性。请将其与会连接服务器的选项区分开来。

</details>

### 8. _helpers.tpl 的用途是什么？

- A) 存储元数据
- B) 定义可复用的命名 template
- C) 存储默认 values
- D) 存储 release 历史记录

<details>
<summary>显示答案</summary>

**答案：B**

使用 define 创建命名 template，并使用 include 使用它们。为名称添加前缀以避免冲突，并传递预期的 context。

</details>

### 9. helm get values demo --all 输出什么？

- A) 仅用户覆盖的值
- B) 包含 chart 默认值的计算后 values
- C) 仅 manifest
- D) 仅历史记录

<details>
<summary>显示答案</summary>

**答案：B**

选择正确的 namespace 和 release。Values 可能包含敏感信息，因此请保护输出。

</details>

### 10. 为什么要将 toYaml 与 nindent 结合使用？

- A) 自动加密
- B) 将结构化 values 序列化为 YAML，并添加换行和缩进
- C) 仅生成 JSON
- D) 始终将数字转换为字符串

<details>
<summary>显示答案</summary>

**答案：B**

与 indent 不同，nindent 还会在开头添加换行。缩进应与插入位置所需的格式匹配。

</details>

## 简答题

### 1. 默认的 release 存储资源是什么？

<details>
<summary>显示答案</summary>

release namespace 中的一个 Secret，名称为 `sh.helm.release.v1.<release>.v<revision>`。也可以配置 ConfigMap 或 SQL 等其他 backend。Base64 不是加密。

</details>

### 2. dependency update 创建哪个 lock 文件，其限制是什么？

<details>
<summary>显示答案</summary>

Chart.lock。dependency build 使用锁定的版本，但仅有 lock 并不能保证 artifact 完整性、固定的 image 或完全可复现性。

</details>

### 3. 使用 default 时，哪些空 values 很重要？

<details>
<summary>显示答案</summary>

False、零、空字符串和 collection 都算作空值。当必须保留显式的 false/zero 时，请检查是否存在以及类型。default 无法保护每一种嵌套查找。

</details>

### 4. 哪个 annotation 控制 hook 排序？

<details>
<summary>显示答案</summary>

`helm.sh/hook-weight`。在同一 phase 内，较低的 weight 会先运行，包括负 weight。还应考虑 kind/name 的并列排序、Job 完成情况和 timeout。

</details>

### 5. NOTES.txt 在何时使用，以及为什么使用？

<details>
<summary>显示答案</summary>

它会生成在成功 install/upgrade 后显示的说明，并可通过 `helm get notes` 获取。请保持说明准确，并避免包含 secret。Notes 无法证明 application 已就绪。

</details>

## 实操

### 1. 在 frontend 中以三个 replica 将示例安装为 web-server。

<details>
<summary>显示答案</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

在 repository root 中使用已批准的 cluster context 和权限运行。此次审计运行了 lint/template/package，但未执行安装。

</details>

### 2. LOG_LEVEL=debug 和 MAX_CONNECTIONS="100" 应如何渲染为 env？

<details>
<summary>显示答案</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

遍历 map，并为每个 value 加引号，以确保两者都保持为字符串。Go template 会按键顺序使用基本有序键遍历 map；这不同于 list 排序。

</details>

### 3. 为 chart、release 和 appVersion label 编写一个 helper。

<details>
<summary>显示答案</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

传递预期的 root context，并在调用位置缩进。appVersion 是元数据，不会自动选择 image tag。

</details>

## 高级

### 1. 使用 Helm 实现 Blue/Green 和 canary 交付需要什么？

<details>
<summary>显示答案</summary>

Blue/Green 需要两个带 label 的 Deployment，以及一个真实的 Service template，在验证后选择活动颜色。values.yaml 中的 template 字符串不会被自动求值。Canary 需要真实的 route/subset 或 rollout controller、weight、观测指标和中止条件。仅靠 values 无法创建自动化分析或 rollback。还要考虑数据库兼容性和进行中的请求。

</details>

### 2. 设计 chart 安全性和 secret 管理。

<details>
<summary>显示答案</summary>

使用受支持的 values.schema.json 验证必需的 values 和类型，并固定已审查的 chart/image revision。为所需的 ServiceAccounts 和 RoleBindings 配置最小 API 权限。Secret volume 并不意味着应授予 app 访问所有 Secret 的权限。不要将 secret value 放在默认值、CLI 参数和 debug log 中；规划已批准的文件挂载、轮换和重新读取。ESO v1、Sealed Secrets 和 helm-secrets 需要其 controller/plugin 以及 provider/key 权限。检查解密后的 values 是否会进入 release record。结合非 root UID、移除的 capability、只读 root 和所需的可写 volume，然后验证实际的 image 兼容性。

</details>
