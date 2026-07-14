# Helm パッケージマネージャー

> **サポート対象バージョン**: Helm v3.x
> **最終更新**: February 23, 2026

## 概要

Helm は、Kubernetes アプリケーションをパッケージ化、デプロイ、管理するためのパッケージマネージャーです。Charts と呼ばれるパッケージ形式を使用することで、複雑なアプリケーションを簡単に定義、インストール、アップグレードできます。

## Helm の中核概念

### Helm v3 アーキテクチャ

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

Helm v3 では Tiller が削除されたため、クライアントは Kubernetes API と直接通信します。

### 中核コンポーネント

| コンポーネント | 説明 |
|-----------|-------------|
| Chart | Kubernetes resources を定義するパッケージ |
| Release | cluster にインストールされた Chart のインスタンス |
| Repository | Charts を共有するためのストレージ |
| Values | Chart templates に渡される設定値 |

## Chart 構造

### 基本的なディレクトリ構造

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

### Chart.yaml の例

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

## Helm コマンド

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

### Chart のインストールと管理

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

### Chart 開発

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

## Template の作成

### 基本構文

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

### 組み込みオブジェクト

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

### 条件分岐とループ

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

### Helper Templates

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

### 便利な関数

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

### 構造化された values.yaml

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

### 環境固有の Values ファイル

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

## Dependency 管理

### Chart Dependencies の定義

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

### Dependency コマンド

```bash
# Download dependencies
helm dependency update mychart/

# List dependencies
helm dependency list mychart/

# Build dependencies
helm dependency build mychart/
```

### Values を Subcharts に渡す

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

### Hook の種類

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

| Hook | 説明 |
|------|-------------|
| pre-install | templates がレンダリングされた後、resources が作成される前 |
| post-install | すべての resources が作成された後 |
| pre-delete | delete request の後、resources が削除される前 |
| post-delete | すべての resources が削除された後 |
| pre-upgrade | upgrade request の後、resources が更新される前 |
| post-upgrade | すべての resources が更新された後 |
| pre-rollback | rollback request の後、resources が復元される前 |
| post-rollback | すべての resources が復元された後 |
| test | helm test が実行されるとき |

### Hook 削除ポリシー

| ポリシー | 説明 |
|--------|-------------|
| before-hook-creation | 新しい hook を実行する前に前回の hook を削除する |
| hook-succeeded | hook が成功したときに削除する |
| hook-failed | hook が失敗したときに削除する |

## Testing

### Tests の定義

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

## GitOps 連携

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

## セキュリティのベストプラクティス

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

### RBAC Templates

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

## トラブルシューティング

### デバッグ

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

### よくあるエラー

| エラー | 原因 | 解決策 |
|-------|-------|----------|
| `Error: INSTALLATION FAILED: cannot re-use a name` | 同じ名前の Release が存在する | `helm uninstall` または別の名前を使用する |
| `Error: rendered manifests contain a resource that already exists` | Resource の競合 | 既存の resource を削除するか `--force` を使用する |
| `Error: UPGRADE FAILED: has no deployed releases` | 失敗した release state | `helm rollback` または `--force` を使用する |
| `Error: template: ... not defined` | 未定義の template | `_helpers.tpl` を確認する |

## 参考資料

- [Helm 公式ドキュメント](https://helm.sh/docs/)
- [Helm Chart ベストプラクティス](https://helm.sh/docs/chart_best_practices/)
- [Artifact Hub](https://artifacthub.io/)
- [Helm GitHub](https://github.com/helm/helm)
