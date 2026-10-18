# Helm 包管理器测验

> **相关指南**： [Helm](../../platform-engineering/01-helm.md)

以下 20 道题对应 Helm 3.21.3 / 4.3.0 的复习内容。

## 单项选择

### 1. 移除 Tiller 带来了什么变化？

- A) 只有 Chart 大小会改变。
- B) 客户端使用其 Kubernetes 凭证和 RBAC。
- C) 每个 Chart 都变得安全。
- D) 不再需要 Kubernetes API。

<details>
<summary>显示答案</summary>

**答案：B**

Helm 3 移除了 Tiller，简化了权限路径。仍需审查不安全的资源清单和客户端过大的权限范围。

</details>

### 2. values.yaml 的用途是什么？

- A) Chart 元数据
- B) 供模板使用的默认配置数据
- C) 发布历史记录
- D) 自动执行的模板

<details>
<summary>显示答案</summary>

**答案：B**

只有模板使用的配置值才会生效。配置文件和 --set 的各种形式可以覆盖它们；嵌入的模板字符串不会被自动求值。

</details>

### 3. helm upgrade --install 的作用是什么？

- A) 始终创建新的发布
- B) 始终删除后重新创建
- C) 安装尚不存在的发布或升级现有发布
- D) 保证外部操作的幂等性

<details>
<summary>显示答案</summary>

**答案：C**

它会选择安装或升级。钩子、随机值和外部数据库变更不一定具有幂等性。

</details>

### 4. Release.Name 是什么？

- A) Chart 名称
- B) 集群名称
- C) 所选的发布名称
- D) 镜像标签

<details>
<summary>显示答案</summary>

**答案：C**

在 `helm install demo ./chart` 中，名称是 demo。它不同于 Chart 名称、appVersion 和发布修订版本。

</details>

### 5. 依赖项的 condition 指定什么？

- A) 镜像标签
- B) 控制是否启用依赖项的配置值路径
- C) 镜像仓库密码
- D) Pod 优先级

<details>
<summary>显示答案</summary>

**答案：B**

对于别名 cache，请使用实际的布尔值路径，例如 cache.enabled。测试路径不存在时的行为，并将其与传入子 Chart 的配置值区分开来。

</details>

### 6. pre-upgrade 钩子何时运行？

- A) 删除之后
- B) 渲染之后、常规资源升级之前
- C) 始终在新的 Pod 变为 Ready 后
- D) 仅在回滚后

<details>
<summary>显示答案</summary>

**答案：B**

数据库迁移必须考虑数据库可用性、重试、失败情况以及与先前应用的兼容性。回滚不会自动撤销数据库变更。

</details>

### 7. 普通 helm template 的用途是什么？

- A) 安装到集群中
- B) 在本地渲染资源清单
- C) 验证真实的 webhook
- D) 自动回滚

<details>
<summary>显示答案</summary>

**答案：B**

默认的本地渲染无法证明准入检查、RBAC、镜像运行或连通性符合要求。请将其与会连接服务器的选项区分开来。

</details>

### 8. _helpers.tpl 的用途是什么？

- A) 存储元数据
- B) 定义可复用的命名模板
- C) 存储默认配置值
- D) 存储发布历史记录

<details>
<summary>显示答案</summary>

**答案：B**

使用 define 定义命名模板，再通过 include 引用。为名称添加前缀以避免冲突，并传入预期的上下文。

</details>

### 9. helm get values demo --all 输出什么？

- A) 仅用户覆盖的值
- B) 包含 Chart 默认值的计算结果
- C) 仅资源清单
- D) 仅历史记录

<details>
<summary>显示答案</summary>

**答案：B**

选择正确的命名空间和发布。配置值可能包含敏感信息，因此请保护输出。

</details>

### 10. 为什么要将 toYaml 与 nindent 结合使用？

