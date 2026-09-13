# 시크릿 관리 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

이 퀴즈는 Kubernetes Secrets, AWS Secrets Manager, External Secrets Operator, 암호화에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes Secret의 기본 인코딩 방식은?

A. AES-256 암호화
B. Base64 인코딩
C. SHA-256 해시
D. RSA 암호화

<details>
<summary>정답 보기</summary>

**정답: B. Base64 인코딩**

**설명:**
직렬화된 Secret의 `data` 필드는 Base64를 사용하며 인코딩은 암호화가 아닙니다. API 권한·저장소·소비 앱을 보호해야 하며 외부 저장소가 이 요구를 없애지 않습니다.

</details>

### 2. EKS에서 etcd 암호화를 위해 사용하는 AWS 서비스는?

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>정답 보기</summary>

**정답: B. AWS KMS (Key Management Service)**

**설명:**
EKS 1.28 이상은 AWS 소유 키로 모든 Kubernetes API 데이터의 KMS envelope encryption을 기본 제공합니다. 고객 관리 키도 선택할 수 있습니다. 자체 관리 API 서버 구성과 다르며 EKS의 기본값이 평문이거나 고객 관리 키가 항상 필수라고 가정하지 않습니다.

</details>

### 3. External Secrets Operator에서 AWS Secrets Manager의 시크릿을 참조하는 리소스는?

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A와 B 또는 C와 B

<details>
<summary>정답 보기</summary>

**정답: D. A와 B 또는 C와 B**

**설명:**
SecretStore/ClusterSecretStore는 제공자 접근·identity를, ExternalSecret은 외부 값 선택·대상 Secret을 정의합니다. namespace store는 같은 네임스페이스 ServiceAccount를 참조하며 ClusterSecretStore에는 참조 네임스페이스와 사용 제한이 필요합니다.

</details>

### 4. Pod에서 Secret을 사용하는 방법이 아닌 것은?

A. 환경 변수로 주입
B. 볼륨으로 마운트
C. 이미지 풀 시크릿
D. ConfigMap으로 변환

<details>
<summary>정답 보기</summary>

**정답: D. ConfigMap으로 변환**

**설명:**
Pod는 키 참조·볼륨·imagePullSecrets로 Secret을 사용할 수 있습니다. ConfigMap은 별도 오브젝트이며 시크릿 보호 수단이 아닙니다. 실행 중인 컨테이너의 환경 변수는 갱신되지 않고 볼륨 갱신·앱 재로딩도 별도입니다.

</details>

<span id="_5-aws-secrets-manager에서-자동-로테이션을-구성하는-데-사용하는-aws-서비스는"></span>

### 5. Secrets Manager의 커스텀 Lambda 기반 로테이션 함수를 실행하는 AWS 서비스는?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>정답 보기</summary>

**정답: B. AWS Lambda**

**설명:**
커스텀 Lambda 기반 로테이션은 대상 변경 로직·권한·네트워크가 있는 Lambda 함수를 사용합니다. Secrets Manager에는 관리형 로테이션 통합도 있어 모든 교체에 운영자 관리 Lambda가 필요한 것은 아닙니다. ESO는 값을 동기화하며 DB 자격 증명 자체를 교체하지 않습니다.

</details>

### 6. Sealed Secrets의 주요 특징은?

A. etcd에서 암호화
B. Git에 안전하게 저장 가능
C. AWS 전용
D. 자동 로테이션 지원

<details>
<summary>정답 보기</summary>

**정답: B. Git에 안전하게 저장 가능**

**설명:**
Sealed Secrets는 신뢰한 인증서로 값을 암호화해 Git에 저장할 수 있게 합니다. 복구 담당자 등 적절한 개인키 보유자는 복호화할 수 있습니다. 메타데이터는 보이며 키 갱신이 앱 자격 증명을 교체하거나 과거 Git 암호문을 지우지 않습니다.

</details>

### 7. ExternalSecret의 refreshInterval 필드의 역할은?

A. 시크릿 만료 시간 설정
B. 외부 시크릿과 동기화 주기 설정
C. 캐시 유지 시간 설정
D. 재시도 간격 설정

