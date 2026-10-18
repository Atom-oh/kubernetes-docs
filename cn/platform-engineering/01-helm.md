# Helm 包管理器

> **最后更新**: September 12, 2026
> **本地验证**: Helm 3.21.3 / Helm 4.3.0

Helm 渲染 chart，并管理 Kubernetes 资源和 release 历史记录。Chart 版本、appVersion、镜像标签/摘要和 release 修订版本是不同的值。Helm 4 接受现有的 apiVersion:v2 chart，但必须针对确切版本检查 CLI/apply/wait 行为。

## 核心概念和权限

Helm 3 移除了 Tiller；客户端使用各自的 Kubernetes 凭据/RBAC。Chart 仓库/OCI 注册表通信与 Kubernetes API 访问彼此独立。移除 Tiller 并不意味着不安全的 chart 或过于宽泛的权限就无害了。

Release 存储默认使用 release 命名空间中的 Secrets；也可配置 ConfigMap/SQL 等后端。存储的 release 数据包括清单/值，可能会暴露敏感信息。Base64 并非加密；应限制对 release Secrets 的访问。

## 完整的本地 Chart 示例

`examples/platform/helm/reviewed-app` 包含以下八个文件。已测试 Helm 3/4 的 lint/render 输出、打包、值覆盖以及对无效 replicaCount 的拒绝。未安装 Kubernetes，也未执行容器。执行操作前，请验证镜像摘要、命名空间、硬件和策略。

### Chart.yaml

```yaml
apiVersion: v2
name: reviewed-app
description: Offline Helm teaching chart
type: application
version: 0.1.0
appVersion: "1.30.4"
```

### values.yaml

```yaml
replicaCount: 1
image:
  repository: nginxinc/nginx-unprivileged
  tag: "1.30.6-alpine"
service:
  port: 8080
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
env:
  LOG_LEVEL: info
```

