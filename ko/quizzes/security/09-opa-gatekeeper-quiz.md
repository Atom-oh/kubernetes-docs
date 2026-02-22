# OPA Gatekeeper 퀴즈

다음 질문들을 통해 OPA Gatekeeper와 Rego 정책 언어에 대한 이해도를 점검해보세요.

---

## 문제

### 1. OPA Gatekeeper에서 정책을 작성하는 데 사용되는 언어는?

- A) YAML
- B) JSON
- C) Rego
- D) HCL

<details>
<summary>정답 보기</summary>

**정답: C) Rego**

**설명:**
OPA(Open Policy Agent)는 Rego라는 선언적 정책 언어를 사용합니다. Rego는 JSON/YAML 데이터를 쿼리하고 정책 결정을 내리는 데 최적화되어 있습니다.

```rego
package kubernetes.admission

violation[{"msg": msg}] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}
```

Kyverno와 달리 새로운 언어를 배워야 하지만, 더 복잡한 정책 로직을 표현할 수 있습니다.

</details>

---

### 2. Gatekeeper에서 재사용 가능한 정책 템플릿을 정의하는 CRD는?

- A) Policy
- B) ConstraintTemplate
- C) PolicyTemplate
- D) GatekeeperPolicy

<details>
<summary>정답 보기</summary>

**정답: B) ConstraintTemplate**

**설명:**
ConstraintTemplate은 Rego 정책 로직과 파라미터 스키마를 정의합니다:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg}] {
            # Rego 정책 로직
        }
```

ConstraintTemplate을 기반으로 Constraint를 생성하여 실제 정책을 적용합니다.

</details>

---

### 3. Gatekeeper Constraint의 enforcementAction 필드에서 지원하지 않는 값은?

- A) deny
- B) dryrun
- C) warn
- D) audit

<details>
<summary>정답 보기</summary>

**정답: D) audit**

**설명:**
Gatekeeper의 enforcementAction 지원 값:
- **deny**: 정책 위반 시 요청 거부
- **dryrun**: 위반을 기록하지만 요청은 허용
- **warn**: 경고 메시지 표시, 요청은 허용

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels
spec:
  enforcementAction: deny  # 또는 dryrun, warn
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

audit은 enforcementAction이 아니라 Gatekeeper의 백그라운드 감사 기능입니다.

</details>

---

### 4. Rego에서 배열의 모든 요소를 순회하는 구문은?

- A) for item in array
- B) array.forEach(item)
- C) item := array[_]
- D) loop array as item

<details>
<summary>정답 보기</summary>

**정답: C) item := array[_]**

**설명:**
Rego에서 `[_]`는 배열의 모든 인덱스를 의미합니다:

```rego
# 모든 컨테이너 순회
container := input.request.object.spec.containers[_]

# 모든 레이블 키 순회
label := input.request.object.metadata.labels[_]

# 특정 인덱스
first_container := input.request.object.spec.containers[0]

# 인덱스와 값 모두 필요할 때
some i
container := input.request.object.spec.containers[i]
```

이 구문은 Rego의 핵심 패턴으로, 규칙 내에서 여러 값을 평가할 때 사용됩니다.

</details>

---

### 5. Gatekeeper에서 기존 클러스터 리소스의 정책 준수 여부를 확인하는 기능은?

- A) Validation
- B) Mutation
- C) Audit
- D) Generation

<details>
<summary>정답 보기</summary>

**정답: C) Audit**

**설명:**
Gatekeeper Audit 기능:
- 주기적으로 기존 리소스 검사
- Constraint status에 위반 사항 기록
- 새 리소스뿐만 아니라 기존 리소스도 검증

```bash
# Constraint의 위반 사항 확인
kubectl describe k8srequiredlabels require-labels

# Status 섹션에서 위반 확인:
# Status:
#   Audit Timestamp: 2026-02-21T10:00:00Z
#   Total Violations: 3
#   Violations:
#     - Kind: Pod
#       Name: nginx-without-labels
#       Namespace: default
```

이를 통해 정책 적용 전 영향을 파악할 수 있습니다.

</details>

---

### 6. Gatekeeper v3.10+에서 지원하는 리소스 자동 수정 기능의 CRD는?

- A) MutatingPolicy
- B) Assign / AssignMetadata
- C) ModifyResource
- D) ResourceMutator

<details>
<summary>정답 보기</summary>

**정답: B) Assign / AssignMetadata**

**설명:**
Gatekeeper의 Mutation CRD:
- **AssignMetadata**: 메타데이터(레이블, 어노테이션) 추가
- **Assign**: spec 필드 등 일반 필드 수정
- **ModifySet**: 배열에 값 추가/제거

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: AssignMetadata
metadata:
  name: add-owner-label
spec:
  match:
    scope: Namespaced
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  location: "metadata.labels.owner"
  parameters:
    assign:
      value: "platform-team"
```

Kyverno의 mutate와 유사한 기능입니다.

</details>

---

### 7. Rego에서 두 집합의 차이를 계산하는 연산자는?

- A) difference()
- B) subtract()
- C) - (마이너스)
- D) diff()

<details>
<summary>정답 보기</summary>

**정답: C) - (마이너스)**

**설명:**
Rego의 집합 연산:

