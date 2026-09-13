# EKS 멀티 계정·멀티 클러스터 아키텍처

> **마지막 업데이트**: 2026년 9월 13일

## 1. 클러스터 수용 방식

여러 팀·도메인의 워크로드를 EKS에 배치하는 방식은 크게 네 가지로 나뉩니다.

| 방식 | 구성 |
|---|---|
| 단일 Core EKS | 모든 워크로드를 하나의 클러스터에 배치 |
| Environment별 중앙 EKS | production/non-production마다 클러스터 하나 |
| Domain별 EKS | 도메인마다 전용 클러스터 |
| **Shared + Dedicated** | 일반 워크로드는 공용 클러스터, 강한 tenant·quota·SLO 요구가 있는 워크로드만 전용 클러스터로 분리 |

Shared + Dedicated는 검토할 시작점입니다. 아래 임계값은 조직별 운영 예시이며 AWS의 자동 분리 기준이 아닙니다. 기본 quota와 승인된 실제 quota를 구분하고 SLO·성장률·운영 역량을 함께 평가합니다.

| 신호 | 측정 방법 | 분리 threshold |
|---|---|---|
| Managed node group 수 | EKS API | 25 / 30 |
| Access entry 수 | EKS API | 2,000 / 3,000 |
| Control plane API throttling | CloudWatch, 429 로그 | 지속적 429 발생 |
| etcd 크기·객체 수 | 해당 EKS 버전이 제공하는 control-plane metric과 객체 inventory | 제공 metric·권고 한도 확인 후 경고값 결정 |
| NAU (Network Address Usage) per VPC | VPC 콘솔·CloudWatch | 50,000 / 64,000 (또는 200,000 / 256,000) |
| Upgrade blast radius | 클러스터에 배포된 CUJ 수 | CUJ 2개 이상이면 분리 검토 |
| Add-on 변경 주기 충돌 | 팀별 add-on 버전 요구 차이 | 상충 요구 발생 시 분리 |

임계값 도달은 검토를 시작하는 신호입니다. quota 조정·불필요한 리소스 정리·분할 비용을 비교하고, 클러스터 분리는 검증된 계획과 rollback 절차로 진행합니다.

## 2. A/B EKS Runtime: 두 클러스터로 장애 경계 나누기

같은 CUJ(critical user journey)를 두 개의 독립된 EKS 클러스터에 배포해서, 한쪽 클러스터에 장애가 생겨도 다른 쪽이 트래픽을 받는 구조를 흔히 "A/B EKS Runtime"이라고 부릅니다. 이건 **AWS의 공식 권장 패턴이 아니라 조직이 직접 검증해야 하는 작업 가설**입니다. 실제로 가용성을 높이려면 아래 조건들을 먼저 충족해야 합니다.

### 무엇으로부터 보호하는가를 먼저 정의한다

EKS managed control plane은 Multi-AZ이며 ARC zonal shift/autoshift는 data plane에 작용합니다. A/B 구성은 아래와 같은 클러스터별 장애를 격리할 수 있습니다. 같은 VPC·DNS·계정·Region·데이터 계층을 공유하면 해당 공통 장애는 남으므로 AZ 또는 Region 장애 보호를 자동으로 보장하지 않습니다.

- 클러스터 업그레이드 실패
- Add-on(CNI/CoreDNS/CSI) 회귀
- Admission webhook 오류
- 잘못 배포된 cluster-wide policy
- Control plane API throttling

이 장애 목록을 명문화하고, "A/B로 나눈 뒤 이 목록의 장애가 실제로 한쪽으로 격리되는가"를 POC의 성공 기준으로 삼아야 합니다. "가용성이 향상됐다"는 추상적 표현으로는 검증할 수 없습니다.

<span id="coredns가-가장-흔한-단일-실패-지점"></span>

### DNS의 공통 장애와 용량 확인

DNS는 공통 의존성이므로 replica·AZ 분산·용량을 확인합니다. 장애 빈도 자료 없이 CoreDNS를 “가장 흔한” 단일 장애 지점으로 단정하지 않습니다. Auto Mode 및 혼합 노드는 실제 사용 중인 DNS 경로를 먼저 확인합니다.

