# Helm 패키지 매니저 퀴즈

> **관련 문서**: [Helm 패키지 매니저](../../package-management/01-helm.md)

## 객관식 문제

### 1. Helm v3에서 Tiller 컴포넌트가 제거된 주요 이유는 무엇입니까?

- A) 성능 향상을 위해
- B) 보안 강화와 아키텍처 단순화를 위해
- C) 차트 크기를 줄이기 위해
- D) Kubernetes 버전 호환성을 위해

<details>
<summary>정답 보기</summary>

**정답: B) 보안 강화와 아키텍처 단순화를 위해**

**설명:**
Helm v2의 Tiller는 클러스터 내에서 높은 권한으로 실행되어 보안 위험이 있었습니다. Helm v3에서는 Tiller를 제거하고 클라이언트가 직접 Kubernetes API와 통신하도록 변경하여 보안이 강화되고 아키텍처가 단순해졌습니다.

</details>

### 2. Helm Chart의 values.yaml 파일의 주요 목적은 무엇입니까?

- A) 차트의 메타데이터를 저장
- B) 템플릿에서 사용할 기본 구성 값을 정의
- C) Kubernetes 매니페스트를 직접 저장
- D) 차트의 의존성을 정의

<details>
<summary>정답 보기</summary>

**정답: B) 템플릿에서 사용할 기본 구성 값을 정의**

**설명:**
values.yaml 파일은 차트 템플릿에서 사용할 기본 구성 값을 정의합니다. 사용자는 이 값들을 --set 플래그나 -f 플래그로 재정의하여 다양한 환경에 맞게 배포를 커스터마이징할 수 있습니다.

</details>

### 3. `helm upgrade --install` 명령어의 동작은 무엇입니까?

- A) 항상 새로운 릴리스를 설치
- B) 항상 기존 릴리스를 업그레이드
- C) 릴리스가 없으면 설치하고, 있으면 업그레이드
- D) 릴리스를 삭제하고 재설치

<details>
<summary>정답 보기</summary>

**정답: C) 릴리스가 없으면 설치하고, 있으면 업그레이드**

**설명:**
`helm upgrade --install`은 멱등성(idempotent)을 제공하는 명령어입니다. 지정된 릴리스가 존재하지 않으면 새로 설치하고, 이미 존재하면 업그레이드합니다. CI/CD 파이프라인에서 유용하게 사용됩니다.

</details>

### 4. Helm 템플릿에서 `{{ .Release.Name }}`은 무엇을 참조합니까?

- A) 차트 이름
- B) Kubernetes 클러스터 이름
- C) 설치된 릴리스의 이름
- D) 네임스페이스 이름

<details>
<summary>정답 보기</summary>

**정답: C) 설치된 릴리스의 이름**

**설명:**
`.Release.Name`은 Helm의 내장 객체로, `helm install` 명령어에서 지정한 릴리스 이름을 참조합니다. 예를 들어 `helm install my-app chart/`에서 `.Release.Name`은 "my-app"이 됩니다.

</details>

### 5. Chart.yaml에서 `dependencies` 필드의 `condition` 속성의 역할은 무엇입니까?

- A) 의존성 차트의 버전을 지정
- B) 의존성 차트를 활성화/비활성화하는 values 경로를 지정
- C) 의존성 차트의 저장소 URL을 지정
- D) 의존성 차트의 우선순위를 지정

<details>
<summary>정답 보기</summary>

**정답: B) 의존성 차트를 활성화/비활성화하는 values 경로를 지정**

**설명:**
`condition` 속성은 values.yaml에서 의존성 차트를 활성화할지 결정하는 경로를 지정합니다. 예를 들어 `condition: postgresql.enabled`는 `postgresql.enabled` 값이 true일 때만 PostgreSQL 서브차트를 포함합니다.

</details>

### 6. Helm Hook 중 `pre-upgrade`는 언제 실행됩니까?

- A) 릴리스 삭제 전
- B) 업그레이드 요청 후, 리소스 업데이트 전
- C) 모든 리소스 생성 후
- D) 롤백 완료 후

<details>
<summary>정답 보기</summary>

**정답: B) 업그레이드 요청 후, 리소스 업데이트 전**