- A) 自动加密
- B) 将结构化配置值序列化为 YAML，并添加换行和缩进
- C) 仅生成 JSON
- D) 始终将数字转换为字符串

<details>
<summary>显示答案</summary>

**答案：B**

与 indent 不同，nindent 还会在开头添加换行。缩进应与插入位置所需的格式匹配。

</details>

## 简答题

### 1. 默认的发布存储资源是什么？

<details>
<summary>显示答案</summary>

发布所在命名空间中的一个 Secret，名称为 `sh.helm.release.v1.<release>.v<revision>`。也可以配置 ConfigMap 或 SQL 等其他后端。Base64 不是加密。

</details>

### 2. dependency update 创建哪个锁定文件，其限制是什么？

<details>
<summary>显示答案</summary>

Chart.lock。dependency build 使用其中锁定的版本，但仅凭锁定文件不能保证制品完整性、镜像版本固定或完全可复现性。

</details>

### 3. 使用 default 时，需要注意哪些空值？

<details>
<summary>显示答案</summary>

false、零、空字符串和集合都算作空值。当必须保留显式的 false/零值时，请检查值是否存在及其类型。default 无法保护每一种嵌套查找。

</details>

### 4. 哪个注解控制钩子的执行顺序？

<details>
<summary>显示答案</summary>

`helm.sh/hook-weight`。在同一阶段内，权重较低的钩子会先运行，包括负权重。还应考虑权重相同时的资源种类/名称排序、Job 完成情况和超时。

</details>

### 5. NOTES.txt 在何时使用，以及为什么使用？

<details>
<summary>显示答案</summary>

它会通过模板生成在成功安装/升级后显示的说明，并可通过 `helm get notes` 获取。请保持说明准确，并避免包含机密信息。这些说明无法证明应用已就绪。

</details>

## 实操

### 1. 在 frontend 命名空间中以三个副本将示例安装为 web-server。

<details>
<summary>显示答案</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

在仓库根目录中，使用已批准的集群上下文和权限运行。此次审计运行了 lint/template/package，但未执行安装。

</details>

### 2. LOG_LEVEL=debug 和 MAX_CONNECTIONS="100" 应如何渲染为环境变量？

<details>
<summary>显示答案</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

遍历映射，并为每个值加引号，确保两者都保持为字符串。对于键属于基本有序类型的映射，Go 模板会按键的排序顺序遍历；这与列表的顺序不同。

</details>

### 3. 为 Chart、发布和 appVersion 标签编写辅助模板。

<details>
<summary>显示答案</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

传入预期的根上下文，并在调用位置缩进。appVersion 是元数据，不会自动选择镜像标签。

</details>

## 高级

### 1. 使用 Helm 实现蓝绿和金丝雀发布需要什么？

<details>
<summary>显示答案</summary>

蓝绿发布需要两个带标签的 Deployment，以及一个实际的 Service 模板，在验证后选择接收流量的颜色。values.yaml 中的模板字符串不会被自动求值。金丝雀发布需要实际的路由/子集或发布控制器、权重、观测指标和中止条件。仅靠配置值无法实现自动分析或回滚。还要考虑数据库兼容性和进行中的请求。

</details>

### 2. 设计 Chart 安全性和机密信息管理方案。

<details>
<summary>显示答案</summary>

使用受支持的 values.schema.json 验证必需的配置值及其类型，并固定已审查的 Chart/镜像修订版本。为所需的 ServiceAccount 和 RoleBinding 配置最小 API 权限。使用 Secret 卷并不意味着应授予应用访问所有 Secret 的权限。不要将机密值放在默认值、CLI 参数和调试日志中；规划已批准的文件挂载、轮换和重新读取。ESO v1、Sealed Secrets 和 helm-secrets 需要相应的控制器/插件以及提供方/密钥权限。检查解密后的配置值是否会进入发布记录。结合非 root UID、移除进程能力、只读根文件系统和所需的可写卷，然后验证实际的镜像兼容性。

</details>
