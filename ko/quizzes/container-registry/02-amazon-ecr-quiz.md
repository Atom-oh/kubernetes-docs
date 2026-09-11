# Amazon ECR 퀴즈
> **마지막 업데이트**: 2026년 9월 11일

1. Amazon ECR Private과 ECR Public의 차이점으로 올바른 것은?
   - A) ECR Public은 AWS 계정 없이도 이미지를 푸시할 수 있다
   - B) ECR Private은 리전별로 레포지토리가 분리되고, ECR Public은 글로벌하다
   - C) ECR Public만 라이프사이클 정책을 지원한다
   - D) ECR Private은 무료이고 ECR Public은 유료이다

<details>
<summary>정답 보기</summary>

**정답: B) ECR Private은 리전별로 레포지토리가 분리되고, ECR Public은 글로벌하다**

**설명:**
Private 리포지토리는 리전별로 관리됩니다. Public 이미지는 글로벌 URL로 배포되며 익명 pull에는 AWS 계정이 필요하지 않습니다. Public 게시·관리에는 인증이 필요하고 관리 API의 지원 리전은 현재 엔드포인트 목록을 확인합니다.

</details>

2. ECR 인증 토큰의 유효 기간은 얼마인가요?
   - A) 1시간
   - B) 12시간
   - C) 24시간
   - D) 7일

<details>
<summary>정답 보기</summary>

**정답: B) 12시간**

**설명:**
`aws ecr get-login-password` 명령으로 얻는 인증 토큰은 12시간 동안 유효합니다. 장기 실행 환경에서는 credential helper를 사용하거나 토큰을 주기적으로 갱신해야 합니다.

</details>

3. ECR lifecycle에서 모든 규칙을 평가한 뒤 적용 우선순위를 결정하는 기준은 무엇인가요?
   - A) 알파벳 순서
   - B) 규칙 생성 시간 순서
   - C) rulePriority 숫자가 낮은 것부터 높은 것 순서
   - D) 가장 많은 이미지를 삭제하는 규칙 우선

<details>
<summary>정답 보기</summary>

**정답: C) rulePriority 숫자가 낮은 것부터 높은 것 순서**

**설명:**
모든 규칙을 먼저 평가한 뒤 낮은 `rulePriority` 숫자부터 적용합니다. 높은 우선순위 규칙의 태그 조건에 맞는 이미지는 낮은 우선순위 규칙으로 만료시킬 수 없습니다. 평가와 적용을 구분해야 합니다.

</details>

4. ECR 라이프사이클 정책의 tagPatternList에서 사용되는 패턴 매칭 방식은?
   - A) 정규표현식 (Regex)
   - B) 문서화된 `*` 와일드카드 패턴
   - C) SQL LIKE 패턴
   - D) 완전 일치만 지원

<details>
<summary>정답 보기</summary>

**정답: B) 문서화된 `*` 와일드카드 패턴**

**설명:**
문서화된 와일드카드는 `*`이며 문자열당 최대 4개입니다. 정규식이나 전체 Unix glob 문법으로 가정하지 않습니다. 예를 들어 `v*`로 접두어를 선택할 수 있지만 이것이 SemVer 검증은 아닙니다. 여러 패턴을 한 목록에 넣으면 모든 패턴을 만족하는 이미지가 선택됩니다.

</details>

5. ECR 이미지 관리 전략 중 "Strategy A (환경별 분리 레포지토리)"의 장점이 아닌 것은?
   - A) 환경별로 독립적인 라이프사이클 정책 적용 가능
   - B) IAM 권한을 환경별로 세분화 가능
   - C) 동일 이미지의 환경 간 프로모션이 간단함
   - D) 환경별 비용 추적이 용이함

<details>
<summary>정답 보기</summary>

**정답: C) 동일 이미지의 환경 간 프로모션이 간단함**

**설명:**
환경별 분리 레포지토리 전략에서는 이미지를 다른 환경으로 프로모션할 때 복사(태그 및 푸시)가 필요합니다. 단일 레포지토리 전략(Strategy B)에서는 태그만 변경하면 되므로 프로모션이 더 간단합니다.

</details>

