# 엔터프라이즈 클라우드 거버넌스 개요 퀴즈

> 이 퀴즈는 [엔터프라이즈 클라우드 거버넌스 개요](../../governance/00-governance-overview.md) 문서의 학습 내용을 테스트합니다.

---

1. Account, VPC, EKS 경계를 "독립적으로 판정"하는 접근 방식의 핵심 아이디어는 무엇인가?
   - A) 팀 이름을 기준으로 세 경계를 항상 함께 만든다
   - B) 각 경계를 서로 다른 기준(보안/quota/책임, 네트워크/trust zone, 런타임 장애 영향)으로 독립적으로 정한다
   - C) 모든 워크로드에 하나의 공용 Account·VPC·클러스터만 사용한다
   - D) VPC 경계만 결정하고 나머지는 자동으로 따라오게 한다

<details>
<summary>정답 보기</summary>

**정답: B) 각 경계를 서로 다른 기준(보안/quota/책임, 네트워크/trust zone, 런타임 장애 영향)으로 독립적으로 정한다**

**설명:**
Account는 보안·quota·비용 책임·lifecycle, VPC는 네트워크 정책과 trust zone, EKS는 런타임 장애 영향 범위를 기준으로 각각 판정합니다. domain×environment 조합마다 세 경계를 함께 만드는 고정 산식(BND-A)은 단순하지만 서로 다른 성격의 경계를 하나로 취급하는 대안적 접근입니다.

</details>

---

2. Pod Identity association의 기본 IAM role은 어디에 있어야 하는가?
   - A) 아무 Account
   - B) 클러스터와 같은 Account
   - C) Management Account에만
   - D) Region당 하나의 Account

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터와 같은 Account**

**설명:**
기본 association role은 클러스터 Account에 있어야 합니다. target-role 기능은 역할 연결을 사용하지만, 지원 서비스 resource policy나 IRSA 등 다른 cross-account 경로도 있습니다.

</details>

---

3. 안정적인 Workload ID와 변경 가능한 metadata를 구분하는 이유는 무엇인가?
   - A) AWS API 호출 비용을 줄이기 위해서
   - B) 조직 개편·브랜드 통합처럼 반복되는 변화가 인프라 마이그레이션으로 직결되지 않게 하기 위해서
   - C) Kubernetes RBAC 설정을 단순화하기 위해서
   - D) 모든 워크로드를 하나의 Account에 통합하기 위해서

<details>
<summary>정답 보기</summary>

**정답: B) 조직 개편·브랜드 통합처럼 반복되는 변화가 인프라 마이그레이션으로 직결되지 않게 하기 위해서**

**설명:**
Team은 조직 개편으로 자주 바뀌지만 domain(business capability)은 상대적으로 안정적입니다. Account나 VPC 경계를 팀·브랜드 이름에 직접 묶으면 조직 개편이 곧 인프라 마이그레이션이 되므로, 안정적인 Workload ID에 domain·brand·team·CUJ 등을 변경 가능한 metadata로 붙이는 방식을 권장합니다.

</details>
