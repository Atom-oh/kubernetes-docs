# EKS 멀티 계정·멀티 클러스터 아키텍처

> **마지막 업데이트**: 2026년 9월 9일

## 1. 클러스터 수용 방식

여러 팀·도메인의 워크로드를 EKS에 배치하는 방식은 크게 네 가지로 나뉩니다.

| 방식 | 구성 |
|---|---|
| 단일 Core EKS | 모든 워크로드를 하나의 클러스터에 배치 |
| Environment별 중앙 EKS | production/non-production마다 클러스터 하나 |
| Domain별 EKS | 도메인마다 전용 클러스터 |
| **Shared + Dedicated** | 일반 워크로드는 공용 클러스터, 강한 tenant·quota·SLO 요구가 있는 워크로드만 전용 클러스터로 분리 |

Shared + Dedicated 조합이 대부분의 조직에 현실적인 시작점입니다. 문제는 "언제 전용 클러스터로 분리할 것인가"를 감으로 판단하지 않고, 측정 가능한 신호로 정의하는 것입니다.

| 신호 | 측정 방법 | 분리 threshold |
|---|---|---|
| Managed node group 수 | EKS API | 25 / 30 |
| Access entry 수 | EKS API | 2,000 / 3,000 |
| Control plane API throttling | CloudWatch, 429 로그 | 지속적 429 발생 |
| etcd 크기·객체 수 | `apiserver_storage_size_bytes` | AWS 권고 한도 접근 시 |
| NAU (Network Address Usage) per VPC | VPC 콘솔·CloudWatch | 50,000 / 64,000 (또는 200,000 / 256,000) |
| Upgrade blast radius | 클러스터에 배포된 CUJ 수 | CUJ 2개 이상이면 분리 검토 |
| Add-on 변경 주기 충돌 | 팀별 add-on 버전 요구 차이 | 상충 요구 발생 시 분리 |

이 표의 상한값에 근접했을 때 분리하는 것이 아니라, **분리 결정 자체를 이 지표들의 threshold로 자동화**하는 것이 목표입니다.

## 2. A/B EKS Runtime: 두 클러스터로 장애 경계 나누기

같은 CUJ(critical user journey)를 두 개의 독립된 EKS 클러스터에 배포해서, 한쪽 클러스터에 장애가 생겨도 다른 쪽이 트래픽을 받는 구조를 흔히 "A/B EKS Runtime"이라고 부릅니다. 이건 **AWS의 공식 권장 패턴이 아니라 조직이 직접 검증해야 하는 작업 가설**입니다. 실제로 가용성을 높이려면 아래 조건들을 먼저 충족해야 합니다.

### 무엇으로부터 보호하는가를 먼저 정의한다

EKS managed control plane은 이미 Multi-AZ로 동작하고, ARC(Application Recovery Controller)의 zonal shift/autoshift는 **data plane에만** 작용합니다. 즉 A/B 이중화의 가치는 "AZ 장애 대비"가 아니라 **조직이 직접 만들어내는 장애**에 대한 방어입니다.

- 클러스터 업그레이드 실패
- Add-on(CNI/CoreDNS/CSI) 회귀
- Admission webhook 오류
- 잘못 배포된 cluster-wide policy
- Control plane API throttling

이 장애 목록을 명문화하고, "A/B로 나눈 뒤 이 목록의 장애가 실제로 한쪽으로 격리되는가"를 POC의 성공 기준으로 삼아야 합니다. "가용성이 향상됐다"는 추상적 표현으로는 검증할 수 없습니다.

### CoreDNS가 가장 흔한 단일 실패 지점

A/B 구조와 AZ 이중화 모두에서, CoreDNS가 가장 흔한 단일 실패 지점입니다. 확인해야 할 항목:

- `replicaCount`와 `topologySpreadConstraints`가 AZ에 실제로 분산되어 있는가
- CoreDNS add-on의 autoscaling(`{"autoScaling":{"enabled":true}}`) 또는 HPA / cluster-proportional-autoscaler 적용 여부
- 한 AZ를 제거했을 때 QPS·지연 변화

**EC2 인스턴스의 ENI 하나가 Route 53 Resolver로 보낼 수 있는 패킷은 초당 1,024개(조정 불가)**입니다. Pod 밀도가 높은 노드에서는 이 한도가 DNS 실패의 실제 원인이 될 수 있습니다. NodeLocal DNS 도입을 검토하세요.

### ARC zonal shift는 사전 확보된 여유 capacity 없이는 오히려 장애를 유발한다

AWS 문서가 명시적으로 경고하는 부분입니다. zonal shift가 발생하면 다음이 자동으로 일어납니다.

1. 해당 AZ 전체 node cordon(신규 스케줄링 차단)
2. Managed node group의 AZ rebalancing 중단
3. EndpointSlice에서 해당 AZ의 Pod 제거
4. Node·Pod 자체는 종료되거나 evict되지 않음(해제 시 즉시 복귀)
5. ARC에 등록된 ALB/NLB는 정상 AZ로만 라우팅

**Fail-safe 동작**: 어떤 워크로드의 endpoint가 전부 장애 AZ에만 있으면, EKS는 그 AZ로 트래픽을 계속 보냅니다. 즉 **1-AZ에만 배포된 워크로드는 zonal shift로 보호받지 못합니다.**

