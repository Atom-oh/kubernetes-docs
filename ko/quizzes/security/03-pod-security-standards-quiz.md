# Pod Security Standards 퀴즈

이 퀴즈는 Pod Security Standards(PSS), Pod Security Admission(PSA), 보안 프로파일에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Pod Security Standards(PSS)의 세 가지 보안 수준이 아닌 것은?

A. Privileged
B. Baseline
C. Hardened
D. Restricted

<details>
<summary>정답 보기</summary>

**정답: C. Hardened**

**설명:**
Pod Security Standards는 세 가지 보안 수준을 정의합니다:
- **Privileged**: 무제한, 최대 권한 허용
- **Baseline**: 알려진 권한 상승 방지, 최소한의 제한
- **Restricted**: 강화된 보안, Pod 강화 모범 사례 적용

Hardened는 PSS의 공식 보안 수준이 아닙니다.

</details>

### 2. Pod Security Admission(PSA)의 적용 모드 중 정책 위반 시 Pod 생성을 차단하는 모드는?

A. audit
B. warn
C. enforce
D. deny

<details>
<summary>정답 보기</summary>

**정답: C. enforce**

**설명:**
PSA는 세 가지 적용 모드를 제공합니다:
- **enforce**: 정책 위반 시 Pod 생성 거부
- **audit**: 위반 사항을 감사 로그에 기록하지만 허용
- **warn**: 사용자에게 경고 메시지 표시하지만 허용

deny는 유효한 PSA 모드가 아닙니다.

</details>

### 3. 네임스페이스에 PSS를 적용하기 위해 사용하는 레이블 형식은?

A. security.kubernetes.io/enforce: restricted
B. pod-security.kubernetes.io/enforce: restricted
C. pss.kubernetes.io/level: restricted
D. admission.kubernetes.io/policy: restricted

<details>
<summary>정답 보기</summary>

**정답: B. pod-security.kubernetes.io/enforce: restricted**

**설명:**
PSA는 네임스페이스 레이블을 통해 구성됩니다:
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

