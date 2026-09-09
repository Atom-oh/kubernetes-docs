# 의사결정 프레임워크와 POC 설계

> **마지막 업데이트**: 2026년 9월 9일

지금까지 다룬 Landing Zone, Account/IAM, EKS, VPC, Data/Security 경계는 각각 독립적으로 판정하되, 실제로는 하나의 판정표로 재현 가능해야 합니다. 이 문서는 그 판정표를 어떻게 설계하고, 실측이 필요한 항목을 어떻게 POC로 검증할지 다룹니다.

## 1. 누락되기 쉬운 결정 요소

경계·계정·네트워크 구조를 아무리 정교하게 설계해도, 다음 요소들이 정의되어 있지 않으면 그 설계가 실제로 맞는지 판정할 수 없습니다.

### CUJ별 RTO/RPO 목표 — 가장 큰 누락

CUJ(critical user journey)별 RTO(Recovery Time Objective)/RPO(Recovery Point Objective)가 정의되어 있지 않으면 다음을 전혀 판정할 수 없습니다.

- A/B EKS Runtime 전환이 충분히 빠른가 (DNS TTL + edge 전파 + Route 53 전파 + health 판단 지연의 합)
- 중앙 운영과 워크로드 소유 중 어느 데이터 모델이 실제로 복구 가능한가 (스냅샷 복사 시간이 RTO에 포함되는지)
- 2-AZ와 3-AZ의 차이가 의미 있는가 (N-1 상태에서 SLO를 유지할 수 있는가)
- Cell 단위 격리의 추가 비용이 정당화되는가

**CUJ별 RTO/RPO/허용 오류율 표를 다른 무엇보다 먼저 정의해야 합니다.**

### 장애 시 복구 주체(on-call ownership)

경계 판정 기준에 보안·quota·비용·lifecycle·장애 영향까지 있어도 "누가 1차 대응하는가"가 빠지면, Shared Cluster에서 "이게 CNI 문제인지 애플리케이션 문제인지 불분명한" 야간 장애에서 시간을 잃게 됩니다. 판정표에 "1차 대응 주체", "escalation 경로" 열을 추가하고, **복구 주체가 둘 이상으로 나뉘는 경계는 분리 후보**로 삼는 규칙을 권장합니다.

### Kubernetes 목표 버전과 업그레이드 전략

`trafficDistribution` 필드값, Karpenter의 ARC zonal shift 연동(1.12 이상), EKS Auto Mode 채택 여부(node lifecycle 소유권), add-on 호환성 매트릭스는 모두 EKS 버전에 의존합니다. A/B EKS Runtime의 존재 이유가 업그레이드 격리라면, 버전 스큐 허용 범위·A/B 순차 업그레이드 규칙·extended support 사용 여부를 명문화해야 합니다.

### ALB weighted target group의 fail open 동작

