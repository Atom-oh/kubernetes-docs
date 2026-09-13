# Helm 패키지 매니저 퀴즈

> **관련 문서**: [Helm](../../platform-engineering/01-helm.md)

Helm 3.21.3 / 4.3.0 검토 내용을 기준으로 원문의 20개 문제 주제를 유지했습니다.

## 객관식

### 1. Tiller 제거의 의미는 무엇인가요?

- A) chart 크기만 줄어듭니다.
- B) client가 자신의 Kubernetes credential과 RBAC를 사용합니다.
- C) 모든 chart가 안전해집니다.
- D) Kubernetes API가 필요 없어집니다.

<details>
<summary>정답 보기</summary>

**정답: B**

Helm 3부터 Tiller가 없습니다. 권한 경로와 구조가 단순해졌지만 위험한 manifest나 광범위한 client 권한은 여전히 검토해야 합니다.

</details>

### 2. values.yaml의 역할은 무엇인가요?

- A) chart metadata
- B) template이 사용하는 기본 설정 데이터
- C) release history
- D) 항상 실행되는 template

<details>
<summary>정답 보기</summary>

**정답: B**

template이 참조하는 값에만 효과가 있습니다. -f와 --set 계열로 override할 수 있으며 값 안의 template 문자열은 자동 평가되지 않습니다.

</details>

### 3. helm upgrade --install의 동작은 무엇인가요?

- A) 항상 새 release 생성
- B) 항상 삭제 후 재생성
- C) release가 없으면 설치하고 있으면 upgrade
- D) 모든 외부 작업까지 멱등성 보장

<details>
<summary>정답 보기</summary>

**정답: C**

설치와 upgrade 경로를 선택합니다. hooks, random 값, 외부 DB 변경까지 무조건 멱등적인 것은 아닙니다.

</details>

### 4. Release.Name은 무엇인가요?

- A) chart 이름
- B) cluster 이름
- C) 지정한 release 이름
- D) image tag

<details>
<summary>정답 보기</summary>

**정답: C**

`helm install demo ./chart`에서 이름은 demo입니다. chart 이름, appVersion, release revision과 구분합니다.

</details>

### 5. dependency의 condition은 무엇을 지정하나요?

- A) image tag
- B) dependency 사용 여부를 결정하는 values 경로
- C) registry password
- D) Pod 우선순위

<details>
<summary>정답 보기</summary>

**정답: B**

alias가 cache라면 cache.enabled 같은 실제 Boolean 경로를 사용합니다. 경로 누락 시 동작도 테스트하고 subchart에 전달되는 값과 구분합니다.

</details>

### 6. pre-upgrade hook은 언제 실행되나요?

- A) 삭제 후
- B) template 렌더링 후 일반 리소스 upgrade 전
- C) 항상 새 Pod가 Ready인 후
- D) rollback 후에만

<details>
<summary>정답 보기</summary>

**정답: B**

DB migration에 사용한다면 DB가 이미 존재하는지, 실패·재실행·이전 app과의 호환성을 검토합니다. rollback은 DB 변경을 자동 취소하지 않습니다.

</details>

### 7. 기본 helm template의 목적은 무엇인가요?

- A) cluster에 설치
- B) 로컬 manifest 렌더링
- C) 실제 webhook 검증
- D) 자동 rollback

<details>
<summary>정답 보기</summary>

**정답: B**

기본 로컬 렌더링은 admission, RBAC, image 실행이나 연결성을 증명하지 않습니다. server dry-run 등 다른 옵션의 접근 범위와 구분합니다.

</details>

### 8. _helpers.tpl의 역할은 무엇인가요?

- A) metadata 저장
- B) 재사용할 named template 정의
- C) values 기본값 저장
- D) release 이력 저장

<details>
<summary>정답 보기</summary>

**정답: B**

define으로 helper를 정의하고 include 등으로 사용합니다. 충돌을 피하도록 chart prefix를 붙이고 context를 명시적으로 전달합니다.

</details>

### 9. helm get values demo --all은 무엇을 출력하나요?

- A) 사용자 override만
- B) chart 기본값을 포함한 computed values
- C) manifest만
- D) history만

<details>
<summary>정답 보기</summary>

**정답: B**

대상 namespace와 release를 확인하세요. 값에 민감 정보가 포함될 수 있으므로 출력을 공개 로그에 남기지 않습니다.

</details>

### 10. toYaml과 nindent를 함께 사용하는 이유는 무엇인가요?

- A) 자동 암호화
- B) 구조화 값을 YAML로 바꾸고 새 줄·들여쓰기 적용
- C) JSON만 생성
- D) 숫자를 항상 문자열로 변환

