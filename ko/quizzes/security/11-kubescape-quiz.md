# Kubescape 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

## 문제

<span id="_1-kubescape-프로젝트의-cncf-상태는"></span>

### 1. Kubescape의 현재 CNCF 성숙도는?

- A) Graduated
- B) Incubating
- C) Sandbox
- D) Archived

<details>
<summary>정답 보기</summary>

**정답: B) Incubating**

2022년 12월 13일 CNCF에 합류했고 2025년 1월 13일 Incubating으로 승격됐습니다. 개별 설치의 보안·가용성 보증과는 구분합니다.

</details>

<span id="_2-kubescape가-지원하는-보안-프레임워크가-아닌-것은"></span>

### 2. 프레임워크 이름과 컨트롤 수를 확인하는 올바른 방법은?

- A) 예전 문서의 CIS 별칭을 항상 사용
- B) binary 버전과 policy bundle을 기록하고 실제 목록 확인
- C) 모든 버전에서 NSA 컨트롤 수는 고정
- D) SOC2 scan만 통과하면 인증 완료

<details>
<summary>정답 보기</summary>

**정답: B) binary 버전과 policy bundle을 기록하고 실제 목록 확인**

kubescape list frameworks와 list controls --framework NSA로 확인합니다. 검토 snapshot의 NSA는 26개 control이며 입력에 따라 적용 범위가 달라집니다. 점수 비교에는 policy hash도 보관합니다.

</details>

<span id="_3-kubescape-cli로-클러스터를-스캔하는-기본-명령어-형식은"></span>

### 3. kubescape scan에서 로컬 파일을 생략하면 어떤 위험이 있는가?

- A) 명령이 항상 실패
- B) 현재 kubeconfig의 클러스터를 검사할 수 있음
- C) 자동으로 모든 로컬 파일만 검사
- D) 항상 dry-run만 수행

<details>
<summary>정답 보기</summary>

**정답: B) 현재 kubeconfig의 클러스터를 검사할 수 있음**

CI에서는 존재하는 로컬 파일을 명시하고 빈 경로를 거부합니다. --keep-local, 별도 cache, 고정 policy를 함께 사용하더라도 입력 범위는 별도로 확인해야 합니다.

</details>

<span id="_4-kubescape-operator와-cli-모드의-주요-차이점은"></span>

### 4. Operator와 CLI의 차이를 올바르게 설명한 것은?

- A) Operator는 GUI만 제공
- B) CLI는 정적 입력/일회성 검사, Operator는 선택한 capability의 지속·예약 검사
- C) Operator를 설치하면 모든 runtime 기능이 검증됨
- D) CLI와 Operator image 버전은 항상 같음

<details>
<summary>정답 보기</summary>

**정답: B) CLI는 정적 입력/일회성 검사, Operator는 선택한 capability의 지속·예약 검사**

chart 1.40.4의 scanner image는 4.0.13이고 이 문서의 로컬 CLI는 4.0.14입니다. node/image/runtime/remediation 범위와 권한은 별도 선택·검증 대상입니다.

</details>

<span id="_5-kubescape의-리스크-스코어-risk-score-계산-방식은"></span>

### 5. score와 complianceScore의 관계는?

- A) 항상 같은 값
- B) 항상 두 값의 합이 100
- C) 서로 다른 집계이며 결과 schema에서 구분
- D) 둘 다 CVSS 평균

<details>
<summary>정답 보기</summary>

**정답: C) 서로 다른 집계이며 결과 schema에서 구분**

합성 insecure Pod의 실제 결과는 compliance 55와 score 62.5였습니다. JSON 경로는 summaryDetails.complianceScore와 summaryDetails.score입니다. 이를 실제 클러스터의 보안 수준으로 일반화하지 않습니다.

</details>

<span id="_6-ci-cd-파이프라인에서-kubescape-스캔이-특정-점수-이상이면-실패하도록-설정하는-플래그는"></span>

### 6. compliance 55에 --compliance-threshold 56을 적용한 결과는?

- A) 최대 risk 기준이므로 성공
- B) 최소 compliance 미달로 exit 1
- C) 항상 exit 2
- D) --fail-threshold 0과 같은 현재 게이트

