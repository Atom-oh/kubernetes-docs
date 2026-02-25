# Amazon ECR 퀴즈
> **마지막 업데이트**: 2026년 2월 25일

1. Amazon ECR Private과 ECR Public의 차이점으로 올바른 것은?
   - A) ECR Public은 AWS 계정 없이도 이미지를 푸시할 수 있다
   - B) ECR Private은 리전별로 레포지토리가 분리되고, ECR Public은 글로벌하다
   - C) ECR Public만 라이프사이클 정책을 지원한다
   - D) ECR Private은 무료이고 ECR Public은 유료이다

<details>
<summary>정답 보기</summary>

**정답: B) ECR Private은 리전별로 레포지토리가 분리되고, ECR Public은 글로벌하다**

**설명:**
ECR Private 레포지토리는 각 AWS 리전에 독립적으로 존재하며, ECR Public Gallery(public.ecr.aws)는 글로벌 서비스입니다. 두 서비스 모두 AWS 계정이 필요하며, ECR Private은 스토리지와 데이터 전송에 따른 비용이 발생합니다.

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

3. ECR 라이프사이클 정책에서 여러 규칙이 있을 때 평가 순서는 어떻게 되나요?
   - A) 알파벳 순서
   - B) 규칙 생성 시간 순서
   - C) rulePriority 숫자가 낮은 것부터 높은 것 순서
   - D) 가장 많은 이미지를 삭제하는 규칙 우선

<details>
<summary>정답 보기</summary>

**정답: C) rulePriority 숫자가 낮은 것부터 높은 것 순서**

**설명:**
ECR 라이프사이클 정책은 `rulePriority` 값이 낮은 규칙부터 순차적으로 평가합니다. 한 이미지가 특정 규칙에 의해 만료 대상으로 선택되면, 이후 규칙에서는 해당 이미지를 평가하지 않습니다.

</details>

4. ECR 라이프사이클 정책의 tagPatternList에서 사용되는 패턴 매칭 방식은?
   - A) 정규표현식 (Regex)
   - B) Glob 패턴 (와일드카드)
   - C) SQL LIKE 패턴
   - D) 완전 일치만 지원

<details>
<summary>정답 보기</summary>

**정답: B) Glob 패턴 (와일드카드)**

**설명:**
tagPatternList는 glob 스타일 와일드카드 패턴을 사용합니다. `*`는 임의의 문자열, `?`는 단일 문자를 매칭합니다. 예: `prod-*`, `v1.?.?`. 정규표현식이 아니므로 `^`, `$`, `+` 등의 regex 문법은 지원하지 않습니다.

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
   - C) 규칙 간 OR(합집합) 로직을 표현할 수 없음
   - D) sinceImagePushed는 30일이 최대

<details>
<summary>정답 보기</summary>

**정답: C) 규칙 간 OR(합집합) 로직을 표현할 수 없음**

**설명:**
ECR 라이프사이클 정책은 규칙을 순차적으로 평가하며, 한 규칙에 매칭된 이미지는 이후 규칙에서 제외됩니다. 이로 인해 "dev-* 또는 test-* 태그 중 30일 이상 된 것"과 같은 OR 조건을 단일 규칙으로 표현하기 어렵습니다. 대안으로 별도의 규칙을 만들어 각각의 케이스를 처리해야 합니다.

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

8. EKS에서 ECR 이미지를 풀하기 위한 권장 인증 방식은?
   - A) imagePullSecrets에 ECR 토큰 저장
   - B) 노드 IAM 역할에 ECR 권한 부여
   - C) IRSA(IAM Roles for Service Accounts) 또는 Pod Identity 사용
   - D) ECR을 퍼블릭으로 설정

<details>
<summary>정답 보기</summary>

**정답: C) IRSA(IAM Roles for Service Accounts) 또는 Pod Identity 사용**

**설명:**
IRSA 또는 EKS Pod Identity를 사용하면 Pod 수준에서 세분화된 IAM 권한을 부여할 수 있습니다. 노드 역할 방식은 모든 Pod에 동일한 권한이 부여되어 최소 권한 원칙에 어긋납니다.

</details>

9. ECR 크로스 리전 복제(Replication) 설정 시 고려해야 할 사항은?
   - A) 복제는 실시간으로 동기화된다
   - B) 복제된 이미지는 원본과 다른 다이제스트를 갖는다
   - C) 복제 규칙은 레포지토리 생성 이후 푸시된 이미지에만 적용된다
   - D) 복제는 계정 간에는 불가능하다

<details>
<summary>정답 보기</summary>

**정답: C) 복제 규칙은 레포지토리 생성 이후 푸시된 이미지에만 적용된다**

**설명:**
ECR 복제는 복제 규칙 설정 이후 푸시된 이미지에 대해 작동합니다. 기존 이미지는 자동으로 복제되지 않으며, 필요시 수동으로 복사해야 합니다. 복제된 이미지는 동일한 다이제스트를 유지합니다.

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
