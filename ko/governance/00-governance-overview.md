# 엔터프라이즈 클라우드 거버넌스 개요

> **마지막 업데이트**: 2026년 9월 9일

## 1. 이 섹션이 다루는 문제

지금까지의 EKS·네트워킹·보안 문서는 "클러스터 하나, VPC 하나"를 전제로 개별 기능을 설명했습니다. 하지만 수십 개 팀과 수백 명의 엔지니어가 여러 브랜드·도메인·서비스를 운영하는 대규모 엔터프라이즈 조직에서는 질문이 달라집니다.

- Account는 몇 개를 만들어야 하는가?
- VPC는 공유해야 하는가, 나눠야 하는가?
- EKS 클러스터는 팀마다 따로 둬야 하는가, 공용으로 써야 하는가?
- 이 세 가지 경계(Account/VPC/EKS)와 데이터 경계는 서로 일치해야 하는가?

이 섹션은 실제로 멀티 어카운트·멀티 EKS 환경을 운영 중인 대규모 e-commerce 조직이 AWS Solutions Architect와 진행한 아키텍처 표준화 검토를 기반으로 합니다. 특정 기업의 계정 ID·비용·조직 정보는 전혀 포함하지 않으며, **AWS 공식 문서로 검증된 quota·API 동작·서비스 제약**만 일반화한 원칙으로 정리했습니다. 즉 "이 회사는 이렇게 했다"가 아니라 "AWS 서비스가 실제로 이런 조건에서 막힌다"는 사실 기반 가이드입니다.

## 2. 왜 Account, VPC, EKS, Data 경계를 따로 생각해야 하는가

가장 흔한 실수는 팀이나 브랜드 단위로 Account를 만들고, 그 Account 안에 전용 VPC와 전용 EKS 클러스터를 자동으로 딸려 보내는 **1:1 고정 산식**입니다. 규칙은 단순하지만, 작은 워크로드에도 클러스터 하나만큼의 고정비가 붙고 조직 개편이 있을 때마다 인프라 전체가 마이그레이션 대상이 됩니다.

이 섹션이 제안하는 대안은 **경계마다 독립적으로 판정하는 것**입니다.

| 경계 | 판정 기준 |
|---|---|
| Account | 보안 요구, 서비스 quota, 비용·책임 소재, lifecycle |
| VPC | 네트워크 정책, trust zone(신뢰 경계), 연결 요구 |
| EKS | 런타임 장애 영향 범위, tenant 격리 요구, SLO |
| Data | 데이터 소유권, 규제 경계, 백업/복구 책임 |

이렇게 나누면 "이 워크로드는 별도 VPC가 필요 없지만 규제 때문에 전용 Account는 필요하다"처럼 세밀한 판단이 가능해집니다. 다만 대가도 있습니다 — 경계마다 판정 기준을 관리해야 하고, 예외가 늘어날 수 있습니다.

## 3. AWS가 경계를 강제로 묶는 4가지 조건

독립 판정 원칙을 세워도, AWS 서비스 자체의 동작 때문에 특정 경계는 강제로 결합됩니다. 이 조건은 선택이 아니라 설계 초기에 확정해야 하는 제약입니다.

1. **EKS 클러스터는 여러 VPC에 걸쳐 존재할 수 없습니다.** 두 클러스터를 서로 다른 장애 도메인으로 나누고 싶다면(예: A/B 클러스터 이중화), 그 두 클러스터는 자동으로 서로 다른 VPC에 있어야 합니다. EKS 경계는 언제나 VPC 경계의 하위 집합입니다.
2. **EKS Pod Identity role은 클러스터와 같은 Account에만 존재할 수 있습니다.** Kubernetes 워크로드를 별도의 "공유 클러스터 Account"에서 실행하면서 리소스(Lambda, SQS, RDS 등)는 각 워크로드 소유 Account에 두는 패턴을 쓰려면, cross-account 접근은 항상 "association role → target role" 2단 구조가 됩니다. 이건 최적화가 아니라 필수 구조입니다.
3. **Shared VPC에서도 EKS의 보안 그룹과 IAM role은 participant Account에 위치해야 합니다.** VPC를 공유해도 SG·IAM 경계는 Account 경계를 그대로 따라갑니다.
4. **데이터 경계는 서비스별로 갈립니다.** RDS처럼 VPC에 직접 배치되는 서비스가 있고, S3처럼 VPC 개념이 없는 서비스가 있습니다. Shared VPC의 subnet에 리소스를 만들 수 있는 서비스 목록은 AWS가 명시적으로 정해두고 있으며([Data·Security 경계](./05-data-security-boundaries.md) 참고), 이 목록 밖의 서비스를 쓰는 워크로드는 Shared VPC 전략에서 예외로 다뤄야 합니다.

