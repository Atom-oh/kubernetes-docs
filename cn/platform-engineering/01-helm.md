# Helm 包管理器

> **支持版本**: Helm v3.x
> **最后更新**: February 23, 2026

## 概述

Helm 是用于打包、部署和管理 Kubernetes 应用的包管理器。通过使用一种称为 Charts 的包格式，你可以轻松定义、安装和升级复杂应用。

## Helm 核心概念

### Helm v3 架构

```
┌─────────────────────────────────────────────────────────┐
│                      Helm Client                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   helm CLI  │  │  Chart SDK  │  │  Repository API │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
└─────────┼────────────────┼──────────────────┼───────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                  Kubernetes API Server                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Release Secrets (Storage)               ││
│  │         sh.helm.release.v1.<name>.v<ver>            ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

在 Helm v3 中，Tiller 已被移除，因此客户端会直接与 Kubernetes API 通信。

### 核心组件

| 组件 | 描述 |
|-----------|-------------|
| Chart | 定义 Kubernetes 资源的包 |
| Release | 安装在集群中的 Chart 实例 |
| Repository | 用于共享 Charts 的存储 |
| Values | 传递给 Chart 模板的配置值 |

## Chart 结构

### 基本目录结构

```
mychart/
├── Chart.yaml          # Chart metadata
├── Chart.lock          # Dependency lock file
├── values.yaml         # Default configuration values
├── values.schema.json  # Values schema (optional)
├── charts/             # Dependency Charts
├── crds/               # Custom Resource Definitions
├── templates/          # Kubernetes manifest templates
│   ├── NOTES.txt       # Post-installation notes
│   ├── _helpers.tpl    # Template helper functions
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── ...
└── .helmignore         # Files to exclude from packaging
```

### Chart.yaml 示例

```yaml
apiVersion: v2
name: myapp
description: My Application Helm Chart
type: application
version: 1.0.0
appVersion: "2.0.0"
kubeVersion: ">=1.25.0"
keywords:
  - web
  - application
home: https://example.com
sources:
  - https://github.com/example/myapp
maintainers:
  - name: DevOps Team
    email: devops@example.com
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: "17.x.x"
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
```

## Helm 命令

### Repository 管理

```bash
# Add repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add stable https://charts.helm.sh/stable

# Update repositories
helm repo update

# List repositories
helm repo list

# Remove repository
helm repo remove stable

# Search for Charts
helm search repo nginx
helm search hub wordpress  # Search Artifact Hub
```

### Chart 安装和管理

```bash
# Install Chart
helm install my-release bitnami/nginx

# Specify namespace
helm install my-release bitnami/nginx -n production --create-namespace

# Use values file
helm install my-release bitnami/nginx -f custom-values.yaml

# Set values with --set
helm install my-release bitnami/nginx \
  --set replicaCount=3 \
  --set service.type=LoadBalancer

# Dry-run before installation
helm install my-release bitnami/nginx --dry-run --debug

# Upgrade
helm upgrade my-release bitnami/nginx --set replicaCount=5

# Install or upgrade (idempotent)
helm upgrade --install my-release bitnami/nginx

# Rollback
helm rollback my-release 1

# Uninstall
helm uninstall my-release
helm uninstall my-release --keep-history  # Keep history
```

### Release 管理

```bash
# List releases
helm list
helm list -n production
helm list --all-namespaces

# Release status
helm status my-release

# Release history
helm history my-release

# Get release values
helm get values my-release
helm get values my-release --all  # Include defaults

# Get release manifest
helm get manifest my-release
```

### Chart 开发

```bash
# Create new Chart
helm create mychart

# Lint Chart
helm lint mychart/

# Package Chart
helm package mychart/

# Render templates
helm template my-release mychart/
helm template my-release mychart/ -f values-prod.yaml

# Dependency management
helm dependency list mychart/
helm dependency update mychart/
helm dependency build mychart/
```

## 模板编写

### 基本语法

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "mychart.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
          {{- if .Values.resources }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- end }}
```

### 内置对象

```yaml
# Chart object
{{ .Chart.Name }}        # Chart name
{{ .Chart.Version }}     # Chart version
{{ .Chart.AppVersion }}  # App version

# Release object
{{ .Release.Name }}       # Release name
{{ .Release.Namespace }}  # Namespace
{{ .Release.IsUpgrade }}  # Is upgrade
{{ .Release.IsInstall }}  # Is install
{{ .Release.Revision }}   # Revision number

# Values object
{{ .Values.key }}         # Values from values.yaml

# Capabilities object
{{ .Capabilities.KubeVersion }}           # K8s version
{{ .Capabilities.APIVersions.Has "v1" }}  # Check API version
```

### 条件和循环

```yaml
# Conditionals
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "mychart.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
```

### Helper 模板

```yaml
# templates/_helpers.tpl
{{/*
Expand the name of the chart.
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### 常用函数

```yaml
# Default value
{{ .Values.image.tag | default "latest" }}

# Quoting
{{ .Values.name | quote }}        # "value"
{{ .Values.port | squote }}       # 'value'

# Indentation
{{ toYaml .Values.resources | nindent 12 }}

# Coalesce
{{ coalesce .Values.custom.name .Values.default.name "fallback" }}

# String manipulation
{{ .Values.name | upper }}        # UPPERCASE
{{ .Values.name | lower }}        # lowercase
{{ .Values.name | title }}        # Title Case
{{ .Values.name | trim }}         # Remove whitespace
{{ .Values.name | trunc 63 }}     # Truncate string

# Encoding
{{ .Values.secret | b64enc }}     # Base64 encode
{{ .Values.data | b64dec }}       # Base64 decode

