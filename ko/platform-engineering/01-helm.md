# Helm 패키지 매니저

> **지원 버전**: Helm v3.x
> **마지막 업데이트**: 2026년 2월 23일

## 개요

Helm은 Kubernetes 애플리케이션을 패키징, 배포, 관리하기 위한 패키지 매니저입니다. Chart라는 패키지 형식을 사용하여 복잡한 애플리케이션을 쉽게 정의, 설치, 업그레이드할 수 있습니다.

## Helm 핵심 개념

### Helm v3 아키텍처

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
│  │              Release Secrets (저장소)                ││
│  │         sh.helm.release.v1.<name>.v<ver>            ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

Helm v3에서는 Tiller가 제거되어 클라이언트가 Kubernetes API와 직접 통신합니다.

### 핵심 구성 요소

| 구성 요소 | 설명 |
|----------|------|
| Chart | Kubernetes 리소스를 정의하는 패키지 |
| Release | 클러스터에 설치된 Chart 인스턴스 |
| Repository | Chart를 저장하고 공유하는 저장소 |
| Values | Chart 템플릿에 전달되는 구성 값 |

## Chart 구조

### 기본 디렉토리 구조

```
mychart/
├── Chart.yaml          # Chart 메타데이터
├── Chart.lock          # 의존성 lock 파일
├── values.yaml         # 기본 구성 값
├── values.schema.json  # values 스키마 (선택)
├── charts/             # 의존성 Chart
├── crds/               # Custom Resource Definitions
├── templates/          # Kubernetes 매니페스트 템플릿
│   ├── NOTES.txt       # 설치 후 안내 메시지
│   ├── _helpers.tpl    # 템플릿 헬퍼 함수
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── ...
└── .helmignore         # 패키징 제외 파일
```

### Chart.yaml 예시

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

## Helm 명령어

### 저장소 관리

```bash
# 저장소 추가
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add stable https://charts.helm.sh/stable

# 저장소 업데이트
helm repo update

# 저장소 목록
helm repo list

# 저장소 제거
helm repo remove stable

# Chart 검색
helm search repo nginx
helm search hub wordpress  # Artifact Hub 검색
```

### Chart 설치 및 관리

```bash
# Chart 설치
helm install my-release bitnami/nginx

# 네임스페이스 지정
helm install my-release bitnami/nginx -n production --create-namespace

# values 파일 사용
helm install my-release bitnami/nginx -f custom-values.yaml

# --set으로 값 지정
helm install my-release bitnami/nginx \
  --set replicaCount=3 \
  --set service.type=LoadBalancer

# 설치 전 dry-run
helm install my-release bitnami/nginx --dry-run --debug

# 업그레이드
helm upgrade my-release bitnami/nginx --set replicaCount=5

# 설치 또는 업그레이드 (멱등성)
helm upgrade --install my-release bitnami/nginx

# 롤백
helm rollback my-release 1

# 삭제
helm uninstall my-release
helm uninstall my-release --keep-history  # 히스토리 유지
```

### 릴리스 관리

```bash
# 릴리스 목록
helm list
helm list -n production
helm list --all-namespaces

# 릴리스 상태
helm status my-release

# 릴리스 히스토리
helm history my-release

# 릴리스 값 확인
helm get values my-release
helm get values my-release --all  # 기본값 포함

# 릴리스 매니페스트 확인
helm get manifest my-release
```

### Chart 개발

```bash
# 새 Chart 생성
helm create mychart

# Chart 린트
helm lint mychart/

# Chart 패키징
helm package mychart/

# 템플릿 렌더링
helm template my-release mychart/
helm template my-release mychart/ -f values-prod.yaml

# 의존성 관리
helm dependency list mychart/
helm dependency update mychart/
helm dependency build mychart/
```

## 템플릿 작성

### 기본 문법

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

### 내장 객체

```yaml
# Chart 객체
{{ .Chart.Name }}        # Chart 이름
{{ .Chart.Version }}     # Chart 버전
{{ .Chart.AppVersion }}  # 앱 버전

# Release 객체
{{ .Release.Name }}       # 릴리스 이름
{{ .Release.Namespace }}  # 네임스페이스
{{ .Release.IsUpgrade }}  # 업그레이드 여부
{{ .Release.IsInstall }}  # 설치 여부
{{ .Release.Revision }}   # 리비전 번호

# Values 객체
{{ .Values.key }}         # values.yaml의 값

# Capabilities 객체
{{ .Capabilities.KubeVersion }}           # K8s 버전
{{ .Capabilities.APIVersions.Has "v1" }}  # API 버전 확인
```

### 조건문과 반복문

