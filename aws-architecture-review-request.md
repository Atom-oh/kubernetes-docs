# AWS 인프라 표준화 아키텍처 검토 요청서

상태: 외부 검토용 Draft\
대상: AWS Principal SA 및 관련 Specialist SA\
작성 기준일: 2026-08-21

## 문서 구성

1. [문서 목적](#section-1)
2. [검토 요청 범위](#section-2)
3. [배경과 목표](#section-3)
4. [문장과 근거의 구분](#section-4)
5. [첫 검토에서 확인할 핵심 질문](#section-5)
6. [항목별 상세 선택지](#section-6)
7. [선택지 간 관계와 결합 검증](#section-7)
8. [공개 가능한 유사 사례에서 확인할 내용](#section-8)
9. [AWS와 함께 검토할 POC 후보](#section-9)
10. [기대하는 검토 결과](#section-10)
11. [이 문서에서 사용하는 주요 용어](#section-11)
12. [우리가 전제한 AWS 동작](#section-12)

<a id="section-1"></a>

## 1. 문서 목적

무신사는 AWS 인프라 표준화의 장기 목표 구조를 설계하고 있습니다. 이 문서는 내부 의사결정 자료에서 AWS의 검토가 필요한 선택지와 질문만 추려낸 외부 공유용 문서입니다.

다음 정보는 의도적으로 제외했습니다.

- Account ID, 리소스 이름과 상세 topology
- 실제 비용, 할인, credit와 상세 traffic 수치. 구조 비교에 필요한 거친 상대 비율은 포함할 수 있습니다.
- 현재 보안 설정의 상세 coverage와 취약 지점
- 내부 조직·담당자 정보와 의사결정 과정

이 문서의 선택지는 아직 승인된 결론이 아닙니다. 다만 모든 선택지를 같은 무게로 나열하지 않고, 현재 검토 방향·비교 후보·POC 후보·조건별 적용·대안·예외로 구분했습니다. AWS에는 현재 방향을 승인해 달라는 것이 아니라, 기술적으로 잘못 이해한 부분과 이 방향을 바꿔야 하는 조건을 검토해 달라고 요청합니다.

처음 읽을 때는 2장부터 4장까지 요청 범위와 배경을 확인한 뒤, 5장의 핵심 질문에 먼저 답변해 주시면 됩니다. 6장은 판단 근거가 필요한 상세 선택지이고, 7장 이후는 결합 검증과 후속 검토 자료입니다.

<a id="section-2"></a>

## 2. 검토 요청 범위

각 항목에 대해 우선 다음 세 가지를 중심으로 답변해 주시기를 요청드립니다.

1. **기술적 타당성**: 지원되지 않거나 잘못 이해한 AWS 동작이 있는지 확인해 주십시오.
2. **AWS 기술 관점의 조건과 제약**: 각 선택지가 성립하는 AWS 서비스 조건, quota·지원 한계와 반복적으로 문제가 된 구성을 알려 주십시오. AWS 공식 지침이나 명확한 운영 근거가 있는 경우에만 선호하거나 피할 방향을 함께 알려 주십시오.
3. **중요한 누락**: 보안, 가용성, 운영과 migration에서 결정을 바꿀 정도로 중요한 조건이 빠졌는지 알려 주십시오.

모든 선택지의 순위를 매겨 달라고 요청하지는 않습니다. 현재 검토 방향을 표시하되, AWS 기술 관점에서 성립 여부와 적용 조건을 독립적으로 판단해 주십시오. 선택지 ID는 우선순위가 아니라 답변과 ADR을 연결하기 위한 식별자입니다.

조직 책임, 비용 배분, 위험 수용 수준과 최종 선택은 무신사가 결정합니다. AWS에는 이를 대신 결정해 달라고 요청하지 않습니다. AWS 서비스의 quota·지원 범위·장애 특성·cross-account 제약처럼 고객이 임의로 바꿀 수 없는 조건과, 유사 규모에서 반복적으로 문제가 된 기술적 선택을 확인하고자 합니다.

비용 차이가 선택을 좌우하는 항목은 주요 과금 요소와 비교 방법을, 기술 판단에 근거가 필요한 항목은 AWS 공식 문서를 함께 알려 주시면 됩니다. 8장의 공개 사례와 9장의 POC 후보는 첫 검토에서 모두 답변하거나 수행해 달라는 요청이 아닙니다. 5장의 핵심 질문과 6~7장의 선택지를 좁힌 뒤, 판단에 필요한 항목만 후속으로 검토하고자 합니다.

2025년 WADD와 당시의 비식별 규모·topology는 최근 AWS와 별도 세션에서 다시 검토했으며, 확인한 내용은 이 문서의 선택지와 평가에 반영했습니다. 이 문서에서는 이미 공유한 inventory나 WADD 전체를 다시 검토해 달라고 요청하지 않습니다. 검토 결과를 바꿀 정도의 현황 변화가 있으면 해당 질문에서만 보완합니다.

AWS 공식 문서나 기존 기술 자료로 답변할 수 있는 항목은 서면 답변만으로도 충분합니다. 추가 분석이나 Specialist SA 참여가 필요한 항목, AWS의 일반적인 기술 자문 범위를 벗어나는 요청, 범위가 너무 큰 요청은 그렇게 표시해 주시면 우선순위를 다시 조정하겠습니다. 고객 대외비나 비공개 정보를 요청하지 않습니다.

답변을 확정하기 어려운 항목은 `추가 자료 필요`, `POC 필요`, `보안팀 공동 검토 필요`로 구분하고 필요한 입력만 알려 주시면 됩니다.

첫 검토에서는 5장의 여섯 가지 핵심 질문을 우선합니다. 6장의 항목별 질문은 이번 문서에서 삭제하지 않고 `상세·후속 질문`으로 보존하며, 핵심 답변에 추가 확인이 필요할 때 이어서 검토합니다.

<a id="section-3"></a>

## 3. 배경과 목표

무신사는 수십 개 팀과 수백 명의 엔지니어가 Musinsa·29CM 등의 brand와 많은 서비스를 운영하는 e-commerce 조직입니다. `One Core`는 Musinsa의 여러 brand가 공통으로 사용하는 business domain들의 집합을 뜻합니다. 이미 multi-account와 여러 EKS cluster를 사용하고 있으며, 앞으로도 brand·domain·팀과 workload가 추가·통합·종료될 수 있습니다.

현재 AWS network는 중앙 TGW를 중심으로 여러 Workload VPC와 on-prem network가 연결된 hub-and-spoke 구조입니다. On-prem에는 사옥·서버실, MLOps, 물류와 SASE 보안망이 있으며 VPN 연결을 사용합니다. 상세 topology, 내부 Account·망 이름, Account별 수치와 절대 비용은 이 문서에 포함하지 않습니다.

이번 결정 범위는 `ap-northeast-2`(서울) 단일 Region입니다. Multi-Region DR은 이번 검토 범위에 포함하지 않으며, 향후 다른 Region을 추가할 수 있도록 Account·IPAM·DNS와 network 설계에서 Region을 독립된 축으로 유지합니다.

이 문서에서 `규제 경계`는 개인정보보호법, ISMS-P와 보안팀의 내부 security 기준에 따라 별도 접근·기록·격리가 필요한 범위를 뜻합니다. 규제 경계라는 이유만으로 Account나 VPC 분리를 자동 결정하지 않고, 달성하려는 control objective와 필요한 IAM·KMS·network·logging control을 함께 확인합니다.

이번 표준화의 목표는 현재 운영 인력이나 기존 도구에 가장 편한 구조를 고정하는 것이 아닙니다. 장기 목표를 먼저 정하고, 현실적인 전환은 그 목표에서 멀어지지 않는 방향으로 단계적으로 진행하려고 합니다.

다음 원칙을 공통 전제로 두고 있습니다.

- Account, VPC, EKS와 데이터는 서로 관련되지만 같은 경계가 아닙니다.
- 중앙 Platform 역할은 guardrail, 공통 기반과 표준 제공 경로(paved road)를 제공하고, workload 소유 팀은 비용·SLO·배포·장애·lifecycle을 책임지는 분산 ownership model을 검토합니다.
- 모든 workload에 같은 Account·VPC·EKS를 공유하게 하거나, 반대로 workload마다 전용 Account·VPC·EKS를 만드는 방식을 일괄 적용하지 않습니다. 보안, quota, 장애 영향, 비용과 운영 책임을 기준으로 각 경계를 공유할지 분리할지 결정합니다.
- 지금 선택한 옵션에서 다른 옵션으로 이동할 수 있도록 identity, DNS, 데이터, 정책과 ownership 정보를 처음부터 유지합니다.
- AI-native는 물리 구조를 대신하는 제품이 아니라 discovery·plan·검증·상태 대조·복구를 안전하게 자동화하는 공통 운영 원칙입니다.
- 선택지를 명시적으로 나누는 이유는 AI와 자동화가 결정 이후 `선택한 기본값 적용`, `선택하지 않은 옵션 차단`, `조건 충족 시에만 조건부 옵션 허용`, `예외 만료 확인`을 수행할 수 있는 실행 계약을 만들기 위해서입니다.

### 현재 검토 방향

아래 내용은 승인된 결론이 아니라 AWS 검토의 출발점입니다. AWS 서비스 제약이나 운영 위험이 이 방향을 바꿔야 한다면 그 조건을 확인하고자 합니다.

| 영역 | 현재 검토 방향 | 아직 열어 둔 조건 |
|---|---|---|
| 경계 | Account·VPC·EKS·Data 수를 각각 판정하고 공유와 전용을 함께 사용합니다. | 특정 AWS 서비스가 경계를 결합하도록 요구하는 경우 |
| Landing Zone·OU | Control Tower의 조직 control과 내부 workload bootstrap을 분리하고, 단계적 전환을 검토합니다. OU는 평면형과 얕은 functional 혼합형을 함께 비교합니다. | 기존 Account 편입 충돌, effective policy와 운영 책임 |
| Account·IAM | team이나 brand를 Account 축으로 고정하지 않고 domain·보안·quota·lifecycle로 판정합니다. 사람은 Identity Center, workload는 임시 role을 기본으로 합니다. | brand 독립 규제·손익·분사와 서비스별 cross-account 제약 |
| EKS | Shared Cluster와 Dedicated Cluster를 함께 사용하고, 선택한 CUJ(critical user journey)만 A/B EKS Runtime에 배포하는 방식을 검토합니다. | tenant isolation, surviving capacity, 공통 dependency와 실제 SLO |
| VPC·Connectivity | 같은 trust zone은 Shared VPC를 활용하되 개인정보·규제 경계는 전용 VPC로 분리합니다. 최소 Shared VPC Pool과 Workload별 전용 Shared VPC를 비교하고 연결은 traffic 요구별로 선택합니다. | SG·NACL·DNS 통제, quota, inspection과 on-prem 요구 |
| Data·Security | workload lifecycle과 data 책임을 가깝게 두되 공통 data platform은 별도 소유를 허용합니다. 기존 CNAPP와 AWS-native 기능은 보안 목적별 지원 범위로 비교합니다. | 개인정보 경계, cross-account KMS·backup·restore와 AWS 고유 telemetry |
| 전환·운영 | Workload별 점진 전환과 위험 등급별 AI-assisted 운영을 검토합니다. | 변경 위험, rollback 가능성, audit와 실제 상태 대조 |

이 문서의 `중앙 Platform 역할`, `network owner`, `보안 역할`, `workload 소유 팀`은 현재 조직명을 고정하는 표현이 아니라 목표 운영 모델의 논리적 책임입니다. 중앙 Platform 역할은 Account 공급·공통 guardrail·표준 module을, network owner는 VPC·IP·route·DNS 기반을, 보안 역할은 control objective와 finding 대응 기준을, workload 소유 팀은 application·data·SLO·비용과 장애 대응을 책임합니다. 세부 RACI는 선택한 구조가 좁혀진 뒤 별도 운영 설계에서 확정합니다.

<a id="section-4"></a>

## 4. 문장과 근거의 구분

| 구분 | 의미 |
|---|---|
| AWS 공식 동작 | 현재 AWS 공식 문서로 확인한 서비스 기능이나 제약입니다. |
| 무신사 내부 판단 | AWS 답변을 받은 뒤 별도 ADR에서 확정할 판단입니다. 이 요청서에는 현재 검토 방향과 아직 열어 둔 조건을 구분해 표시합니다. |
| 작업 가설 | 기술적으로 가능해 보이지만 규모·비용·운영 효과를 POC나 실측으로 확인해야 합니다. |

특히 `A/B EKS Runtime`(두 EKS cluster로 cluster 수준의 장애 영향을 나누는 방식)과 `최소 VPC·Shared VPC Pool`은 무신사 작업 가설입니다. AWS의 일반 권고로 인용하지 않습니다.

<a id="section-5"></a>

## 5. 첫 검토에서 확인할 핵심 질문

아래 여섯 질문을 첫 답변 범위로 요청합니다. 6장의 세부 질문은 이 답변만으로 판단하기 어렵거나 Specialist 검토가 필요할 때 이어서 확인합니다.

1. **경계 산정**: Account, VPC, EKS와 Data 경계를 서로 다른 기준으로 산정할 때, AWS 서비스의 quota·cross-account 지원·장애 특성 때문에 특정 경계를 1:1로 맞추거나 특정 구성을 피해야 하는 조건이 있습니까?
2. **Landing Zone·OU·Control**: 기존 Account를 Control Tower에 단계적으로 편입하고 Root에는 최소 control, OU에는 version이 있는 policy 묶음을 적용하려고 합니다. Control Tower와 내부 pipeline의 책임, OU 상속과 effective policy 측면에서 이 방향을 바꿔야 하는 제약이 있습니까?
3. **Account·IAM**: Account는 team이나 brand보다 domain·보안·quota·lifecycle로 판정하고, Kubernetes workload는 별도 Shared Cluster Account에서도 실행할 수 있게 하려고 합니다. 이 구조를 제한하는 IAM·EKS·RAM·network의 cross-account 제약이나 규모 한계가 있습니까?
4. **EKS 가용성**: 일반 workload는 Shared Cluster에 두고 강한 격리가 필요한 workload만 분리하며, 선택한 CUJ는 두 A/B EKS Runtime에 배포하려고 합니다. Cluster 분리 기준과 CUJ 이중화가 실질적인 가용성 향상을 제공하기 위한 AWS 측 조건은 무엇입니까?
5. **VPC·Connectivity**: 같은 trust zone의 workload는 중앙 소유 Shared VPC를 사용하고 개인정보·규제 경계는 전용 VPC로 분리하려고 합니다. 최소 Shared VPC Pool과 Workload별 전용 Shared VPC의 quota·owner/participant 제약, 그리고 Peering·TGW·PrivateLink·Lattice·inspection을 traffic 요구별로 조합할 때 빠진 제약이 있습니까?
6. **Data·Security**: Workload-owned data와 공통 Data Platform을 함께 사용하고 Development·QA의 Production 원본 데이터 접근을 차단하려고 합니다. cross-account KMS·backup·restore, 개인정보 경계와 AWS-native security telemetry 측면에서 반드시 보완해야 할 조건이 있습니까?

<a id="section-6"></a>

## 6. 항목별 상세 선택지

각 표는 선택지의 구성, 장점, 위험과 성립 조건을 같은 순서로 보여 줍니다. 선택지 ID는 답변과 ADR을 연결하기 위한 고유 식별자입니다. 서로 함께 적용할 수 있거나 포함 관계인 항목은 별도 결정 축으로 나눕니다. 각 절의 `상세·후속 질문`은 첫 검토에서 모두 답변받지 않고, 5장의 답변만으로 판단하기 어려운 항목만 이어서 확인합니다.

상태 표현은 다음 의미로 사용합니다. `현재 검토 방향`은 잠정 방향, `비교 후보`는 결론 전 비교할 대안, `POC 후보`는 실측이 필요한 가설, `조건별 적용`은 요구에 따라 여러 항목을 함께 쓰는 pattern, `대안`은 현재 방향이 아니지만 판단 근거를 보존할 항목, `예외`는 명시적인 승인과 종료 조건이 필요한 항목입니다. Connectivity·IAM처럼 서로 배타적이지 않은 표는 표 앞에서 `조건별 적용`임을 밝히며, 그 행에 일률적인 순위를 붙이지 않습니다.

### 6.1 운영 모델과 경계 기준

#### 결정할 내용

Account, VPC, EKS와 데이터 경계를 어떤 기준으로 나누고 누가 운영 결과를 소유할지 결정합니다.

##### 경계 산정 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| BND-A · Domain×Environment 고정 산식 | domain과 environment 조합마다 Account·VPC·EKS를 같은 단위로 함께 만듭니다. 규칙과 수량 예측이 단순합니다. | 서로 다른 경계를 같은 단위로 취급하고 domain 변화가 전체 구조에 전파됩니다. | 대안입니다. AWS 서비스 제약 때문에 세 경계를 1:1로 맞춰야 하는 경우가 있는지 확인해야 합니다. |
| BND-B · 경계별 독립 판정 | Account는 보안·quota·책임, VPC는 network·trust zone, EKS는 runtime 장애 영향을 기준으로 각각 나눕니다. 실제 요구에 맞게 각 경계의 수를 독립적으로 정할 수 있습니다. | 판정표와 선택지 간 의존 관계를 계속 관리해야 합니다. | 현재 검토 방향입니다. 대표 workload에 판정표를 적용했을 때 결과가 일관되고 예외율이 감당 가능해야 합니다. |

##### 공유·전용 경계의 기본 방향

BND-B로 각 경계를 독립 판정할 때, 분리 사유가 없는 workload를 공유 기반에 둘지 전용 경계에 둘지 결정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| BND-C · 중앙 공유 우선 | Account·VPC·EKS 각각에서 분리 사유가 없는 작은 workload는 해당 공용 기반에 먼저 수용합니다. 초기 생성 속도를 높이고 기반 중복을 줄일 수 있습니다. | 한 workload의 과도한 사용이 다른 workload에 영향을 주는 noisy neighbor 문제, quota와 책임자 없는 공유 resource가 누적될 수 있습니다. | 현재 검토 방향입니다. 수용 quota, 분리 threshold, owner와 shared resource 정리 기준이 있어야 합니다. |
| BND-D · 전용 경계 우선 | Account·VPC·EKS 각각에서 분리 여부가 애매하면 공유보다 전용 경계를 먼저 검토합니다. 선택한 경계의 비용과 운영 책임, 장애 영향 범위가 명확해집니다. | Account·VPC·cluster와 고정비가 빠르게 증가합니다. | 조건별 적용입니다. 규제·독립 quota·강한 SLO나 장애 격리처럼 분리 비용을 정당화하는 요건이 있어야 합니다. |

BND-B는 Account·VPC·EKS·데이터의 수를 각각 정하는 방식이고, BND-C와 BND-D는 각 경계를 공유할지 전용으로 둘지를 판단하는 방식입니다. 현재는 BND-C를 출발점으로 하되 규제·독립 quota·강한 SLO처럼 분리 사유가 확인되면 BND-D를 적용하는 Hybrid를 검토합니다. 어떤 조합을 선택하더라도 안정적인 Workload ID를 두고 domain, brand, team, CUJ, environment, data class와 SLO는 변경 가능한 metadata로 관리하려고 합니다. 중앙 Platform 역할은 공통 control plane과 표준 제공 경로(paved road)를 제공하고, workload 소유 팀은 운영 결과를 책임지는 분산 ownership model을 검토합니다.

(근거: [AWS multi-account design principles](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html))

#### 상세·후속 질문

1. 위 분산 ownership model에서 Organizations delegated administrator, Security·Log Archive, network owner처럼 AWS 기능상 중앙 관리가 필요한 범위와 workload 소유 팀에 위임할 수 있는 범위를 구분하는 제약이 있습니까?

### 6.2 Landing Zone, OU와 조직 Control

#### Landing Zone 목표 플랫폼

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| LZ-PLATFORM-1 · Control Tower | Account 생성과 조직 baseline·control에 Control Tower를 사용합니다. AWS managed update와 Account Factory를 활용할 수 있습니다. | 기존 설정과 충돌할 수 있고 Control Tower가 지원하지 않는 내부 요구는 별도 automation이 필요합니다. | 현재 검토 방향입니다. 기존 Account 편입 충돌과 Control Tower가 소유할 resource를 확인해야 합니다. |
| LZ-PLATFORM-2 · Organizations + Custom Landing Zone | Control Tower 대신 Organizations와 내부 자동화로 Account 생성·기본 설정·control을 운영합니다. 내부 lifecycle과 toolchain에 맞게 설계할 수 있습니다. | Account 생성·초기 설정, baseline·control update와 drift 탐지·복구를 직접 운영해야 합니다. | 대안입니다. 이 기능과 운영 책임자를 내부에서 지속 제공할 수 있어야 합니다. |

#### 기존 Account 전환 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| LZ-MIG-1 · 일괄 전환 | 기존 Account를 짧은 기간에 Control Tower 관리 대상으로 함께 편입합니다. 하나의 baseline으로 빠르게 수렴할 수 있습니다. | Config·CloudTrail·SCP·IAM 충돌이 동시에 발생하면 영향과 복구 범위가 큽니다. | 대안입니다. 영향 범위가 작고 기존 설정 충돌을 전수 검사하며, Account별 enrollment 실패 격리와 편입 전 상태 복구 절차를 검증한 경우에만 검토합니다. |
| LZ-MIG-2 · 단계적 전환 | 신규 또는 일부 Account부터 편입해 작은 범위에서 충돌과 운영 절차를 확인합니다. | 기존 model과 새 model이 공존하며 임시 운영이 길어질 수 있습니다. | 현재 검토 방향입니다. Pilot 범위, 차수별 성공·중단 조건과 기존 model 종료 시점을 정해야 합니다. |

#### Control Tower와 내부 pipeline의 책임

Landing Zone·조직 control은 Control Tower가 담당하고 내부 pipeline은 workload 배포에 필요한 IAM, network 연결과 공통 설정을 적용하는 방향을 검토합니다. 두 도구가 같은 resource를 생성하거나 수정하지 않도록 resource별 owner, 변경 경로와 drift 처리 책임을 먼저 정합니다. 이 책임 분리는 목표 플랫폼과 기존 Account 전환 방식과 별개의 결정입니다.

현재 설계 검토는 Control Tower landing zone 4.0의 동작을 기준으로 합니다. 4.0에서는 AWS Config·CloudTrail·SecurityRoles·Backup 등의 service integration을 선택하고, member Account에 적용할 resource는 OU별 baseline과 control로 구분합니다. 특히 landing zone 수준의 Config integration은 일반 member Account에 Config recorder를 자동 배포하는 설정이 아니므로, 활성화할 service integration과 OU baseline 조합별로 Control Tower와 내부 pipeline의 resource ownership을 정합니다. 실제 구축 시에는 당시 최신 지원 version의 변경 사항을 다시 확인합니다.

Auto-enrollment는 landing zone 3.1 이상에서 사용할 수 있으며, 등록된 OU로 Account를 이동하면 해당 OU의 baseline과 control을 적용합니다. 이를 사용하면 `Account 이동 → 자동 enrollment → 내부 workload bootstrap` 순서를 명시하고, 수동 enrollment와 자동 enrollment 중 어느 경로를 표준으로 할지 결정해야 합니다. Auto-enrollment가 사전 검사를 대신하지는 않으므로 Config 등 기존 설정 충돌, 실패한 Account의 격리 위치, 재시도·복구와 내부 pipeline 시작 조건을 별도로 검증합니다. `Transitional OU`는 이 사전 검사와 실패 격리에 사용하며, 등록 OU로 이동한 뒤 자동 enrollment가 시작되는 구조와 역할이 겹치지 않게 합니다.

기존 Account 편입 시 전제한 Control Tower 동작과 근거는 12장에 정리했습니다.

#### OU 선택지

OU와 Account 유형은 순차적으로 한 번씩 확정하지 않습니다. Account 유형·lifecycle 가설에서 필요한 control 차이로 OU 후보를 만들고, 실제 Account를 배치해 effective policy를 확인한 뒤 Account 유형 또는 OU를 다시 조정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| OU-1 · 깊은 계층형 OU | Root 아래에 Workload, Production, Standard처럼 분류를 여러 단계로 중첩하고 상위 control을 하위 OU가 상속합니다. 분류와 공통 control을 hierarchy에 표현하기 쉽습니다. | 상위 Deny 영향이 넓고 여러 분류 축이 hierarchy에 고정됩니다. | 대안입니다. 상속 재사용의 이점과 상위 control 변경의 영향 범위를 함께 검증해야 합니다. |
| OU-2 · Root 하위 평면형 OU | Production-Standard, Sandbox 같은 OU를 대부분 Root 바로 아래에 두고 control을 OU별로 직접 연결합니다. OU별 영향 범위를 설명하기 쉽습니다. | 공통 policy 중복과 누락이 생길 수 있습니다. | 비교 후보입니다. 공통 policy의 중복·누락과 attachment drift를 자동 검증할 수 있어야 합니다. |
| OU-3 · 얕은 functional 혼합형 | Security·Infrastructure처럼 쉽게 변하지 않는 기능 OU를 기본으로 하고, Production·Non-production Workload OU와 Transitional·Suspended 같은 절차 OU를 얕게 조합합니다. 조직도 변화의 영향을 줄이면서 운영 상태를 표현할 수 있습니다. | Functional 분류, lifecycle, inheritance와 policy bundle을 함께 검증해야 합니다. | 비교 후보입니다. Account 이동 전후의 effective policy와 예외 만료 절차가 검증되어야 합니다. |

OU-3을 적용할 경우 `Security`, `Infrastructure`, `Workloads/Production`, `Workloads/Non-production`, `Sandbox`, `PolicyStaging`, `Transitional`, `Suspended`를 시작점으로 둘 수 있습니다. `Network`는 별도 OU로 둘지 `Infrastructure` 아래에 둘지 실제 control 차이로 결정합니다. `Transitional`은 인수·이전한 Account를 표준 OU에 넣기 전 검사하는 임시 위치이고, `Suspended`는 폐기 예정 Account의 일반 변경을 막는 위치입니다. 침해 의심 Account를 위한 `Quarantine`은 조사 권한·증거 보존·복구 절차가 Suspended와 실제로 다를 때만 별도 OU 또는 절차로 둡니다.

상시 `Production-Exception` OU와 만료되는 예외 정책도 구분합니다. 특정 API나 정책을 일정 기간만 허용할 수 있으면 표준 Production OU 안에서 승인 범위와 만료일이 있는 예외로 처리하고, Account 전체에 장기간 다른 control이 필요하거나 표준 control과 기술적으로 양립하지 않을 때만 별도 OU를 검토합니다.

(근거: [AWS recommended OUs and Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html))

#### SCP와 조직 Control 선택지

SCP를 어디에 연결할지와 어떤 허용·차단 방식을 사용할지는 별도 결정입니다. 연결 위치는 첫 번째 표에서 하나를 선택하고, 허용·차단 방식은 OU의 목적에 따라 두 번째 표의 방식을 조건별로 함께 적용할 수 있습니다.

##### SCP 연결 위치와 상속 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| SCP-ATT-1 · Root-heavy | 조직 전체에 동일하게 적용할 다수의 SCP를 Root에 연결하고 하위 OU가 상속하게 합니다. 신규 Account도 Root에 연결된 control을 즉시 상속합니다. | 잘못된 변경의 영향이 조직 전체로 확산되고 OU별 예외를 만들기 어렵습니다. | 대안입니다. 조직 전체에 동일한 다수 control이 필요하고 OU별 예외가 거의 없을 때만 성립합니다. |
| SCP-ATT-2 · OU별 완성형 직접 연결 | 각 OU에 필요한 SCP 전체를 직접 연결하고 상위 OU 의존을 줄입니다. OU별 독립 시험과 작은 변경 영향 범위를 확보합니다. | policy 중복, drift와 attachment가 증가합니다. | 비교 후보입니다. OU별 policy bundle 생성과 attachment drift를 자동 검증할 수 있어야 합니다. |
| SCP-ATT-3 · Layered bundle | Root에는 절대 예외가 없는 최소 SCP만 두고, 나머지는 version이 있는 OU별 policy 묶음과 만료되는 예외로 적용합니다. 공통 기준과 작은 rollout 범위를 함께 확보합니다. | catalog, 조합과 effective policy 검증이 필요합니다. | 현재 검토 방향입니다. Policy version, staging, effective policy 검사와 rollback 절차가 있어야 합니다. |

##### 허용·차단 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| SCP-MODE-1 · Allow-list 중심 | 명시적으로 허용한 AWS 서비스와 API만 사용할 수 있게 SCP를 구성합니다. 제한 구역을 강하게 통제할 수 있습니다. | 신규 서비스와 숨은 dependency를 차단할 수 있습니다. | 조건별 적용입니다. Sandbox·규제 구역처럼 사용 가능 서비스를 사전에 제한할 수 있는 범위에 적용합니다. |
| SCP-MODE-2 · Deny-list 중심 | 대부분의 서비스 사용을 허용하고 위험한 서비스·API·리전만 명시적으로 차단합니다. 일반 workload의 자율성과 AWS 변화를 수용하기 쉽습니다. | 누락된 위험과 새 API를 별도로 탐지해야 합니다. | 현재 검토 방향입니다. 일반 Workload OU에서 새 서비스·API 위험을 탐지하고 Deny catalog를 갱신하는 절차가 있어야 합니다. |

SCP·RCP·declarative policy에 대해 전제한 AWS 동작과 근거는 12장에 정리했습니다.

#### 상세·후속 질문

1. Control Tower와 내부 pipeline이 같은 AWS resource를 중복 관리하지 않도록 책임을 나누려고 합니다. Landing zone 4.0에서 활성화할 service integration과 OU별 baseline 조합을 기준으로, Control Tower가 소유해야 하는 resource와 내부 pipeline에 두어도 되는 workload 초기 설정의 경계, 기존 Account 편입 전 검사할 충돌 항목은 무엇입니까? Auto-enrollment를 사용할 때 Account 이동·사전 검사·실패 격리·workload bootstrap 순서도 확인하고 싶습니다.
2. 위 얕은 혼합형 OU와 Layered policy bundle에서 Organizations·Control Tower의 상속, policy attachment나 quota 때문에 성립하지 않거나 운영 위험이 커지는 부분이 있습니까?
3. SCP는 principal의 최대 권한, RCP는 지원 resource의 resource policy가 허용할 수 있는 접근의 최대 범위, declarative policy는 지원 서비스의 조직 공통 설정, Tag Policy는 tag 준수, Control Tower control은 예방·사전 검사·탐지 control로 사용하려고 합니다. 이 구분에서 중복되거나 잘못 이해한 AWS 동작이 있습니까?

### 6.3 Account와 IAM

#### Account Partitioning 선택지

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| ACC-1 · Domain×Environment | 각 domain에 Production·Non-production Account를 별도로 제공합니다. 비용·quota·권한과 운영 책임을 domain에 연결하기 쉽습니다. | 작은 domain에도 고정비가 들고 domain 재편이 migration으로 이어집니다. | 비교 후보입니다. Domain에 독립 lifecycle·quota·보안 또는 장애 책임이 있을 때 적용합니다. |
| ACC-2 · Domain×Brand×Environment | domain Account를 brand와 environment별로 다시 나눕니다. brand별 격리와 독립 lifecycle이 명확합니다. | brand 수와 domain 수의 곱으로 Account가 증가합니다. | 대안입니다. 규제·분사처럼 brand를 독립 경계로 유지할 강한 이유가 있을 때만 적용합니다. |
| ACC-3 · Brand×Environment | Musinsa·29CM 같은 brand와 environment별로 Account를 만들고 여러 domain을 그 안에 둡니다. brand별 비용·quota·권한과 분리·이관을 Account 경계로 관리할 수 있습니다. | 여러 brand가 함께 쓰는 One Core의 ownership이 모호해지고 작은 brand Account는 유휴 기반이 늘 수 있습니다. Brand lifecycle 변화가 Account 재편으로 이어지며 domain별 권한·quota 차이를 Account 안에서 다시 구현해야 합니다. | 대안입니다. One Core와 brand별 기능의 규모 비대칭보다 독립 손익·규제·분사 가능성이 더 강한 경우에 성립합니다. |
| ACC-4 · 소수 중앙 Workload Account | 여러 domain과 팀의 workload를 소수의 공용 Account에 함께 둡니다. 초기 운영과 작은 workload 수용이 단순합니다. | quota·권한·장애 영향이 커지고 나중 분리가 어려워집니다. | 비교 후보입니다. 작은 공용 workload에 한정하고 수용 quota, owner와 Account 분리 절차가 있어야 합니다. |
| ACC-5 · Hybrid portfolio | 작은 workload는 공용 Account에, 강한 domain·규제·quota 경계가 있는 workload는 전용 Account에 둡니다. 요구에 따라 공유·domain·전용 Account를 조합할 수 있습니다. | 판정 기준이 약하면 예외가 증가합니다. | 현재 검토 방향입니다. 공유·domain·전용 Account의 수용·분리 기준이 동일한 판정표로 재현되어야 합니다. |

Account는 팀 이름 자체가 아니라 관련 workload가 공유하는 보안, quota, 비용 책임과 lifecycle로 판단합니다. Team은 조직 개편으로 바뀔 수 있지만 domain은 business capability와 lifecycle에 연결되므로 상대적으로 안정적인 Account 후보입니다. 팀에는 Identity Center Permission Set을 부여합니다. Brand는 비용 구분만 필요하면 metadata로 두고, 규제·독립 quota·권한·분사 같은 강한 경계가 있을 때만 Account 축으로 사용합니다. ACC-1부터 ACC-5까지를 대표 workload에 적용해 Account 수·고정비·권한과 lifecycle 차이를 비교합니다.

여러 domain의 데이터를 수집해 API로 제공하는 workload는 독립 SLO·quota·data access와 lifecycle이 있으면 별도 Workload Account 후보가 될 수 있습니다. 별도 Account가 별도 EKS를 뜻하지는 않습니다.

(근거: [EKS multi-account strategy](https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html))

#### Account와 EKS 실행 관계

Account partitioning을 정한 뒤, Kubernetes workload를 같은 Account의 EKS에서 실행할지 별도 Shared Cluster Account에서 실행할지 결정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| RUN-1 · Workload Account별 EKS | 각 Workload Account가 자체 EKS cluster를 소유하고 Kubernetes workload를 실행합니다. Account·runtime 책임과 장애 경계가 일치합니다. | 작은 workload에도 cluster가 필요해 관리할 cluster 수와 유휴 capacity가 증가합니다. | 비교 후보입니다. Account와 EKS를 함께 분리해야 할 tenant·quota·SLO 요건이 있을 때 성립합니다. |
| RUN-2 · Workload Account + Shared Cluster Account | Lambda·SQS·DB 같은 resource는 Workload Account가 소유하고 Kubernetes workload는 별도 Cluster Account의 공유 EKS에서 실행합니다. Account 경계와 관리할 EKS cluster 수를 독립적으로 결정할 수 있습니다. | cross-account identity·network와 shared cluster 책임이 복잡해집니다. | 현재 검토 방향입니다. Cross-account identity·network와 cluster incident ownership을 POC로 확인해야 합니다. |

#### Workforce와 Workload IAM 선택지

사람의 AWS 접근, application의 AWS API 접근과 Kubernetes API 접근은 서로 다른 결정입니다.

##### 사람의 AWS 접근

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| IAM-H1 · Identity Center + RBAC | 사용자는 Identity Center로 로그인하고 직무·역할별 Permission Set을 통해 Account에 접근합니다. 임시 credential과 중앙 회수·감사가 가능합니다. | team×domain×environment 조합으로 Permission Set이 늘 수 있습니다. | 현재 검토 방향입니다. Permission Set 조합과 lifecycle을 중앙에서 관리해야 합니다. |
| IAM-H2 · RBAC + 제한된 ABAC | IAM-H1의 직무별 최대 권한 안에서 tag로 resource 범위를 더 제한합니다. 권한 상한과 확장성을 함께 확보할 수 있습니다. | RBAC·ABAC를 모두 시험하고 tag 발급자를 통제해야 합니다. | 조건별 적용입니다. Permission Set 수, tag 변경 권한과 권한 확대 방지 검사가 감당 가능할 때 적용합니다. |
| IAM-H3 · ABAC 중심 | 사용자와 resource tag가 일치할 때 권한을 주로 부여합니다. Account와 workload가 늘어도 policy 복제를 줄일 수 있습니다. | tag authority가 약하면 권한 확대와 debug 난이도가 커집니다. | 대안입니다. 신뢰할 수 있는 tag 발급·변경 통제와 권한 simulation이 갖춰질 때만 다시 검토합니다. |

Account별 IAM user는 일반 선택지에서 제외합니다. Identity Center를 사용할 수 없는 비상 접근에만 목적·owner·사용 조건·credential 보관·정기 검증·종료 조건을 명시해 예외로 관리합니다.

##### Application과 automation의 AWS 접근

아래 항목은 서로 배타적인 선택지가 아니라 실행 환경과 cross-account 접근 여부에 따른 `조건별 적용` pattern입니다. Static access key는 role이나 federation을 지원하지 않는 legacy 연동에만 목적·owner·만료일·rotation을 명시해 예외로 허용합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| IAM-W1 · Runtime role | EC2·Lambda·ECS 등 실행 환경에 IAM role을 연결해 임시 credential을 사용합니다. 장기 access key를 제거할 수 있습니다. | 공유 role과 cross-account trust가 넓어질 수 있습니다. | EKS 외 workload에 최소 권한 role과 제한된 cross-account trust를 적용합니다. |
| IAM-W2 · EKS Pod Identity | EKS Pod와 IAM role을 Pod Identity association으로 연결합니다. Cluster 안에서 service account별 AWS 권한을 분리할 수 있습니다. | EKS Pod Identity Agent와 association lifecycle을 운영해야 합니다. | 현재 검토 방향입니다. 지원되는 EKS workload에 적용합니다. |
| IAM-W3 · IRSA | Kubernetes service account token과 IAM OIDC provider를 사용해 Pod에 role을 연결합니다. 기존 EKS와 toolchain에서 널리 사용할 수 있습니다. | OIDC provider와 trust policy를 cluster별로 관리해야 합니다. | 기존 IRSA workload 또는 Pod Identity로 바로 전환하기 어려운 경우에 적용합니다. |
| IAM-W4 · Cross-account target role | IAM-W1부터 IAM-W3까지의 source role이 resource Account의 target role을 assume합니다. Workload 실행 위치와 resource ownership을 분리할 수 있습니다. | role chaining, trust와 session policy가 복잡해집니다. | Cross-account resource 접근이 필요한 경우에만 최소 권한 trust와 session을 검증합니다. |

##### Kubernetes API 접근

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| K8S-AUTH-1 · EKS Access Entries를 통한 Access Policy 또는 RBAC 연결 | IAM principal의 cluster 접근을 EKS Access Entry로 관리하고, EKS Access Policy를 연결하거나 Kubernetes group에 mapping해 RBAC을 사용합니다. Access lifecycle을 EKS API에서 관리할 수 있습니다. | 두 방식을 함께 사용하면 허용 권한이 합쳐지며 한쪽의 권한으로 다른 쪽을 제한할 수 없습니다. | 현재 검토 방향입니다. Principal별 주 권한 부여 경로를 정하고 Access Policy와 RBAC의 중복 grant를 검사해야 합니다. |
| K8S-AUTH-2 · aws-auth ConfigMap | IAM principal과 Kubernetes identity mapping을 cluster의 `aws-auth` ConfigMap으로 관리합니다. 기존 cluster와의 호환성이 있습니다. | 변경·복구와 audit이 cluster별 ConfigMap에 의존합니다. | 예외입니다. 기존 cluster migration 중 필요한 경우에만 유지합니다. |

(근거: [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html), [EKS Pod Identity target role](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-assign-target-role.html), [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [IAM Identity Center ABAC](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html))

#### 상세·후속 질문

1. Domain×Environment, Brand×Environment와 Hybrid Account 구성을 비교하고 있습니다. AWS 서비스별 quota, cross-account 구성의 지원 범위와 제약, 장애 시 영향 범위를 고려할 때 특정 구성을 선택하거나 피해야 하는 조건이 있습니까?
2. Shared Cluster Account와 Workload Account를 분리하는 pattern을 막거나 규모를 제한하는 EKS·IAM·RAM·network quota와 cross-account 지원 제약이 있습니까?
3. 사람의 AWS 접근은 Identity Center RBAC과 제한적인 ABAC, workload의 AWS 접근은 runtime role·Pod Identity·IRSA, Kubernetes API 접근은 EKS Access Entries로 분리하려고 합니다. 이 조합에서 동작하지 않는 구성, 권한 확대 위험이나 규모 한계가 있습니까?

### 6.4 EKS Runtime, VPC와 Data

이 절에서 `EKS Runtime`은 application이 어느 EKS cluster에 배포되고, cluster 장애 영향이 어떻게 나뉘는지를 뜻합니다.

이 세 항목은 따로 비교하지만 최종 결정 전에는 하나의 후보 구성으로 함께 검증합니다.

#### EKS Runtime 선택지

EKS cluster를 몇 개 운영하고 workload를 어디에 수용할지와, CUJ를 복수 장애 경계에 배포할지는 별도 결정입니다. 아래 두 표에서 각각 선택합니다.

##### Cluster 수용 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| EKS-1 · 단일 Core EKS | Production Kubernetes workload 대부분을 하나의 중앙 EKS cluster에서 실행합니다. control plane·add-on·유휴 capacity 효율이 높습니다. | API·upgrade·공통 policy 장애 영향이 큽니다. | 대안입니다. Cluster quota, tenant isolation과 목표 SLO가 하나의 장애 영향을 허용하는지 확인해야 합니다. |
| EKS-2 · Environment별 중앙 EKS | Production과 Non-production 등 environment마다 중앙 EKS cluster를 하나씩 운영합니다. 환경을 분리하면서 운영 표면을 줄입니다. | Production 내부의 tenant·quota·upgrade 장애 영향은 여전히 공유합니다. | 비교 후보입니다. 같은 environment의 workload가 tenant·quota·SLO와 cluster lifecycle을 공유할 수 있을 때 성립합니다. |
| EKS-3 · Domain별 EKS | Order·Catalog 같은 domain마다 EKS cluster를 따로 운영합니다. domain별 독립 변경·quota·장애 경계를 확보합니다. | domain 변화와 cluster 재편이 결합되고 관리할 cluster 수가 증가합니다. | 비교 후보입니다. Domain마다 독립적인 tenant·quota·SLO와 변경 주기가 있는지 확인해야 합니다. |
| EKS-4 · Shared + Dedicated | 일반 workload는 공용 EKS에서 실행하고 강한 tenant·quota·SLO 요구가 있는 workload만 전용 cluster로 분리합니다. 효율과 격리를 요구에 맞게 조합할 수 있습니다. | 전용 판정이 약하면 cluster가 계속 증가합니다. | 현재 검토 방향입니다. 전용 cluster 생성·통합 threshold와 lifecycle owner가 명확해야 합니다. |

##### Availability와 Cell 배포 방식

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| AVAIL-1 · A/B EKS Runtime | 두 EKS cluster를 A와 B로 나누고, 일부 CUJ만 양쪽에 배포하며 나머지는 한쪽에 배포합니다. EKS control plane·add-on·upgrade·capacity 장애에 대비하면서 전체 workload 복제 비용을 피할 수 있습니다. | Network·DNS·data 같은 공통 dependency를 그대로 공유하므로 두 cluster만으로 완전한 failure domain이 되지는 않습니다. DNS·capacity·data dependency가 준비되지 않으면 가용성 효과도 없습니다. | POC 후보입니다. CUJ 선정, DNS 전환, surviving capacity와 data dependency가 실제 장애 시험을 통과해야 합니다. |
| AVAIL-2 · Full Workload Cell | 하나의 workload가 요청을 독립 처리할 수 있도록 ingress·compute·data와 필수 dependency를 Cell 단위로 함께 분할하거나 복제합니다. 장애 영향을 Cell에 제한할 수 있습니다. | partition, consistency, 용량과 운영 비용이 큽니다. | 대안입니다. 독립 data partition·replication과 Cell별 traffic·capacity 운영이 가능한 workload에만 적용합니다. |

A/B는 모든 서비스를 두 곳에 배포하는 안이 아닙니다. 일반 workload는 single-home으로 두되 다른 A/B EKS Runtime에 재배포할 수 있는 manifest, image, identity, DNS와 data contract를 유지합니다. CUJ만 active-active 또는 active-standby를 비교합니다. A/B cluster는 AZ 분산을 대신하지 않으며 Shared cluster의 namespace와 RBAC는 soft multi-tenancy이므로 default-deny NetworkPolicy, quota와 admission control이 필요합니다.

##### Worker/Data Plane AZ 구성

EKS managed control plane, cluster 생성에 지정하는 subnet과 customer-managed worker/Data Plane의 AZ 수를 구분합니다. EKS cluster에는 서로 다른 두 AZ의 subnet이 필요하지만 worker node는 한 AZ에만 둘 수도 있습니다. 이번 결정은 2-AZ와 3-AZ의 가용성·capacity·비용 차이를 먼저 검증하는 범위이므로 4-AZ는 비교에서 제외합니다. 4-AZ가 지원되지 않거나 항상 부적합하다는 뜻은 아닙니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| AZ-1 · 1-AZ worker | Worker/Pod를 한 AZ에 두어 chargeable cross-AZ compute 경로와 AZ별 network resource를 가장 작게 만들 수 있습니다. | AZ 장애 시 실행 capacity가 모두 사라집니다. 다른 AZ에서 복구하려면 node 배치 제약, quota·capacity와 zonal storage 전환이 준비돼야 합니다. ALB·Multi-AZ data service 경로의 cross-AZ 비용도 남을 수 있습니다. | 예외입니다. Non-production, 재생 가능한 batch 또는 낮은 availability를 명시적으로 수용한 경우에만 검토합니다. |
| AZ-2 · 2-AZ worker | 두 AZ에 worker/Pod를 분산합니다. Production EKS의 최소 비교안이며 3-AZ보다 subnet·zonal resource와 배치 표면이 작습니다. | 한 AZ 장애 후 하나만 남고, 균등 배치에서 한 AZ를 잃어도 같은 peak를 처리하려면 총 약 2배의 사전 compute capacity가 필요합니다. | 비교 후보입니다. 한 AZ를 제외한 peak 처리와 data·load balancer 전환을 시험해야 합니다. |
| AZ-3 · 3-AZ worker | 세 AZ에 worker/Pod를 분산합니다. 한 AZ 장애 후 두 AZ가 남고, 균등 배치에서 한 AZ를 잃어도 같은 peak를 처리하는 N-1 구성은 총 약 1.5배 사전 compute capacity로 만들 수 있습니다. | subnet·IP, AZ별 endpoint, replica와 placement 운영이 늘 수 있습니다. NAT는 Zonal과 Regional 구현에 따라 중복·경로 특성이 달라지며, locality가 없으면 cross-AZ traffic이 남습니다. | 비교 후보입니다. CUJ·높은 SLO의 전사 기본값으로 미리 확정하지 않습니다. |

2배와 1.5배는 정상 peak를 균등하게 배치하고 한 AZ를 잃어도 같은 peak를 처리한다는 가정에서 도출한 비교값입니다. AWS가 모든 EKS에 요구하는 고정 배수가 아니며, 실제 값은 workload와 data dependency별로 검증해야 합니다.

내부 CUR 분석에서 `direct InterZone`으로 분류한 cross-AZ data transfer 비용은 network 관련 비용의 절반 이상이고 소수 Account에 집중되어 있었습니다. `direct InterZone`은 AWS의 공식 architecture 용어가 아니라 TGW·NAT·endpoint processing 비용과 구분하기 위해 사용한 내부 집계 분류입니다. 정확한 금액은 이 문서에 포함하지 않았습니다. CUR만으로 source/destination AZ·VPC·workload pair를 확인할 수 없고, AZ 수 자체가 cross-AZ 비율을 결정하지도 않습니다. AZ 수를 줄이기 전에 Flow Logs·ENI/AZ mapping으로 상위 경로를 찾고 same-zone routing, `trafficDistribution: PreferClose`, topology spread, ALB IP target, NAT·endpoint의 zonal locality와 data locality를 적용한 뒤 남는 비용을 비교하려고 합니다.

“한 AZ가 실패하면 Region 내 여러 고객의 failover 수요가 정상 AZ의 신규 capacity 확보를 제약할 수 있다”는 의견은 무신사의 내부 가설이며 AWS의 공식 입장으로 인용하지 않습니다. 영향 규모는 공개 자료로 확인하지 못했으므로 빠른 provisioning을 복구 전제로 두지 않고, 사전 capacity와 ARC zonal shift practice run으로 검증하려고 합니다.

(근거: [EKS subnet과 Multi-AZ](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html), [EKS network cost 최적화](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html), [EKS zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html), [Static stability](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/), [Well-Architected Multi-AZ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html), [2019 Tokyo AZ event](https://aws.amazon.com/message/56489/), [EKS tenant isolation](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html))

#### VPC Ownership 선택지

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| VPC-1 · Workload Account별 VPC | 각 Workload Account가 자체 VPC와 subnet·route를 소유합니다. network 운영 책임과 장애 영향이 Account 단위로 명확해집니다. | NAT·endpoint·CIDR·연결이 늘고 구성이 파편화됩니다. | 조건별 적용입니다. 개인정보·규제·독립 routing·inspection처럼 별도 network 경계가 필요한 workload에 성립합니다. |
| VPC-2 · 중앙 Shared VPC | Network Account가 VPC와 subnet·route를 소유하고 RAM으로 여러 Workload Account에 subnet을 공유합니다. 중앙 IP·route·egress와 VPC 내부 local routing을 활용할 수 있습니다. | Network Team bottleneck과 공통 route·DNS 장애가 생길 수 있습니다. | 비교 후보입니다. 같은 trust zone과 network lifecycle을 공유할 수 있는 workload만 수용하고 owner·participant 권한을 구분해야 합니다. |
| VPC-3 · trust zone 혼합형 | 같은 network control을 적용할 수 있는 일반 workload는 Shared VPC에 두고 개인정보·규제·특수 요구가 있는 workload는 전용 VPC에 둡니다. 효율과 강한 network 격리를 조합할 수 있습니다. | 두 운영 model과 분리 기준을 유지해야 합니다. | 현재 검토 방향입니다. 개인정보·규제 VPC 분리 기준과 두 운영 model의 owner·control이 명확해야 합니다. |

##### Shared VPC 확장 방식

VPC-2 또는 VPC-3을 선택하면 Shared VPC를 몇 개까지 확장할지 다음 pattern을 별도로 검증합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| SVPC-1 · 최소 VPC·Shared VPC Pool | 리전·환경·trust zone당 1개 VPC로 시작하고 여러 Account에 subnet을 RAM으로 공유합니다. 참여 Account 사이의 Peering·TGW와 중복 network 기반을 줄일 수 있으며, 한계를 넘을 때만 같은 blueprint의 다음 VPC를 추가합니다. | route·DNS·NACL·IP의 공통 장애 영향, participant SG 통제, owner bottleneck과 VPC quota가 커집니다. | POC 후보입니다. SG·NACL·route·DNS 통제, IP·quota와 다음 VPC로 분리하는 threshold를 확인해야 합니다. |
| SVPC-2 · 중앙 소유·Workload별 전용 Shared VPC | Network Account가 Workload 경계마다 VPC를 하나씩 소유하고 해당 Workload Account 하나에만 subnet을 1:1로 RAM 공유합니다. Network 객체는 중앙에서 관리하면서 VPC 장애 영향을 Workload 단위로 제한할 수 있습니다. | VPC·NAT·endpoint와 VPC 간 연결 수는 줄지 않고 중앙 pipeline의 잘못된 변경이 여러 VPC에 전파될 수 있습니다. Participant는 자기 ENI와 SG를 계속 소유합니다. | 비교 후보입니다. Workload별 독립 network 경계가 필요하지만 VPC 객체의 생성·변경 권한은 중앙화하려는 경우에 성립합니다. VPC 수는 brand·Account 수에서 자동 계산하지 않습니다. |

##### IP address management

Shared VPC와 Dedicated VPC 중 무엇을 선택하더라도 CIDR allocation과 overlap 탐지는 Organizations와 연동한 VPC IPAM을 공통 기반 후보로 둡니다. IPAM delegated administrator, 리전·environment·trust zone별 pool hierarchy, RAM을 통한 allocation 권한, 기존 VPC의 비준수 CIDR 처리와 VPC 생성 pipeline 연동을 함께 설계합니다. IPAM 자체 도입을 결론으로 고정하지 않고, Free Tier와 Advanced Tier의 기능 차이·active IP 과금과 기존 도구 대비 운영 효과를 확인한 뒤 결정합니다.

(근거: [IPAM과 AWS Organizations 연동](https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam.html), [IPAM pool 공유](https://docs.aws.amazon.com/vpc/latest/ipam/share-pool-ipam.html), [IPAM pricing](https://docs.aws.amazon.com/vpc/latest/ipam/pricing-ipam.html))

##### Shared VPC의 cross-account 운영

Shared subnet을 여러 Account에서 사용할 때 `ap-northeast-2a` 같은 AZ 이름은 Account마다 물리 AZ mapping이 다를 수 있으므로, subnet·Pod·data의 zonal 배치는 Account 사이에서 일관된 AZ ID(`apne2-az*`)를 기준으로 관리합니다.

Participant가 임의 SG를 만들거나 넓은 Allow를 추가하는 문제는 NACL만으로 해결하지 않습니다. Network owner가 공통 SG를 RAM으로 공유하거나 Firewall Manager의 common·audit SG policy를 적용하고, IAM·SCP로 SG 변경 주체와 API를 제한하며 source·port 기준은 policy-as-code와 Firewall Manager audit으로 검사하는 방식을 비교합니다. 이 수단들은 SG rule의 `Allow 전용`과 여러 SG rule이 합쳐지는 동작을 바꾸지 않으므로, 다른 SG의 넓은 Allow를 중앙 SG로 상쇄할 수는 없습니다.

(근거: [Shared subnet의 AZ ID](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html), [Security Group 공유](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html), [Firewall Manager common SG policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html), [Firewall Manager SG audit policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html))

##### A/B EKS Runtime의 VPC 배치

VPC ownership을 정한 뒤 A/B cluster가 network 장애 경계까지 분리되어야 하는지 별도로 결정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| RUNTIME-VPC-1 · A/B가 같은 Shared VPC 사용 | A와 B EKS cluster를 같은 Shared VPC의 서로 다른 subnet에 배치합니다. data 경로가 단순해지고 별도 VPC 연결을 줄일 수 있습니다. | A/B가 network failure domain을 공유합니다. | 비교 후보입니다. A/B의 목표가 EKS 장애 분리에 한정되고 route·DNS 장애 공유를 수용할 수 있을 때 적용합니다. |
| RUNTIME-VPC-2 · A/B 또는 Cell별 VPC | A와 B cluster 또는 각 Cell을 서로 다른 VPC에 배치합니다. runtime뿐 아니라 network 장애 영향도 분리할 수 있습니다. | VPC 간 연결·data transfer·endpoint 비용이 증가합니다. | 비교 후보입니다. Network 장애까지 분리해야 하고 추가 연결·비용을 정당화할 SLO가 있을 때 적용합니다. |

SVPC-1은 참여 Account 사이의 Peering·TGW를 대부분 없애고 NAT·endpoint·route 같은 중복 기반을 줄이는 것을 목표로 합니다. 하나의 VPC를 기술적 최대치까지 영구 확장하는 안은 아닙니다. 같은 environment와 trust zone을 공유할 수 있는 workload만 수용하고, quota·정책·장애 영향이 threshold를 넘으면 다음 Shared VPC 또는 전용 VPC로 분리합니다.

Shared VPC의 owner·participant 책임, quota와 Security Group 동작은 선택을 좌우하는 전제이므로 12장에 정리했습니다.

#### VPC 간 Connectivity 선택지

이 표는 `조건별 적용`입니다. 전사에 하나의 연결 방식을 고르지 않고, 통신하는 두 resource가 같은 VPC인지, 다른 VPC인지와 각 연결의 transitivity·inspection 요구에 따라 edge별로 하나를 선택합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| CONN-1 · VPC Peering | 통신이 필요한 두 VPC를 1:1로 직접 연결하고 양쪽 route table에 경로를 추가합니다. 경로가 direct·non-transitive이며 TGW processing 비용이 없습니다. | CIDR overlap이 불가능하고 양쪽 route를 관리해야 하며 연결 쌍이 많아지면 복잡해집니다. | 실제 통신하는 VPC 쌍이 적고 transitive routing·중앙 inspection이 필요하지 않을 때 성립합니다. |
| CONN-2 · Transit Gateway | 여러 VPC와 on-prem network를 중앙 TGW hub에 attachment로 연결합니다. transitive routing과 중앙 inspection 경로를 집약할 수 있습니다. 현재 무신사의 AWS·on-prem 연결 기준선입니다. | attachment·processing 비용과 중앙 route 변경의 영향이 생깁니다. | On-prem·외부 시스템, transitive routing, 중앙 inspection 또는 연결이 많은 VPC 구간에 유지합니다. 현재 attachment를 모두 유지한다는 뜻은 아닙니다. |
| CONN-3 · PrivateLink | 제공자 VPC의 특정 service 또는 지원 resource를 consumer VPC의 endpoint로만 공개합니다. VPC 전체 routing이나 상호 신뢰 없이 필요한 대상만 연결할 수 있습니다. | endpoint 비용과 provider/consumer 운영이 반복됩니다. | VPC 전체가 아니라 특정 service·지원 resource만 단방향으로 노출할 때 사용합니다. |
| CONN-4 · VPC Lattice | 여러 Account와 VPC의 application service·지원 resource를 Lattice service network에 등록해 routing과 auth를 적용합니다. VPC topology보다 application 단위로 연결을 관리할 수 있습니다. | 별도 control plane, protocol·quota·비용을 검증해야 합니다. | 지원 protocol·quota·비용과 auth 운영이 기존 방식보다 유리함을 POC로 확인해야 합니다. |
| CONN-5 · Same-VPC local routing | 통신하는 resource를 같은 VPC에 배치해 VPC의 local route로 연결합니다. Peering·TGW 같은 별도 VPC 연결 장치가 필요하지 않습니다. | route·DNS·IP 장애를 공유하고 서비스·경로별 cross-AZ 과금은 별도로 검토해야 합니다. | 같은 trust zone이고 동일 VPC 배치가 가능한 resource 사이에 사용합니다. |

연결 방식은 전사 단일 제품이 아니라 다음 traffic 요구별 pattern으로 선택합니다.

| Traffic 요구 | 우선 비교할 pattern | 선택을 바꾸는 조건 |
|---|---|---|
| 같은 VPC·같은 trust zone | CONN-5 | route·DNS·IP 장애 공유를 수용할 수 없는 경우 |
| 소수 VPC의 직접 양방향 통신 | CONN-1 | transitive routing, 중앙 inspection, CIDR overlap 또는 연결 graph 증가 |
| 다수 VPC·on-prem·중앙 inspection | CONN-2 | attachment·processing 비용과 중앙 장애 영향이 요구보다 큰 경우 |
| 특정 service의 단방향 제공 | CONN-3 | protocol·resource 지원 범위 또는 endpoint 비용이 맞지 않는 경우 |
| application 단위 service network·auth | CONN-4 | protocol·quota·운영 control plane이 기존 방식보다 복잡한 경우 |

목표 구조에서는 같은 trust zone의 AWS workload를 Shared VPC나 Same-VPC routing으로 수용해 불필요한 TGW attachment를 줄이되, on-prem VPN·외부 시스템·transitive routing·inspection이 필요한 backbone은 TGW를 유지하는 Hybrid를 검토합니다. 현재 연결도는 attachment 존재만 나타내므로 실제 통신 가능 범위는 TGW route table의 association·propagation과 inspection 경로를 기준으로 확인합니다.

##### East-west inspection 선택지

이 표는 traffic 위험과 trust zone에 따른 `조건별 적용`입니다. 연결 방식과 inline inspection은 별도 결정이며, 같은 trust zone의 내부 경로까지 모두 중앙 firewall로 보낼지 먼저 정하지 않습니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| INSP-1 · 분산 정책 통제 | SG·NACL·route·EKS NetworkPolicy와 Flow Logs로 VPC별 통신을 통제합니다. 추가 처리비와 중앙 hop이 없습니다. | Signature 기반 inline 탐지·차단이 없고 정책·증거가 분산됩니다. | 같은 trust zone이며 규제상 inline inspection이 필요하지 않은 경로에 성립합니다. |
| INSP-2 · VPC별 분산 firewall | 필요한 VPC에 독립 firewall endpoint를 둡니다. 중앙 route 장애를 피하고 VPC별 inspection을 적용할 수 있습니다. | Endpoint·로그·정책 비용이 VPC마다 반복됩니다. | 독립 inspection이 필요한 VPC가 적거나 중앙 장애 경계를 피해야 할 때 성립합니다. |
| INSP-3 · TGW 중앙 inspection | TGW route table로 대상 트래픽을 중앙 AWS Network Firewall에 강제합니다. Inspection VPC 안의 firewall endpoint를 경유하는 방식과 TGW에 firewall을 직접 attachment하는 방식을 비교합니다. | TGW·firewall 처리비, 추가 hop과 중앙 장애 영향이 생기며 요청과 응답의 symmetric routing을 보장해야 합니다. | 여러 VPC의 trust zone 간·규제·on-prem 트래픽을 공통 지점으로 강제해야 할 때 성립합니다. 두 구현 방식의 route·Account ownership·비용·장애 영향을 비교해야 합니다. |
| INSP-4 · Hybrid | trust zone 내부는 INSP-1/INSP-2, trust zone 간·규제 경로는 INSP-3을 사용합니다. 위험과 트래픽에 맞춰 비용을 조절할 수 있습니다. | 트래픽 분류와 우회 경로 검증, 두 운영 방식의 책임이 필요합니다. | 현재 검토 방향입니다. 경로가 연결하는 trust zone, inspection 요구와 owner가 명확해야 합니다. |

INSP-3의 inspection VPC 방식은 TGW appliance mode와 양방향 route를 통해 같은 firewall endpoint를 지나도록 구성해야 합니다. TGW-attached Network Firewall은 appliance mode가 항상 적용되지만, TGW owner와 firewall owner가 다른 Account이면 두 Account의 삭제 권한과 제한된 가시성을 운영 절차에 반영해야 합니다.

(근거: [AWS network inspection guidance](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_network_protection_inspection.html), [Centralized VPC inspection](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html), [TGW-attached Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html), [TGW-attached firewall 고려사항](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall-considerations.html), [Asymmetric routing 방지](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html))

(근거: [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html), [VPC connectivity options](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html), [Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html), [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html), [VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html))

#### Data Placement 선택지

##### Data ownership

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| DATA-1 · 중앙 DB 운영 Account | 여러 workload의 RDS·DynamoDB 같은 운영 데이터 저장소를 DB 운영팀 Account가 소유·운영합니다. 운영 도구·backup·encryption과 전문성을 집중할 수 있습니다. 현재 무신사의 일부 운영 방식과 가깝습니다. | 중앙 quota·운영팀 bottleneck과 workload lifecycle 분리가 생기고 cross-account 권한·복구 책임이 복잡해질 수 있습니다. | 비교 후보입니다. 전문 운영 SLO와 일관된 통제가 workload별 독립 quota·lifecycle·장애 책임보다 중요한 경우에 성립합니다. |
| DATA-2 · Workload-owned data | 각 workload가 사용하는 transactional DB와 저장소를 해당 Workload Account가 소유합니다. application·schema·비용·복구 책임이 일치합니다. | 운영 품질 편차가 생길 수 있고 DBA 표준·복구 지원을 여러 Account에 제공해야 합니다. | 비교 후보입니다. Schema와 application lifecycle을 같은 책임자가 소유하고 중앙 운영 품질을 공통 automation으로 제공할 수 있을 때 성립합니다. |
| DATA-3 · Hybrid | 운영 데이터 저장소는 DATA-1 또는 DATA-2를 workload별로 선택하고, lake·warehouse·streaming backbone은 별도 Data Platform이 소유합니다. 데이터 유형별 전문성과 책임을 조합할 수 있습니다. | CDC·schema·품질·비용 contract가 필요하고 판정 기준이 약하면 운영 방식이 늘어납니다. | 현재 검토 방향입니다. Transactional data와 공통 data product의 소유·schema·SLO·비용 contract가 명확해야 합니다. |

##### Data의 network·Cell 배치

Data ownership을 정한 뒤 application과 같은 VPC 또는 Cell에 배치할지 별도로 결정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| DATA-4 · Shared VPC locality | DB의 소유권은 Workload Account에 두고, participant가 shared subnet에 생성할 수 있는 RDS 등의 지원 resource를 application과 같은 Shared VPC에 배치합니다. Account 책임을 유지하면서 VPC 간 연결을 줄일 수 있습니다. | 지원 resource·participant 제약과 공통 VPC 장애가 남습니다. | 조건별 적용입니다. VPC Sharing에서 participant 생성이 지원되고 application과 같은 trust zone·VPC 장애 경계를 공유할 수 있어야 합니다. |
| DATA-5 · Cell-local data | 각 Cell이 요청 처리에 필요한 data partition 또는 replica를 따로 보유합니다. runtime과 data 장애 영향을 Cell에 제한할 수 있습니다. | consistency·replication·failover 비용이 큽니다. | 대안입니다. CUJ의 consistency·replication·failover 요구와 추가 비용을 감당할 수 있을 때 적용합니다. |

개인정보 원본을 저장하는 RDS 등 VPC 배치형 저장소는 일반 application serving 계층과 별도 VPC에 둡니다. 목적은 개인정보 저장 계층의 route·inspection·직접 접근 주체와 incident containment 범위를 일반 serving 계층과 분리하는 것입니다. 별도 VPC만으로 이 목적이 달성되지는 않으므로 IAM, Security Group, KMS key policy, logging과 승인된 접근 경로를 함께 적용합니다. S3는 VPC에 배치되는 resource가 아니므로 bucket·Account ownership, VPC endpoint와 endpoint policy, bucket·access point policy, KMS key policy와 조직 control로 승인된 경로만 허용합니다. Serving 계층은 승인된 API·private endpoint·CDC 등 명시된 경로로만 접근하도록 설계하고, 별도 Account 여부는 권한·규제·lifecycle 기준으로 추가 판단합니다.

Development와 QA는 Production 원본 데이터, snapshot, backup과 CDC stream에 직접 접근하지 않는 것을 공통 guardrail로 둡니다. Route뿐 아니라 IAM, KMS key policy, resource policy와 VPC endpoint policy로 강제하고 synthetic 또는 승인된 masked data를 사용합니다. Staging은 Production release 검증을 위해 제한된 의존성이 필요할 수 있으므로 QA와 합치지 않고 목적·범위·보존 기간·승인·종료 조건을 별도 계약으로 관리합니다.

#### 상세·후속 질문

1. EKS API·quota, tenant isolation, add-on·upgrade 영향과 SLO를 기준으로 Shared Cluster를 추가하거나 전용 cluster로 분리하려고 합니다. AWS에서 측정 가능한 분리 신호와 서비스 한계가 있습니까?
2. CUJ를 두 EKS cluster에 배포할 때, 한 cluster에 장애가 발생해도 서비스를 유지하려면 DNS 전환, 남은 cluster의 사전 capacity, 데이터 동기화와 공통 dependency에 어떤 조건이 필요합니까?
3. SVPC-1과 SVPC-2가 AWS 기능상 성립하는지, 각각에서 먼저 도달할 가능성이 큰 quota, 지원되지 않는 resource와 owner·participant 제약은 무엇입니까? Organizations-integrated IPAM, AZ ID, Shared SG와 Firewall Manager를 함께 사용할 때 추가 제약도 확인하고 싶습니다.
4. CONN-1부터 CONN-5까지와 INSP-1부터 INSP-4까지를 traffic 요구별로 조합하는 접근에서 빠진 AWS 제약이나 중앙 TGW inspection이 필수인 조건이 있습니까? 중앙 inspection은 inspection VPC와 TGW-attached Network Firewall을 비교하며 symmetric routing, Account ownership과 route-table 강제 조건도 확인하고 싶습니다.
5. 중앙 DB 운영 Account, Workload-owned data와 Hybrid를 비교할 때 cross-account backup·KMS·network·복구 특성상 선택을 바꿀 조건이 있습니까? 개인정보 저장 계층과 serving 계층을 별도 VPC로 분리하고 Development·QA의 Production 원본 데이터 접근을 차단하는 방식에서 빠진 AWS 통제가 있습니까?

### 6.5 Ingress, Egress와 DNS

#### Public Edge 선택지

무신사는 Cloudflare를 주 public edge, Akamai를 이중화 edge로 사용하는 방향을 기준 후보로 두고 있습니다. AWS WAF는 기본으로 중첩하지 않으며, 두 edge가 제공하지 못하는 control이나 규제 요구가 확인된 경우에만 비교합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| EDGE-1 · CloudFront + AWS WAF | 모든 public traffic을 CloudFront와 AWS WAF를 통해 AWS origin으로 전달합니다. AWS-native logging·Shield·origin 연계가 직접적입니다. | 현재 edge 전환과 policy·cache 차이, 이중 운영이 필요합니다. | 대안입니다. Cloudflare·Akamai로 충족하지 못하는 AWS-native control이나 규제 요구가 확인될 때 비교합니다. |
| EDGE-2 · Cloudflare + Akamai | Cloudflare를 주 public edge로, Akamai를 provider 장애에 대비한 보조 edge로 사용합니다. 현재 운영 자산과 provider 이중화를 활용할 수 있습니다. | rule·certificate·cache·health 의미를 동기화해야 합니다. | 현재 검토 방향입니다. 두 provider의 rule·certificate·health와 failover 동작이 동일한 운영 기준을 만족해야 합니다. |
| EDGE-3 · Cloudflare + CloudFront/WAF 중첩 | Cloudflare 뒤에 CloudFront와 AWS WAF를 한 계층 더 둔 뒤 AWS origin에 연결합니다. 서로 다른 provider의 control을 계층화할 수 있습니다. | 지연·비용·cache·장애 분석이 복잡해집니다. | 대안입니다. 추가 control 효과가 지연·비용·운영 복잡도보다 크다는 근거가 있어야 합니다. |
| EDGE-4 · 서비스별 edge 선택 | 공통 edge를 고정하지 않고 서비스별 요구에 따라 Cloudflare·Akamai·CloudFront/WAF 중 하나를 선택합니다. 특수 요구에 유연하게 대응할 수 있습니다. | coverage·log·certificate와 incident 운영이 파편화됩니다. | 예외입니다. 공통 edge로 충족할 수 없는 요구, owner와 종료 조건이 승인되어야 합니다. |

#### ALB 선택지

##### 서비스 수용 방식

ALB-1과 ALB-2는 서비스의 owner·policy·SLO·quota에 따른 `조건별 적용` pattern입니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| ALB-1 · 서비스별 ALB | 각 서비스가 전용 ALB를 소유합니다. 배포·quota·장애 영향을 서비스에 제한할 수 있습니다. | ALB·LCU·IP와 운영 대상이 증가합니다. | 독립 배포·quota·보안 policy나 장애 격리가 필요한 서비스에 적용합니다. |
| ALB-2 · trust zone별 공유 | 같은 owner·policy·SLO를 가진 여러 서비스가 하나의 ALB를 공유합니다. 고정비와 공통 policy 중복을 줄일 수 있습니다. | rule 충돌과 공유 장애 영향이 생깁니다. | 같은 owner·policy·SLO·trust zone이고 rule·LCU quota에 여유가 있어야 합니다. |

##### A/B EKS Runtime ingress와 전사 ALB 운영 원칙

A/B cluster 또는 Cell마다 `ALB-3 · Runtime gateway`를 두고 해당 runtime의 서비스를 연결하는 pattern을 검토합니다. A/B traffic 전환, gateway capacity와 공통 장애 영향이 목표 SLO를 만족해야 합니다.

전사 ALB는 `ALB-1`과 `ALB-2`를 함께 사용합니다. CUJ·고위험 서비스는 전용 ALB를 사용하고, 나머지는 같은 owner·policy·SLO·trust zone 안에서 공유합니다. 전용·공유 판정표와 lifecycle owner를 유지합니다.

물리 ALB나 cluster endpoint를 외부 contract로 사용하지 않고 stable FQDN 뒤에 둡니다. ALB를 사용할 때는 새 target group을 listener의 weighted forward action에 weight 0으로 연결하고 target health와 synthetic transaction을 검증한 뒤 weight를 단계적으로 높이며, 실패하면 자동 중단과 rollback을 수행합니다. Weighted target group 중 하나가 비어 있거나 unhealthy여도 ALB가 다른 target group으로 자동 failover하지 않으므로 별도의 health 판단과 전환 절차가 필요합니다. `musinsa.com`과 `29cm.co.kr`의 public authoritative DNS는 Route 53을 사용하고 public web 응답은 Cloudflare edge를 경유합니다. Authoritative DNS와 edge traffic 전환은 서로 다른 control plane이므로 Route 53 record 변경과 Cloudflare·Akamai 전환 각각의 health 판단 위치, 실행 주체, propagation과 rollback을 검증합니다.

(근거: [ALB weighted target group](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html), [Route 53 weighted routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html), [Route 53 failover routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html))

#### Egress 선택지

##### Traffic class별 egress 경로

EGRESS-1부터 EGRESS-3까지는 traffic class와 강제할 control에 따른 `조건별 적용` pattern입니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| EGRESS-1 · Cloudflare Gateway | 지원되는 outbound traffic을 Cloudflare Gateway로 보내 internet·SaaS 접근 policy를 적용합니다. identity-aware policy를 중앙화할 수 있습니다. | workload protocol coverage와 NAT/IGW bypass를 검증해야 합니다. | 대상 protocol coverage와 NAT·IGW 우회 차단이 검증된 traffic에 적용합니다. |
| EGRESS-2 · TGW + AWS Network Firewall | 여러 VPC의 egress route를 TGW로 모아 중앙 AWS Network Firewall과 NAT를 거치게 합니다. route 수준 inspection과 on-prem 연결을 집약할 수 있습니다. | 비용·추가 hop·중앙 장애 영향이 생깁니다. | 명시적인 중앙 inspection·transitive routing 요구가 있을 때 적용합니다. |
| EGRESS-3 · 분산 egress | 각 VPC 또는 Cell이 자체 NAT·endpoint와 필요한 inspection을 운영합니다. VPC/Cell별 장애 격리와 local path를 확보할 수 있습니다. | NAT·endpoint 중복과 policy drift가 생깁니다. | Cell 독립성이 중앙화 비용과 policy 중복보다 중요할 때 적용합니다. |

##### NAT Gateway 구현 방식

EGRESS-2 또는 EGRESS-3에서 public egress에 NAT Gateway가 필요하면 Zonal과 Regional availability mode를 조건별로 비교합니다.

| 구현 방식 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| NAT-1 · Zonal NAT Gateway | AZ별 NAT Gateway와 route를 명시적으로 배치합니다. AZ별 egress IP·route와 private NAT를 제어할 수 있습니다. | AZ마다 NAT와 public subnet을 운영해야 하며 잘못된 route는 cross-AZ 처리나 단일 AZ 의존을 만들 수 있습니다. | Private NAT 또는 AZ별 IP·route 제어가 필요한 경우에 적용합니다. AZ별 비용, route와 장애 전환을 검증해야 합니다. |
| NAT-2 · Regional NAT Gateway | 하나의 NAT Gateway ID가 workload가 있는 AZ로 자동 확장·축소되고 public subnet 없이 public egress를 제공합니다. AZ 추가 시 route와 NAT를 반복 생성하는 작업을 줄일 수 있습니다. | Private NAT를 지원하지 않고 새 AZ 확장에 최대 60분이 걸릴 수 있으며 그동안 cross-AZ로 처리될 수 있습니다. 기존 Zonal NAT 전환 시 connection reset이나 IP 변경·중단이 생길 수 있습니다. | Public egress에 적용합니다. 서울 리전 지원, IP 전략, 확장 지연, 전환 절차와 실제 비용을 Zonal NAT와 비교해야 합니다. |

(근거: [Regional NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html), [Regional NAT Gateway 리전 지원](https://aws.amazon.com/about-aws/whats-new/2025/11/aws-nat-gateway-regional-availability/))

##### 전사 egress 운영 원칙

현재는 `EGRESS-4 · Traffic class별 Hybrid`를 검토합니다. Internet·SaaS는 Cloudflare Gateway를 우선 검토하고, 지원되는 AWS API는 gateway 또는 interface VPC endpoint를 우선 사용하며, private·on-prem traffic은 별도 route를 적용하는 방식으로 경로 종류별 control을 선택합니다. 서비스·Region·기능별 endpoint와 endpoint policy 지원 여부를 확인하고, endpoint가 없거나 endpoint만으로 최소 권한을 강제할 수 없는 경로는 통제된 egress를 사용합니다. 제품을 먼저 고르지 않고 `Pod/EC2/Lambda→Internet`, `SaaS`, `AWS API`, `VPC 간 private`, `on-prem` 경로별 위협·강제 지점·우회 차단·owner를 coverage matrix로 확인합니다.

(근거: [AWS centralized egress](https://docs.aws.amazon.com/prescriptive-guidance/latest/transitioning-to-multiple-aws-accounts/centralized-egress.html), [PrivateLink 지원 AWS 서비스](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html), [VPC endpoint policy](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html))

#### Private DNS 선택지

Private DNS는 Shared VPC, PrivateLink, cross-account service와 cluster 전환에서 stable name과 ownership을 유지하기 위해 필요합니다. Public DNS와 별개의 후속 결정으로 다룹니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| DNS-1 · 중앙 PHZ·Resolver 소유 | Network Account가 private hosted zone, Resolver endpoint와 rule을 중앙 관리합니다. name·forwarding policy와 on-prem 연계를 한 곳에서 통제할 수 있습니다. | 중앙팀 bottleneck, zone association과 공통 DNS 변경 영향이 커집니다. | 비교 후보입니다. 소수 공통 namespace와 중앙 승인이 필요한 DNS rule에 적용합니다. |
| DNS-2 · Namespace governance + workload 위임 | 중앙은 namespace와 공통 Resolver rule을 관리하고 workload는 위임받은 subdomain과 service record를 소유합니다. Workload lifecycle과 DNS 책임을 연결할 수 있습니다. | 위임·PHZ association·name collision과 split-horizon 검증이 필요합니다. | 현재 검토 방향입니다. Shared VPC owner/participant 책임, cross-account association, Resolver rule 공유와 삭제 순서를 자동 검증해야 합니다. |
| DNS-3 · Route 53 Profiles 배포 | Profile에 PHZ, Resolver rule, DNS Firewall rule group, interface endpoint의 private DNS와 query logging 설정을 묶어 여러 VPC·Account에 적용합니다. VPC별 반복 association과 설정 drift를 줄일 수 있습니다. | VPC에는 Profile 하나만 연결할 수 있고 local VPC 설정과 Profile 설정의 우선순위, RAM 권한, VPC association 비용을 관리해야 합니다. | 조건별 적용입니다. DNS-1 또는 DNS-2의 ownership을 대신하지 않고, 공통 DNS 설정을 여러 VPC에 배포할 때 운영 효과와 비용을 비교합니다. |

현재 topology에는 AWS와 on-prem 사옥·서버실, MLOps, 물류, SASE 망을 잇는 VPN 경로가 있습니다. 목표 Private DNS는 on-prem에서 AWS private name을 조회하는 inbound 경로와 AWS에서 on-prem name을 조회하는 outbound 경로를 구분하고, Resolver endpoint·forwarding rule·PHZ/Profile의 owner, query logging, 장애 시 대체 경로와 삭제 순서를 정의해야 합니다. 현재 topology만으로 실제 DNS server, Resolver endpoint와 forwarding rule 구성을 확인할 수는 없으므로, 기존 설정은 전환 설계 전에 별도로 확인합니다.

Route 53 Profiles는 서울 리전에서 지원됩니다. Profile owner가 공유와 resource association을 관리하고 VPC association 비용을 부담하므로, Network Account가 소유할지 DNS 전용 역할이 소유할지도 함께 결정합니다.

(근거: [다른 Account의 VPC와 Private Hosted Zone 연결](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zone-private-associate-vpcs-different-accounts.html), [Resolver rule 관리와 공유](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-rules-managing.html), [Route 53 Resolver hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html), [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html), [Route 53 Profile 공유](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/sharing-profiles.html), [Route 53 endpoint·리전](https://docs.aws.amazon.com/general/latest/gr/r53.html))

#### 상세·후속 질문

1. Cloudflare/Akamai를 public edge로 두는 AWS origin에서 origin bypass, DDoS, certificate, logging과 failover에 필요한 구성은 무엇이며, AWS WAF를 추가해야 하는 조건이 있습니까?
2. 같은 owner·policy·SLO·trust zone을 가진 서비스만 ALB를 공유하려고 합니다. 이 조건 외에 ALB·EKS quota나 장애 특성 때문에 전용 ALB가 필요한 경우가 있습니까?
3. Internet·SaaS, AWS API, VPC 간 private traffic과 on-prem을 나눠 Cloudflare Gateway, AWS Network Firewall, 분산 egress와 VPC endpoint를 선택하려고 합니다. Zonal·Regional NAT Gateway와 서비스별 VPC endpoint·endpoint policy 지원 범위를 포함할 때, AWS 서비스 관점에서 대체할 수 없거나 반드시 별도로 통제해야 하는 경로가 있습니까?
4. Shared VPC와 PrivateLink에서 중앙 namespace governance와 workload별 private DNS ownership을 조합할 때 PHZ association, Resolver rule·Route 53 Profile 공유, hybrid DNS, split-horizon과 삭제 순서에서 주의할 AWS 제약이 있습니까?

### 6.6 Secrets, KMS와 Security

#### Secrets와 KMS 선택지

##### Secret과 KMS ownership

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| KEY-1 · 중앙 Secrets/KMS Account | 공통 secret과 KMS key를 중앙 Security 또는 Shared Services Account가 소유하고 다른 Account가 cross-account로 사용합니다. policy·rotation·audit을 집중할 수 있습니다. | 중앙 의존성과 넓은 cross-account policy가 생깁니다. | 비교 후보입니다. 여러 workload가 함께 쓰는 integration이고 cross-account policy·KMS와 중앙 장애 영향을 감수할 때 적용합니다. |
| KEY-2 · Workload-owned | 각 Workload Account가 자기 application의 secret과 KMS key를 소유합니다. application·data·key lifecycle과 책임이 일치합니다. | 여러 workload가 함께 쓰는 integration까지 중복될 수 있고 운영 품질 편차가 생깁니다. | 비교 후보입니다. 모든 secret과 key가 한 workload lifecycle에만 속을 때 적용합니다. |
| KEY-3 · Hybrid | workload 소유를 기본으로 하고 여러 workload가 함께 쓰는 secret만 중앙 관리합니다. 중앙화 범위를 제한하면서 공통 운영을 재사용할 수 있습니다. | Secret 유형과 중앙·workload owner를 분류해야 합니다. | 현재 검토 방향입니다. Secret 유형별 owner와 rotation SLO가 명확해야 합니다. |

Secrets Manager와 KMS의 cross-account 접근에 대해 전제한 AWS 동작과 근거는 12장에 정리했습니다.

#### Security와 Observability capability matrix

AWS-native 서비스와 기존 CNAPP를 서로 대체하는 제품 선택지로 보지 않습니다. 보안 목적별로 현재 지원 범위와 AWS 고유 기능을 비교하고, 확인된 공백만 보완합니다.

| ID | 보안 목적 | 현재 검토 방향 | AWS와 확인할 내용 |
|---|---|---|---|
| SEC-1 | 조직 예방 control | OU·SCP·Control Tower control과 기존 보안 기준을 함께 사용합니다. | 신규 Account 자동 적용, 우회 방지와 delegated administrator가 필요한 기능 |
| SEC-2 | Configuration posture | 기존 CSPM과 AWS Config·Security Hub control의 중복·고유 coverage를 비교합니다. | AWS 원천 configuration·조직 aggregation이 외부 솔루션으로 대체 가능한 범위 |
| SEC-3 | Data security posture | 기존 DSPM을 기준으로 개인정보 저장소 coverage를 확인합니다. | RDS·S3·KMS·resource policy에서 AWS-native 기능만 제공하는 신호 |
| SEC-4 | Workload runtime protection | 기존 CWPP를 기준으로 Pod·host runtime coverage를 확인합니다. | GuardDuty Runtime Monitoring 등 AWS telemetry의 중복·공백 |
| SEC-5 | Threat detection | CloudTrail·VPC·DNS·EKS 등 원천 telemetry별로 기존 CNAPP와 GuardDuty coverage를 비교합니다. | 서울 리전에서 실제 지원되는 finding type과 조직 운영 방식 |
| SEC-6 | Finding·대응 workflow | 기존 보안팀의 finding 처리 절차를 기준으로 중복 제거·severity·case owner·SLA를 통일합니다. | Security Hub aggregation·automation을 추가할 때의 고유 이점과 중복 비용 |
| SEC-7 | Workload 맥락 탐지 | 중앙 최소 기준 위에서 workload 소유 팀이 application 맥락의 추가 탐지와 대응을 소유합니다. | 중앙 correlation·감사와 workload 소유 팀 책임을 연결하는 pattern |

AWS Security Reference Architecture는 Security Tooling Account와 Log Archive Account, 조직 지원 서비스의 delegated administrator를 설명합니다. 이를 모든 AWS-native 보안 서비스를 중복 도입해야 한다는 의미로 해석하지 않습니다.

GuardDuty와 Security Hub는 서울 리전에서 사용할 수 있지만 일부 finding type과 control의 지원 범위가 다르므로, 서울 리전의 실제 coverage를 기준으로 비교합니다.

(근거: [AWS Security Reference Architecture - Security Tooling](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html), [GuardDuty 리전별 차이](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html), [Security Hub 리전별 control](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html))

#### 상세·후속 질문

1. Secret과 KMS key는 workload 소유를 기본으로 하고 여러 workload가 함께 쓰는 integration만 중앙에서 소유하려고 합니다. cross-account KMS, rotation, replica와 복구 특성상 중앙 또는 workload 소유를 다르게 해야 하는 조건이 있습니까?
2. 기존 CNAPP와 AWS-native 서비스를 보안 목적별로 비교한 뒤 확인된 공백만 보완하려고 합니다. Organizations delegated administrator, AWS service의 원천 telemetry처럼 외부 솔루션으로 대체하기 어려운 고유 기능이 있습니까?

### 6.7 전환 계획과 표준 준수 검증 (Migration and Conformance)

목표 구조를 정하는 것과 실제 workload를 안전하게 옮기는 것은 별개의 결정입니다. 이 절에서는 전환 단위와 공통 기반의 구축 순서를 비교하고, 전환 후 실제 AWS 상태가 선택한 표준을 계속 지키는지 검증하는 방법을 함께 다룹니다.

#### Workload 전환 단위

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| MIG-1 · 일괄 전환 | 여러 Account·VPC·workload를 짧은 기간에 새 구조로 한꺼번에 전환합니다. 기존 구조와 새 구조가 함께 운영되는 기간을 줄일 수 있습니다. | 숨은 identity·DNS·data·billing dependency가 한꺼번에 드러나며 실패 영향과 rollback 범위가 커집니다. | 대안입니다. 전체 dependency·cutover 순서·동시 rollback을 사전 시험하고 프로그램 수준의 중단을 수용할 때만 성립합니다. |
| MIG-2 · Workload별 점진 전환 | workload 하나 또는 관련된 작은 묶음씩 새 구조로 전환합니다. 작은 실패에서 학습하고 workload별로 rollback할 수 있습니다. | 기존 구조와 새 구조를 잇는 임시 연결과 이중 운영이 장기화될 수 있습니다. | 현재 검토 방향입니다. Workload별 dependency, rollback 방법과 임시 연결의 owner·종료 시점이 정의되어야 합니다. |

#### 공통 기반 구축 순서

Workload 전환 단위와 별개로 Account 생성, identity, network, logging, guardrail과 검증 기반을 어느 시점까지 구축할지 결정합니다.

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| FOUNDATION-1 · Foundation-first | 공통 기반을 먼저 완성한 뒤 workload 전환을 시작합니다. 모든 전환에 같은 기준과 도구를 적용할 수 있습니다. | 실제 workload를 적용하기 전에 과도하게 설계하거나 전환 시작이 늦어질 수 있습니다. | 대안입니다. 전환 전에 반드시 완성해야 하는 공통 control과 실제 workload 없이 검증할 수 있는 범위를 구분해야 합니다. |
| FOUNDATION-2 · 최소 Foundation + Workload 차수 | 첫 workload 전환에 필요한 최소 공통 기반을 만든 뒤, 전환 차수마다 기반을 보강합니다. 공통 기준과 실제 workload에서 얻은 학습을 함께 반영할 수 있습니다. | Dependency와 version이 늘고 임시 구조가 장기적으로 남을 수 있습니다. | 현재 검토 방향입니다. 첫 전환의 최소 control, 차수별 dependency와 임시 구조의 owner·종료 시점이 정의되어야 합니다. |

전환 단위마다 source와 target, dependency, 성공·중단 조건, rollback 또는 restore 방법, 마지막으로 되돌릴 수 있는 시점과 임시 연결의 종료 조건을 기록합니다. Account, VPC, EKS와 데이터 이동은 각각 관리하되, 서로 의존하는 cutover는 함께 사전 검증합니다.

현재 연결된 외부 dependency에는 on-prem·SASE 망, managed SAP 환경, 외부 partner와 폐기 예정 legacy network가 포함됩니다. 외부 공유 문서에는 내부 이름을 노출하지 않되, 실제 전환 항목에는 연결 방식, owner, CIDR·DNS·certificate·허용 목록 dependency, 상대 조직과의 변경 일정, rollback 가능 시점과 종료 예정일을 기록합니다. TGW attachment를 제거하거나 Shared VPC로 경로를 바꾸기 전에 이 dependency가 남아 있지 않은지 확인합니다.

전환 후에는 선택한 OU·SCP, IAM, network, logging, tag와 보안 기준이 실제 AWS 상태에 적용되어 있는지 지속적으로 확인해야 합니다. 표준에서 벗어난 상태를 발견하는 것뿐 아니라 허용된 예외의 owner와 만료일, 자동 복구 가능 여부까지 관리해야 합니다.

#### 상세·후속 질문

이 질문은 목표 구조가 좁혀진 뒤 진행할 후속 검토 항목입니다.

1. Landing Zone·identity·logging·조직 control을 최소 기반으로 만든 뒤 workload별로 Account·VPC·EKS를 전환할 때, AWS managed service와 delegated administrator의 dependency 때문에 순서를 바꿔야 하는 단계가 있습니까?
2. Workload ID, DNS, resource ownership, data contract와 policy metadata를 유지해 Shared에서 Dedicated Account·VPC로, 또는 중앙 EKS에서 복수 Cluster Account로 전환하려고 합니다. AWS resource의 이동·재생성 특성상 추가로 보존해야 할 정보가 있습니까?

### 6.8 AI-native Infrastructure Operations

AI-native는 Account·VPC·EKS 같은 topology 선택지가 아니라 모든 ADR에 적용하는 운영 원칙입니다. AI를 문서 작성 보조에만 쓰는 것이 아니라 현재 상태 확인, 변경안 작성, 정책 검증, 실행 후 상태 대조와 복구까지 수행하는 운영 주체로 가정합니다. 실제 변경을 어떤 경로로 실행할지는 별도로 비교합니다.

#### 개별 변경의 실행 경로

| 선택지 | 구성·장점 | 단점·위험 | 성립 조건·확인할 사항 |
|---|---|---|---|
| AIOPS-1 · IaC-only | 지속되는 infrastructure 변경은 사람이 작성·검토한 IaC를 통해서만 실행합니다. review 가능한 diff, 반복 실행과 drift 기준이 명확합니다. | 긴급·탐색·일회성 작업이 느리고 repository가 병목이 될 수 있습니다. | 대안입니다. AI-assisted 방식과 통제·재현성 차이를 비교하는 기준으로 사용합니다. |
| AIOPS-2 · AI-assisted IaC | AI agent가 IaC 변경안을 만들고 기존 review·plan·apply 절차로 실행합니다. IaC의 재현성을 유지하면서 작성 비용을 줄일 수 있습니다. | 큰 기계 생성 diff와 실제 상태 불일치 위험이 있습니다. | 현재 검토 방향입니다. 고위험·지속 형상은 생성 diff 크기 제한, plan·policy 검사와 post-check를 기존 IaC 절차로 강제해야 합니다. |
| AIOPS-3 · Policy/Intent + Generated Plan | 사람이 원하는 상태와 policy를 선언하면 agent가 현재 상태를 읽고 IaC 또는 API 실행 plan을 생성합니다. intent와 실행 backend를 분리할 수 있습니다. | Intent schema와 상태 대조가 약하면 같은 요청의 결과가 달라질 수 있습니다. | POC 후보입니다. Intent schema, 생성 plan의 재현성과 실제 상태 대조가 검증되어야 합니다. |
| AIOPS-4 · Agent-direct MCP/CLI/API | 승인된 agent가 현재 AWS 상태를 읽고 MCP·CLI·API로 직접 변경한 뒤 결과를 검증합니다. 현재 상태 확인부터 수정·검증까지의 시간이 짧습니다. | 넓은 권한, 부분 실패, 숨은 prompt와 실행 기록 누락 위험이 있습니다. | POC 후보입니다. 저위험·가역 작업에서 제한된 임시 권한, 실행 전 승인, 실행 후 검증과 복구 기록을 강제해야 합니다. |

#### 전사 실행 경로

`AIOPS-5 · 위험 등급별 Hybrid`를 현재 검토 방향으로 둡니다. 고위험·지속 형상은 IaC, 저위험·가역 작업은 제한된 agent 직접 실행처럼 변경 위험에 따라 실행 경로를 나눕니다. 속도와 통제를 상황에 맞게 조절할 수 있지만 여러 실행 경로의 증거와 실제 상태를 함께 대조해야 하므로, 변경 위험 등급과 허용 실행 경로, 공통 audit·상태 대조 기준을 먼저 정의합니다.

모든 실행 경로는 machine-readable intent, 실행 직전 snapshot, plan, deterministic policy 검사, 승인, 제한된 임시 identity, post-check, CloudTrail, 실제 상태 대조와 복구 contract를 만족해야 합니다.

AWS MCP Server에 대해 전제한 IAM·audit·endpoint 동작과 근거는 12장에 정리했습니다.

#### 상세·후속 질문

이 질문은 AI-native 운영 POC와 위험 등급별 실행 기준을 정리한 뒤 진행할 후속 검토 항목입니다.

1. AWS MCP Server를 Production 운영에 사용할 때 AWS가 권고하는 identity, OAuth, SCP condition, CloudTrail과 approval pattern은 무엇입니까?
2. MCP나 agent의 직접 변경에 특히 부적합한 AWS resource·API 유형이 있습니까? 비가역성, 비동기 실행, 광범위한 전파와 복구 한계가 판단 기준이며, IaC와 병행할 때 활용할 수 있는 AWS 측 drift 신호도 확인하고 싶습니다.

<a id="section-7"></a>

## 7. 선택지 간 관계와 결합 검증

선택지를 먼저 개별적으로 검토한 뒤 아래 관계를 확인합니다. Account, VPC, EKS와 데이터의 개수는 각각 산정하지만, EKS Runtime(EKS cluster 배치와 장애 경계)·Network(VPC 배치와 연결)·Data(데이터 소유와 배치)는 최종적으로 하나의 후보 구성으로 함께 검증해야 합니다.

```text
운영 모델·경계 기준
  ├─ Landing Zone → Account 유형 ↔ OU/Account lifecycle → SCP/Control rollout
  ├─ Account partitioning → IAM·Runtime 소유
  └─ EKS Runtime ─┬─ VPC/Connectivity ─┬─ Ingress·DNS
                  └─ Data placement    └─ Egress·Private DNS

Secrets·KMS와 Security·Observability는 모든 구조에 적용합니다.
전환·표준 준수 검증과 AI-native 운영 원칙은 모든 변경에 적용합니다. 다만 세부 전환 순서와 agent 실행 방식에 대한 AWS 질문은 목표 구조와 POC가 구체화된 뒤 후속 검토합니다.
```

| 결합 후보 | 성격 | 구성 | 기대 효과 | 주요 위험 |
|---|---|---|---|---|
| BDL-1 · 최소 VPC 중앙 공유형 | 검증 조합 | Workload Account + 소수 Shared Cluster + 리전·환경·trust zone별 최소 Shared VPC + workload-owned data | 참여 Account 간 Peering·TGW와 중복 network 기반을 줄이고 작은 workload를 빠르게 수용합니다. | cluster와 VPC의 공통 장애 영향, tenant isolation과 중앙팀 bottleneck이 커질 수 있습니다. |
| BDL-2 · A/B 공유 VPC형 | 검증 조합 | A/B EKS Runtime + 동일 Shared VPC + Hybrid data | cluster 장애 경계를 나누면서 별도 network hop과 중복 기반을 줄입니다. | A/B가 route·DNS·IP 장애 경계를 공유해 분리 효과가 약해질 수 있습니다. |
| BDL-3 · A/B 전용 VPC형 | 검증 조합 | A/B EKS Runtime + Cell별 VPC + Hybrid 또는 Cell-local data | EKS Runtime과 Network 장애 경계를 함께 분리합니다. | Peering/TGW/PrivateLink, data transfer, endpoint와 운영 비용이 증가합니다. |
| BDL-4 · Shared + Dedicated형 | 검증 조합 | 일반 workload는 공유하고 규제·고규모·특수 요구만 전용 Account/VPC/cluster를 사용합니다. | 효율과 강한 격리를 requirement에 맞게 조합합니다. | 분리 기준이 약하면 예외와 운영 model이 계속 늘어납니다. |

이 후보는 그대로 채택할 package나 별도 의사결정 축이 아닙니다. 각 ADR에서 선택한 Account·EKS·VPC·Data 옵션이 함께 놓였을 때 기술적으로 성립하는지 검증하기 위한 대표 시나리오입니다. 개별 옵션은 bundle과 무관하게 선택할 수 있지만, 최종 후보는 최소 하나의 결합 시나리오로 장애 영향·비용·dependency를 검증해야 합니다. AWS에는 각 조합의 성립 조건과 함께 선택하면 위험한 옵션을 확인하고, AWS 공식 지침이나 명확한 운영 근거가 있는 경우에만 대안을 제시해 주시기를 요청드립니다.

<a id="section-8"></a>

## 8. 공개 가능한 유사 사례에서 확인할 내용

이 절은 첫 검토의 필수 답변이 아닙니다. 선택지 판단에 직접 도움이 되는 사례가 있을 때만 고객 대외비가 아닌 공개 자료나 익명화된 일반 pattern을 공유해 주시면 됩니다.

1. domain·brand·team을 Account 축으로 사용했다가 재편한 이유
2. 중앙 EKS나 Shared VPC가 너무 커졌거나, 반대로 cluster·VPC 수가 과도하게 늘어나 다시 분리하거나 통합한 기준
3. Peering, TGW, PrivateLink와 Lattice 사이에서 구성을 변경한 조건
4. cluster 이중화나 Account·Control Tower 전환에서 data·DNS·capacity·RAM·trust 같은 dependency를 놓친 사례

가능하다면 `초기 선택 → 문제가 된 조건 → 변경 기준 → 이후 확인된 결과` 순서로 설명해 주시기를 요청드립니다.

<a id="section-9"></a>

## 9. AWS와 함께 검토할 POC 후보

모든 옵션을 POC할 필요는 없습니다. 첫 검토에서는 아래 POC가 기술적 불확실성을 줄이는 데 유효한지만 확인합니다. POC 필요성에 합의한 뒤 AWS Specialist 참여, 아키텍처 검토, 검증 기준 확인 등 구체적인 지원 범위와 일정은 별도로 협의합니다.

| POC | 비교할 내용 | 성공 기준 |
|---|---|---|
| POC-1 · Shared Cluster + Workload Account | Pod Identity/IRSA, subnet sharing, tenant quota와 incident ownership을 비교합니다. | cross-account 최소 권한, 독립 배포·감사와 운영 책임을 설명할 수 있어야 합니다. |
| POC-2 · A/B EKS Runtime과 AZ 구성 | CUJ active-active/standby, 1-AZ 예외·2-AZ·3-AZ worker, same-zone routing, DNS rollback과 surviving capacity를 비교합니다. | 한 cluster 또는 한 AZ 장애에서 목표 SLO를 만족하고, cross-AZ bytes·사전 capacity·공통 dependency를 측정해야 합니다. |
| POC-3 · 최소 VPC·Shared VPC Pool | participant SG, NACL, route/DNS 변경, IP·quota와 분리 절차를 검증합니다. | 금지 flow를 차단하고 owner bottleneck·quota·분리 threshold를 측정할 수 있어야 합니다. |

<a id="section-10"></a>

## 10. 기대하는 검토 결과

- 기술적으로 성립하지 않거나 주의해야 할 선택지, 적용 조건과 간단한 이유
- Account·OU·EKS·VPC·Data의 공유·분리 판단에 영향을 주는 AWS quota·지원 범위·장애 특성과 cross-account 제약
- AWS 공식 지침이나 반복된 운영 근거가 있을 때 선호하거나 피할 방향
- 필요한 후속 POC·Specialist SA 검토와 주요 판단을 뒷받침하는 AWS 공식 문서

<a id="section-11"></a>

## 11. 이 문서에서 사용하는 주요 용어

- **brand**: Musinsa·29CM처럼 고객에게 구분되어 노출되는 사업 브랜드입니다. 비용 구분을 위한 metadata일 수 있지만 규제·독립 quota·권한·분사 요구가 강하면 Account 경계 후보가 됩니다.
- **One Core**: Musinsa의 여러 brand가 공통으로 사용하는 주문·상품·회원 등 business domain들의 집합입니다. 특정 Account나 EKS cluster의 이름을 뜻하지 않습니다.
- **domain**: 주문·상품·회원처럼 독립적인 business capability와 lifecycle을 가진 영역입니다. 조직 개편으로 자주 바뀌는 team과 구분합니다.
- **workload**: 공통 owner·SLO·lifecycle을 가지고 함께 배포·운영되는 application과 AWS resource의 단위입니다. 하나의 workload가 반드시 하나의 Account·VPC·EKS와 대응하지는 않습니다.
- **CUJ**: 로그인·상품 탐색·주문·결제처럼 장애가 고객과 business에 직접 영향을 주어 별도 가용성 목표를 적용하는 핵심 고객 흐름입니다.
- **A/B EKS Runtime**: 두 EKS cluster를 A와 B로 구분해 EKS control plane, add-on, upgrade, capacity와 공통 운영 변경의 장애 영향을 나누는 무신사 작업 가설입니다. Network·DNS·data를 별도로 분리하지 않으면 완전한 failure domain은 아니며, 모든 workload를 양쪽에 복제한다는 뜻도 아닙니다.
- **Full Workload Cell**: ingress, compute, data와 필수 dependency를 함께 분할하거나 복제해 독립적으로 요청을 처리하는 단위입니다.
- **trust zone**: 데이터 민감도, environment와 보안 요구가 비슷해 같은 수준의 network·접근 통제를 적용할 수 있는 범위입니다. 같은 trust zone이라는 이유만으로 resource 사이의 통신을 자동으로 허용하지는 않습니다.
- **최소 VPC·Shared VPC Pool**: 리전·환경·trust zone별로 한 VPC에서 시작해 participant Account에 subnet을 공유하고, 정한 한계에 도달하면 같은 설계의 다음 VPC를 추가하는 무신사 작업 가설입니다.
- **Organizations delegated administrator**: Organizations 관리 Account 대신 지정한 member Account가 특정 AWS 조직 지원 서비스를 관리하도록 위임받은 역할입니다. 서비스별 지원 범위와 권한은 다릅니다.
- **Account Factory**: Control Tower가 정한 baseline으로 신규 Account를 공급하고 관리하기 위한 기능입니다. Account 안의 application resource까지 배포하는 기능과는 구분합니다.
- **workload bootstrap**: 신규 Workload Account가 application을 배포할 수 있도록 IAM role, network 연결, logging, tag와 공통 설정을 초기 적용하는 절차입니다. Landing Zone 자체의 조직 baseline과 구분합니다.
- **Workload ID**: Account·VPC·cluster 이름이 바뀌어도 같은 workload를 추적하기 위한 변하지 않는 식별자입니다. Domain·brand·team·environment·data class·SLO는 이 ID에 연결된 변경 가능한 metadata로 관리합니다.
- **표준 제공 경로(paved road)**: 서비스 팀이 보안·운영 기준을 매번 직접 구현하지 않고 사용할 수 있도록 Platform이 제공하는 검증된 Account, IAM, network와 배포 module·workflow입니다. 예외 경로를 금지한다는 뜻은 아니며 예외는 owner와 종료 조건을 가집니다.
- **data contract**: 데이터 제공자와 소비자 사이의 schema, 품질, 보존, 접근 권한, 변경 호환성과 SLO에 대한 합의입니다. Account·VPC·runtime을 옮길 때 숨은 데이터 결합을 드러내는 기준으로 사용합니다.
- **Foundation**: 첫 workload 전환 전에 필요한 최소 공통 기반입니다. Account 공급, identity, logging, network·IP 관리, 조직 guardrail과 상태 검증을 포함하며 application resource 전체를 뜻하지 않습니다.

<a id="section-12"></a>

## 12. 우리가 전제한 AWS 동작

아래 내용은 선택지의 근거로 사용한 AWS 동작입니다. AWS에는 기능 자체를 다시 설명해 달라는 것이 아니라, 현재 이해에서 틀리거나 빠진 제약을 지적해 달라고 요청합니다.

| 영역 | 전제한 AWS 동작 | 설계에 미치는 영향 |
|---|---|---|
| Control Tower 4.0과 기존 Account 편입 | Landing zone 4.0에서는 Config·CloudTrail·SecurityRoles·Backup 등의 service integration을 선택할 수 있습니다. Landing zone 수준의 Config integration은 service integration Account에 중앙 resource를 구성하며, 일반 member Account의 Config recorder 등은 destination OU에 적용한 baseline에 따라 달라집니다. 기존 VPC는 편입 과정에서 제거되지 않습니다. | 활성화할 service integration과 OU baseline 조합을 먼저 정하고, 그 조합이 생성·변경하는 Config·CloudTrail·IAM·StackSet과 기존 설정의 충돌·중복 비용을 Account별로 검사해야 합니다. ([4.0 변경 사항](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html), [Baseline 유형](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html), [기존 Account 편입](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)) |
| Control Tower auto-enrollment | Landing zone 3.1 이상에서 auto-enrollment를 활성화하면 Account를 등록 OU로 이동할 때 해당 OU의 baseline과 control이 자동 적용됩니다. 기존 설정 충돌과 실패 복구를 자동으로 해결하는 기능은 아닙니다. | Transitional OU의 사전 검사, 등록 OU 이동, 자동 enrollment와 내부 workload bootstrap의 실행 순서를 분리해야 합니다. ([근거](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)) |
| SCP 평가 | SCP는 권한을 부여하지 않고 principal이 가질 수 있는 최대 권한을 제한합니다. Allow-list는 Root부터 Account까지 직접 경로의 모든 level에서 Allow가 필요하고, 어느 level의 explicit Deny도 하위 Allow로 되돌릴 수 없습니다. | Root policy와 OU 상속을 변경하기 전에 effective policy를 계산하고 시험해야 합니다. ([근거](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)) |
| RCP | RCP는 지원되는 resource가 허용할 수 있는 접근의 최대 범위를 제한하며 권한을 직접 부여하지 않습니다. 지원 서비스와 management Account·service-linked role 예외가 있습니다. | 모든 resource 접근을 RCP 하나로 통제할 수 없으므로 지원 범위와 예외를 별도 관리해야 합니다. ([근거](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)) |
| Declarative policy·Tag Policy·Control Tower control | Declarative policy는 지원 AWS 서비스의 baseline 설정을 service control plane에서 유지합니다. Tag Policy는 정의된 tag의 표준과 지원 resource의 준수를 검사·강제할 수 있으며, Control Tower control은 OU 단위로 예방·사전 검사·탐지 control을 적용합니다. | 같은 목적을 SCP에 중복 구현하지 않고 control objective별 owner와 적용 수단을 구분해야 합니다. ([Declarative policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html), [Tag Policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html), [Control Tower control](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)) |
| Shared VPC 책임 | Owner는 subnet·route·NACL·NAT·endpoint·TGW attachment 등을 관리하고 participant는 자기 ENI와 Security Group을 관리할 수 있습니다. Participant가 만든 resource의 일부 quota는 participant Account에 계산됩니다. | Network 권한이 완전히 0이 되는 model은 아닙니다. Participant SG 권한과 owner가 볼 수 있으나 변경할 수 없는 resource를 별도 통제해야 합니다. ([근거](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)) |
| VPC quota와 Security Group | IPv4 CIDR은 VPC당 기본 5개이며 quota 조정 후 최대 50개입니다. Subnet·NAU·participant·SG·endpoint 등 다른 quota가 먼저 한계가 될 수 있습니다. Security Group은 allow rule만 지원하고 연결된 여러 SG의 rule은 합쳐집니다. | SVPC-1은 최대 CIDR 수가 아니라 먼저 도달하는 quota·운영 한계와 SG 통제를 기준으로 분리해야 합니다. ([VPC quota](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html), [Security Group](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)) |
| Shared VPC의 AZ와 SG | AZ 이름은 Account마다 다른 물리 AZ를 가리킬 수 있으므로 cross-account 배치는 AZ ID로 맞춰야 합니다. VPC owner는 Organizations 안에서 SG를 공유할 수 있고 Firewall Manager는 공통 SG 배포와 SG audit policy를 제공하지만, SG의 additive Allow 동작은 그대로입니다. | A/B·AZ 배치에는 AZ ID를 사용하고, participant SG 권한·Shared SG·Firewall Manager와 policy 검사를 함께 설계해야 합니다. ([AZ ID](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html), [Shared SG](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html), [Firewall Manager](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)) |
| VPC IPAM | Organizations와 연동해 delegated IPAM Account가 member Account의 CIDR과 사용 현황을 확인하고 RAM으로 IPAM pool을 공유할 수 있습니다. 사용 tier에 따라 기능과 active IP 과금이 달라집니다. | Shared·Dedicated VPC 모두 같은 pool hierarchy와 allocation policy를 사용하되, 기존 CIDR 처리와 비용을 확인해야 합니다. ([Organizations 연동](https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam.html), [Pricing](https://docs.aws.amazon.com/vpc/latest/ipam/pricing-ipam.html)) |
| Regional NAT Gateway | Regional NAT Gateway는 하나의 ID로 workload가 있는 AZ에 자동 확장·축소되며 public subnet 없이 public egress를 제공합니다. Private NAT는 지원하지 않고 새 AZ 확장에 최대 60분이 걸릴 수 있으며, 기존 Zonal NAT 전환은 connection reset이나 IP 변경·중단을 수반할 수 있습니다. | 2-AZ·3-AZ와 중앙·분산 egress의 NAT 고정비와 경로를 Zonal NAT만으로 계산하지 않고, 두 availability mode의 비용·IP·확장 지연·전환 위험을 비교해야 합니다. ([동작과 제약](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html), [리전 지원](https://aws.amazon.com/about-aws/whats-new/2025/11/aws-nat-gateway-regional-availability/)) |
| TGW와 Network Firewall | 중앙 inspection은 inspection VPC의 firewall endpoint를 TGW가 경유하는 방식과 Network Firewall을 TGW에 직접 attachment하는 방식으로 구성할 수 있습니다. Network Firewall은 asymmetric routing을 지원하지 않으며 inspection VPC 방식은 appliance mode와 양방향 route가 필요합니다. | INSP-3은 단일 구현으로 고정하지 않고 symmetric routing, route-table 강제, TGW·firewall Account ownership, 삭제 권한과 비용을 비교해야 합니다. ([TGW-attached firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html), [고려사항](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall-considerations.html), [Asymmetric routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)) |
| AWS API와 VPC endpoint | AWS service·Region·기능에 따라 gateway 또는 interface endpoint 지원 여부와 endpoint policy 지원 여부가 다릅니다. Endpoint policy를 명시하지 않으면 기본 full-access policy가 적용되고, endpoint policy를 지원하지 않는 서비스도 있습니다. | AWS API 경로를 일괄적으로 endpoint로 고정하지 않고 지원 범위와 resource policy·`aws:SourceVpce` 적용 가능성을 확인하며, 미지원 경로에는 통제된 egress를 둬야 합니다. ([지원 서비스](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html), [Endpoint policy](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)) |
| Route 53 Profiles와 hybrid DNS | Route 53 Profiles는 서울 리전에서 PHZ·Resolver rule·DNS Firewall·query logging 등을 여러 VPC에 적용하고 RAM으로 공유할 수 있으며 VPC에는 Profile 하나를 연결합니다. Resolver inbound·outbound endpoint와 forwarding rule은 VPN 또는 Direct Connect로 AWS와 on-prem 사이의 private DNS 조회를 연결합니다. | DNS ownership과 설정 배포를 분리하고, local VPC 설정 우선순위·Profile 비용·hybrid DNS 장애와 삭제 순서를 검증해야 합니다. ([Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html), [Hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html), [서울 리전](https://docs.aws.amazon.com/general/latest/gr/r53.html)) |
| EKS Access Entries·Pod Identity | Access Entry는 IAM principal에 EKS Access Policy를 연결하거나 Kubernetes group에 mapping해 RBAC을 사용할 수 있습니다. EKS와 Kubernetes authorizer는 allow 또는 pass로 동작하므로 두 경로의 허용 권한은 합쳐지며 한쪽으로 다른 쪽의 권한을 줄일 수 없습니다. Pod Identity role은 cluster와 같은 Account에 있어야 하므로 cross-account resource 접근에는 target role이 추가로 필요합니다. | 사람의 cluster 접근과 Pod의 AWS API 접근을 별도 control로 설계하고, Principal별 Access Policy·RBAC 중복 grant를 검사해야 합니다. ([Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [Authorization 동작](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html), [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)) |
| Secrets Manager·KMS cross-account | Secret resource policy와 호출자 identity policy가 모두 필요하며, cross-account secret에는 customer-managed KMS key가 필요합니다. KMS key도 owner Account의 key policy와 caller Account의 IAM policy가 모두 필요합니다. | 중앙 KEY-1은 policy·rotation뿐 아니라 양쪽 Account의 permission과 복구 책임을 함께 운영해야 합니다. ([Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html), [KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)) |
| AWS MCP Server | AWS API 호출은 기존 IAM credential과 downstream service permission으로 authorize되고 CloudTrail에 기록됩니다. MCP condition context key로 경로를 구분할 수 있습니다. 2026-08-21 기준 service endpoint는 미국 동부와 프랑크푸르트에 있습니다. | MCP 자체를 별도 permission boundary로 간주하지 않고 최소 권한·승인·실행 전후 검증을 설계해야 합니다. ([동작](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html), [IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html), [Endpoint](https://docs.aws.amazon.com/general/latest/gr/aws-mcp.html)) |
