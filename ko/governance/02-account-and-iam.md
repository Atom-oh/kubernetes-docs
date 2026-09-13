# Account 구성과 IAM 경계

> **마지막 업데이트**: 2026년 9월 13일

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

> **분사 계획**: subnet 공유는 같은 Organization 안에서만 지원됩니다. 조직 이탈 전에 독립 네트워크로 이전할 경로를 준비하세요. 공유 해제 시 기존 리소스는 계속 실행될 수 있지만 새 리소스 생성과 managed-service 교체·확장이 영향을 받습니다. 공유 해제가 모든 리소스를 즉시 삭제하거나 중단한다는 뜻은 아닙니다.

## 2. Account와 EKS 실행 관계

Account partitioning을 정한 뒤에는 Kubernetes 워크로드를 어느 Account의 EKS에서 실행할지 결정해야 합니다.

| 옵션 | 구성 | 장점 | 단점 |
|---|---|---|---|
| Workload Account별 EKS | 각 Workload Account가 자체 EKS 클러스터를 소유 | Account와 runtime 책임·장애 경계가 일치 | 작은 워크로드에도 클러스터가 필요해 관리할 클러스터 수와 유휴 capacity가 증가 |
| **Workload Account + Shared Cluster Account** | Lambda·SQS·DB 등은 워크로드 Account가 소유하고, Kubernetes 워크로드는 별도 Cluster Account의 공유 EKS에서 실행 | Account 경계와 관리할 EKS 클러스터 수를 독립적으로 결정할 수 있음 | cross-account identity·network·클러스터 책임이 복잡해짐 |

두 번째 패턴에서는 클러스터 Account의 IAM role과 다른 Account의 데이터 접근 권한을 구분합니다. Shared VPC를 쓰는 경우 EKS를 생성하는 participant는 **Cluster Account**이며, DB·SQS만 소유한 Workload Account와 다를 수 있습니다. Pod Identity target-role chaining, 서비스 resource policy, IRSA를 요구에 맞게 선택합니다.

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

Managed node group 30개는 기본값이며 조정 가능합니다. tenant당 node group 하나를 쓰더라도 30 tenant의 고정 상한으로 해석하지 않습니다. Karpenter NodePool과 taint/toleration은 배치 수단이며 그 자체가 강한 보안 경계는 아닙니다. 승인된 quota·권한·커널 공유·노드 agent 권한을 함께 검토합니다.

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
| Permission Set당 관리형 정책 | 25; IAM role의 기본 10개 quota도 별도 조정 필요 | Permission Set 한도 불가 |
| Permission Set당 inline policy | 32,768바이트, 공백 제외 10,240바이트 | 불가 |
| **한 Account의 한 Permission Set에 할당 가능한 group** | **100** | **불가** |
| 구성 가능 Account 수 | 7,000 | 가능 |
| Identity Center API throttle | 합계 20 TPS; 읽기 API 증설 문의 가능 | API별 별도 제한 확인 |

100개는 **Account 전체 group 수가 아니라 특정 Permission Set과 Account 조합**의 group 할당 한도입니다. 서로 다른 Permission Set을 사용하는 group을 Account 전체로 합산해 100개에서 막힌다고 판정하지 않습니다.

> **설계 제안**: Permission Set별 할당 수와 정책 중복을 측정한 뒤 RBAC 정리·ABAC·Account 분리를 비교하세요. 50개 경고값은 조직이 선택할 운영 예시이며 AWS 의무나 ABAC 강제 조건이 아닙니다.

## 4. 워크로드(애플리케이션·자동화)의 AWS 접근

아래 항목들은 서로 배타적인 선택지가 아니라, 실행 환경과 cross-account 접근 여부에 따라 조합해서 쓰는 패턴입니다.

| 방식 | 구성 | 적합한 상황 |
|---|---|---|
| Runtime role | EC2·Lambda·ECS 등 실행 환경에 IAM role을 연결 | EKS 이외의 워크로드 |
| **EKS Pod Identity** | Pod와 IAM role을 Pod Identity association으로 연결 | 지원되는 EKS 워크로드 (권장 방향) |
| IRSA | Kubernetes service account token + IAM OIDC provider | 기존 EKS·toolchain과의 호환이 필요한 경우 |
| **Cross-account target role** | source role이 대상 Account role을 assume | 대상 role의 권한으로 실행할 필요가 있는 경로 |

Static access key는 role이나 federation을 지원하지 않는 legacy 연동에만, 목적·소유자·만료일·rotation을 명시한 예외로 허용합니다.

Pod Identity의 기본 association role은 클러스터 Account에 있습니다. targetRoleArn을 지정하면 두 role을 연결하지만, 지원 서비스의 resource policy가 이 source role을 직접 허용하는 방식도 가능합니다. IRSA는 대상 Account OIDC provider/role로 직접 연합할 수도 있습니다. role 재사용과 session tag·policy 설계에 따라 role 수가 달라지므로 “워크로드마다 반드시 2개”라는 산식을 사용하지 않습니다. AWS API용 workload role은 Kubernetes API 접근용 Access Entry와 별도로 계산합니다.

## 5. Kubernetes API 접근

| 방식 | 구성 | 상태 |
|---|---|---|
| **EKS Access Entries** | IAM principal의 클러스터 접근을 Access Entry로 관리, Access Policy 연결 또는 Kubernetes group mapping으로 RBAC 사용 | 권장 방향 |
| aws-auth ConfigMap | IAM principal과 Kubernetes identity mapping을 클러스터의 `aws-auth` ConfigMap으로 관리 | 기존 클러스터 migration 중에만 예외로 유지 |

**권한 합산**: Access Policy와 Kubernetes RBAC를 함께 쓰면 허용 권한이 합쳐지며 한쪽으로 다른 쪽을 제한할 수 없습니다. Principal별 주 경로와 의도된 추가 grant를 기록하고 중복 권한을 정기적으로 검토하세요. 자동 검사는 유용한 구현 방식이지만 API 사용의 필수 조건은 아닙니다.

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
- [EKS shared subnet requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Unsharing subnets](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [EKS resource-policy patterns](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
