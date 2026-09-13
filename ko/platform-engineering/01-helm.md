# Helm 패키지 매니저

> **검토일**: 2026년 9월 12일
> **실제 로컬 검증**: Helm 3.21.3 / Helm 4.3.0

Helm은 chart를 렌더링하고 Kubernetes 리소스와 release 이력을 관리합니다. chart version, appVersion, image tag/digest, release revision은 서로 다른 값입니다. Helm 4도 기존 apiVersion:v2 chart를 사용하지만 CLI·적용·대기 방식의 차이는 정확한 버전에서 확인해야 합니다.

## 핵심 개념과 권한

Helm 3부터 Tiller 없이 client가 자신의 Kubernetes credential/RBAC로 API를 사용합니다. chart repository/OCI registry와의 통신은 Kubernetes API 호출과 별도입니다. Tiller가 없다고 위험한 chart나 광범위한 권한이 안전해지는 것은 아닙니다.

기본 release storage는 release namespace의 Secret이며 ConfigMap/SQL 등 다른 backend를 구성할 수도 있습니다. release 기록에는 렌더링된 manifest와 values 등 민감 정보가 포함될 수 있습니다. Base64는 암호화가 아니며 release Secret을 읽는 권한도 제한해야 합니다.

## 완전한 로컬 chart 예제

저장소의 `examples/platform/helm/reviewed-app`에는 아래 8개 파일이 있습니다. Helm 3/4에서 lint와 렌더링 결과를 비교했고 패키징·values override·잘못된 replicaCount 거부를 검증했습니다. 실제 Kubernetes 설치나 컨테이너 실행은 이번 검토에서 하지 않았습니다. 운영 전에 image digest와 실제 namespace·장치·정책을 확인하세요.

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

모든 helper를 정의했고 Service와 container의 named port를 연결했습니다. securityContext는 manifest에 포함되며 resources·env 설정은 values에서 template으로 전달됩니다. values에만 옵션을 적고 template에서 참조하지 않으면 효과가 없습니다. 기본 예제는 DB·Ingress·autoscaler를 생성하지 않습니다.

### 로컬 검사

저장소 root에서 실행합니다. helm 명령이 가리키는 버전은 `helm version --short`로 확인합니다.

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

lint/template 성공은 admission, CEL, RBAC, image 실행, Service 연결이나 readiness의 검증이 아닙니다. native test hook도 클러스터에서 실제 실행해야 합니다. `helm template --api-versions`는 오프라인 capability를 알려줄 뿐 CRD를 설치하지 않습니다.

## 명령과 Helm 3/4 차이

| 목적 | 예시와 주의점 |
| --- | --- |
| Repository | `helm repo add`, `update`, `list`, `remove`, `search repo`; OCI registry는 별도 login/pull 경로 |
| 설치 | `helm install demo ./chart -n example --create-namespace`; namespace와 동일 release 존재 여부 확인 |
| 생성/업그레이드 | `helm upgrade --install`; hooks·random values·외부 상태까지 무조건 멱등적이라는 뜻은 아님 |
| 조회 | `helm list -n example`, `status`, `history`, `get values`, `get manifest`; 민감 값 출력 주의 |
| Computed values | `helm get values demo -n example --all`; chart 기본값을 포함 |
| 롤백 | `helm rollback demo REVISION -n example`; image tag가 아닌 release revision |
| 삭제 | `helm uninstall demo -n example`; PVC/CRD/hooks/외부 자원 lifecycle은 별도 확인 |

기존 stable repository는 보관용이며 새로운 기본 배포 경로로 소개하지 않습니다. 외부 chart와 database image는 현재 공급·라이선스·지원·보안 조건을 확인하고 chart version을 고정합니다. 과거 Bitnami PostgreSQL12/Redis17 의존성을 현재 예제의 기본값으로 유지하지 않았습니다.

### Dry run과 대기

Helm 4.3은 `--dry-run=client`와 `--dry-run=server`를 구분합니다. 이번 환경에서 4.3 client 모드는 클러스터 없이 통과했지만 3.21.3 install의 client dry run은 클러스터 접근을 시도하며 실패했습니다. 오프라인 템플릿 검사는 실제로 통과한 `helm template` 경로를 사용하세요. server 모드도 실제 cluster와 권한이 필요하며 모든 webhook·외부 side effect가 검증되는 것은 아닙니다.