- `replicaCount`와 `topologySpreadConstraints`가 AZ에 실제로 분산되어 있는가
- CoreDNS add-on의 autoscaling(`{"autoScaling":{"enabled":true}}`) 또는 HPA / cluster-proportional-autoscaler 적용 여부
- 한 AZ를 제거했을 때 QPS·지연 변화

**EC2 link-local 서비스에는 초당 1,024 packet 한도가 있으며 DNS·IMDS·NTP 등의 트래픽이 합산됩니다.** VPC DNS 문서의 ENI 한도와 실제 ENA `linklocal_allowance_exceeded`를 함께 확인하세요. 캐시와 DNS replica 배치를 검토하되, 고밀도 노드라는 이유만으로 DNS 장애 원인을 확정하지 않습니다.

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
- Stateful 워크로드는 storage별로 검토합니다. EBS PV는 AZ에 종속되어 다른 AZ에 직접 attach할 수 없습니다. 모든 PVC가 EBS인 것은 아니며 EFS 등 다른 저장소는 가용성·복구 특성이 다릅니다.

> **설계 제안**: autoshift 전에 각 서비스와 DNS·스토리지의 N-1 동작을 검증하세요. single-AZ endpoint는 fail-safe로 남을 수 있으므로 practice run이 항상 중단시킨다고 단정하지 않습니다. 이 동작은 장애 AZ가 정상 서비스를 제공한다는 보장도 아닙니다.

### 사전 capacity 배수 계산의 함정

"2-AZ면 약 2배, 3-AZ(N-1 기준)면 약 1.5배의 사전 capacity가 필요하다"는 계산은 산술적으로는 맞지만, 세 가지를 놓치기 쉽습니다.

1. **노드 추가 지연** — placeholder Pod와 우선순위로 이미 확보된 capacity를 활용할 수 있지만 node provisioning·이미지 pull·애플리케이션 startup 지연까지 제거하지는 않습니다.
2. **정상 AZ의 신규 capacity 확보가 다른 고객 수요로 제약될 수 있다는 위험** — 이건 가설이 아니라 AWS 문서가 "zonal impairment 시 healthy AZ에 신규 노드가 추가되지 못하는 compute capacity constraint 위험"을 실제로 명시하고 있는 사항입니다.
3. **서비스 의존성과 AZ 배치** — surviving AZ에서 CUJ의 모든 필수 hop에 도달하고 부하를 처리할 수 있어야 합니다. topology spread·affinity·cross-zone fallback을 요구에 맞게 조합합니다. strict affinity가 오히려 복구를 막지 않는지도 시험합니다.

### cross-AZ 비용 최적화

측정 → 최적화 → 잔여 비용 비교의 순서로 접근합니다.

1. Flow Logs와 ENI/AZ mapping으로 상위 비용 경로를 특정합니다(CUR만으로는 source/destination AZ pair를 확인할 수 없습니다).
2. same-zone routing, Service의 `spec.trafficDistribution`, topology spread, ALB IP target, NAT/endpoint locality와 data locality를 검토합니다. `trafficDistribution` 필드 자체가 이름을 바꾼 것은 아닙니다. `PreferClose`, `PreferSameZone`, `PreferSameNode`의 지원 여부와 feature gate는 목표 Kubernetes/EKS 버전에서 확인합니다.
3. 적용 후 잔여 cross-AZ 비용을 비교합니다.

ALB 자체의 cross-zone regional data transfer에는 추가 전송 요금이 없으므로 이를 끄면 무조건 비용이 줄어든다고 계산하지 않습니다. target group 수준에서 끄면 target stickiness·Lambda target이 지원되지 않습니다. target이 없는 AZ의 요청은 503이 될 수 있고, target이 있으나 unhealthy인 경우에는 DNS·routing failover 조건이 적용됩니다. 이 둘을 구분하고 AZ별 capacity를 보장할 수 없다면 기본 활성화 설정을 유지합니다.

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
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB cross-zone data transfer](https://aws.amazon.com/elasticloadbalancing/faqs/)
- [Amazon DNS quotas](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Kubernetes Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)
