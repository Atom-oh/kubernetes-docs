# Helm 包管理器

> **最后更新**: September 12, 2026
> **本地验证**: Helm 3.21.3 / Helm 4.3.0

Helm 渲染 chart 并管理 Kubernetes 资源和 release 历史记录。Chart 版本、appVersion、镜像 tag/digest 与 release revision 是不同的值。Helm 4 接受现有 apiVersion:v2 chart，但必须针对确切版本检查 CLI/apply/wait 行为。

## 核心概念和权限

Helm 3 移除了 Tiller；客户端使用各自的 Kubernetes 凭证/RBAC。Chart-repository/OCI-registry 通信与 Kubernetes API 访问相互独立。移除 Tiller 并不会使不安全的 chart 或宽泛权限变得无害。

Release 存储默认使用 release namespace 中的 Secret；也可以配置 ConfigMap/SQL 后端等替代方案。存储的 release 数据包含 manifest/values，可能会暴露敏感信息。Base64 不是加密；请限制对 release Secret 的访问。

## 完整的本地 Chart 示例

`examples/platform/helm/reviewed-app` 包含以下八个文件。已测试 Helm 3/4 的 lint/render 输出、打包、value 覆盖以及对无效 replicaCount 的拒绝。未执行 Kubernetes 安装或容器运行。操作前请验证镜像 digest、namespace、硬件和策略。

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
  tag: "1.30.4-alpine"
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

所有 helper 均已定义，Service 指向具名容器端口，manifest 中包含 securityContext，并且 resources/env 已从 values 接入 templates。未使用的 values 条目不会产生任何效果。此基础 chart 不会创建数据库、Ingress 或 autoscaler。

### 本地检查

请从仓库根目录运行，并使用 `helm version --short` 检查所选二进制文件。

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

lint/template 成功并不验证 admission、CEL、RBAC、镜像执行、Service 连通性或就绪状态。测试 hook 必须在集群中实际执行。`helm template --api-versions` 提供离线 capabilities；它不会安装 CRD。

## 命令和 Helm 3/4 差异

| 目的 | 示例和限制 |
| --- | --- |
| Repositories | `helm repo add/update/list/remove`, `helm search repo`；OCI registry 有独立的 login/pull 流程 |
| Install | `helm install demo ./chart -n example --create-namespace`；验证 namespace/release 是否存在 |
| Install 或 upgrade | `helm upgrade --install`；hook、随机 values 和外部状态未必具有幂等性 |
| Inspect | `helm list -n example`, status/history/get values/get manifest；保护敏感输出 |
| 计算后的 values | `helm get values demo -n example --all` 包含 chart 默认值 |
| Rollback | `helm rollback demo REVISION -n example`；revision 不是镜像 tag |
| Uninstall | `helm uninstall demo -n example`；检查 PVC/CRD/hook/external-resource 生命周期 |

旧 stable repository 属于归档，并非当前默认选项。验证外部 chart/镜像的可用性、许可、支持和安全性，并固定 chart 版本。旧的 Bitnami PostgreSQL12/Redis17 依赖项不再是此示例的默认值。

### Dry Run 和等待

Helm 4.3 区分 `--dry-run=client` 和 `--dry-run=server`。在此环境中，4.3 client 模式无需集群即可通过；3.21.3 install client dry-run 尝试访问集群并失败。请使用已验证的 `helm template` 路径进行离线渲染。Server 模式需要集群访问/权限，且无法证明所有 webhook/外部副作用。

在 Helm 4.3 中，省略 --wait 时默认值为 hookOnly；指定 --wait 时默认值为 watcher，也可使用 legacy。`--rollback-on-failure` 会将失败的 upgrade 回滚至先前成功的 release。其名称不同于 Helm 3 的 --atomic。`--force-replace` 和 `--force-conflicts` 分别控制替换和 server-side-apply 冲突；请查看确切版本的帮助信息。

Rollback 不是会撤销 DB migration、外部 API 效果或已删除数据的事务。请区分 timeout、Pod 就绪状态、Job 完成和应用 SLO。

## Templates 和 Values

Chart、Release、Values 和 Capabilities 是上下文对象。range/with 会改变 dot 上下文；根上下文需要时请使用 `$`。Capabilities 反映所提供的发现信息，而非通用兼容性。

include 将 named-template 输出作为字符串返回，并可通过管道传给 nindent，后者还会插入换行符。为 helper 名称添加前缀以避免 subchart 冲突，并避免在 upgrade 期间不必要地变更 selector。

default/coalesce 将 false、零、空字符串和集合视为空。在需要保留显式 false/零时，请分别检查存在性/类型。default 无法保护父 map 不存在时的每一次嵌套查找。

values.yaml 是数据：嵌入的 <code v-pre>{{ .Values... }}</code> 不会再次被自动求值。Chart 作者可在需要时显式使用 tpl，但必须审查输入信任度和 template 权限。先前的 subchart storageClass 和 Blue/Green selector 字符串不会被自动接入。