레이블 형식: `pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. Baseline 보안 수준에서 허용되지 않는 것은?

A. hostNetwork: true
B. runAsNonRoot: false
C. allowPrivilegeEscalation: true
D. readOnlyRootFilesystem: false

<details>
<summary>정답 보기</summary>

**정답: A. hostNetwork: true**

**설명:**
Baseline 수준은 알려진 권한 상승을 방지합니다. 다음이 금지됩니다:
- hostNetwork, hostPID, hostIPC
- privileged 컨테이너
- 위험한 capabilities (NET_RAW 제외한 추가 불가)
- hostPath 볼륨 (특정 경로 제외)

runAsNonRoot, allowPrivilegeEscalation, readOnlyRootFilesystem은 Baseline에서 제한되지 않으며, Restricted 수준에서 강제됩니다.

</details>

### 5. Restricted 보안 수준의 요구사항이 아닌 것은?

A. runAsNonRoot: true
B. allowPrivilegeEscalation: false
C. readOnlyRootFilesystem: true
D. capabilities.drop: ["ALL"]

<details>
<summary>정답 보기</summary>

**정답: C. readOnlyRootFilesystem: true**

**설명:**
Restricted 수준은 다음을 요구합니다:
- runAsNonRoot: true (필수)
- allowPrivilegeEscalation: false (필수)
- capabilities.drop: ["ALL"] (필수)
- seccompProfile.type: RuntimeDefault 또는 Localhost (필수)

readOnlyRootFilesystem은 보안 모범 사례이지만 Restricted 수준의 필수 요구사항은 아닙니다.

</details>

### 6. PodSecurityPolicy(PSP)가 제거된 Kubernetes 버전은?

A. 1.21
B. 1.23
C. 1.25
D. 1.27

<details>
<summary>정답 보기</summary>

**정답: C. 1.25**

**설명:**
PSP 타임라인:
- Kubernetes 1.21: PSP 사용 중단(deprecated) 발표
- Kubernetes 1.22: PSA 알파 도입
- Kubernetes 1.23: PSA 베타
- Kubernetes 1.25: PSP 완전 제거, PSA GA

</details>

### 7. PSA에서 특정 버전의 PSS를 적용하는 레이블은?

A. pod-security.kubernetes.io/enforce-version: v1.28
B. pod-security.kubernetes.io/version: v1.28
C. pod-security.kubernetes.io/enforce-version: 1.28
D. pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>정답 보기</summary>

**정답: A. pod-security.kubernetes.io/enforce-version: v1.28**

**설명:**
버전 레이블 형식:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

버전 값은 `v1.XX` 형식 또는 `latest`를 사용합니다. 버전을 지정하면 해당 Kubernetes 버전의 PSS 정의를 사용합니다.

</details>

### 8. EKS에서 PSA를 활성화하는 방법은?

A. EKS 애드온 설치 필요
B. 기본적으로 활성화되어 있음
C. eksctl 명령어로 활성화
D. AWS 콘솔에서 설정

<details>
<summary>정답 보기</summary>

**정답: B. 기본적으로 활성화되어 있음**

**설명:**
Pod Security Admission은 Kubernetes 1.25+에서 기본적으로 활성화되어 있습니다. EKS 1.25 이상 버전에서는 추가 구성 없이 PSA를 사용할 수 있습니다. 네임스페이스에 적절한 레이블만 추가하면 됩니다.

</details>

### 9. PSA 예외를 구성하는 방법이 아닌 것은?

A. RuntimeClass 예외
B. 사용자 예외
C. 네임스페이스 예외
D. Pod 레이블 예외

<details>
<summary>정답 보기</summary>

**정답: D. Pod 레이블 예외**

**설명:**
PSA는 다음 예외 유형을 지원합니다:
- **usernames**: 특정 사용자에 대한 예외
- **runtimeClassNames**: 특정 RuntimeClass에 대한 예외
- **namespaces**: 특정 네임스페이스에 대한 예외

Pod 레이블 기반 예외는 PSA에서 지원되지 않습니다. 예외는 AdmissionConfiguration을 통해 구성됩니다.

</details>

### 10. Restricted 수준에서 허용되는 seccompProfile 타입은?

A. Unconfined
B. RuntimeDefault
C. Custom
D. Disabled

<details>
<summary>정답 보기</summary>

**정답: B. RuntimeDefault**

**설명:**
Restricted 수준에서 허용되는 seccompProfile 타입:
- **RuntimeDefault**: 컨테이너 런타임의 기본 프로파일
- **Localhost**: 노드에 정의된 커스텀 프로파일

Unconfined는 Restricted 수준에서 허용되지 않습니다. 이는 seccomp 필터링을 비활성화하여 보안 위험이 있습니다.

</details>

### 11. PSP에서 PSA로 마이그레이션할 때 권장되는 첫 번째 단계는?

A. PSP 즉시 삭제
B. 모든 네임스페이스에 enforce 모드 적용
C. audit/warn 모드로 시작하여 위반 사항 확인
D. 새 클러스터 생성

<details>
<summary>정답 보기</summary>

**정답: C. audit/warn 모드로 시작하여 위반 사항 확인**

**설명:**
PSA 마이그레이션 권장 단계:
1. **audit/warn 모드로 시작**: 위반 사항 파악
2. **워크로드 수정**: 위반 사항 해결
3. **enforce 모드로 전환**: 단계적 적용
4. **PSP 제거**: 마이그레이션 완료 후

즉시 enforce 모드를 적용하면 기존 워크로드가 중단될 수 있습니다.

</details>

### 12. 다음 중 Privileged 수준에서도 제한되는 것은?

A. hostNetwork 사용
B. privileged 컨테이너
C. 없음 (모든 것이 허용됨)
D. hostPath 볼륨

<details>
<summary>정답 보기</summary>

**정답: C. 없음 (모든 것이 허용됨)**

**설명:**
Privileged 수준은 완전히 무제한입니다:
- 모든 보안 컨텍스트 설정 허용
- hostNetwork, hostPID, hostIPC 허용
- privileged 컨테이너 허용
- 모든 capabilities 허용
- 모든 볼륨 타입 허용

이 수준은 시스템 및 인프라 워크로드(예: CNI, 스토리지 드라이버)에 사용됩니다.

</details>
