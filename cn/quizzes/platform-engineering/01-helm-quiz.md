# Helm 包管理器测验

> **相关文档**: [Helm 包管理器](../../platform-engineering/01-helm.md)

## 选择题

### 1. Helm v3 中移除 Tiller 的主要原因是什么？

- A) 为了提升性能
- B) 为了增强安全性并简化架构
- C) 为了减小 Chart 大小
- D) 为了兼容 Kubernetes 版本

<details>
<summary>显示答案</summary>

**答案：B) 为了增强安全性并简化架构**

**解释：**
Helm v2 的 Tiller 在集群内以提升的权限运行，带来了安全风险。在 Helm v3 中，Tiller 被移除，客户端直接与 Kubernetes API 通信，从而增强了安全性并简化了架构。

</details>

### 2. Helm Chart 中 values.yaml 文件的主要用途是什么？

- A) 存储 Chart 元数据
- B) 定义模板中使用的默认配置值
- C) 直接存储 Kubernetes manifests
- D) 定义 Chart 依赖项

<details>
<summary>显示答案</summary>

**答案：B) 定义模板中使用的默认配置值**

**解释：**
values.yaml 文件定义 Chart 模板使用的默认配置值。用户可以使用 --set 标志或 -f 标志覆盖这些值，以便为不同环境自定义部署。

</details>

### 3. `helm upgrade --install` 命令的行为是什么？

- A) 总是安装一个新的 release
- B) 总是升级一个已有的 release
- C) 如果 release 不存在则安装；如果存在则升级
- D) 删除并重新安装该 release

<details>
<summary>显示答案</summary>

**答案：C) 如果 release 不存在则安装；如果存在则升级**

**解释：**
`helm upgrade --install` 提供幂等行为。如果指定的 release 不存在，它会安装一个新的 release；如果存在，则会升级它。这在 CI/CD pipelines 中特别有用。

</details>

### 4. Helm 模板中的 <code v-pre>{{ .Release.Name }}</code> 引用什么？

- A) Chart 名称
- B) Kubernetes 集群名称
- C) 已安装 release 的名称
- D) Namespace 名称

<details>
<summary>显示答案</summary>

**答案：C) 已安装 release 的名称**

**解释：**
`.Release.Name` 是 Helm 内置对象，引用 `helm install` 命令中指定的 release 名称。例如，在 `helm install my-app chart/` 中，`.Release.Name` 将是 "my-app"。

</details>

### 5. Chart.yaml 的 `dependencies` 字段中 `condition` 属性的用途是什么？

- A) 指定依赖 Chart 的版本
- B) 指定启用/禁用依赖 Chart 的 values 路径
- C) 指定依赖 Chart 仓库 URL
- D) 指定依赖 Chart 优先级

<details>
<summary>显示答案</summary>

**答案：B) 指定启用/禁用依赖 Chart 的 values 路径**

**解释：**
`condition` 属性指定 values.yaml 中的一个路径，用于决定是否启用依赖 Chart。例如，`condition: postgresql.enabled` 表示只有当 `postgresql.enabled` 值为 true 时，才会包含 PostgreSQL subchart。

</details>

### 6. `pre-upgrade` Helm Hook 何时执行？

- A) release 删除之前
- B) 升级请求之后、资源更新之前
- C) 所有资源创建之后
- D) rollback 完成之后

<details>
<summary>显示答案</summary>

**答案：B) 升级请求之后、资源更新之前**

**解释：**
`pre-upgrade` Hook 在收到升级请求后、实际资源更新开始前运行。它通常用于数据库迁移或备份操作。

</details>

### 7. `helm template` 命令的主要用途是什么？

- A) 将 Chart 部署到集群
- B) 在本地渲染 Chart 模板以进行验证
- C) 更新 Chart 依赖项
- D) rollback 一个 release

<details>
<summary>显示答案</summary>

**答案：B) 在本地渲染 Chart 模板以进行验证**

**解释：**
`helm template` 在本地渲染 Chart 模板，使你可以预览将生成的 Kubernetes manifests。这可以在不连接集群的情况下验证模板。

</details>

### 8. Helm 中 `_helpers.tpl` 文件的用途是什么？

- A) 存储 Chart 元数据
- B) 定义可复用的模板辅助函数
- C) 存储默认值
- D) 显示安装后的消息

<details>
<summary>显示答案</summary>

**答案：B) 定义可复用的模板辅助函数**

**解释：**
`_helpers.tpl` 文件定义 helper functions（命名模板），这些函数通常在多个模板中使用。它封装了 Chart 名称、labels 和 selectors 等重复逻辑。

</details>

### 9. `helm get values my-release --all` 命令输出什么？

- A) 仅用户指定的 values
- B) 包括默认值在内的所有 values
- C) release manifest
- D) release 历史

<details>
<summary>显示答案</summary>

**答案：B) 包括默认值在内的所有 values**

**解释：**
使用 `--all` 标志会输出所有计算后的 values，包括用户覆盖的 values 以及 Chart 在 values.yaml 中的默认 values。

</details>

### 10. 为什么 `toYaml` 和 `nindent` 函数在 Helm charts 中经常一起使用？

- A) 将 YAML 转换为 JSON
- B) 以正确缩进将复杂值插入 YAML
- C) 对 values 进行 Base64 编码
- D) 用引号包裹字符串

<details>
<summary>显示答案</summary>

**答案：B) 以正确缩进将复杂值插入 YAML**

**解释：**
`toYaml` 将 Go objects 转换为 YAML 字符串，`nindent` 应用指定数量的空格进行缩进。这个组合对于将 resources 和 annotations 等复杂结构正确插入模板至关重要。

</details>

