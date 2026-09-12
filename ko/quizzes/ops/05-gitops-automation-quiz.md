# GitOps 자동화 퀴즈

> **관련 문서**: [GitOps 자동화](../../ops/05-gitops-automation.md)

## 객관식 문제

### 1. Atlantis의 주요 역할은 무엇인가요?

- A) Kubernetes 배포 자동화
- B) Pull Request 기반 Terraform 워크플로우 자동화
- C) 컨테이너 이미지 빌드
- D) 모니터링 대시보드 생성

<details>
<summary>정답 보기</summary>

**정답: B) Pull Request 기반 Terraform 워크플로우 자동화**

**설명:**
Atlantis는 GitHub/GitLab Pull Request에서 Terraform plan과 apply를 자동으로 실행하는 도구입니다. PR에 댓글로 `atlantis plan`, `atlantis apply` 명령을 입력하면 Atlantis가 해당 명령을 실행하고 결과를 PR에 댓글로 보여줍니다. 이를 통해 인프라 변경을 코드 리뷰 프로세스와 통합할 수 있습니다.

</details>

### 2. HCP Terraform의 Run Trigger 기능의 용도는 무엇인가요?

- A) 수동 실행만 허용
- B) 특정 워크스페이스 적용 완료 시 다른 워크스페이스 자동 실행
- C) 로그 트리거
- D) 알림 전송

<details>
<summary>정답 보기</summary>

**정답: B) 특정 워크스페이스 적용 완료 시 다른 워크스페이스 자동 실행**

**설명:**
Run Trigger는 상위 workspace의 성공한 apply 후 하위 run을 대기열에 넣습니다. 일반 auto_apply와 auto_apply_run_trigger는 별도 설정이며 trigger가 출력 값 전달이나 자동 승인을 대신하지 않습니다. 예를 들어, Network 워크스페이스 적용 후 Cluster 워크스페이스가 자동으로 실행되도록 설정하여 계층적 인프라 배포를 자동화할 수 있습니다.

</details>

### 3. FluxCD의 Image Automation Controller가 하는 일은 무엇인가요?

- A) 컨테이너 이미지 빌드
- B) 새 이미지 태그 감지 후 Git 저장소의 매니페스트 자동 업데이트
- C) 이미지 스캐닝
- D) 이미지 서명

<details>
<summary>정답 보기</summary>

**정답: B) 새 이미지 태그 감지 후 Git 저장소의 매니페스트 자동 업데이트**

**설명:**
Image-reflector-controller가 ImageRepository를 스캔하고 ImagePolicy를 평가합니다. 별도의 image-automation-controller가 선택 결과와 Setters marker를 사용합니다. 새 버전이 발견되면 ImageUpdateAutomation이 Git 저장소의 Kubernetes 매니페스트에서 이미지 태그를 자동으로 업데이트하고 커밋합니다.

</details>

### 4. ArgoCD와 FluxCD의 주요 차이점은 무엇인가요?

- A) ArgoCD만 Helm을 지원
- B) 둘 다 선언적 reconciliation을 사용하며 UI와 API/컨트롤러 구성 방식이 다름
- C) FluxCD만 멀티 클러스터 지원
- D) 차이점 없음

<details>
<summary>정답 보기</summary>

**정답: B) 둘 다 선언적 reconciliation을 사용하며 UI와 API/컨트롤러 구성 방식이 다름**

**설명:**
ArgoCD는 강력한 웹 UI를 제공하고 Application CRD로 배포를 관리합니다. FluxCD는 GitRepository, Kustomization 등 여러 CRD와 controller를 사용합니다. ArgoCD도 여러 컴포넌트로 구성됩니다. 어느 도구가 더 GitOps에 충실하거나 모든 환경에서 더 효율적이라고 단정할 수는 없습니다.

</details>

### 5. Atlantis atlantis.yaml 파일에서 autoplan의 역할은 무엇인가요?

- A) 자동으로 apply 실행
- B) PR 생성/업데이트 시 자동으로 terraform plan 실행
- C) 자동 롤백
- D) 자동 승인

<details>
<summary>정답 보기</summary>

**정답: B) PR 생성/업데이트 시 자동으로 terraform plan 실행**

**설명:**
atlantis.yaml의 autoplan 설정을 활성화하면 PR이 생성되거나 업데이트될 때 Atlantis가 자동으로 terraform plan을 실행합니다. when_modified로 특정 파일 변경 시에만 plan을 실행하도록 조건을 설정할 수도 있습니다.