```rego
# 필요한 레이블과 존재하는 레이블 비교
required := {"app", "env", "team"}
provided := {"app", "team"}

# 차집합: 없는 레이블 찾기
missing := required - provided
# 결과: {"env"}

# 교집합
common := required & provided
# 결과: {"app", "team"}

# 합집합
all := required | provided
```

이 연산은 필수 레이블 검증 등에 자주 사용됩니다.

</details>

---

### 8. Gatekeeper에서 다른 네임스페이스의 리소스를 참조하기 위해 필요한 설정은?

- A) CrossNamespacePolicy
- B) Config의 sync.syncOnly
- C) GlobalConstraint
- D) NamespaceSelector

<details>
<summary>정답 보기</summary>

**정답: B) Config의 sync.syncOnly**

**설명:**
Gatekeeper가 외부 데이터를 참조하려면 Config 리소스로 동기화 설정이 필요합니다:

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
      - group: ""
        version: "v1"
        kind: "Namespace"
      - group: "networking.k8s.io"
        version: "v1"
        kind: "Ingress"
```

동기화된 리소스는 Rego에서 `data.inventory`로 접근할 수 있습니다:
```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

---

### 9. Gatekeeper 정책 테스트를 위한 공식 CLI 도구는?

- A) opa test
- B) gatekeeper-cli
- C) gator
- D) conftest

<details>
<summary>정답 보기</summary>

**정답: C) gator**

**설명:**
Gator는 Gatekeeper 정책을 로컬에서 테스트하는 공식 CLI 도구입니다:

```bash
# 설치
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# 정책 검증
gator verify ./policies/

# 테스트 스위트 실행
gator test ./tests/
```

테스트 스위트 예시:
```yaml
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
metadata:
  name: required-labels-test
tests:
  - name: "Pod without labels should fail"
    template: ../templates/k8srequiredlabels.yaml
    constraint: ../constraints/require-labels.yaml
    cases:
      - name: pod-without-labels
        object: fixtures/pod-no-labels.yaml
        assertions:
          - violations: yes
```

</details>

---

### 10. Gatekeeper와 Kyverno 비교 시 Gatekeeper의 장점은?

- A) 더 낮은 학습 곡선
- B) YAML 네이티브 정책
- C) 리소스 생성(Generate) 기능
- D) 복잡한 정책 로직 표현력

<details>
<summary>정답 보기</summary>

**정답: D) 복잡한 정책 로직 표현력**

**설명:**
Gatekeeper(OPA) vs Kyverno 비교:

| 특성 | Gatekeeper | Kyverno |
|------|------------|---------|
| 정책 언어 | Rego | YAML |
| 학습 곡선 | 높음 | 낮음 |
| 복잡한 로직 | 매우 유연 | 제한적 |
| 리소스 생성 | 미지원 | 지원 |
| 외부 데이터 | OPA 번들 지원 | API Call |

Gatekeeper는 Rego의 유연성 덕분에:
- 복잡한 조건 조합
- 재귀적 데이터 구조 처리
- 고급 집합 연산
- 외부 데이터 통합

등이 더 쉽습니다.

</details>

---

### 11. Rego에서 violation 규칙이 여러 개 정의되어 있을 때 평가 방식은?

- A) 첫 번째 규칙만 평가
- B) 모든 규칙을 OR로 평가
- C) 모든 규칙을 AND로 평가
- D) 랜덤하게 하나 선택

<details>
<summary>정답 보기</summary>

**정답: B) 모든 규칙을 OR로 평가**

**설명:**
Rego에서 같은 이름의 규칙이 여러 개 있으면 OR로 평가됩니다:

```rego
# 규칙 1: privileged 컨테이너 검사
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers not allowed"
}

# 규칙 2: root 실행 검사
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := "Running as root not allowed"
}

# 둘 중 하나라도 위반하면 violation 발생
```

각 violation 규칙의 결과는 집합에 추가되며, 하나 이상의 위반이 있으면 전체 정책이 실패합니다.

</details>

---

### 12. Gatekeeper에서 Constraint가 특정 네임스페이스에만 적용되도록 설정하는 필드는?

- A) spec.targetNamespaces
- B) spec.match.namespaces
- C) spec.scope.namespaces
- D) spec.selector.namespaces

<details>
<summary>정답 보기</summary>

**정답: B) spec.match.namespaces**

**설명:**
Constraint의 match 섹션에서 적용 범위를 지정합니다:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-prod
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
      - staging
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
    namespaceSelector:
      matchLabels:
        environment: production
```

- `namespaces`: 포함할 네임스페이스 목록
- `excludedNamespaces`: 제외할 네임스페이스 목록
- `namespaceSelector`: 레이블 기반 선택

</details>

---

## 점수 계산

각 문제당 1점으로 계산합니다.

| 점수 | 평가 |
|------|------|
| 11-12 | 우수 - OPA Gatekeeper 전문가 수준 |
| 8-10 | 양호 - 기본 개념 이해, Rego 심화 학습 필요 |
| 5-7 | 보통 - 추가 학습 권장 |
| 0-4 | 기초 학습 필요 |

---

## 관련 문서

- [OPA Gatekeeper](../security/09-opa-gatekeeper.md)
- [Kyverno 정책 관리](../security/01-kyverno-policy-management.md)
- [Pod Security Standards](../security/03-pod-security-standards.md)
