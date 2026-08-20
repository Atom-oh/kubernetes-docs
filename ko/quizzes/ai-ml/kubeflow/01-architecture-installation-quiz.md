# EKS에서의 Kubeflow 아키텍처와 설치 퀴즈

이 퀴즈는 Kubeflow의 컴포넌트 아키텍처, CNCF 졸업, Kubeflow Community Distribution의 릴리스 모델, EKS 특화 설치 패턴, Pipelines 아티팩트 저장을 위한 IAM 접근 패턴에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 2026년 8월 17일, Kubeflow가 CNCF와 관련해 달성한 마일스톤은 무엇인가요?
   - A) CNCF Sandbox 프로젝트로 승인됨
   - B) Sandbox에서 Incubating 상태로 이동함
   - C) 보안 감사를 통과하고 스티어링 커미티를 구성한 뒤 CNCF 최고 성숙도 등급인 졸업(Graduated)에 도달함
   - D) 활동 부족으로 CNCF에 의해 보관(archive) 처리됨

<details>
<summary>정답 보기</summary>

**정답: C) 보안 감사를 통과하고 스티어링 커미티를 구성한 뒤 CNCF 최고 성숙도 등급인 졸업(Graduated)에 도달함**

**설명:**
Kubeflow는 2023년 CNCF Incubating 프로젝트로 편입되었고, [2026년 8월 17일](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) 독립적인 제3자 보안 감사를 통과하고 프로젝트 거버넌스를 위한 공식 스티어링 커미티를 구성한 뒤 졸업했습니다. 졸업은 CNCF의 최고 성숙도 등급입니다.
</details>

2. Kubeflow Community Distribution이 사용하는 버전 체계와, 기본 릴리스가 대략 얼마나 자주 나오는지는 무엇인가요?
   - A) 시맨틱 버전(major.minor.patch), 지속적으로 배포
   - B) 캘린더 버전(YY.MM.patch), 대략 연 2회
   - C) 별도 릴리스 없이 단일 롤링 "latest" 태그만 존재
   - D) LTS 버전, 3년에 한 번

<details>
<summary>정답 보기</summary>

**정답: B) 캘린더 버전(YY.MM.patch), 대략 연 2회**

**설명:**
Kubeflow Community Distribution은 YY.MM.patch 형식의 캘린더 버전을 사용하며, 연 2회 정도 기본 릴리스를 냅니다. 이 글을 쓰는 시점의 최신 기본 릴리스는 26.03입니다(이후 더 새로운 컴포넌트 버전을 담은 26.03.1 패치가 나왔습니다).
</details>

3. Kubeflow 아키텍처에서 "Kubeflow Profile"이란 무엇인가요?
   - A) 사용자 개인의 대시보드 테마와 레이아웃 설정
   - B) Profile Controller가 조정(reconcile)하는, Kubernetes 네임스페이스와 RBAC 바인딩·리소스 쿼터·Istio AuthorizationPolicy 객체의 묶음
   - C) 클러스터에 설치된 컴포넌트 목록을 나열한 YAML 파일
   - D) 관리형 Kubeflow 벤더만 사용하는 과금 단위

<details>
<summary>정답 보기</summary>

**정답: B) Profile Controller가 조정(reconcile)하는, Kubernetes 네임스페이스와 RBAC 바인딩·리소스 쿼터·Istio AuthorizationPolicy 객체의 묶음**

**설명:**
Kubeflow Profile은 멀티테넌시 경계입니다 — 하나의 Profile 커스텀 리소스로부터 Profile Controller가 조정하는 네임스페이스와 RBAC 바인딩, 쿼터, Istio 인가 정책의 묶음입니다. 다른 컴포넌트들(Notebooks, Pipelines, Katib)은 사용자의 프로필 네임스페이스 안에 리소스를 생성합니다.
</details>

4. `awslabs/kubeflow-manifests`가 Kubeflow의 기본 Dex, 클러스터 내부 MySQL, MinIO를 대체하기 위해 사용하는 세 가지 AWS 네이티브 서비스는 무엇인가요?
   - A) IAM, DynamoDB, EFS
   - B) Cognito, RDS, S3
   - C) Secrets Manager, Aurora Serverless, EBS
   - D) SSO, Redshift, Glacier

<details>
<summary>정답 보기</summary>

**정답: B) Cognito, RDS, S3**

**설명:**
`awslabs/kubeflow-manifests`는 인증에 Dex 대신 Amazon Cognito를, Pipelines/Katib 메타데이터에 클러스터 내부 MySQL 대신 Amazon RDS를, Pipelines 아티팩트 저장에 MinIO 대신 Amazon S3를 사용합니다. kustomize 기반 매니페스트 배포와 Terraform 기반 배포 모두 이 패턴을 문서화하고 있습니다.
</details>

