# Kyverno를 사용한 정책 관리 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

검토한 Kyverno 1.19.1 CEL 정책을 기준으로 합니다. 예제는 로컬 fixture이며 실제 cluster나 destructive cleanup을 실행하지 않았습니다.

## 퀴즈 문제

### 1. Kyverno는 무엇인가요?

- A) Admission과 별도로 구성한 background/lifecycle controller를 가진 Kubernetes 정책 엔진.
- B) 취약점 스캐너만을 의미한다.
- C) API server 인증을 대체한다.
- D) Service mesh dataplane이다.

<details>
<summary>정답 보기</summary>

**정답: A) Admission과 별도로 구성한 background/lifecycle controller를 가진 Kubernetes 정책 엔진.**

정책 범위에 따라 validation·mutation·generation·image verification·deletion을 수행합니다. 현재 v1 정책은 YAML/JSON 안에서 CEL을 사용하며 기존 ClusterPolicy pattern·JMESPath와는 다른 문법입니다. Kubernetes-native 형식이 표현식 학습을 없애지는 않습니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_2-kyverno에서-지원하는-정책-유형이-아닌-것은-무엇인가요"></span>

### 2. 정책 작업의 차이에 대한 올바른 설명은?

- A) 모든 정책은 admission에서만 실행되고 다른 객체를 바꾸지 않는다.
- B) Audit은 generation과 deletion도 읽기 전용으로 바꾼다.
- C) 모든 GET/list 요청을 admission webhook이 가로챈다.
- D) Validation·mutation·generation·scheduled deletion은 controller·설정·권한이 서로 다르다.

<details>
<summary>정답 보기</summary>

**정답: D) Validation·mutation·generation·scheduled deletion은 controller·설정·권한이 서로 다르다.**

Kubernetes 인증(OIDC·ServiceAccount token 등)과 인가(RBAC)는 admission policy와 별개이며 Authenticate는 Kyverno policy action이 아닙니다. DeletingPolicy는 schedule과 conditions를 사용하며 ClusterPolicy rule의 cleanup.ttl이 해당 API가 아닙니다. 별도 validation이 Audit이어도 mutation·generation·deletion은 리소스를 변경할 수 있습니다. 명시한 실습 범위·RBAC·복구 계획이 필요합니다. 다음 선택적 deletion 정의는 schema 이해용이며 적용하지 않았고 24시간 age 조건을 구현하지도 않습니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: DeletingPolicy
metadata:
  name: cleanup-lab-completed-pods
spec:
  schedule: 0 1 * * *
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      scope: Namespaced
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: policy-lab
  conditions:
  - name: explicitly-approved-completed
    expression: object.metadata.?labels['training.example.com/disposable'].orValue('') == 'true' && object.?status.phase.orValue('')
      in ['Succeeded', 'Failed']
```

</details>

### 3. 현재 ValidatingPolicy의 validationActions: [Audit]과 [Deny]는 어떻게 다른가요?

- A) 둘 다 항상 위반을 거부한다.
- B) Audit은 매칭 위반을 허용하며 보고하고, Deny는 해당 admission을 거부한다.
- C) Audit은 기존 위반 객체를 삭제한다.
- D) Deny는 자동으로 리소스를 수정한다.

<details>
<summary>정답 보기</summary>

**정답: B) Audit은 매칭 위반을 허용하며 보고하고, Deny는 해당 admission을 거부한다.**

Webhook failurePolicy는 평가/통신 실패를 다루는 별도 설정입니다. 로컬 CLI fail 결과는 위반의 기록이지 실제 Audit 정책이 요청을 막았다는 증거가 아닙니다. 레거시 API의 Enforce/Audit failure action은 필드가 다르므로 명시적으로 이전합니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-container-limits
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, has(c.resources) && has(c.resources.limits) && ['cpu', 'memory'].all(k, k in c.resources.limits
      && string(c.resources.limits[k]) != ''))
    message: Normal and init containers need nonempty CPU and memory limits.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([])
```

</details>

<span id="_4-kyverno에서-정책을-적용할-리소스를-선택하는-데-사용되는-필드는-무엇인가요"></span>

### 4. CEL ValidatingPolicy의 적용 리소스 범위는 어떻게 선택하나요?