```yaml
# 조건문
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

### 헬퍼 템플릿

```yaml
# templates/_helpers.tpl
{{/*
차트 이름 확장
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
전체 이름 생성
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
공통 레이블
*/}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
셀렉터 레이블
*/}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### 유용한 함수들

```yaml
# 기본값
{{ .Values.image.tag | default "latest" }}

# 따옴표
{{ .Values.name | quote }}        # "value"
{{ .Values.port | squote }}       # 'value'

# 들여쓰기
{{ toYaml .Values.resources | nindent 12 }}

# 조건부 기본값
{{ coalesce .Values.custom.name .Values.default.name "fallback" }}

# 문자열 처리
{{ .Values.name | upper }}        # 대문자
{{ .Values.name | lower }}        # 소문자
{{ .Values.name | title }}        # Title Case
{{ .Values.name | trim }}         # 공백 제거
{{ .Values.name | trunc 63 }}     # 문자열 자르기

# 인코딩
{{ .Values.secret | b64enc }}     # Base64 인코딩
{{ .Values.data | b64dec }}       # Base64 디코딩

# 리스트/딕셔너리
{{ list "a" "b" "c" }}
{{ dict "key1" "value1" "key2" "value2" }}
{{ .Values.list | first }}
{{ .Values.list | last }}
{{ .Values.list | uniq }}

# 조건 검사
{{ if empty .Values.name }}
{{ if not (empty .Values.name) }}
{{ if and .Values.a .Values.b }}
{{ if or .Values.a .Values.b }}
```

## Values 관리

### values.yaml 구조화

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

# 서브차트 설정
postgresql:
  enabled: true
  auth:
    postgresPassword: "secret"
    database: "myapp"

redis:
  enabled: false
```

### 환경별 Values 파일

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
# 환경별 배포
helm upgrade --install myapp ./mychart -f values-prod.yaml -n production
```

## 의존성 관리

### Chart 의존성 정의

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

### 의존성 명령어

```bash
# 의존성 다운로드
helm dependency update mychart/

# 의존성 목록 확인
helm dependency list mychart/

# 의존성 빌드
helm dependency build mychart/
```

### 서브차트 값 전달

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

### Hook 유형

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

| Hook | 설명 |
|------|------|
| pre-install | 템플릿 렌더링 후, 리소스 생성 전 |
| post-install | 모든 리소스 생성 후 |
| pre-delete | 삭제 요청 후, 리소스 삭제 전 |
| post-delete | 모든 리소스 삭제 후 |
| pre-upgrade | 업그레이드 요청 후, 리소스 업데이트 전 |
| post-upgrade | 모든 리소스 업데이트 후 |
| pre-rollback | 롤백 요청 후, 리소스 복원 전 |
| post-rollback | 모든 리소스 복원 후 |
| test | helm test 실행 시 |

### Hook 삭제 정책

| 정책 | 설명 |
|------|------|
| before-hook-creation | 새 Hook 실행 전 이전 Hook 삭제 |
| hook-succeeded | Hook 성공 시 삭제 |
| hook-failed | Hook 실패 시 삭제 |

## 테스트

### 테스트 정의

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
# 테스트 실행
helm test my-release
helm test my-release --logs  # 로그 출력
```

## GitOps 통합

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

## 보안 모범 사례

### 시크릿 관리

```yaml
# 외부 시크릿 참조
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

### RBAC 템플릿

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

## 문제 해결

### 디버깅

```bash
# 템플릿 렌더링 확인
helm template my-release ./mychart --debug

# dry-run으로 서버 검증
helm install my-release ./mychart --dry-run --debug

# 릴리스 상태 확인
helm status my-release

# 릴리스 매니페스트 확인
helm get manifest my-release

# 릴리스 값 확인
helm get values my-release --all
```

### 일반적인 오류

| 오류 | 원인 | 해결 방법 |
|------|------|----------|
| `Error: INSTALLATION FAILED: cannot re-use a name` | 같은 이름의 릴리스 존재 | `helm uninstall` 또는 다른 이름 사용 |
| `Error: rendered manifests contain a resource that already exists` | 리소스 충돌 | 기존 리소스 삭제 또는 `--force` 사용 |
| `Error: UPGRADE FAILED: has no deployed releases` | 실패한 릴리스 상태 | `helm rollback` 또는 `--force` 사용 |
| `Error: template: ... not defined` | 정의되지 않은 템플릿 | `_helpers.tpl` 확인 |

## 참고 자료

- [Helm 공식 문서](https://helm.sh/docs/)
- [Helm Chart 모범 사례](https://helm.sh/docs/chart_best_practices/)
- [Artifact Hub](https://artifacthub.io/)
- [Helm GitHub](https://github.com/helm/helm)