5. Kubeflow Pipelines Pod에 S3 접근 권한을 부여하는 IRSA 지원, 특히 KFPv2에 대한 지원 이력은 어떻게 문서화되어 있나요?
   - A) IRSA는 예외 없이 항상 KFPv2를 완전히 지원했다
   - B) IRSA는 어떤 Kubeflow Pipelines 버전에서도 EKS에서 사용할 수 없었다
   - C) IRSA 지원은 KFPv2에서 역사적으로 뒤처져 있었고, 그 사이에는 IAM 사용자 기반 임시 해법이 문서화되어 있었으며, EKS Pod Identity는 IAM-Pod 바인딩 전반에 대한 더 넓은 방향으로 제시된다
   - D) KFPv2는 IAM을 완전히 비활성화하고 익명 S3 접근을 사용해야 한다

<details>
<summary>정답 보기</summary>

**정답: C) IRSA 지원은 KFPv2에서 역사적으로 뒤처져 있었고, 그 사이에는 IAM 사용자 기반 임시 해법이 문서화되어 있었으며, EKS Pod Identity는 IAM-Pod 바인딩 전반에 대한 더 넓은 방향으로 제시된다**

**설명:**
`kubeflow-manifests` 가이드는 과거 IRSA가 KFPv1에서는 지원되지만 KFPv2에서는 아직 지원되지 않는다고 명시했고, 그 사이에는 정적 자격 증명을 가진 전용 IAM 사용자를 임시 해법으로 권장했습니다. 별개로, EKS Pod Identity는 EKS 전반에서 새로운 IAM-Pod 바인딩에 대해 점점 더 권장되는 기본 메커니즘이 되고 있지만, KFPv2에 특화된 Pod Identity 지원의 현재 상태는 가정하지 말고 최신 공식 문서로 직접 확인해야 합니다.
</details>

6. 이 문서에서 다룬 "관리형 대안 대신 EKS에서 운영하는 이유" 트레이드오프에 따르면, SageMaker 같은 완전 관리형 플랫폼 대신 EKS에서 Kubeflow를 운영하는 것을 가장 강하게 정당화하는 조건은 무엇인가요?
   - A) 팀이 Kubernetes 컨트롤러나 CRD를 절대 다루고 싶어하지 않는 경우
   - B) 팀이 이미 EKS에서 다양한 워크로드를 운영 중이며, ML도 동일한 노드 풀·오토스케일링·관측성 스택을 공유하기를 원하는 경우
   - C) 팀에 기존 Kubernetes 운영 경험이 전혀 없는 경우
   - D) 이동성과 무관하게 운영 부담을 절대적으로 최소화하고 싶은 경우

<details>
<summary>정답 보기</summary>

**정답: B) 팀이 이미 EKS에서 다양한 워크로드를 운영 중이며, ML도 동일한 노드 풀·오토스케일링·관측성 스택을 공유하기를 원하는 경우**

**설명:**
EKS에서 Kubeflow를 운영하는 것이 가장 타당해지는 경우는, 팀이 이미 EKS에서 다른 워크로드를 운영하고 있어 ML을 위한 별도의 병렬 운영 체계를 유지하지 않아도 되는 상황, 그리고 이동성/종속 회피나 학습·서빙 내부에 대한 세밀한 제어가 필요한 상황입니다. 기존 Kubernetes 운영 역량이 없거나 운영 부담 최소화를 최우선으로 하는 팀은 보통 완전 관리형 플랫폼이 더 적합합니다.
</details>

## 단답형 문제

7. 2026년 8월 17일 발표된 CNCF 졸업(Graduation)이 Kubeflow 프로젝트의 성숙도에 대해 무엇을 의미하는지 한 문장으로 설명하고, 졸업을 위해 프로젝트가 충족해야 했던 구체적인 요건 하나를 드세요.

<details>
<summary>정답 보기</summary>

**정답:**
졸업은 CNCF 프로젝트가 프로덕션급 성숙도, 광범위한 도입, 건전한 거버넌스를 입증했다는 신호입니다. 이를 위해 Kubeflow는 독립적인 제3자 보안 감사를 통과하고 정식 운영위원회(Steering Committee)를 구성해야 했습니다. 자세한 내용은 [CNCF 발표문](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)을 참고하세요.
</details>

8. EKS에 Kubeflow를 배포할 때 `awslabs/kubeflow-manifests` 배포 패턴이 클러스터 내부 MinIO 아티팩트 저장소와 기본 내장 Dex 인증을 각각 S3와 Cognito로 대체하는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
EKS에는 이미 관리형이고 내구성이 있으며 IAM과 통합된 대응 서비스가 존재하기 때문입니다 — 오브젝트 스토리지는 S3, 신원 관리는 Cognito입니다. 대신 기본 내장된 클러스터 내부 대안을 계속 쓰면, AWS가 이미 제공하는 기능을 중복해서 운영하는 추가 상태 유지 서비스를 떠안게 되는데, 자체 호스팅 버전에서 Kubeflow가 특별히 필요로 하는 이점은 없습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/01-architecture-installation.md) | [다음 퀴즈: Pipelines](./02-pipelines-quiz.md)
