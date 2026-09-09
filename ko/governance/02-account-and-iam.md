# Account 구성과 IAM 경계

> **마지막 업데이트**: 2026년 9월 9일

## 1. Account partitioning: 무엇을 기준으로 나눌 것인가

Account를 나누는 축으로 가장 흔하게 등장하는 후보는 팀, 브랜드, 도메인, 환경(production/non-production)입니다. 하지만 **Account는 팀 이름 자체가 아니라, 관련 워크로드가 공유하는 보안·quota·비용 책임·lifecycle로 판단**해야 합니다. Team은 조직 개편으로 자주 바뀌지만, domain(business capability)은 상대적으로 안정적인 Account 후보입니다.

| 옵션 | 구성 | 장점 | 단점 |
|---|---|---|---|
| Domain × Environment | 도메인마다 Production/Non-production Account를 별도 제공 | 비용·quota·권한·책임을 도메인에 연결하기 쉬움 | 작은 도메인에도 고정비가 들고, 도메인 재편이 곧 마이그레이션이 됨 |
| Brand × Environment | 브랜드와 환경별로 Account를 만들고 여러 도메인을 그 안에 둠 | 브랜드별 비용·quota·권한·분리·이관을 Account 경계로 관리 | 여러 브랜드가 공유하는 공통 기능의 소유권이 모호해짐. 브랜드 lifecycle 변화가 Account 재편으로 직결 |
| 소수 중앙 Workload Account | 여러 도메인·팀의 워크로드를 소수의 공용 Account에 함께 배치 | 초기 운영과 작은 워크로드 수용이 단순 | quota·권한·장애 영향이 커지고, 나중에 분리하기 어려워짐 |
| **Hybrid portfolio** | 작은 워크로드는 공용 Account, 강한 도메인·규제·quota 경계가 있는 워크로드는 전용 Account | 요구에 따라 공유·도메인·전용 Account를 조합 가능 | 판정 기준이 약하면 예외가 급격히 증가 |

실무에서는 Hybrid portfolio를 출발점으로 하고, 공유·전용 여부를 매번 재현 가능한 판정표로 결정하는 방식이 일반적입니다(판정표 설계는 [의사결정 프레임워크](./06-decision-framework-and-poc.md) 참고).

브랜드는 비용 구분만 필요하다면 metadata로 관리하고, 규제·독립 quota·권한·분사(carve-out) 가능성처럼 강한 경계가 있을 때만 Account 축으로 승격하는 것이 좋습니다. 여러 도메인의 데이터를 모아 API로 제공하는 워크로드는 독립적인 SLO·quota·data access·lifecycle이 있다면 별도 Workload Account 후보가 될 수 있습니다. **단, 별도 Account가 곧 별도 EKS를 의미하지는 않습니다.**

> **분사 가능성이 있다면 반드시 확인할 것**: RAM(Resource Access Manager) 기반의 subnet 공유는 **동일 Organization 내에서만** 가능합니다. 특정 조직 단위가 실제로 분사(carve-out)될 가능성이 있다면, Shared VPC를 유지한 채 Account만 나누는 구조로는 대응할 수 없습니다 — 분사 시점에 Shared VPC 관계가 먼저 끊어집니다. 이 경우 전용 VPC가 사실상 강제됩니다.

## 2. Account와 EKS 실행 관계

Account partitioning을 정한 뒤에는 Kubernetes 워크로드를 어느 Account의 EKS에서 실행할지 결정해야 합니다.

| 옵션 | 구성 | 장점 | 단점 |
|---|---|---|---|
| Workload Account별 EKS | 각 Workload Account가 자체 EKS 클러스터를 소유 | Account와 runtime 책임·장애 경계가 일치 | 작은 워크로드에도 클러스터가 필요해 관리할 클러스터 수와 유휴 capacity가 증가 |
| **Workload Account + Shared Cluster Account** | Lambda·SQS·DB 등은 워크로드 Account가 소유하고, Kubernetes 워크로드는 별도 Cluster Account의 공유 EKS에서 실행 | Account 경계와 관리할 EKS 클러스터 수를 독립적으로 결정할 수 있음 | cross-account identity·network·클러스터 책임이 복잡해짐 |