- A) 최상위 target 문자열 하나면 충분하다.
- B) matchConstraints와 선택적 matchConditions에서 kind·operation·namespace·request 정보 가용성을 확인한다.
- C) 모든 정책은 모든 Kubernetes 리소스와 자동 매칭된다.
- D) metadata.name만으로 모든 범위를 선택한다.

<details>
<summary>정답 보기</summary>

**정답: B) matchConstraints와 선택적 matchConditions에서 kind·operation·namespace·request 정보 가용성을 확인한다.**

Classic ClusterPolicy의 rule match/exclude와 현재 CEL 필드 구조는 다릅니다. Resource/user 조건의 AND/OR 의미를 실제 표현식으로 확인합니다. Admission의 user/role 정보가 background scan에도 항상 있는 것은 아닙니다. Namespace label selector는 그 label을 바꿀 수 있는 주체의 권한과도 연결됩니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_5-kyverno에서-정책-위반-시-자동으로-리소스를-수정하는-정책-유형은-무엇인가요"></span>

### 5. 다음 resource-default mutation이 기존 값을 보존하는 이유는?

- A) 모든 container를 동일한 limit으로 덮어쓴다.
- B) CREATE에서 일반 container의 requests/limits가 모두 없을 때만 채우며 기존 전체·부분 설정을 보존한다.
- C) 첫 번째 container 값을 나머지 모두에게 복사한다.
- D) Kyverno 표현식 안에서 Helm if/hasKey를 사용한다.

<details>
<summary>정답 보기</summary>

**정답: B) CREATE에서 일반 container의 requests/limits가 모두 없을 때만 채우며 기존 전체·부분 설정을 보존한다.**

실제 CLI의 변형 출력과 기존 전체·부분 설정 입력을 비교하여 값이 그대로임을 확인했습니다. 부분 필드는 별도 검토하며 기존 작은 limit보다 큰 request를 만들지 않습니다. ApplyConfiguration과 JSONPatch 의미는 다르고 JSONPatch에는 parent path가 필요합니다. 독립 정책 실행 순서는 보장되지 않습니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: default-unset-resources
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        Object{spec: Object.spec{containers: object.spec.containers.map(c,
          (!has(c.resources) || ((!has(c.resources.requests) || c.resources.requests.size() == 0) &&
            (!has(c.resources.limits) || c.resources.limits.size() == 0)))
          ? Object.spec.containers{name: c.name, resources: Object.spec.containers.resources{
              requests: {"cpu": "250m", "memory": "256Mi"},
              limits: {"cpu": "500m", "memory": "512Mi"}
            }}
          : Object.spec.containers{name: c.name}
        )}}
```

</details>

### 6. GeneratingPolicy는 언제 유용한가요?

- A) 매칭한 trigger에서 필요한 권한으로 명시한 downstream 리소스를 생성할 때.
- B) 삭제된 모든 리소스를 자동 백업할 때.
- C) Namespace 생성과 동시에 원자적으로 네트워크 격리를 보장할 때.
- D) Background controller의 RBAC를 우회할 때.

<details>
<summary>정답 보기</summary>

**정답: A) 매칭한 trigger에서 필요한 권한으로 명시한 downstream 리소스를 생성할 때.**

다음 Deployment 예제는 참여 조건과 desired replicas 2 이상을 요구하고 spec.selector 전체를 복사합니다. Generation은 비동기일 수 있습니다. Synchronization·data/clone source·generate-existing·orphaning에 따라 update/deletion이 달라집니다. 승인된 source/target 경계 없이 모든 새 namespace에 registry Secret을 복제하지 않습니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-pdb
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - deployments
  matchConditions:
  - name: approved-deployment
    expression: object.metadata.namespace == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true' && object.spec.?replicas.orValue(1) >= 2
  generate:
  - expression: |-
      generator.Apply(object.metadata.namespace, [{
        "apiVersion": dyn("policy/v1"), "kind": dyn("PodDisruptionBudget"),
        "metadata": dyn({"name": object.metadata.name + "-pdb", "namespace": object.metadata.namespace}),
        "spec": dyn({"minAvailable": 1, "selector": object.spec.selector})
      }])
```

</details>

<span id="_7-kyverno에서-컨테이너-이미지-서명을-검증하는-정책-유형은-무엇인가요"></span>

### 7. 현재 Kyverno에서 이미지 서명·attestation을 검증하는 유형은?