Helm 4.3에서 `--wait`를 생략하면 기본 hookOnly, 지정하면 기본 watcher를 사용하며 legacy도 선택할 수 있습니다. `--rollback-on-failure`는 실패한 upgrade를 이전 성공 release로 되돌리는 옵션입니다. Helm 3의 `--atomic`과 동일한 이름이 아니며 해당 버전 도움말을 확인합니다. `--force-replace`와 `--force-conflicts`도 replacement와 server-side apply conflict를 다루는 서로 다른 기능입니다.

rollback은 DB migration·외부 API side effect·이미 발생한 데이터 삭제를 되돌리는 transaction이 아닙니다. timeout과 Pod readiness, job 완료, application SLO를 구분하세요.

## 템플릿과 values

`Chart`, `Release`, `Values`, `Capabilities`는 context 객체입니다. range/with 내부에서는 점(.) context가 바뀌므로 root가 필요할 때 `$`를 사용합니다. `.Capabilities.APIVersions.Has`는 주어진 discovery/capability 정보이며 모든 운영 호환성을 보장하지 않습니다.

`include`는 named template 결과를 string으로 반환하므로 `nindent`와 조합할 수 있습니다. `nindent`는 새 줄도 추가합니다. helper 이름은 subchart와 충돌하지 않도록 chart prefix를 사용하고 selector는 release 업그레이드 시 불필요하게 바꾸지 않습니다.

`default`와 `coalesce`의 empty에는 false,0,빈 문자열·목록 등이 포함됩니다. 명시한 false/0을 보존해야 한다면 존재 여부와 타입을 따로 검사합니다. 부모 map이 없는 nested lookup의 오류를 모든 default가 자동 방지하지는 않습니다.

values.yaml은 기본적으로 데이터이며 내부의 <code v-pre>{{ .Values... }}</code>가 자동으로 다시 렌더링되지 않습니다. 필요한 경우 chart 작성자가 `tpl`을 명시적으로 사용하지만, 평가 가능한 template 권한과 입력 신뢰를 검토해야 합니다. 이전 subchart storageClass와 Blue/Green selector 예제의 literal template 문자열은 자동 연결이 아니었습니다.

여러 `-f` 파일과 같은 계열의 override는 오른쪽 값이 우선하며 map과 list의 merge/교체 동작을 확인합니다. dev/staging/prod는 별도 파일로 저장하세요. 한 YAML 문서에 중복 key를 나열하는 것은 환경별 파일을 만드는 것과 다릅니다. 숫자처럼 보이는 문자열에는 `--set-string`, 구조화 값에는 해당 버전의 `--set-json` 등을 사용합니다.

`--reuse-values`, `--reset-values`, `--reset-then-reuse-values`는 이전 release와 새 chart 기본값을 합치는 방식이 다릅니다. 변경 전에 computed values와 렌더링 diff를 검토하고 암묵적 default에 의존하지 않습니다.

## 의존성 관리

Chart.yaml의 dependencies는 chart 이름·버전·repository와 선택적인 alias/condition을 선언합니다. 아래는 **로컬 helper subchart가 준비된 경우**의 fragment입니다.

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

alias를 사용하면 values도 cache 아래로 전달하며 condition도 일치시킵니다. condition 경로가 존재하지 않는 경우의 기본 동작까지 테스트해야 합니다. global 값은 subchart가 해당 값을 실제 참조할 때만 효과가 있습니다. import-values는 child/parent export 구조가 맞아야 합니다.

dependency update는 Chart.yaml의 버전 제약을 해석하고 Chart.lock을 작성합니다. build는 lock의 버전을 사용하며 lock이 없으면 update와 유사하게 해석할 수 있습니다. lock만으로 변조 방지·runtime image 고정·완전한 재현성이 보장되지는 않습니다. chart artifact digest/서명, 공급 경로와 image revision도 관리합니다. 검토에서는 로컬 file dependency의 update/build와 alias condition on/off를 Helm 3/4에서 실행했습니다.

## Hooks, CRDs와 테스트

pre/post install·upgrade·rollback·delete와 test hook은 특정 lifecycle 단계에 실행됩니다. 같은 단계에서는 낮은 weight가 먼저 실행되고 동률의 kind/name 순서도 검토합니다. pre-install DB migration은 일반 chart의 DB가 아직 생성되지 않았을 수 있으므로 의존성을 확인해야 합니다.

