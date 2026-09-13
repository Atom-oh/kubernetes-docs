# Kubeflow 아키텍처와 EKS 설치 퀴즈

기준: Community Distribution 26.03.1 / Dashboard 2.0.0 / KFP 2.16.1.

## 객관식 문제

1. 2026년 8월 17일 Kubeflow의 CNCF 졸업은 무엇을 의미하나요?

   - A) 모든 EKS 배포의 자동 규제 준수
   - B) 독립 보안 감사를 포함한 프로젝트 성숙도와 거버넌스 인정
   - C) 이후 보안 업데이트 불필요
   - D) 설정 없이 모든 테넌트 격리 보장

<details>
<summary>정답 보기</summary>

**정답: B) 독립 보안 감사를 포함한 프로젝트 성숙도와 거버넌스 인정**

졸업은 프로젝트에 관한 평가입니다. 개별 배포의 보안, 격리, 규제 준수는 따로 검토해야 합니다.
</details>

2. 이 장의 릴리스 기준은 무엇인가요?

   - A) AWS Kubeflow 1.7과 Community 26.03.1은 동일
   - B) KFP 2.16.1과 Dashboard 2.0.0을 포함한 Community 26.03.1
   - C) 모든 컴포넌트의 버전이 26.03.1
   - D) 릴리스 고정 없이 master 사용

<details>
<summary>정답 보기</summary>

**정답: B) KFP 2.16.1과 Dashboard 2.0.0을 포함한 Community 26.03.1**

배포판과 컴포넌트 버전은 다릅니다. 커뮤니티는 연간 약 두 번의 기본 릴리스를 계획하고 지원을 SLA가 아닌 best effort로 설명합니다.
</details>

3. Profile의 resourceQuotaSpec.hard를 생략하면 어떻게 되나요?

   - A) 컨트롤러가 기본 GPU 쿼터 설정
   - B) Istio가 동등한 CPU 쿼터 제공
   - C) Profile 컨트롤러가 자신의 ResourceQuota를 생성하지 않음
   - D) 네임스페이스에 무제한 AWS IAM 권한 부여

<details>
<summary>정답 보기</summary>

**정답: C) Profile 컨트롤러가 자신의 ResourceQuota를 생성하지 않음**

쿼터는 선택 사항입니다. hard를 비우면 컨트롤러가 관리하던 쿼터를 제거합니다. RBAC, 네트워크 정책, 스토리지, AWS 접근은 별도 경계입니다.
</details>

4. 이전 AWS 배포판 설치 가이드를 따르기 전에 무엇을 확인해야 하나요?

   - A) 최근 저장소 활동만 확인
   - B) 대시보드 로고 변경 여부
   - C) 릴리스 호환성과 필수 이미지의 가용성
   - D) 모든 컴포넌트가 CRD인지 여부

<details>
<summary>정답 보기</summary>

**정답: C) 릴리스 호환성과 필수 이미지의 가용성**

확인한 v1.7.0-aws-b1.0.3 릴리스에는 OIDC 이미지 제거로 신규 설치가 실패한다는 경고가 있습니다. 검증된 26.03.1 설치 방법이 아닙니다.
</details>

5. 현재 KFP의 S3 신원 연동에 대한 올바른 설명은 무엇인가요?

   - A) 모든 KFPv2는 정적 IAM 사용자 키 필요
   - B) fromEnv는 정적 키만 허용
   - C) 현재 가이드는 IRSA를 설명하며 실제 SDK, ServiceAccount, 역할 신뢰를 검증해야 함
   - D) Profile이 Pod Identity association을 자동 생성

<details>
<summary>정답 보기</summary>

**정답: C) 현재 가이드는 IRSA를 설명하며 실제 SDK, ServiceAccount, 역할 신뢰를 검증해야 함**

KFP 2.16.1의 fromEnv는 Go Cloud로 위임되고 고정된 기본 구현은 AWS SDK v2 자격 증명 체인을 사용합니다. 코드 검토만으로 EKS Pod Identity 배포 성공이 증명되지는 않습니다.
</details>

6. 대시보드의 역할은 무엇인가요?

   - A) 모든 모델의 자동 학습과 배포
   - B) 컴포넌트 인터페이스로의 탐색 제공
   - C) 모든 애플리케이션 인가 대체
   - D) 모든 파이프라인 아티팩트를 CRD에 저장

<details>
<summary>정답 보기</summary>

**정답: B) 컴포넌트 인터페이스로의 탐색 제공**

워크로드 컨트롤러와 애플리케이션 API가 각 작업을 수행합니다. KFP API는 별도 저장소도 사용하며 Run과 Experiment 개념이 항상 CRD인 것은 아닙니다.
</details>

## 단답형 문제

7. Dashboard v2 마이그레이션 때 Profile 객체와 CRD를 보존해야 하는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

Profile 컨트롤러는 네임스페이스 소유권을 설정합니다. Profile 삭제는 네임스페이스와 내부 리소스의 연쇄 삭제로 이어질 수 있습니다. 릴리스별 절차로 이전 컨트롤러 리소스를 정리하고 테넌트 Profile과 네임스페이스는 삭제하지 않아야 합니다.
</details>

8. Profile 오버레이 렌더링 성공은 무엇을 증명하고 무엇을 증명하지 않나요?

<details>
<summary>정답 보기</summary>

선택한 Kustomize 입력이 매니페스트를 생성한다는 것을 증명합니다. 검토한 오버레이는 Dashboard 2.0.0 이미지와 14개 리소스를 생성했습니다. EKS API admission, 컨트롤러 준비, 테넌트 격리, S3 접근 성공을 증명하지는 않습니다. 관리형 서비스 교체도 신원, 호환성, 네트워크, 비용, 이전 검토가 필요합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/01-architecture-installation.md) | [다음 퀴즈: Pipelines](02-pipelines-quiz.md)