**설명:**
`pre-upgrade` Hook은 업그레이드 요청을 받은 후, 실제 리소스 업데이트가 시작되기 전에 실행됩니다. 데이터베이스 마이그레이션이나 백업 작업에 주로 사용됩니다.

</details>

### 7. `helm template` 명령어의 주요 용도는 무엇입니까?

- A) 차트를 클러스터에 배포
- B) 차트 템플릿을 로컬에서 렌더링하여 확인
- C) 차트의 의존성을 업데이트
- D) 릴리스를 롤백

<details>
<summary>정답 보기</summary>

**정답: B) 차트 템플릿을 로컬에서 렌더링하여 확인**

**설명:**
`helm template`은 차트 템플릿을 로컬에서 렌더링하여 생성될 Kubernetes 매니페스트를 미리 확인할 수 있게 합니다. 클러스터에 연결하지 않고도 템플릿 결과를 검증할 수 있습니다.

</details>

### 8. Helm에서 `_helpers.tpl` 파일의 역할은 무엇입니까?

- A) 차트 메타데이터 저장
- B) 재사용 가능한 템플릿 헬퍼 함수 정의
- C) 기본 values 값 저장
- D) 설치 후 안내 메시지 표시

<details>
<summary>정답 보기</summary>

**정답: B) 재사용 가능한 템플릿 헬퍼 함수 정의**

**설명:**
`_helpers.tpl` 파일은 여러 템플릿에서 공통으로 사용되는 헬퍼 함수(named templates)를 정의합니다. 차트 이름, 레이블, 셀렉터 등 반복적으로 사용되는 로직을 캡슐화합니다.

</details>

### 9. `helm get values my-release --all` 명령어는 무엇을 출력합니까?

- A) 사용자가 지정한 값만 출력
- B) 기본값을 포함한 모든 values 출력
- C) 릴리스의 매니페스트 출력
- D) 릴리스의 히스토리 출력

<details>
<summary>정답 보기</summary>

**정답: B) 기본값을 포함한 모든 values 출력**

**설명:**
`--all` 플래그를 사용하면 사용자가 재정의한 값뿐만 아니라 차트의 기본값(values.yaml)을 포함한 모든 computed values를 출력합니다.

</details>

### 10. Helm 차트에서 `toYaml` 함수와 `nindent`를 함께 사용하는 이유는 무엇입니까?

- A) YAML을 JSON으로 변환하기 위해
- B) 복잡한 값을 올바른 들여쓰기로 YAML에 삽입하기 위해
- C) 값을 Base64로 인코딩하기 위해
- D) 문자열을 따옴표로 감싸기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 복잡한 값을 올바른 들여쓰기로 YAML에 삽입하기 위해**

**설명:**
`toYaml`은 Go 객체를 YAML 문자열로 변환하고, `nindent`는 해당 문자열에 지정된 수의 공백으로 들여쓰기를 적용합니다. 이 조합은 resources, annotations 등 복잡한 구조를 템플릿에 올바르게 삽입할 때 필수적입니다.

</details>

## 단답형 문제

### 1. Helm v3에서 릴리스 정보가 저장되는 Kubernetes 리소스 유형은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: Secret**

**설명:**
Helm v3는 릴리스 정보를 릴리스가 배포된 네임스페이스 내의 Secret으로 저장합니다. Secret의 이름 형식은 `sh.helm.release.v1.<릴리스이름>.v<버전>`입니다.

</details>

### 2. `helm dependency update` 명령어가 생성하는 lock 파일의 이름은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: Chart.lock**

**설명:**
`helm dependency update`는 Chart.yaml의 dependencies를 해석하고 정확한 버전을 포함하는 Chart.lock 파일을 생성합니다. 이 파일은 재현 가능한 빌드를 보장합니다.

</details>

### 3. Helm 템플릿에서 값이 없을 때 기본값을 제공하는 함수는 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: default**

**설명:**
`default` 함수는 값이 비어있거나 정의되지 않은 경우 기본값을 제공합니다. 사용 예: `{{ .Values.image.tag | default .Chart.AppVersion }}`

</details>