hook Job/Pod는 실제 executable·image·Service·Secret과 권한, timeout·재실행의 멱등성을 갖춰야 합니다. before-hook-creation/hook-succeeded/hook-failed와 Job TTL로 cleanup을 설계하며 uninstall이 모든 hook 자원을 정리한다고 가정하지 않습니다. post-install 의미도 --wait 설정에 따라 준비 상태와 구분합니다.

crds/ 아래 CRD는 일반 template과 lifecycle이 다릅니다. 자동 upgrade/delete나 rollback으로 CRD schema가 원복된다고 가정하지 말고 별도 migration·CR 보존 계획을 사용하세요. CRD를 삭제하면 해당 custom resource 데이터에 영향을 줄 수 있습니다.

helm test는 정의한 test hook을 실행합니다. 단순 HTTP 연결 성공은 DB, 보안, load·복구를 검증하지 않습니다. Blue/Green이나 canary를 구현하려면 실제 Deployment·Service/mesh route와 controller·metric/rollback 조건을 함께 준비해야 합니다. Helm values만으로 점진적 배포가 실행되지는 않습니다.

## GitOps와 보안

Argo CD는 보통 Helm을 template renderer로 사용하며 Helm release lifecycle을 직접 소유하는 방식과 다릅니다. Flux helm-controller는 HelmRelease를 reconcile합니다. Git/source chart version, valuesFrom namespace와 precedence, hook mapping·prune·reconciliation 주체를 확인하고 두 controller가 같은 자원을 경쟁 관리하지 않게 합니다.

비밀은 chart 기본값이나 --set 인자, debug 출력에 넣지 않습니다. --hide-secret은 dry-run의 Kubernetes Secret 출력 범위이며 모든 log나 values에 대한 일반 마스킹을 보장하지 않습니다. 기존 Secret 참조도 app의 환경 변수로 전달하면 파일 credential 정책을 충족하지 않습니다. 승인된 Secret volume과 파일 재읽기/회전 경로를 사용하세요.

ESO v1 등 현재 API와 controller를 별도로 준비해야 합니다. Sealed Secrets와 helm-secrets는 선택한 controller/plugin·key/KMS 접근과 복호화 과정이 필요하며 Helm core 기능이 아닙니다. 복호화한 values가 최종 release 기록이나 log에 남는지도 검사합니다.

ServiceAccount/Role만 정의해서 권한이 연결되지는 않습니다. 필요한 경우 RoleBinding과 workload serviceAccountName을 연결하고, 단순 secret volume mount를 위해 app에 모든 Secrets get/list/watch 권한을 주지 않습니다. 예제 web chart는 Kubernetes API 권한이 필요하지 않아 token 자동 mount를 끕니다.

## 문제 해결 순서

| 증상 | 확인과 수정 |
| --- | --- |
| 이름 재사용 | namespace와 release 상태/history 확인 후 의도한 upgrade 또는 새 이름 선택 |
| 기존 자원 충돌 | owner annotation/label과 관리 주체 확인; 승인된 adoption/migration 또는 이름 변경 |
| 실패 release | 실패 원인·events·history를 확인하고 검증된 revision/설정으로 재시도 |
| helper 누락 | helper 정의·이름·scope와 root context 확인 |
| schema 실패 | values 타입·required·범위와 실제 최종 병합값 확인 |

기존 자원 삭제나 --force를 보편적 해결책으로 권하지 않습니다. 실제 변경 diff, immutable field, 데이터 보존과 다른 controller 영향을 검토한 뒤 필요한 조치를 선택합니다.

## 검증 범위와 참고 자료

원문 764줄·퀴즈 462줄씩과 58개 고유 block을 읽었습니다. 완전한 chart의 Helm 3/4 lint/template/package, values override·negative schema, 로컬 dependency/alias를 검사했고 4.3 client dry run이 통과했습니다. 3.21.3 install dry run의 cluster access 실패도 기록했습니다. 실제 Kubernetes install/upgrade/rollback/hooks나 app HTTP 실행을 검증한 것은 아닙니다.

- [Helm install](https://helm.sh/docs/helm/helm_install/)
- [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Charts and values](https://helm.sh/docs/topics/charts/)
- [Chart hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 release](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm 퀴즈](../quizzes/platform-engineering/01-helm-quiz.md)