</details>

### 6. IAM Identity Center를 ArgoCD와 연동하는 주요 이점은 무엇인가요?

- A) 빌드 속도 향상
- B) 중앙 집중식 사용자 인증 및 RBAC 관리
- C) 이미지 저장소 연결
- D) 네트워크 최적화

<details>
<summary>정답 보기</summary>

**정답: B) 중앙 집중식 사용자 인증 및 RBAC 관리**

**설명:**
IAM Identity Center(구 AWS SSO)를 ArgoCD와 연동하면 AWS 조직의 사용자/그룹을 ArgoCD 인증에 사용할 수 있습니다. 이 문서군은 공식 Identity Center 가이드의 SAML + Dex 경로를 사용합니다. 애플리케이션 할당과 실제 assertion 속성 전달은 다르며, 검증한 이메일 또는 지원되는 그룹 claim에 맞춰 ArgoCD RBAC를 따로 구성해야 합니다.

</details>

### 7. FluxCD의 GitRepository 리소스에서 interval 설정의 의미는 무엇인가요?

- A) 이미지 빌드 간격
- B) Git 저장소 변경 사항 폴링 주기
- C) 로그 수집 간격
- D) 헬스 체크 간격

<details>
<summary>정답 보기</summary>

**정답: B) Git 저장소 변경 사항 폴링 주기**

**설명:**
GitRepository의 interval은 FluxCD가 Git 저장소의 변경 사항을 확인하는 주기입니다. 예를 들어 `interval: 1m`이면 1분마다 저장소를 확인합니다. 변경이 감지되면 연결된 Kustomization이 트리거되어 클러스터에 변경 사항이 적용됩니다.

</details>

### 8. AIOps 분석에서 이상 후보를 찾은 뒤 트래픽 변경 전에 필요한 것은 무엇인가요?

- A) 이상치 점수만 확인하고 모든 listener를 덮어쓰기
- B) 데이터 신선도·대상 건강 상태·현재 설정·승인·용량을 검증하기
- C) 데이터가 없으면 정상으로 보고 100/0을 복원하기
- D) 승인 버튼을 보내면 승인된 것으로 간주하기

<details>
<summary>정답 보기</summary>

**정답: B) 데이터 신선도·대상 건강 상태·현재 설정·승인·용량을 검증하기**

**설명:** 이상 탐지는 실행 허가가 아닙니다. 누락·오래된 데이터는 정상의 증거가 아니며, 별도 실행기는 승인·만료·현재 revision과 대상의 상태를 확인해야 합니다. 본문의 분석 도구는 보고서만 생성하고 어떤 리소스도 변경하지 않습니다.

</details>

### 9. External Secrets Operator의 역할은 무엇인가요?

- A) Secret 암호화
- B) AWS Secrets Manager 등 외부 비밀 저장소의 값을 Kubernetes Secret으로 동기화
- C) Secret 삭제
- D) Secret 버전 관리

<details>
<summary>정답 보기</summary>

**정답: B) AWS Secrets Manager 등 외부 비밀 저장소의 값을 Kubernetes Secret으로 동기화**

**설명:**
External Secrets Operator(ESO)는 AWS Secrets Manager, HashiCorp Vault, Azure Key Vault 등의 외부 비밀 관리 서비스에서 값을 가져와 Kubernetes Secret으로 자동 생성하고 동기화합니다. 이를 통해 민감한 정보를 Git에 저장하지 않으면서도 GitOps 워크플로우를 유지할 수 있습니다.

</details>

### 10. HCP Terraform의 Sentinel Policy의 주요 용도는 무엇인가요?

- A) 로그 수집
- B) 인프라 변경에 대한 정책 기반 규정 준수 검사
- C) 비용 계산
- D) 성능 최적화

<details>
<summary>정답 보기</summary>

**정답: B) 인프라 변경에 대한 정책 기반 규정 준수 검사**

**설명:**
Sentinel은 HCP Terraform/Enterprise의 정책 엔진입니다. terraform plan 결과를 검사하여 보안, 비용, 규정 준수 등의 정책을 적용합니다. 예를 들어, "퍼블릭 IP가 있는 리소스 금지", "특정 리전만 허용", "태그 필수" 같은 규칙을 정의할 수 있습니다. 실제 차단 여부는 policy set의 적용 대상과 enforcement 설정에 달려 있으며, 예제 정책은 지정한 리소스·필드만 검사합니다.

</details>