### 4. Helm Hook의 실행 순서를 제어하는 어노테이션은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: helm.sh/hook-weight**

**설명:**
`helm.sh/hook-weight` 어노테이션은 동일한 Hook 유형 내에서 실행 순서를 결정합니다. 숫자가 낮을수록 먼저 실행되며, 음수 값도 사용 가능합니다.

</details>

### 5. Helm 차트의 NOTES.txt 파일은 언제 사용자에게 표시됩니까?

<details>
<summary>정답 보기</summary>

**정답: helm install 또는 helm upgrade 완료 후**

**설명:**
NOTES.txt는 설치나 업그레이드가 성공적으로 완료된 후 사용자에게 표시되는 안내 메시지입니다. 애플리케이션 접속 방법, 초기 설정 안내 등을 포함합니다.

</details>

## 실습 문제

### 1. 다음 요구사항을 충족하는 Helm 명령어를 작성하세요.

- bitnami/nginx 차트를 "web-server" 릴리스로 설치
- "frontend" 네임스페이스에 배포 (네임스페이스가 없으면 생성)
- replicaCount를 3으로 설정

<details>
<summary>정답 보기</summary>

```bash
helm install web-server bitnami/nginx \
  -n frontend --create-namespace \
  --set replicaCount=3
```

**설명:**
- `helm install web-server bitnami/nginx`: "web-server" 릴리스로 nginx 차트 설치
- `-n frontend`: frontend 네임스페이스 지정
- `--create-namespace`: 네임스페이스가 없으면 생성
- `--set`: 인라인으로 values 재정의

</details>

### 2. 다음 Helm 템플릿 스니펫의 출력을 예측하세요.

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
<summary>정답 보기</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

**설명:**
- `range` 함수가 `.Values.env` 맵을 반복
- `$key`는 맵의 키, `$value`는 맵의 값
- `quote` 함수가 값을 따옴표로 감쌈
- 맵은 알파벳 순으로 정렬됨

</details>

### 3. 다음 요구사항을 충족하는 `_helpers.tpl` 템플릿을 작성하세요.

- 이름: mychart.labels
- app.kubernetes.io/name: 차트 이름
- app.kubernetes.io/instance: 릴리스 이름
- app.kubernetes.io/version: 앱 버전

<details>
<summary>정답 보기</summary>

```yaml
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

**설명:**
- `define`으로 재사용 가능한 named template 정의
- `.Chart.Name`으로 차트 이름 참조
- `.Release.Name`으로 릴리스 이름 참조
- `.Chart.AppVersion`으로 앱 버전 참조 (quote로 문자열 보장)

</details>

## 심화 문제

### 1. Helm 차트의 Blue-Green 배포와 Canary 배포를 구현하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**Blue-Green 배포:**
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

**구현 전략:**
1. Blue와 Green 두 개의 Deployment 템플릿 생성
2. Service selector를 activeColor 값으로 전환
3. 배포 시 green.image.tag를 새 버전으로 설정
4. 검증 후 deployment.activeColor를 green으로 변경
5. 문제 발생 시 blue로 즉시 롤백

**Canary 배포 (Istio 활용):**
```yaml
# VirtualService로 트래픽 분배
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

**구현 전략:**
1. Stable과 Canary 두 개의 Deployment 생성
2. Istio VirtualService로 트래픽 비율 제어
3. 점진적으로 Canary 비율 증가 (10% -> 25% -> 50% -> 100%)
4. 메트릭 모니터링으로 자동 롤백 구현

</details>

### 2. Helm 차트의 보안 모범 사례를 설명하고, 시크릿 관리 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

**보안 모범 사례:**

1. **값 검증 (values.schema.json)**
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

2. **RBAC 최소 권한 원칙**
```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]  # 필요한 권한만 부여
```

3. **Pod Security Standards 적용**
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**시크릿 관리 전략:**

1. **외부 시크릿 매니저 통합 (AWS Secrets Manager)**
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

2. **Sealed Secrets 활용**
```bash
# 시크릿 암호화
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

3. **Helm Secrets 플러그인**
```bash
# 암호화된 values 파일 사용
helm secrets install myapp ./mychart -f secrets.yaml
```

</details>