<details>
<summary>정답 보기</summary>

**정답: B. 외부 시크릿과 동기화 주기 설정**

**설명:**
refreshPolicy가 Periodic이고 refreshInterval이 양수이면 ESO가 외부 값을 주기적으로 조정합니다. 완료 시한 보장이 아니며 OnChange/CreatedOnce와 다릅니다. 제공자 오류·재시도·앱 재로딩도 처리해야 합니다.

</details>

### 8. Kubernetes Secret의 immutable 필드를 true로 설정하면?

A. 시크릿 삭제 불가
B. 시크릿 데이터 수정 불가
C. 시크릿 읽기 불가
D. 시크릿 복사 불가

<details>
<summary>정답 보기</summary>

**정답: B. 시크릿 데이터 수정 불가**

**설명:**
immutable은 Secret 데이터 변경을 막고 다시 mutable로 되돌릴 수 없습니다. 메타데이터 변경과 삭제는 여전히 가능합니다. 사용 중인 의존성을 교체할 때는 새 이름의 Secret과 통제된 롤아웃을 우선 검토합니다.

</details>

### 9. CSI Secrets Store Driver의 주요 기능은?

A. Secret을 etcd에 암호화
B. 외부 시크릿을 볼륨으로 마운트
C. Secret 자동 생성
D. Secret 백업

<details>
<summary>정답 보기</summary>

**정답: B. 외부 시크릿을 볼륨으로 마운트**

**설명:**
Secrets Store CSI Driver와 지원 provider는 외부 값을 파일로 마운트합니다. Kubernetes Secret 동기화는 선택 기능이며 sync 기능과 실제 소비 마운트가 필요합니다. 교체·파일 전파·앱 재로딩은 별도이며 플랫폼 지원도 확인해야 합니다.

</details>

### 10. IRSA(IAM Roles for Service Accounts)와 함께 External Secrets를 사용할 때의 장점은?

A. 더 빠른 시크릿 접근
B. IAM 자격 증명을 Pod에 하드코딩할 필요 없음
C. 자동 시크릿 로테이션
D. 무료 사용

<details>
<summary>정답 보기</summary>

**정답: B. IAM 자격 증명을 Pod에 하드코딩할 필요 없음**

**설명:**
IRSA는 정확한 역할 신뢰 바인딩으로 projected identity token을 임시 AWS 자격 증명으로 교환합니다. 장기 액세스 키 하드코딩을 피하는 것이지 자격 증명을 없애는 것은 아닙니다. ESO의 Pod Identity는 컨트롤러 identity를 사용하며 serviceAccountRef 가장 방식에 대입할 수 없습니다.

</details>

### 11. Secret 데이터를 stringData로 정의할 때의 특징은?

A. 암호화됨
B. Base64 인코딩 불필요
C. 더 안전함
D. 압축됨

<details>
<summary>정답 보기</summary>

**정답: B. Base64 인코딩 불필요**

**설명:**
stringData는 수동 Base64 변환 없이 평문 입력을 받아 data로 병합합니다. 암호화나 추가 접근 보호가 아니며 권한 있는 API 조회자는 data 표현을 읽을 수 있습니다. 추적되는 YAML에 실제 값을 넣지 않고 server-side apply의 한계도 고려합니다.

</details>

### 12. 시크릿 관리 모범 사례가 아닌 것은?

A. etcd 암호화 활성화
B. RBAC로 Secret 접근 제한
C. 평문 자격 증명을 소스 코드에 커밋
D. 외부 시크릿 관리 시스템 사용

<details>
<summary>정답 보기</summary>

**정답: C. 평문 자격 증명을 소스 코드에 커밋**

**설명:**
평문 자격 증명·복호화 개인키를 커밋하지 않습니다. 검토한 recipient, 보호된 키, 복구 시험, 접근 제어를 갖춘 SOPS/SealedSecret 암호문과 값 없는 ESO 참조는 Git에 둘 수 있습니다. 어떤 도구도 단독으로 보안·규정 준수를 보장하지 않습니다.

</details>

---

[시크릿 관리 가이드](../../security/05-secrets-management.md)
