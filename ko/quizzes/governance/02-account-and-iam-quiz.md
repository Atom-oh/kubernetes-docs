# Account 구성과 IAM 경계 퀴즈

> 이 퀴즈는 [Account 구성과 IAM 경계](../../governance/02-account-and-iam.md) 문서의 학습 내용을 테스트합니다.

---

1. IAM Identity Center에서 순수 RBAC 확장의 실제 상한이 되는 조정 불가 quota는?
   - A) 전체 Permission Set 수 3,500개
   - B) Account당 프로비저닝된 Permission Set 500개
   - C) Account당 Permission Set에 할당 가능한 group 수 100개
   - D) API 전체 throttle 20 TPS

<details>
<summary>정답 보기</summary>

**정답: C) Account당 Permission Set에 할당 가능한 group 수 100개**

**설명:**
이 quota는 조정 불가능하며, 다수 팀이 공동으로 접근하는 Account(Shared Cluster Account 등)에서 팀×직무 조합의 group을 할당하면 100개에서 멈춥니다. 이 제약 때문에 다수 팀이 접근하는 Account에서는 "RBAC + 제한된 ABAC"가 조건별 선택이 아니라 필수로 격상되어야 합니다.

</details>

---

2. 분사(carve-out) 가능성이 있는 조직 단위에 대해 Shared VPC를 유지한 채 Account만 나누는 구조가 위험한 이유는?
   - A) Shared VPC는 애초에 여러 Account를 지원하지 않는다
   - B) RAM 기반 subnet 공유는 동일 Organization 내에서만 가능해서, 분사 시점에 Shared VPC 관계가 먼저 끊어진다
   - C) IAM Identity Center가 분사된 조직을 인식하지 못한다
   - D) EKS 클러스터가 자동으로 삭제된다

<details>
<summary>정답 보기</summary>

**정답: B) RAM 기반 subnet 공유는 동일 Organization 내에서만 가능해서, 분사 시점에 Shared VPC 관계가 먼저 끊어진다**

**설명:**
RAM(Resource Access Manager)의 subnet 공유는 동일 Organization 내에서만 가능합니다. 분사 가능성이 실재하면 Shared VPC를 유지한 채 Account만 나누는 구조로는 대응할 수 없고, 전용 VPC가 사실상 강제됩니다.

</details>

---

3. Workload Account + Shared Cluster Account 패턴에서 cross-account 리소스 접근이 필수적으로 갖는 구조는?
   - A) 단일 role로 모든 Account에 직접 접근
   - B) association role → target role(AssumeRole)의 2단 구조
   - C) IAM user의 access key를 워크로드마다 발급
   - D) aws-auth ConfigMap을 통한 직접 매핑

<details>
<summary>정답 보기</summary>

**정답: B) association role → target role(AssumeRole)의 2단 구조**

**설명:**
EKS Pod Identity role은 클러스터와 같은 Account에만 존재할 수 있으므로, Shared Cluster Account 패턴에서 다른 Account의 리소스에 접근하려면 항상 association role이 target role을 assume하는 2단 구조가 필요합니다. 이는 최적화가 아니라 필수 구조입니다.

</details>

---

4. EKS Access Entries에서 Access Policy와 Kubernetes RBAC(group mapping)를 함께 사용할 때 주의해야 할 점은?
   - A) 나중에 연결한 방식만 적용된다
   - B) 두 경로의 허용 권한은 합쳐지며, 한쪽으로 다른 쪽을 제한할 수 없다
   - C) 두 방식은 동시에 사용할 수 없다
   - D) RBAC이 항상 Access Policy를 덮어쓴다

<details>
<summary>정답 보기</summary>

**정답: B) 두 경로의 허용 권한은 합쳐지며, 한쪽으로 다른 쪽을 제한할 수 없다**

**설명:**
Access Policy와 RBAC를 함께 쓰면 허용 권한이 합쳐집니다. 따라서 Principal별로 주 권한 부여 경로를 하나만 지정하고, 두 경로의 중복 grant를 자동으로 검사하는 절차가 필수 통제로 필요합니다. 자동화하지 않으면 시간이 지나며 권한이 의도치 않게 확대됩니다.

</details>