<details>
<summary>정답 보기</summary>

**정답: B) 최소 compliance 미달로 exit 1**

같은 fixture는 threshold 55에서 exit 0, 56에서 exit 1이었습니다. --fail-threshold는 4.0.14에서 deprecated로 받아들이지만 실제 게이트 값은 무시하므로 사용하지 않습니다.

</details>

<span id="_7-kube-bench와-kubescape의-주요-차이점은"></span>

### 7. kube-bench와 Kubescape를 비교할 때 올바른 기준은?

- A) 도구 이름만 보고 하나가 모든 검사를 대체한다고 판단
- B) 노드/CIS 검사와 workload/config 검사 등 실제 범위·접근 권한 비교
- C) 둘 다 노드 접근 없이 control plane 전체 검사 가능
- D) Kubescape 통과는 CIS 인증서 발급과 같음

<details>
<summary>정답 보기</summary>

**정답: B) 노드/CIS 검사와 workload/config 검사 등 실제 범위·접근 권한 비교**

관리형 EKS control plane, 로컬 매니페스트, 노드 파일 접근은 서로 다른 가시성을 제공합니다. 검증 불가능·미검사 항목을 통과와 구분하고 필요한 도구를 선택합니다.

</details>

<span id="_8-kubescape의-rbac-시각화-기능이-제공하는-정보는"></span>

### 8. RBAC 컨트롤에 관한 올바른 설명은?

- A) C-0036은 모든 버전에서 wildcard RBAC 검사
- B) RoleBinding은 모든 namespace에 권한 부여
- C) 현재 bundle의 ID·이름과 수집 권한 범위를 확인해야 함
- D) scan rbac는 검토한 CLI의 독립 subcommand

<details>
<summary>정답 보기</summary>

**정답: C) 현재 bundle의 ID·이름과 수집 권한 범위를 확인해야 함**

검토 bundle의 C-0035는 Administrative Roles, C-0036/0039는 validating/mutating admission 관련 검사입니다. RoleBinding은 namespace 범위이며 정적 분석이 외부 IAM까지 자동 검증하지 않습니다.

</details>

<span id="_9-kubescape에서-이미지-취약점-스캐닝을-위해-연동되는-도구는"></span>

### 9. 이미지 스캔과 host scan을 올바르게 구분한 것은?

- A) host scan을 켜면 이미지 CVE만 검사
- B) 명시적 image scan은 registry·DB 접근이 필요하며 host scan은 별도 범위
- C) Grype는 SBOM 생성만 수행
- D) 이미지 버전·platform·DB 날짜는 무관

<details>
<summary>정답 보기</summary>

**정답: B) 명시적 image scan은 registry·DB 접근이 필요하며 host scan은 별도 범위**

검토 CLI 소스는 Grype와 Syft를 사용하며 Operator kubevuln은 별도 버전입니다. 호스트 검사는 추가 리소스·권한이 필요할 수 있고 이번 검토에서는 이미지 pull이나 host scan을 실행하지 않았습니다.

</details>

<span id="_10-kubescape에서-특정-컨트롤을-예외-처리하는-방법은"></span>

### 10. CLI 예외와 in-cluster 예외의 올바른 형식은?

- A) CLI는 일반 ConfigMap을 그대로 읽음
- B) CLI JSON 배열의 alertOnly와 v1beta1 SecurityException의 alert_only를 구분
- C) 모든 ignore annotation이 자동 예외
- D) 예외를 등록하면 문제 수정 완료

<details>
<summary>정답 보기</summary>

**정답: B) CLI JSON 배열의 alertOnly와 v1beta1 SecurityException의 alert_only를 구분**

alertOnly는 시험에서 실패를 acknowledged로 표시했지만 compliance는 그대로였습니다. exclude-controls는 평가 분모를 바꿉니다. 예외의 owner·범위·만료·재검토를 유지하고 실제 수정과 구분합니다.

</details>

## 점수 계산

- 9–10개: 핵심 개념 이해
- 7–8개: 틀린 항목의 scope와 gate를 복습
- 6개 이하: 본문과 실제 예제로 복습

## 관련 문서

- [Kubescape](../../security/11-kubescape.md)