# Lists and Dictionaries
{{ list "a" "b" "c" }}
{{ dict "key1" "value1" "key2" "value2" }}
{{ .Values.list | first }}
{{ .Values.list | last }}
{{ .Values.list | uniq }}

# Conditional checks
{{ if empty .Values.name }}
{{ if not (empty .Values.name) }}
{{ if and .Values.a .Values.b }}
{{ if or .Values.a .Values.b }}
```

## Values 管理

### 结构化 values.yaml

```yaml
# values.yaml
replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: ""

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}
podSecurityContext: {}

securityContext:
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls: []

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 100
  targetCPUUtilizationPercentage: 80

nodeSelector: {}
tolerations: []
affinity: {}

# Subchart settings
postgresql:
  enabled: true
  auth:
    postgresPassword: "secret"
    database: "myapp"

redis:
  enabled: false
```

### 特定环境 Values 文件

```yaml
# values-dev.yaml
replicaCount: 1
image:
  tag: "dev-latest"
resources:
  limits:
    cpu: 100m
    memory: 128Mi

# values-staging.yaml
replicaCount: 2
image:
  tag: "staging-latest"
resources:
  limits:
    cpu: 250m
    memory: 256Mi

# values-prod.yaml
replicaCount: 3
image:
  tag: "v1.0.0"
resources:
  limits:
    cpu: 500m
    memory: 512Mi
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
```

```bash
# Environment-specific deployment
helm upgrade --install myapp ./mychart -f values-prod.yaml -n production
```

## 依赖管理

### 定义 Chart 依赖

```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: "12.1.0"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
    tags:
      - database
  - name: redis
    version: "17.0.0"
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
    alias: cache
  - name: common
    version: "2.0.0"
    repository: https://charts.bitnami.com/bitnami
    import-values:
      - child: image
        parent: global.image
```

### 依赖命令

```bash
# Download dependencies
helm dependency update mychart/

# List dependencies
helm dependency list mychart/

# Build dependencies
helm dependency build mychart/
```

### 向 Subcharts 传递 Values

```yaml
# values.yaml
global:
  storageClass: "gp3"

postgresql:
  enabled: true
  primary:
    persistence:
      storageClass: "{{ .Values.global.storageClass }}"
  auth:
    postgresPassword: "secret"
```

## Hooks

### Hook 类型

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: "{{ .Release.Name }}-db-migrate"
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["./migrate.sh"]
      restartPolicy: Never
```

| Hook | 描述 |
|------|-------------|
| pre-install | 模板渲染后、资源创建前 |
| post-install | 所有资源创建后 |
| pre-delete | 删除请求后、资源删除前 |
| post-delete | 所有资源删除后 |
| pre-upgrade | 升级请求后、资源更新前 |
| post-upgrade | 所有资源更新后 |
| pre-rollback | 回滚请求后、资源恢复前 |
| post-rollback | 所有资源恢复后 |
| test | 执行 helm test 时 |

### Hook 删除策略

| 策略 | 描述 |
|--------|-------------|
| before-hook-creation | 运行新 hook 前删除之前的 hook |
| hook-succeeded | hook 成功时删除 |
| hook-failed | hook 失败时删除 |

## 测试

### 定义测试

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "mychart.fullname" . }}-test-connection"
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
spec:
  containers:
    - name: wget
      image: busybox
      command: ['wget']
      args: ['{{ include "mychart.fullname" . }}:{{ .Values.service.port }}']
  restartPolicy: Never
```

```bash
# Run tests
helm test my-release
helm test my-release --logs  # Show logs
```

## GitOps 集成

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/helm-charts
    targetRevision: HEAD
    path: charts/myapp
    helm:
      valueFiles:
        - values-prod.yaml
      parameters:
        - name: image.tag
          value: v1.2.3
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Flux HelmRelease

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: myapp
  namespace: production
spec:
  interval: 5m
  chart:
    spec:
      chart: myapp
      version: "1.x"
      sourceRef:
        kind: HelmRepository
        name: my-charts
        namespace: flux-system
  values:
    replicaCount: 3
    image:
      tag: v1.2.3
  valuesFrom:
    - kind: ConfigMap
      name: myapp-values
```

## 安全最佳实践

### Secret 管理

```yaml
# Reference external secrets
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Values.existingSecret | default (include "mychart.fullname" .) }}
              key: password
```

### RBAC 模板

```yaml
# templates/serviceaccount.yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "mychart.serviceAccountName" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}

# templates/role.yaml
{{- if .Values.rbac.create -}}
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ include "mychart.fullname" . }}
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
{{- end }}
```

## 故障排查

### 调试

```bash
# Check template rendering
helm template my-release ./mychart --debug

# Server validation with dry-run
helm install my-release ./mychart --dry-run --debug

# Check release status
helm status my-release

# Get release manifest
helm get manifest my-release

# Get release values
helm get values my-release --all
```

### 常见错误

| 错误 | 原因 | 解决方案 |
|-------|-------|----------|
| `Error: INSTALLATION FAILED: cannot re-use a name` | 已存在同名 Release | `helm uninstall` 或使用不同名称 |
| `Error: rendered manifests contain a resource that already exists` | 资源冲突 | 删除现有资源或使用 `--force` |
| `Error: UPGRADE FAILED: has no deployed releases` | Release 处于失败状态 | `helm rollback` 或使用 `--force` |
| `Error: template: ... not defined` | 未定义模板 | 检查 `_helpers.tpl` |

## 参考资料

- [Helm 官方文档](https://helm.sh/docs/)
- [Helm Chart 最佳实践](https://helm.sh/docs/chart_best_practices/)
- [Artifact Hub](https://artifacthub.io/)
- [Helm GitHub](https://github.com/helm/helm)
