# 의사결정 프레임워크와 POC 설계

> **마지막 업데이트**: 2026년 9월 13일

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

<span id="alb-weighted-target-group의-fail-open-동작"></span>

### ALB weighted forwarding과 target-group fail-open 구분

Weighted forward action은 weight가 있는 target group이 비거나 unhealthy하다고 다른 group으로 자동 failover하지 않습니다. **선택된 group 내부의 fail-open**은 별도 동작으로, healthy-target 기준이 부족하면 해당 LB node가 접근 가능한 unhealthy target에도 라우팅할 수 있습니다. 다음 속성의 DNS failover와 routing failover를 함께 검토합니다.

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count`(또는 `.percentage`)
- `target_group_health.dns_failover.minimum_healthy_targets.count`(또는 `.percentage`)

Unified configuration은 두 action에 같은 임계값을 적용합니다. DNS failover 기준은 routing failover 기준 이상이어야 하며 count와 percentage를 함께 설정하면 어느 하나를 위반해도 동작합니다. 비율은 등록 target 수를 기준으로 하므로 그 자체가 CUJ 처리 용량이나 N-1 SLO를 증명하지 않습니다. weight 변경 gate에는 실제 부하·오류율·지연을 함께 사용합니다.

### 미사용 리전 통제

단일 리전 운영을 결정했다면, 그 결정과 별개로 다음을 챙겨야 합니다.

- **예방**: SCP `aws:RequestedRegion` Deny (global 서비스는 예외 목록 필요)
- **탐지**: 허용·사용 가능한 Region의 CloudTrail·GuardDuty·Security Hub CSPM coverage를 확인합니다. 한 제품이 꺼져 있다고 모든 활동이 탐지 불가능한 것은 아닙니다.
- **Opt-in Region**: 사용하지 않는 opt-in Region은 비활성화할 수 있지만 기본 활성화 Region은 이 방법으로 끌 수 없습니다. 비활성화가 기존 resource를 삭제하거나 요금을 중지하지도 않습니다. cleanup·SCP·탐지를 함께 설계합니다.

### 비용 관측성과 태그 강제 시점

cross-AZ 비용 귀속은 Flow Logs·ENI/IP·Kubernetes workload identity와 CUR의 과금 항목을 연결해 검증합니다. 모든 ENI가 사용자 태그를 지원하거나 생성 시점의 RequestTag 조건을 제공하는 것은 아닙니다. 태그 정책·IaC·지원 API의 SCP 조건은 서비스별 coverage를 확인해 적용합니다.

## 2. 판정표 설계

여러 문서에서 다룬 선택지들 — 경계 독립 판정, Hybrid Account portfolio, Shared+Dedicated EKS, trust zone 혼합 VPC, Hybrid data, Hybrid key ownership — 은 전부 **"판정표로 재현 가능하다"를 성립 조건**으로 둡니다. 판정표가 없으면 어떤 POC 결과도 표준으로 전환되지 않습니다.

판정표에 포함할 것을 권장하는 열:

| 열 | 목적 |
|---|---|
| EKS 필요 여부 | EKS 경계가 VPC 경계에 종속되는지 판단 |
| Cross-account 리소스 접근 | target-role chaining, resource policy, IRSA 중 적합한 경로 확인 |
| Shared subnet 미지원 서비스 사용 여부 | Shared VPC locality 대상 제외 판단 |
| Permission Set–Account별 group 할당 수 | 실제100개 한도와 성장률 확인;50경고는 조직별 예시 |
| 1차 대응 주체 / escalation 경로 | 복구 주체가 둘 이상이면 분리 후보 |
| CUJ RTO/RPO | 데이터·가용성 설계 전반의 판정 근거 |

## 3. POC 설계 패턴

서면 검토만으로 확정할 수 없는 항목은 실측이 필요합니다. 아래 POC는 우선순위 순서로 배치했습니다.

### POC-0. 판정표 dry-run (다른 POC보다 먼저 수행)

- **입력**: 대표 워크로드 10~15개 (CUJ 포함, 개인정보 취급 1개 이상, 공통 도메인 1개 이상, 작은 사내 도구 2개 이상, 외부 파트너 연동 1개 이상)
- **절차**: 판정표를 두 사람이 독립적으로 적용하고 결과를 대조
- **성공 기준 예시**: 불일치율 20% 미만, 예외 처리율 15% 미만(조직이 조정할 가설)
- **부수 산출물**: 판정 결과로부터 Account/VPC/클러스터 수 추정치가 나오고, 이 값이 나머지 POC의 quota 측정 목표값을 결정

### POC-1. Shared Cluster + Workload Account

| 측정 항목 | 판정 기준 |
|---|---|
| Pod Identity·resource policy·IRSA의 권한 경로 | source/target role 재사용·scope·회수·KMS와 resource-policy 검증; 고정2role산식 금지 |
| Shared subnet에서 ALB Controller의 subnet 자동 탐색 | 태그 자동 탐색 실패 여부 → 실패 시 명시적 annotation을 표준으로 전환 |
| Access entry 수 증가율 | 워크로드 1개 추가 시 증가량 × 목표 워크로드 수 < 3,000 |
| Managed node group 수 | 기본30과 승인 quota 대비 여유; node placement와 보안 격리 구분 |
| Cluster Account/Workload Account 간 장애 1차 대응 시간 | "CNI 문제 vs 애플리케이션 문제" 판별 소요 시간 측정 |
| Participant SG의 넓은 Allow 탐지·차단 시간 | Firewall Manager audit policy 위반 탐지 → 차단 시간 |

### POC-2. A/B EKS Runtime과 AZ 구성 (선행 조건: CUJ별 RTO/RPO 정의)

| 측정 항목 | 판정 기준 |
|---|---|
| [3장](./03-eks-multi-account-multi-cluster.md)의 장애 목록 중 3개 이상 실제 주입 | 각 장애가 한쪽 클러스터로 격리되는지 확인 |
| ARC zonal autoshift practice run | A/B 각 클러스터가 단독으로 N-1 AZ peak를 처리하는지 |
| CoreDNS N-1 처리량/지연 | 지연 증가율, ENI당 1,024 packet/s 한도 도달 여부 |
| CUJ 서비스 그래프의 AZ 커버리지 | surviving AZ에서 모든 dependency의 도달성·용량·fallback 검증 |
| Stateful 복구 | EBS의 AZ 제약, 대체 storage/replication, 복구 시간·데이터 손실 검증 |
| A→B 전환 end-to-end 시간 | edge 전환과 Route 53 record 변경을 각각 분리 측정 |
| Rollback 시간 | 전환 시간과 별도로 측정 |
| cross-AZ bytes | Flow Logs 기반, 최적화 전후 비교 |
| 사전 capacity 배수 | 실측값을 2배/1.5배 가설과 대조 |

### POC-3. 최소 Shared VPC / Shared VPC Pool

| 측정 항목 | 판정 기준 |
|---|---|
| **TGW와 VPC route 수(현재/3년 예상)** | TGW table 합계10,000과 VPC non-propagated500/조정1,000을 별도 계산; VGW100과 구분 |
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

어떤 실행 경로를 택하든 작업 위험에 맞춰 다음 조건을 정의합니다: machine-readable intent, 실행 직전 snapshot, plan, deterministic policy 검사, 승인, 제한된 임시 identity, post-check, CloudTrail 기록, 실제 상태 대조, 복구 contract.

> **AWS MCP Server 확인 범위**: 현재 endpoint 목록은 us-east-1과 eu-central-1을 제시합니다. endpoint 위치와 조작 대상 resource Region은 구분합니다. API 실행은 IAM 및 downstream permission으로 제한되고 CloudTrail 기록을 검토할 수 있습니다. endpoint·인증·로그 범위·데이터 경로는 조직 요구에 맞게 확인하며, 서울 endpoint 부재만으로 규제 위반 여부를 결론내리지 않습니다.

## 관련 문서

- [엔터프라이즈 클라우드 거버넌스 개요](./00-governance-overview.md)
- [Landing Zone, OU와 조직 Control](./01-landing-zone-and-ou.md)
- [Account 구성과 IAM 경계](./02-account-and-iam.md)
- [EKS 멀티 계정·멀티 클러스터 아키텍처](./03-eks-multi-account-multi-cluster.md)
- [Shared VPC와 Connectivity](./04-shared-vpc-and-connectivity.md)
- [Data·Security 경계](./05-data-security-boundaries.md)

## 참고 자료

- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB rule action types (weighted)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Route 53 weighted routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Route 53 failover routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [AWS MCP Server IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
- [AWS MCP regional endpoints](https://docs.aws.amazon.com/general/latest/gr/aws-mcp.html)
- [Charges in disabled Regions](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/checklistforunwantedcharges.html)