두 번째 패턴을 막는 AWS 제약은 없지만, [개요](./00-governance-overview.md)에서 설명한 대로 **EKS Pod Identity role이 클러스터와 같은 Account에만 존재할 수 있다는 제약 때문에, cross-account 리소스 접근은 선택이 아니라 모든 워크로드에 기본으로 적용되는 필수 구조**가 됩니다. Shared Cluster의 보안 그룹과 IAM role은 항상 participant Account(리소스를 소유한 워크로드 Account)에 위치합니다.

### EKS 관련 quota — 여유 있는 항목과 먼저 막히는 항목

| Quota | 기본값 | 조정 가능 여부 |
|---|---|---|
| Cluster / Region | 100 | 가능 |
| Managed node group / cluster | 30 | 가능 |
| Node / node group | 450 | 가능 |
| Control plane security group / cluster | 4 | 불가 |
| Public endpoint 접근 가능 CIDR / cluster | 40 | 불가 |
| **Access entry / cluster** | **3,000** | **불가** |

대부분의 EKS quota는 여유가 있지만, **access entry 3,000개(조정 불가)**는 수십 개 팀의 CI/CD role을 워크로드×환경별로 개별 발급하면 빠르게 근접하는 실제 상한입니다. Permission Set이나 팀 단위 role로 접근 경로를 집약하고, access entry는 principal 유형별로 묶어서 관리하는 설계를 권장합니다.

또한 **managed node group 30개**가 access entry보다 먼저 실무적으로 걸릴 수 있습니다. tenant별로 node group을 분리하는 격리 전략은 30개 tenant에서 한계에 도달합니다. Karpenter와 taint/toleration, NodePool 기반 격리를 대안으로 검토할 수 있습니다(Karpenter의 [ARC zonal shift 연동](./03-eks-multi-account-multi-cluster.md)은 1.12 이상에서 지원됩니다).

## 3. 사람의 AWS 접근 (Workforce IAM)

| 옵션 | 구성 | 장점 | 단점 |
|---|---|---|---|
| **Identity Center + RBAC** | 사용자는 Identity Center로 로그인, 직무·역할별 Permission Set으로 Account 접근 | 임시 credential, 중앙 회수·감사 | team×domain×environment 조합으로 Permission Set이 늘어날 수 있음 |
| RBAC + 제한된 ABAC | RBAC의 직무별 최대 권한 안에서 tag로 resource 범위를 추가 제한 | 권한 상한과 확장성을 함께 확보 | RBAC·ABAC를 모두 시험하고 tag 발급자를 통제해야 함 |
| ABAC 중심 | 사용자·리소스 tag가 일치할 때 권한 부여 | Account·워크로드가 늘어도 정책 복제가 적음 | tag authority가 약하면 권한 확대·디버깅 난이도가 커짐 |

Account별 IAM user는 일반적인 선택지에서 제외하는 것이 안전합니다. Identity Center를 쓸 수 없는 비상 접근에만, 목적·소유자·사용 조건·credential 보관·정기 검증·종료 조건을 명시한 예외로 관리합니다.

### IAM Identity Center의 실제 상한

| Quota | 기본값 | 조정 |
|---|---|---|
| 전체 Permission Set 수 | 3,500 | 가능 |
| Account당 프로비저닝된 Permission Set 수 | 500 | 가능 |
| Permission Set당 관리형 정책 | 25 (단, IAM의 "role당 관리형 정책 10개"가 실효 상한) | — |
| Permission Set당 inline policy 크기 | 32,768바이트 | 불가 |
| **Account당 Permission Set에 할당 가능한 group 수** | **100** | **불가** |
| 구성 가능 Account 수 | 7,000 | — |
| API 전체 throttle | 20 TPS | — |