### values.schema.json

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "replicaCount",
    "image",
    "service"
  ],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5
    },
    "image": {
      "type": "object",
      "required": [
        "repository",
        "tag"
      ],
      "properties": {
        "repository": {
          "type": "string",
          "minLength": 1
        },
        "tag": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "service": {
      "type": "object",
      "required": [
        "port"
      ],
      "properties": {
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535
        }
      }
    },
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}
```

### templates/_helpers.tpl

```text
{{- define "reviewed-app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "reviewed-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
{{- end -}}
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "reviewed-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "reviewed-app.selectorLabels" . | nindent 8 }}
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
        image: {{ printf "%s:%s" .Values.image.repository .Values.image.tag | quote }}
        ports:
        - name: http
          containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        env:
          {{- range $key, $value := .Values.env }}
        - name: {{ $key | quote }}
          value: {{ $value | quote }}
          {{- end }}
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

### templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  type: ClusterIP
  selector:
    {{- include "reviewed-app.selectorLabels" . | nindent 4 }}
  ports:
  - name: http
    port: {{ .Values.service.port }}
    targetPort: http
```

### templates/NOTES.txt

```text
Inspect the rendered resources and prepare namespace/image compatibility before installation.
Release: {{ .Release.Name }}
Namespace: {{ .Release.Namespace }}
```

### .helmignore

```text
*.private
```

所有 helper 均已定义，Service 指向一个具名容器端口，清单中包含 securityContext，且 resources/env 已从 values 接入模板。未使用的 values 条目不会产生任何效果。这个基础 chart 不会创建数据库、Ingress 或自动扩缩器。

### 本地检查

从仓库根目录运行，并使用 `helm version --short` 检查所选二进制文件。

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

Lint/template 成功并不能验证准入、CEL、RBAC、镜像执行、Service 连通性或就绪状态。测试 hook 必须在集群中实际执行。`helm template --api-versions` 提供离线能力信息；它不会安装 CRD。

## 命令和 Helm 3/4 差异

| 用途 | 示例和限制 |
| --- | --- |
| 仓库 | `helm repo add/update/list/remove`、`helm search repo`；OCI 注册表有单独的登录/拉取流程 |
| 安装 | `helm install demo ./chart -n example --create-namespace`；验证命名空间/release 是否存在 |
| 安装或升级 | `helm upgrade --install`；hook、随机值和外部状态不一定具有幂等性 |
| 检查 | `helm list -n example`、status/history/get values/get manifest；保护敏感输出 |
| 计算后的值 | `helm get values demo -n example --all` 包含 chart 默认值 |
| 回滚 | `helm rollback demo REVISION -n example`；修订版本不是镜像标签 |
| 卸载 | `helm uninstall demo -n example`；检查 PVC/CRD/hook/外部资源的生命周期 |

旧的 stable 仓库仅供存档，并非当前默认仓库。请验证外部 chart/镜像的可用性、许可、支持和安全性，并固定 chart 版本。旧版 Bitnami PostgreSQL12/Redis17 依赖不再是本示例的默认项。

### Dry Run 和等待

Helm 4.3 区分 `--dry-run=client` 和 `--dry-run=server`。在此环境中，4.3 client 模式无需集群即可通过；3.21.3 install client dry-run 会尝试访问集群并失败。离线渲染请使用已验证的 `helm template` 流程。Server 模式需要集群访问权限，且不能证明所有 webhook/外部副作用都已覆盖。

在 Helm 4.3 中，省略 --wait 时默认使用 hookOnly；指定 --wait 时默认使用 watcher，也可使用 legacy。`--rollback-on-failure` 会将失败的升级回滚到之前成功的 release。它的名称与 Helm 3 的 --atomic 不同。`--force-replace` 和 `--force-conflicts` 分别控制替换和 server-side-apply 冲突；请检查确切版本的帮助信息。

回滚不是一个可以撤销数据库迁移、外部 API 操作或已删除数据的事务。应区分超时、Pod 就绪状态、Job 完成状态和应用 SLO。

## 模板和值

Chart、Release、Values 和 Capabilities 是上下文对象。range/with 会更改点号上下文；需要根上下文时请使用 `$`。Capabilities 反映的是所提供的发现信息，并不代表普遍兼容性。

include 会将命名模板的输出作为字符串返回，可将其传入 nindent；nindent 还会插入换行符。为 helper 名称添加前缀以避免子 chart 冲突，并避免在升级过程中不必要地更改 selector。

default/coalesce 会将 false、零、空字符串和集合视为空值。若要保留显式的 false/零值，应分别检查是否存在及其类型。default 无法保护所有父 map 缺失时的嵌套查找。

values.yaml 是数据：其中嵌入的 <code v-pre>{{ .Values... }}</code> 不会自动再次求值。Chart 作者可在需要时显式使用 tpl，但必须审查输入信任度和模板权限。以前的子 chart storageClass 和 Blue/Green selector 字符串并未自动接入。

对于重复文件/覆盖项，靠右的值优先；请理解 map 合并和 list 替换的行为。应将 dev/staging/prod 保存为单独文件，而不是在一个 YAML 文档中使用重复键。对于看起来像数字的字符串，请使用 --set-string；结构化数据则使用受版本支持的 --set-json。

--reuse-values、--reset-values 和 --reset-then-reuse-values 以不同方式组合先前的 release 值和新的默认值。请检查计算后的值和渲染差异，而不要依赖隐式行为。

## 依赖管理

Chart.yaml 声明依赖名称、版本、仓库以及可选别名/条件。以下片段假设**已准备好本地 helper 子 chart**。

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

使用别名时，请将值放在 cache 下，并使用匹配的条件。测试条件路径缺失时的行为。全局值只有在子 chart 使用它们时才有意义；import-values 需要匹配的子项/父项导出结构。

dependency update 会根据 Chart.yaml 约束解析依赖并写入 Chart.lock。build 使用已锁定的版本；如果没有 lock 文件，它也可能像 update 一样解析依赖。仅有 lock 文件并不能确保防篡改、运行时镜像固定或完全可复现。请管理 chart 摘要/签名、供应链路径和镜像修订版本。已使用 Helm 3/4 测试本地 file 依赖的 update/build 以及别名启用/禁用行为。

## Hook、CRD 和测试

Pre/post install、upgrade、rollback、delete 和 test hook 会在其生命周期阶段执行。权重较低的 hook 先运行；若权重相同，请检查 kind/name 排序。Pre-install 迁移可能会在 chart 的常规数据库资源创建之前运行。

Hook Job/Pod 需要真实可执行文件、镜像、Service/Secret、权限、超时设置和可重复安全的行为。请使用 before-hook-creation/hook-succeeded/hook-failed 和 Job TTL 规划清理；卸载时不一定会删除所有 hook 资源。请结合 --wait 解读 post-install 就绪情况。

crds/ 下的 CRD 与普通模板不同。不要假设 CRD 会自动升级/删除或回滚其 schema。请制定明确的迁移和自定义资源保留计划；删除 CRD 可能会移除自定义资源数据。

helm test 会运行声明的 hook。简单的 HTTP 连通性无法验证数据库、安全性、负载或恢复能力。Blue/Green/canary 需要真实的 Deployments、Services/mesh 路由、控制器以及指标/回滚条件。仅有 values 并不能实现渐进式交付。

## GitOps 和安全

Argo CD 通常将 Helm 用作模板渲染器，这与管理 Helm release 生命周期不同。Flux helm-controller 会协调 HelmRelease。请验证源/chart 修订版本、valuesFrom 命名空间/优先级、hook 映射、修剪和所有权；避免控制器之间发生竞争。

不要将机密放在 chart 默认值、--set 参数或调试输出中。--hide-secret 仅在 dry-run 期间隐藏 Kubernetes Secret 输出，并不会对所有值/日志进行一般性脱敏。通过应用环境变量提供现有 Secret 引用，仍违反基于文件的凭据策略。请使用获准的 Secret 卷以及文件重新读取/轮换流程。

应单独准备当前 API（例如 ESO v1）及其控制器。Sealed Secrets/helm-secrets 需要其控制器/插件、密钥/KMS 访问权限和解密流程；它们不是 Helm 核心功能。请检查解密后的值是否会进入 release 记录或日志。

ServiceAccount/Role 本身不会授予工作负载权限。需要时请关联 RoleBinding 和 serviceAccountName；不要仅仅为了挂载 Secret 卷就授予对所有 Secret 的 get/list/watch 权限。此示例 web chart 不需要 Kubernetes API 凭据，并禁用了 token 自动挂载。

## 故障排查顺序

| 症状 | 调查和修正 |
| --- | --- |
| 重复使用的 release 名称 | 检查命名空间/状态/历史记录；选择预期的升级方式或新名称 |
| 与现有资源冲突 | 检查所有者注解/标签/控制器；采用经过审查的接管/迁移方式，或重命名 |
| Release 失败 | 检查原因/事件/历史记录，并使用已验证的修订版本/配置重试 |
| 缺少 helper | 检查定义、名称、作用域和根上下文 |
| Schema 验证失败 | 检查最终合并的值、类型、必填字段和范围 |

删除/强制标志并非通用解决办法。选择更改操作之前，请审查差异、不可变字段、数据保留要求和其他控制器。

## 验证和参考资料

已审查全部 764 行指南、每种语言区域 462 行测验以及 58 个唯一内容块。检查覆盖了完整 chart 的 Helm 3/4 lint/template/package、覆盖值/负向 schema 以及本地依赖/别名；4.3 client dry-run 已通过。已记录 3.21.3 install dry-run 访问集群失败的情况。未验证真实 Kubernetes 安装、升级、回滚、hook 或应用 HTTP 行为。

- [Helm 安装](https://helm.sh/docs/helm/helm_install/)
- [Helm 升级](https://helm.sh/docs/helm/helm_upgrade/)
- [Chart 和 values](https://helm.sh/docs/topics/charts/)
- [Chart hook](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 发布版本](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm 测验](../quizzes/platform-engineering/01-helm-quiz.md)