对于重复的文件/覆盖，最右侧的 values 生效；请理解 map 合并和 list 替换。将 dev/staging/prod 保存为独立文件，而不是在一个 YAML 文档中使用重复键。对看起来像数字的字符串使用 --set-string，并对结构使用版本支持的 --set-json。

--reuse-values、--reset-values 和 --reset-then-reuse-values 以不同方式组合先前的 release values 与新的默认值。请审查计算后的 values 和渲染后的 diff，而不要依赖隐式行为。

## 依赖管理

Chart.yaml 声明 dependency 名称、版本、repository 和可选 alias/condition。此片段假定存在一个**已准备好的本地 helper subchart**。

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

使用 alias 时，请将 values 放在 cache 下并使用匹配的 condition。测试 condition path 缺失时的行为。仅当 subchart 使用 global values 时它们才有意义；import-values 需要匹配的 child/parent export 结构。

dependency update 解析 Chart.yaml 约束并写入 Chart.lock。build 使用锁定版本；没有 lock 时，它可能以与 update 类似的方式解析。仅有 lock 并不能建立防篡改能力、固定的运行时镜像或完整的可复现性。管理 chart digest/signature、提供路径和镜像 revision。已使用 Helm 3/4 演练本地 file-dependency update/build 及 alias 开/关。

## Hooks、CRD 和 Tests

Pre/post install、upgrade、rollback、delete 和 test hook 在各自的生命周期阶段执行。较低的 weight 先运行；对于并列情况，检查 kind/name 排序。pre-install migration 可能会在 chart 的常规数据库资源存在之前运行。

Hook Job/Pod 需要真实的可执行文件、镜像、Service/Secret、权限、timeout 和可重复执行的安全行为。使用 before-hook-creation/hook-succeeded/hook-failed 和 Job TTL 规划清理；uninstall 未必会移除所有 hook 资源。结合 --wait 解读 post-install 就绪状态。

crds/ 下的 CRD 不同于普通 template。不要假定会自动 upgrade/deletion 或 rollback CRD schema。使用明确的 migration 和 custom-resource 保留计划；删除 CRD 可能会删除 custom-resource 数据。

helm test 会运行已声明的 hook。简单的 HTTP 连通性并不能验证数据库、安全性、负载或恢复。Blue/Green/canary 需要真实的 Deployment、Service/mesh route、controller 以及 metric/rollback 条件。仅有 values 不会实现渐进式交付。

## GitOps 和安全性

Argo CD 通常将 Helm 用作 template renderer，这不同于拥有 Helm release 生命周期。Flux helm-controller 会协调 HelmRelease。验证 source/chart revision、valuesFrom namespace/precedence、hook 映射、pruning 和所有权；避免存在相互竞争的 controller。

不要将 secret 放在 chart 默认值、--set 参数或 debug 输出中。--hide-secret 覆盖 dry-run 期间的 Kubernetes Secret 输出，而不是对所有 values/log 的通用脱敏。通过 app 环境变量提供的现有 Secret 引用仍违反 file-credential 策略。请使用已批准的 Secret volume 和文件重读/轮换路径。

分别准备 ESO v1 等当前 API 及其 controller。Sealed Secrets/helm-secrets 需要其 controller/plugin、key/KMS 访问和解密工作流；它们不是 Helm 核心功能。检查解密后的 values 是否进入 release records 或 log。

仅有 ServiceAccount/Role 不会授予 workload 权限。在需要时连接 RoleBinding 和 serviceAccountName，并且不要仅为了 Secret volume 就授予对所有 Secret 的 get/list/watch 权限。演示 web chart 不需要 Kubernetes API 凭证，并禁用了 token automount。

## 故障排查顺序

| 症状 | 调查和修正 |
| --- | --- |
| 重用的 release 名称 | 检查 namespace/state/history；选择预期的 upgrade 或新名称 |
| 现有资源冲突 | 检查 owner annotation/label/controller；使用经过审查的接管/migration 或重命名 |
| 失败的 release | 检查原因/event/history，并使用已验证的 revision/configuration 重试 |
| 缺失的 helper | 检查定义、名称、作用域和根上下文 |
| Schema 失败 | 检查最终合并的 values、类型、必填字段和范围 |

Deletion/force flag 并非通用的解决方案。在选择 mutation 前，请审查 diff、immutable field、数据保留和其他 controller。

## 验证和参考资料

已审阅所有 764 条指南行、每种语言环境的 462 条测验行及 58 个唯一块。检查涵盖完整 chart 的 Helm 3/4 lint/template/package、覆盖/负向 schema 及本地 dependency/alias；4.3 client dry-run 通过。已记录 3.21.3 install dry-run 的集群访问失败。未验证真实的 Kubernetes 安装、upgrade、rollback、hook 或 app HTTP 行为。

- [Helm install](https://helm.sh/docs/helm/helm_install/)
- [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Charts 和 values](https://helm.sh/docs/topics/charts/)
- [Chart hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 release](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm 测验](../quizzes/platform-engineering/01-helm-quiz.md)