<details>
<summary>정답 보기</summary>

**정답: B**

nindent는 indent와 달리 앞에 새 줄도 추가합니다. resources, labels 등을 실제 삽입 위치에 맞게 들여씁니다.

</details>

## 단답형

### 1. release 정보의 기본 저장 리소스는 무엇인가요?

<details>
<summary>정답 보기</summary>

release namespace의 Secret입니다. `sh.helm.release.v1.<release>.v<revision>` 형태이며 ConfigMap/SQL 같은 다른 backend도 가능합니다. Secret의 Base64는 암호화가 아닙니다.

</details>

### 2. dependency update가 만드는 lock 파일과 한계는 무엇인가요?

<details>
<summary>정답 보기</summary>

Chart.lock입니다. dependency build는 lock의 버전을 사용하지만 lock만으로 artifact 무결성, image 고정, 완전한 재현성을 보장하지 않습니다.

</details>

### 3. default 함수에서 주의할 empty 값은 무엇인가요?

<details>
<summary>정답 보기</summary>

false, 0, 빈 문자열·목록 등도 empty입니다. 명시한 false/0을 보존하려면 존재 여부와 타입을 검사합니다. default만으로 모든 nested lookup 오류가 방지되지는 않습니다.

</details>

### 4. hook 실행 순서를 지정하는 annotation은 무엇인가요?

<details>
<summary>정답 보기</summary>

`helm.sh/hook-weight`입니다. 같은 단계에서 작은 값부터 실행하며 음수도 가능합니다. 동률의 kind/name 순서와 Job 완료·timeout도 고려합니다.

</details>

### 5. NOTES.txt는 언제, 어떤 목적으로 사용하나요?

<details>
<summary>정답 보기</summary>

성공한 install/upgrade 후 안내를 표시하는 template이며 `helm get notes`로도 조회할 수 있습니다. 실제 URL·명령과 일치해야 하며 비밀을 출력하지 않습니다. 안내문이 app readiness를 증명하지는 않습니다.

</details>

## 실습형

### 1. 예제 chart를 web-server라는 이름으로 frontend에 설치하고 replica를 3으로 설정하세요.

<details>
<summary>정답 보기</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

저장소 root에서 실행할 명령입니다. 실제 설치에는 검토된 cluster context와 권한이 필요합니다. 이 검토에서는 설치 대신 lint/template/package만 실행했습니다.

</details>

### 2. LOG_LEVEL=debug, MAX_CONNECTIONS="100"을 env로 렌더링하면 어떤 형태인가요?

<details>
<summary>정답 보기</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

range로 map을 순회하고 value를 quote하면 아래처럼 모두 문자열이 됩니다. Go template에서 기본 ordered key를 가진 map은 key 순으로 순회합니다. 배열 순서와 혼동하지 마세요.

</details>

### 3. chart·release·appVersion label을 반환하는 helper를 작성하세요.

<details>
<summary>정답 보기</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

호출 위치에서 올바른 root context와 YAML 들여쓰기를 전달합니다. appVersion은 label용 metadata이며 image tag를 자동 변경하지 않습니다.

</details>

## 심화

### 1. Helm으로 Blue/Green·Canary를 구현할 때 필요한 구성은 무엇인가요?

<details>
<summary>정답 보기</summary>

Blue/Green은 두 Deployment의 label과 Service selector를 실제 template에서 연결하고 새 버전 검증 후 selector를 바꿉니다. values.yaml에 template 문자열을 적는 것만으로 평가되지 않습니다. Canary는 실제 mesh route/subset 또는 rollout controller, 가중치와 관찰 지표·중단 조건이 필요합니다. values 변경만으로 자동 분석·rollback이 생기지 않으며 DB 호환성과 전환 중 요청도 검토합니다.

</details>

### 2. chart 보안과 비밀 관리 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

values.schema.json으로 실제 지원 schema의 타입·필수값을 검사하고, 검토된 chart와 image revision을 고정합니다. ServiceAccount가 필요한 API 권한만 갖도록 RoleBinding까지 연결합니다. 단순 Secret volume mount를 위해 app에 모든 Secrets 조회 권한을 주지 않습니다. Secret 값은 chart 기본값·CLI 인자·debug log에 넣지 않고 승인된 파일 mount 및 회전·재읽기를 설계합니다. ESO v1, Sealed Secrets, helm-secrets는 각각 controller/plugin과 provider/key 권한이 필요합니다. 복호화한 값이 release 기록에 남는지도 검사합니다. 비특권 UID, capability 제거, 읽기 전용 root와 필요한 쓰기 volume을 함께 구성하고 실제 image 호환성을 검증합니다.

</details>