## 4. 공유 우선 vs 전용 우선

경계를 독립 판정하기로 했다면, 다음 질문은 "분리할 이유가 없는 워크로드는 기본적으로 공유 자원에 둘 것인가, 전용 자원에 둘 것인가"입니다.

- **공유 우선**: 작은 워크로드를 공용 Account/VPC/클러스터에 먼저 수용합니다. 생성 속도가 빠르고 기반 중복이 줄지만, noisy neighbor 문제와 소유자 없는 공유 리소스가 누적될 위험이 있습니다.
- **전용 우선**: 분리 여부가 애매하면 전용 경계를 먼저 검토합니다. 비용·책임·장애 범위가 명확해지지만 고정비가 빠르게 증가합니다.

실무적으로는 **공유 우선으로 출발하되, 규제·독립 quota·강한 SLO 요구가 확인되면 전용으로 전환하는 Hybrid**가 합리적인 시작점입니다. 이 판단을 사람이 매번 새로 하지 않도록, 뒤에 나오는 [의사결정 프레임워크와 POC 설계](./06-decision-framework-and-poc.md)에서 재현 가능한 판정표를 만드는 방법을 다룹니다.

## 5. 안정적인 Workload ID와 변경 가능한 metadata

조직 개편, 브랜드 통합, 팀 이름 변경은 앞으로도 계속 일어납니다. 그런데 Account나 VPC 경계를 팀·브랜드 이름에 직접 묶으면, 조직 개편이 곧 인프라 마이그레이션이 됩니다.

권장하는 방식은 **안정적인 Workload ID**를 하나 두고, domain·brand·team·CUJ(critical user journey)·environment·data class·SLO는 그 ID에 붙는 **변경 가능한 metadata**로 관리하는 것입니다. Team은 조직 개편으로 바뀌지만, domain(business capability)은 상대적으로 안정적이므로 Account 경계의 기준으로는 team보다 domain이 낫습니다.

## 6. 이 섹션의 구성

| 문서 | 다루는 내용 |
|---|---|
| [Landing Zone, OU와 조직 Control](./01-landing-zone-and-ou.md) | Control Tower의 baseline 의존 관계, OU 설계, SCP/RCP/Tag Policy 역할 구분 |
| [Account 구성과 IAM 경계](./02-account-and-iam.md) | Account partitioning, 사람/워크로드 IAM, Kubernetes API 접근 |
| [EKS 멀티 계정·멀티 클러스터 아키텍처](./03-eks-multi-account-multi-cluster.md) | Shared/Dedicated 클러스터, A/B EKS Runtime 이중화의 실제 조건 |
| [Shared VPC와 Connectivity](./04-shared-vpc-and-connectivity.md) | Shared VPC의 실제 상한 체인, TGW/PrivateLink/Lattice 조합 |
| [Data·Security 경계](./05-data-security-boundaries.md) | cross-account 백업/복구 제약, 개인정보 계층 분리 |
| [의사결정 프레임워크와 POC 설계](./06-decision-framework-and-poc.md) | 판정표 설계, 누락되기 쉬운 결정 요소, POC 측정 지표 |

각 문서는 "이렇게 하는 게 좋다"는 의견보다 "AWS 서비스가 이 조건에서 이렇게 동작한다"는 검증된 사실을 우선하고, 조직의 판단이 필요한 부분은 명확히 구분해서 표시합니다.