## 简答题

### 1. Helm v3 使用哪种 Kubernetes resource 类型来存储 release 信息？

<details>
<summary>显示答案</summary>

**答案：Secret**

**解释：**
Helm v3 将 release 信息以 Secrets 形式存储在部署该 release 的 namespace 中。Secret 名称格式为 `sh.helm.release.v1.<release-name>.v<version>`。

</details>

### 2. `helm dependency update` 命令生成的 lock file 名称是什么？

<details>
<summary>显示答案</summary>

**答案：Chart.lock**

**解释：**
`helm dependency update` 解析 Chart.yaml 中的依赖项，并生成包含精确版本的 Chart.lock 文件。该文件确保构建可复现。

</details>

### 3. 在 Helm 模板中，哪个函数会在值为空时提供默认值？

<details>
<summary>显示答案</summary>

**答案：default**

**解释：**
当某个值为空或未定义时，`default` 函数会提供默认值。用法示例：<code v-pre>{{ .Values.image.tag | default .Chart.AppVersion }}</code>

</details>

### 4. 哪个 annotation 控制 Helm Hooks 的执行顺序？

<details>
<summary>显示答案</summary>

**答案：helm.sh/hook-weight**

**解释：**
`helm.sh/hook-weight` annotation 决定同一 Hook 类型内的执行顺序。数字越小越先执行，并且允许使用负值。

</details>

### 5. Helm chart 中的 NOTES.txt 文件何时显示给用户？

<details>
<summary>显示答案</summary>

**答案：helm install 或 helm upgrade 成功完成之后**

**解释：**
NOTES.txt 会在安装或升级成功后显示给用户。它通常包含应用访问说明和初始设置指导。

</details>

## 实践题

### 1. 编写一个满足以下要求的 Helm 命令：

- 将 bitnami/nginx chart 安装为 "web-server" release
- 部署到 "frontend" namespace（如果不存在则创建）
- 将 replicaCount 设置为 3

<details>
<summary>显示答案</summary>

```bash
helm install web-server bitnami/nginx \
  -n frontend --create-namespace \
  --set replicaCount=3
```

**解释：**
- `helm install web-server bitnami/nginx`: 将 nginx chart 安装为 "web-server" release
- `-n frontend`: 指定 frontend namespace
- `--create-namespace`: 如果 namespace 不存在则创建
- `--set`: 内联覆盖 values

</details>

### 2. 预测以下 Helm 模板片段的输出：

```yaml
# values.yaml
env:
  LOG_LEVEL: debug
  MAX_CONNECTIONS: "100"

# template
env:
{{- range $key, $value := .Values.env }}
  - name: {{ $key }}
    value: {{ $value | quote }}
{{- end }}
```

<details>
<summary>显示答案</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

**解释：**
- `range` 函数遍历 `.Values.env` map
- `$key` 是 map key，`$value` 是 map value
- `quote` 函数用引号包裹 values
- Maps 按字母顺序排序

</details>

### 3. 编写一个满足以下要求的 `_helpers.tpl` 模板：

- Name: mychart.labels
- app.kubernetes.io/name: chart name
- app.kubernetes.io/instance: release name
- app.kubernetes.io/version: app version

<details>
<summary>显示答案</summary>

```yaml
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

**解释：**
- `define` 创建可复用的命名模板
- `.Chart.Name` 引用 Chart 名称
- `.Release.Name` 引用 release 名称
- `.Chart.AppVersion` 引用 app version（quote 确保字符串类型）

</details>

## 高级题

### 1. 说明如何使用 Helm charts 实现 Blue-Green 和 Canary deployments。

<details>
<summary>显示答案</summary>

**Blue-Green Deployment:**
```yaml
# values.yaml
deployment:
  activeColor: blue

blue:
  enabled: true
  image:
    tag: "v1.0.0"

green:
  enabled: true
  image:
    tag: "v2.0.0"

service:
  selector:
    color: "{{ .Values.deployment.activeColor }}"
```

**实施策略：**
1. 为 Blue 和 Green 创建两个 Deployment 模板
2. 使用 activeColor 值切换 Service selector
3. 在部署期间将 green.image.tag 设置为新版本
4. 验证后，将 deployment.activeColor 更改为 green
5. 如果出现问题，立即 rollback 到 blue

**Canary Deployment (with Istio):**
```yaml
# VirtualService for traffic distribution
http:
  - route:
      - destination:
          host: myapp
          subset: stable
        weight: 90
      - destination:
          host: myapp
          subset: canary
        weight: 10
```

**实施策略：**
1. 为 Stable 和 Canary 创建两个 Deployments
2. 使用 Istio VirtualService 控制流量比例
3. 逐步增加 Canary 比例 (10% -> 25% -> 50% -> 100%)
4. 基于指标监控实现自动 rollback

</details>

### 2. 说明 Helm chart 安全最佳实践，并设计一个 secret 管理策略。

<details>
<summary>显示答案</summary>

**安全最佳实践：**

1. **Value Validation (values.schema.json)**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["image"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9.-/]+$"
        }
      }
    }
  }
}
```

2. **RBAC Least Privilege Principle**
```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]  # Grant only necessary permissions
```

3. **Apply Pod Security Standards**
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Secret 管理策略：**

1. **External Secrets Manager Integration (AWS Secrets Manager)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: {{ include "mychart.fullname" . }}-secrets
  data:
    - secretKey: database-password
      remoteRef:
        key: myapp/database
        property: password
```

2. **Using Sealed Secrets**
```bash
# Encrypt secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

3. **Helm Secrets Plugin**
```bash
# Use encrypted values file
helm secrets install myapp ./mychart -f secrets.yaml
```

</details>