"unhealthy target으로는 자동 failover하지 않는다"는 설명은 절반만 맞습니다. 실제로는 **healthy target이 부족하면 ALB가 등록된 모든 target(unhealthy 포함)에 트래픽을 보냅니다(fail open).** 완화 설정은 두 가지입니다.

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count`(또는 `.percentage`)
- `target_group_health.dns_failover.minimum_healthy_targets.count`(또는 `.percentage`)

AWS 권고는 "Unified configuration" — 양쪽에 동일한 임계값을 설정하는 것입니다. 기본값은 "healthy target 1개면 healthy"이므로, 대규모 target group에서 1개만 살아 있어도 정상으로 판단됩니다. 트래픽 weight를 올리는 게이트는 target health 자체가 아니라 **`minimum_healthy_targets.percentage`(CUJ의 N-1 capacity 기준)** 통과 여부로 설정하는 것을 권장합니다.

### 미사용 리전 통제

단일 리전 운영을 결정했다면, 그 결정과 별개로 다음을 챙겨야 합니다.

- **예방**: SCP `aws:RequestedRegion` Deny (global 서비스는 예외 목록 필요)
- **탐지**: Security Hub CSPM·GuardDuty는 활성화한 리전의 finding만 처리하고 소급 수집하지 않습니다 — 미사용 리전을 비활성화하지 않으면 그 리전의 활동은 탐지되지 않습니다.
- **가장 강한 통제**: Region opt-in 비활성화

### 비용 관측성과 태그 강제 시점

cross-AZ 비용을 워크로드 pair 단위로 귀속하려면 ENI 수준까지 태그가 필요하고, **리소스 생성 시점에 강제**되어야 합니다. Tag Policy는 준수 검사·강제는 하지만 모든 리소스를 덮지는 않습니다. IaC 템플릿 강제 + SCP `aws:RequestTag` 조건 + Tag Policy 검사의 3중 구조를 권장합니다. Shared VPC에서 owner의 태그가 participant에게 보이지 않는다는 점([04장](./04-shared-vpc-and-connectivity.md))도 비용 귀속 설계에 반영해야 합니다.

## 2. 판정표 설계

여러 문서에서 다룬 선택지들 — 경계 독립 판정, Hybrid Account portfolio, Shared+Dedicated EKS, trust zone 혼합 VPC, Hybrid data, Hybrid key ownership — 은 전부 **"판정표로 재현 가능하다"를 성립 조건**으로 둡니다. 판정표가 없으면 어떤 POC 결과도 표준으로 전환되지 않습니다.

판정표에 포함할 것을 권장하는 열:

| 열 | 목적 |
|---|---|
| EKS 필요 여부 | EKS 경계가 VPC 경계에 종속되는지 판단 |
| Cross-account 리소스 접근 필요 여부 | Pod Identity 2단 구조 필요성 판단 |
| Shared subnet 미지원 서비스 사용 여부 | Shared VPC locality 대상 제외 판단 |
| 이 Account에 접근할 group 수 예상치 | ABAC 전환·Account 분리 threshold (50개 기준) |
| 1차 대응 주체 / escalation 경로 | 복구 주체가 둘 이상이면 분리 후보 |
| CUJ RTO/RPO | 데이터·가용성 설계 전반의 판정 근거 |

## 3. POC 설계 패턴

서면 검토만으로 확정할 수 없는 항목은 실측이 필요합니다. 아래 POC는 우선순위 순서로 배치했습니다.

### POC-0. 판정표 dry-run (다른 POC보다 먼저 수행)

- **입력**: 대표 워크로드 10~15개 (CUJ 포함, 개인정보 취급 1개 이상, 공통 도메인 1개 이상, 작은 사내 도구 2개 이상, 외부 파트너 연동 1개 이상)
- **절차**: 판정표를 두 사람이 독립적으로 적용하고 결과를 대조
- **성공 기준**: 불일치율 20% 미만, 예외 처리율 15% 미만
- **부수 산출물**: 판정 결과로부터 Account/VPC/클러스터 수 추정치가 나오고, 이 값이 나머지 POC의 quota 측정 목표값을 결정

### POC-1. Shared Cluster + Workload Account

| 측정 항목 | 판정 기준 |
|---|---|
| Pod Identity 2단 구조(association → target role)의 권한 경로 수 | 워크로드 1개당 role 2개 + trust policy 2개, 워크로드 수에 선형 증가하는지 확인 |
| Shared subnet에서 ALB Controller의 subnet 자동 탐색 | 태그 자동 탐색 실패 여부 → 실패 시 명시적 annotation을 표준으로 전환 |
| Access entry 수 증가율 | 워크로드 1개 추가 시 증가량 × 목표 워크로드 수 < 3,000 |
| Managed node group 수 | tenant 격리 전략 적용 시 30개 한도 대비 여유 |
| Cluster Account/Workload Account 간 장애 1차 대응 시간 | "CNI 문제 vs 애플리케이션 문제" 판별 소요 시간 측정 |
| Participant SG의 넓은 Allow 탐지·차단 시간 | Firewall Manager audit policy 위반 탐지 → 차단 시간 |

### POC-2. A/B EKS Runtime과 AZ 구성 (선행 조건: CUJ별 RTO/RPO 정의)

| 측정 항목 | 판정 기준 |
|---|---|
| [3장](./03-eks-multi-account-multi-cluster.md)의 장애 목록 중 3개 이상 실제 주입 | 각 장애가 한쪽 클러스터로 격리되는지 확인 |
| ARC zonal autoshift practice run | A/B 각 클러스터가 단독으로 N-1 AZ peak를 처리하는지 |
| CoreDNS N-1 처리량/지연 | 지연 증가율, ENI당 1,024 packet/s 한도 도달 여부 |
| CUJ 서비스 그래프의 AZ 커버리지 | 모든 hop이 모든 AZ에 존재하는지 (pod affinity 포함) |
| Stateful 워크로드의 PV 재바인딩 | 정상 AZ에서 Pod가 실제로 뜨는지 |
| A→B 전환 end-to-end 시간 | edge 전환과 Route 53 record 변경을 각각 분리 측정 |
| Rollback 시간 | 전환 시간과 별도로 측정 |
| cross-AZ bytes | Flow Logs 기반, 최적화 전후 비교 |
| 사전 capacity 배수 | 실측값을 2배/1.5배 가설과 대조 |

### POC-3. 최소 Shared VPC / Shared VPC Pool

| 측정 항목 | 판정 기준 |
|---|---|
| **TGW 전파 prefix 수(현재/3년 후 예상)** | 100 미달 여부, 초과 시 default route 전환 가능 여부 |
| Participant Account 수 증가율 | 목표 팀 수 대비 100 한도 |
| Account당 공유 subnet 수 | AZ×trust zone×용도 조합 vs 100 |
| NAU 사용량 | Pod 밀도 반영, 64,000 → 256,000 조정 필요 시점 |
| Owner에게 route/DNS 변경 요청 → 반영 시간 | bottleneck 정량화 |
| Flow log 증거 완결성 | owner+participant 로그로 전체 flow를 재구성할 수 있는지 |
| 최소 구성 vs 전용 구성에서 잘못된 중앙 route 변경의 탐지·복구 시간 | 두 안 모두 측정 (실제 선택 기준) |
| TGW attachment 처리량 | AZ당 100 Gbps/7.5M PPS 대비 여유 |

## 4. AI 기반 운영과의 관계

이 프레임워크는 Account/VPC/EKS 같은 topology 선택에만 적용되는 것이 아니라, 모든 ADR(Architecture Decision Record)에 적용하는 운영 원칙으로 확장할 수 있습니다. 인프라 변경을 자동화하는 실행 경로는 크게 다음과 같이 나뉩니다.

- **IaC-only**: 사람이 작성·검토한 IaC로만 변경. 재현성이 가장 높지만 긴급·탐색 작업에는 느립니다.
- **AI-assisted IaC**: agent가 IaC 변경안을 생성하고, 기존 review → plan → apply 절차로 실행. 작성 비용은 줄지만 큰 생성 diff와 실제 상태 불일치 위험이 있습니다.
- **Policy/Intent + Generated Plan**: agent가 현재 상태를 읽고 실행 plan을 생성. intent와 backend가 분리되지만, intent schema·상태 대조가 약하면 결과가 일관되지 않습니다.
- **Agent-direct MCP/CLI/API**: 승인된 agent가 직접 변경 후 검증. 속도가 가장 빠르지만 넓은 권한·부분 실패·prompt injection 위험이 있습니다.
- **위험 등급별 Hybrid**: 고위험·지속적인 형상 변경은 IaC로, 저위험·가역적인 작업은 제한된 agent 직접 실행으로 처리. 대부분의 조직에 현실적인 방향입니다.

어떤 실행 경로를 택하든 최소한 다음 조건은 만족해야 합니다: machine-readable intent, 실행 직전 snapshot, plan, deterministic policy 검사, 승인, 제한된 임시 identity, post-check, CloudTrail 기록, 실제 상태 대조, 복구 contract.

> **AWS MCP Server 관련 확인 사실**: AWS API 호출은 기존 IAM credential과 downstream service permission으로 authorize되고 CloudTrail에 기록됩니다. MCP condition context key로 접근 경로를 구분할 수 있습니다. 다만 이 글 작성 시점 기준 AWS MCP Server의 서비스 endpoint는 미국 동부와 프랑크푸르트에만 존재합니다 — **서울 리전에 없다는 사실 자체가 결정 조건**이 됩니다. (a) 규제 관점에서 데이터 이동 검토 대상이 되는지, (b) 리전 장애 시 복구 도구가 타 리전에 의존하는 것이 이점인지 위험인지를 보안팀과 함께 판단해야 합니다.

## 관련 문서

- [엔터프라이즈 클라우드 거버넌스 개요](./00-governance-overview.md)
- [Landing Zone, OU와 조직 Control](./01-landing-zone-and-ou.md)
- [Account 구성과 IAM 경계](./02-account-and-iam.md)
- [EKS 멀티 계정·멀티 클러스터 아키텍처](./03-eks-multi-account-multi-cluster.md)
- [Shared VPC와 Connectivity](./04-shared-vpc-and-connectivity.md)
- [Data·Security 경계](./05-data-security-boundaries.md)

## 참고 자료

- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health.html)
- [ALB rule action types (weighted)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Route 53 weighted routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Route 53 failover routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [AWS MCP Server IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