이 중 **"Account당 group 할당 100개(조정 불가)"가 순수 RBAC 확장의 실제 상한**입니다. 수십 개 팀×직무 조합의 group을 다수 팀이 공동으로 접근하는 Account(예: Shared Cluster Account, 중앙 DB Account)에 할당하면 100개에서 멈춥니다.

> **판정 규칙 권장**: 이 제약 때문에 "RBAC + 제한된 ABAC"는 조건별 선택 사항이 아니라, **다수 팀이 접근하는 Account에서는 필수로 격상**해야 합니다. 판정표에 "이 Account에 접근할 group 수 예상치" 열을 추가하고, 50개(한도의 절반)를 넘으면 ABAC 적용 또는 Account 분리 threshold로 삼는 것을 권장합니다.

## 4. 워크로드(애플리케이션·자동화)의 AWS 접근

아래 항목들은 서로 배타적인 선택지가 아니라, 실행 환경과 cross-account 접근 여부에 따라 조합해서 쓰는 패턴입니다.

| 방식 | 구성 | 적합한 상황 |
|---|---|---|
| Runtime role | EC2·Lambda·ECS 등 실행 환경에 IAM role을 연결 | EKS 이외의 워크로드 |
| **EKS Pod Identity** | Pod와 IAM role을 Pod Identity association으로 연결 | 지원되는 EKS 워크로드 (권장 방향) |
| IRSA | Kubernetes service account token + IAM OIDC provider | 기존 EKS·toolchain과의 호환이 필요한 경우 |
| **Cross-account target role** | 위 세 방식의 source role이 resource Account의 target role을 assume | cross-account resource 접근이 필요한 모든 경우 |

Static access key는 role이나 federation을 지원하지 않는 legacy 연동에만, 목적·소유자·만료일·rotation을 명시한 예외로 허용합니다.

앞서 강조했듯, **Pod Identity role은 클러스터와 같은 Account에만 존재할 수 있습니다.** Shared Cluster Account 패턴을 쓰면 cross-account 리소스 접근은 항상 "association role → target role(AssumeRole)"의 2단 구조가 됩니다. 워크로드 1개당 role 2개와 trust policy 2개가 필요하다는 뜻이고, 워크로드 수가 늘면 이 구조도 선형으로 늘어난다는 점을 access entry quota와 함께 계획해야 합니다.

## 5. Kubernetes API 접근

| 방식 | 구성 | 상태 |
|---|---|---|
| **EKS Access Entries** | IAM principal의 클러스터 접근을 Access Entry로 관리, Access Policy 연결 또는 Kubernetes group mapping으로 RBAC 사용 | 권장 방향 |
| aws-auth ConfigMap | IAM principal과 Kubernetes identity mapping을 클러스터의 `aws-auth` ConfigMap으로 관리 | 기존 클러스터 migration 중에만 예외로 유지 |

**중요한 제약**: Access Entry에서 Access Policy와 Kubernetes RBAC(group mapping)를 함께 쓰면, **두 경로의 허용 권한은 합쳐지며 한쪽으로 다른 쪽을 제한할 수 없습니다.** 즉 "Principal별로 주 권한 부여 경로를 하나만 지정하고, Access Policy와 RBAC의 중복 grant를 자동으로 검사하는 절차"는 선택 사항이 아니라 필수 통제입니다. 이걸 자동화하지 않으면 시간이 지나면서 반드시 권한이 의도치 않게 확대됩니다.

## 다음

Account와 IAM 경계가 정해졌다면, 그 위에서 EKS 클러스터를 몇 개 두고 어떻게 가용성을 확보할지가 다음 결정입니다 → [EKS 멀티 계정·멀티 클러스터 아키텍처](./03-eks-multi-account-multi-cluster.md)

## 참고 자료

- [IAM Identity Center quotas](https://docs.aws.amazon.com/singlesignon/latest/userguide/limits.html)
- [IAM Identity Center ABAC](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS IAM best practices](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Pod Identity target role](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-assign-target-role.html)
- [IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS multi-account strategy](https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html)
- [EKS quotas](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