6. ECR 라이프사이클 정책의 주요 제한사항은 무엇인가요?
   - A) 최대 10개의 규칙만 생성 가능
   - B) 태그가 있는 이미지만 관리 가능
   - C) 한 규칙의 여러 tagPatternList 항목을 OR로 해석할 수 없음
   - D) sinceImagePushed는 30일이 최대

<details>
<summary>정답 보기</summary>

**정답: C) 한 규칙의 여러 tagPatternList 항목을 OR로 해석할 수 없음**

**설명:**
한 규칙의 패턴 목록은 AND입니다. dev와 test를 각각 선택하려면 별도 규칙을 구성합니다. 이와 별개로 최소 개수와 보존 기간을 함께 만족시키는 조건은 독립적인 만료 규칙을 나열한다고 자동 구현되지 않습니다.

</details>

7. Terraform에서 ECR 라이프사이클 정책을 정의할 때 사용하는 리소스는?
   - A) aws_ecr_repository
   - B) aws_ecr_lifecycle_policy
   - C) aws_ecr_repository_policy
   - D) aws_ecr_image_policy

<details>
<summary>정답 보기</summary>

**정답: B) aws_ecr_lifecycle_policy**

**설명:**
`aws_ecr_lifecycle_policy` 리소스는 ECR 레포지토리에 라이프사이클 정책을 연결합니다. `aws_ecr_repository`는 레포지토리 자체를, `aws_ecr_repository_policy`는 IAM 리소스 기반 정책을 정의합니다.

</details>

8. EC2 기반 EKS 노드에서 컨테이너가 시작되기 전 ECR 이미지를 pull하는 주체의 권한은 어디에서 제공하나요?
   - A) imagePullSecrets에 ECR 토큰 저장
   - B) 노드 IAM 역할에 ECR 권한 부여
   - C) IRSA(IAM Roles for Service Accounts) 또는 Pod Identity 사용
   - D) ECR을 퍼블릭으로 설정

<details>
<summary>정답 보기</summary>

**정답: B) 노드 IAM 역할에 ECR 권한 부여**

**설명:**
EC2 노드의 kubelet이 초기 image pull을 수행하므로 노드 IAM 역할에 ECR pull 권한이 필요합니다. Fargate는 Pod execution role을 사용합니다. IRSA/Pod Identity는 실행된 애플리케이션의 AWS API 자격 증명이며 kubelet의 초기 pull 권한을 대체하지 않습니다.

</details>

9. ECR 크로스 리전 복제(Replication) 설정 시 고려해야 할 사항은?
   - A) 복제는 실시간으로 동기화된다
   - B) 복제된 이미지는 원본과 다른 다이제스트를 갖는다
   - C) 복제 설정 이후 push 또는 restore된 콘텐츠가 대상이며 기존 콘텐츠는 별도 backfill이 필요하다
   - D) 복제는 계정 간에는 불가능하다

<details>
<summary>정답 보기</summary>

**정답: C) 복제 설정 이후 push 또는 restore된 콘텐츠가 대상이며 기존 콘텐츠는 별도 backfill이 필요하다**

**설명:**
복제는 비동기이며 설정 이전 콘텐츠를 자동 backfill하지 않습니다. 필요한 digest를 명시적으로 복사하고 대상에서 확인합니다. 리포지토리 설정·lifecycle·권한은 별도로 구성하며, 태그 불변성으로 RPO 0이나 삭제 방지가 보장되지는 않습니다.

</details>

10. ECR 이미지 태그 불변성(Immutable Tags) 설정의 효과는?
    - A) 이미지 삭제가 불가능해진다
    - B) 동일한 태그로 새 이미지를 푸시할 수 없다
    - C) 라이프사이클 정책이 적용되지 않는다
    - D) 이미지 스캔이 자동으로 활성화된다

<details>
<summary>정답 보기</summary>

**정답: B) 동일한 태그로 새 이미지를 푸시할 수 없다**

**설명:**
태그 불변성을 활성화하면 기존 태그를 덮어쓰는 것이 방지됩니다. 이는 프로덕션 환경에서 특정 태그의 이미지가 예기치 않게 변경되는 것을 방지합니다. 이미지 삭제는 여전히 가능하며, 라이프사이클 정책도 정상 작동합니다.

</details>
