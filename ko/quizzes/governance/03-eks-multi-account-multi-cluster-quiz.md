# EKS 멀티 계정·멀티 클러스터 아키텍처 퀴즈

> 이 퀴즈는 [EKS 멀티 계정·멀티 클러스터 아키텍처](../../governance/03-eks-multi-account-multi-cluster.md) 문서의 학습 내용을 테스트합니다.

---

1. A/B EKS Runtime(두 클러스터로 장애 경계를 나누는 방식)이 실질적인 가용성 향상을 주는 주된 이유는?
   - A) EKS managed control plane이 Multi-AZ가 아니기 때문에 발생하는 AZ 장애를 방어하기 위해서
   - B) 클러스터 업그레이드 실패, add-on 회귀, 잘못된 cluster-wide policy처럼 조직이 직접 만드는 장애를 격리하기 위해서
   - C) AWS가 공식적으로 권장하는 표준 패턴이기 때문에
   - D) 비용을 절감하기 위해서

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 업그레이드 실패, add-on 회귀, 잘못된 cluster-wide policy처럼 조직이 직접 만드는 장애를 격리하기 위해서**

**설명:**
EKS managed control plane은 이미 Multi-AZ이고, ARC zonal shift/autoshift는 data plane에만 작용합니다. A/B EKS Runtime의 가치는 AZ 장애 대비가 아니라 조직이 직접 만들어내는 장애에 대한 방어이며, 이는 AWS의 공식 권장 패턴이 아니라 조직이 직접 검증해야 하는 작업 가설입니다.

</details>

---

2. ARC zonal shift의 fail-safe 동작에 대한 설명으로 옳은 것은?
   - A) 어떤 워크로드든 zonal shift가 발생하면 즉시 트래픽이 차단된다
   - B) 워크로드의 endpoint가 전부 장애 AZ에만 있으면, EKS는 그 AZ로 트래픽을 계속 보낸다
   - C) 모든 워크로드가 자동으로 다른 AZ로 재배치된다
   - D) EKS Fargate에서만 이 동작이 발생한다

<details>
<summary>정답 보기</summary>

**정답: B) 워크로드의 endpoint가 전부 장애 AZ에만 있으면, EKS는 그 AZ로 트래픽을 계속 보낸다**

**설명:**
이것이 fail-safe 동작입니다. 즉 1-AZ에만 배포된 워크로드는 zonal shift로 보호받지 못합니다. 이 때문에 "ARC zonal autoshift 대상 클러스터에는 1-AZ 워크로드를 두지 않는다"를 명문 규칙으로 두는 것이 권장됩니다.

</details>

---

3. EC2 인스턴스의 ENI 하나가 Route 53 Resolver로 보낼 수 있는 패킷 수 제약과 관련해 옳은 것은?
   - A) 초당 1,024개(조정 불가)이며, Pod 밀도가 높은 노드에서 CoreDNS 실패의 원인이 될 수 있다
   - B) 제한이 없으며 얼마든지 늘릴 수 있다
   - C) AZ당 100 Gbps로 제한된다
   - D) NAU(Network Address Usage) 계산에 포함되지 않는다

<details>
<summary>정답 보기</summary>

**정답: A) 초당 1,024개(조정 불가)이며, Pod 밀도가 높은 노드에서 CoreDNS 실패의 원인이 될 수 있다**

**설명:**
이 한도는 조정 불가능하며, CoreDNS는 A/B 구조와 AZ 이중화 모두에서 가장 흔한 단일 실패 지점입니다. 고밀도 Pod 노드에서는 이 패킷 한도가 DNS 실패의 실제 원인이 될 수 있어 NodeLocal DNS 도입을 검토해야 합니다.

</details>

---

4. ALB target group의 cross-zone load balancing을 비활성화할 때의 위험은?
   - A) 비용이 오히려 증가한다
   - B) sticky session과 Lambda target을 쓸 수 없고, 특정 AZ에 healthy target이 하나도 없으면 그 AZ로 들어온 요청이 전부 503이 된다
   - C) EKS 클러스터가 자동으로 재시작된다
   - D) NAT Gateway quota가 초과된다

<details>
<summary>정답 보기</summary>

**정답: B) sticky session과 Lambda target을 쓸 수 없고, 특정 AZ에 healthy target이 하나도 없으면 그 AZ로 들어온 요청이 전부 503이 된다**

**설명:**
cross-zone load balancing 비활성화는 cross-AZ 비용을 줄이는 수단이지만 제약이 큽니다. AZ별 capacity를 확실히 보장할 수 없다면 기본값(활성화 상태)을 유지하는 것이 AWS 권고입니다.

</details>