기술적 제약도 확인이 필요합니다.

- **EKS Fargate에서는 동작하지 않습니다.**
- Self-managed Karpenter는 **1.12 이상**에서 지원합니다.
- EKS Auto Mode는 추가 설정 없이 연동되며, node provisioning 중단과 consolidation/drift 같은 voluntary disruption까지 자동으로 처리합니다.
- Stateful 워크로드는 별도 판단이 필요합니다 — 정상 AZ의 새 Pod는 장애 AZ에 바인딩된 EBS 볼륨(PV)에 attach할 수 없습니다. **AZ 수와 무관하게 PVC를 쓰는 워크로드는 zonal EBS에 묶여 있습니다.**

> **설계 규칙 권장**: "ARC zonal autoshift 대상 클러스터에는 1-AZ 워크로드를 두지 않는다"를 명문 규칙으로 두세요. 같은 클러스터에 1-AZ 워크로드가 섞여 있으면, autoshift practice run이 그 워크로드를 중단시킵니다.

### 사전 capacity 배수 계산의 함정

"2-AZ면 약 2배, 3-AZ(N-1 기준)면 약 1.5배의 사전 capacity가 필요하다"는 계산은 산술적으로는 맞지만, 세 가지를 놓치기 쉽습니다.

1. **노드 추가 소요 시간(scaling lag)** — Pod priority와 over-provisioning(placeholder Pod)으로 스케줄링 지연을 제거하는 것이 표준 해법입니다.
2. **정상 AZ의 신규 capacity 확보가 다른 고객 수요로 제약될 수 있다는 위험** — 이건 가설이 아니라 AWS 문서가 "zonal impairment 시 healthy AZ에 신규 노드가 추가되지 못하는 compute capacity constraint 위험"을 실제로 명시하고 있는 사항입니다.
3. **상호 의존하는 Pod의 AZ 공존(co-location)** — topology spread만으로는 부족하고 pod affinity를 병행해야 합니다. CUJ 서비스 그래프의 모든 hop이 모든 AZ에 존재하는지 확인해야 합니다.

### cross-AZ 비용 최적화

측정 → 최적화 → 잔여 비용 비교의 순서로 접근합니다.

1. Flow Logs와 ENI/AZ mapping으로 상위 비용 경로를 특정합니다(CUR만으로는 source/destination AZ pair를 확인할 수 없습니다).
2. same-zone routing, `trafficDistribution`(최신 Kubernetes 버전에서는 필드명·값이 `PreferSameZone`/`PreferSameNode`로 바뀌었으므로 **목표 EKS 버전을 먼저 고정한 뒤 그 버전의 필드명으로 기술**), topology spread, ALB IP target, NAT/endpoint의 zonal locality, data locality를 순서대로 적용합니다.
3. 적용 후 잔여 cross-AZ 비용을 비교합니다.

ALB target group의 cross-zone load balancing을 비활성화하면 비용을 줄일 수 있지만 제약이 큽니다 — sticky session 불가, Lambda target 불가, **target group의 특정 AZ에 healthy target이 하나도 없으면 그 AZ로 들어온 요청이 전부 503**이 됩니다. AZ별 capacity를 확실히 보장할 수 없다면 기본값(활성화 상태) 유지가 AWS 권고입니다.

### 업그레이드 전략은 A/B의 존재 이유와 직결된다

A/B EKS Runtime을 두는 실질적인 이유가 업그레이드 격리라면, 다음을 명문 규칙으로 정해야 합니다.

- A/B 클러스터 간 허용되는 버전 스큐 범위
- 항상 한쪽을 먼저 업그레이드하는 순서 규칙
- Extended support 사용 여부

이게 없으면 A/B는 단순히 "클러스터 2개"에 그치고 이중화의 의미가 없어집니다.

### Worker AZ 수와 control plane subnet은 별개 개념

클러스터를 생성하려면 서로 다른 두 AZ의 subnet이 필요하지만, worker node는 1개 AZ에만 배치할 수도 있습니다. "1-AZ 워커 구성"이 EKS 자체에서 금지되지는 않는다는 뜻이며, 앞서 언급한 zonal shift 예외 규칙과는 별개로 판단해야 합니다.

## 3. Full Workload Cell — 더 강한 격리가 필요할 때의 대안

A/B EKS Runtime보다 더 강한 격리가 필요하다면, ingress·compute·data와 필수 dependency를 "Cell" 단위로 함께 분할·복제해서 장애 영향을 Cell 안에 제한하는 방식이 있습니다. Partition, consistency, 용량, 운영 비용이 크게 늘기 때문에 **독립적인 data partition·replication이 가능한 워크로드에만** 적용하는 것이 현실적입니다.

## 다음

EKS 가용성 설계는 그 위에 올라가는 VPC 구조와 분리해서 생각할 수 없습니다 → [Shared VPC와 Connectivity](./04-shared-vpc-and-connectivity.md)

## 참고 자료

- [EKS quotas](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [EKS subnet과 Multi-AZ](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
- [EKS network cost 최적화](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EKS zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)
- [EKS tenant isolation](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html)
- [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Well-Architected: Multi-AZ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html)
- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health.html)