- A) ResourceQuota.
- B) ImageValidatingPolicy.
- C) ServiceMonitor.
- D) LimitRange.

<details>
<summary>정답 보기</summary>

**정답: B) ImageValidatingPolicy.**

레거시 ClusterPolicy verifyImages rule과 새 manifest kind를 구분합니다. 이미지 보안 문서의 지원되는 Cosign 또는 Notary/Notation trust 경로, 정확한 signer/issuer/key와 registry 접근을 구성합니다. 임의 GPG/Docker Content Trust 자료를 그대로 대입하지 않습니다. 서명 검증은 취약점 스캔이나 자동 registry allowlist가 아닙니다. Digest mutation 설정은 image reference를 바꿀 수 있으며 이 장에서는 실제 registry/signature 작업을 실행하지 않았습니다.

[이미지 보안 문서](../../security/07-image-security.md)

</details>

<span id="_8-kyverno-정책에서-background-false-설정의-의미는-무엇인가요"></span>

### 8. Background validation scan 비활성화의 의미는?

- A) 해당 설정의 주기적 기존 리소스 검사는 꺼지지만 매칭되는 admission update는 여전히 검사할 수 있다.
- B) 기존 리소스는 admission에서 영구 면제된다.
- C) 모든 Kyverno controller가 중지된다.
- D) 기존 정책 위반 객체를 삭제한다.

<details>
<summary>정답 보기</summary>

**정답: A) 해당 설정의 주기적 기존 리소스 검사는 꺼지지만 매칭되는 admission update는 여전히 검사할 수 있다.**

현재 유형은 spec.evaluation.background.enabled, classic ClusterPolicy는 background를 사용했습니다. Mutate-existing·generation·cleanup 전체를 제어하는 switch가 아닙니다. Background reporting은 이미 저장된 객체를 복구·거부·삭제하지 않습니다. Admission operation과 match 조건은 update에 여전히 적용됩니다.

</details>

### 9. 올바른 PolicyReport 표현은?

- A) resource/status 필드와 결과에 관계없는 summary 수를 사용한다.
- B) resources/result entry를 사용하고 summary가 해당 결과 수와 일치한다.
- C) 항상 문자열 timestamp.created를 사용한다.
- D) ClusterPolicyReport는 모든 namespace 결과를 임의로 합친 뜻이다.

<details>
<summary>정답 보기</summary>

**정답: B) resources/result entry를 사용하고 summary가 해당 결과 수와 일치한다.**

기본 chart profile은 Policy WG report를 사용합니다. PolicyReport는 namespaced, ClusterPolicyReport는 cluster-scoped resource를 다룹니다. 다음은 실제 수집 증거가 아닌 합성 schema 예시입니다. Timestamp를 넣으면 정수 seconds/nanos를 사용합니다. 다른 backend는 별도로 확인합니다.

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: example-report
  namespace: policy-lab
summary:
  pass: 1
  fail: 1
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: good
    namespace: policy-lab
  result: pass
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: missing-label
    namespace: policy-lab
  result: fail
  message: A nonempty team label is required.
```

</details>

<span id="_10-kyverno에서-정책을-테스트하는-데-사용할-수-있는-명령줄-도구는-무엇인가요"></span>

### 10. Kyverno 정책을 로컬에서 테스트하는 올바른 방법은?

- A) kyverno apply --cluster로 모든 policy를 설치한다.
- B) Test manifest directory에 kyverno test를 사용하거나 로컬 resource 파일에 kyverno apply를 사용한다.
- C) 존재하지 않는 일반 kyverno validate 명령을 실행한다.
- D) Helm render 성공으로 정책 동작과 RBAC가 입증된다.

<details>
<summary>정답 보기</summary>

**정답: B) Test manifest directory에 kyverno test를 사용하거나 로컬 resource 파일에 kyverno apply를 사용한다.**

본문은 정상 입력과 예상 위반 입력이 있는 policy-lab-tests를 제공합니다. --require-tests로 빈 test folder를 성공 처리하지 않습니다. Apply는 평가용이고 --cluster도 선택한 cluster를 읽어 평가하며 설치 명령이 아닙니다. --output은 변형/생성 객체를 쓸 경로입니다. 지원되는 helper용 create 하위 명령은 있으나 create disallow-latest-tag 같은 명령을 만들지 않습니다.

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[본문으로 돌아가기](../../security/01-kyverno-policy-management.md)
