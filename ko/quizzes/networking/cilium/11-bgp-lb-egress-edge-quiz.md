# Part 11: BGP Control Plane, Load Balancer IP, Egress 퀴즈

> **Cilium 1.20.2 · 2026-10-15**

1. **ENI IPAM을 쓰는 EKS 클러스터에서 `PodCIDR` 타입의 `CiliumBGPAdvertisement`는 어떤 효과가 있나요?**
   - A) 모든 ENI 보조 IP를 /32 경로로 피어에 광고한다
   - B) VPC 라우트 테이블에 경로를 프로그래밍한다
   - C) 각 노드에서 VPC CIDR를 광고한다
   - D) 의미 있는 효과가 없다. ENI IPAM은 노드에 Cilium이 소유한 PodCIDR를 주지 않으므로 광고할 노드별 prefix가 없다

   <details>
   <summary>정답 보기</summary>

   **정답: D) 의미 있는 효과가 없다. ENI IPAM은 노드에 Cilium이 소유한 PodCIDR를 주지 않으므로 광고할 노드별 prefix가 없다**

   `PodCIDR` 광고는 노드마다 PodCIDR을 할당하는 IPAM 모드(cluster-pool, Kubernetes host scope)에서만 동작합니다. ENI에서는 Pod IP가 VPC가 이미 라우팅하는 VPC 주소이며, BGP Control Plane은 클라우드 라우트 테이블을 프로그래밍하지 않습니다.

   </details>

2. **`CiliumBGPPeerConfig`는 피어에게 보낼 advertisement를 어떻게 고르나요?**
   - A) `families[].advertisements`의 label selector를 `CiliumBGPAdvertisement` 오브젝트의 `metadata.labels`와 매칭한다
   - B) 피어의 `families` 항목에서 `advertisementType`을 매칭한다
   - C) `peerConfigRef`에 advertisement 이름을 나열한다
   - D) 노드의 어노테이션으로 고른다

   <details>
   <summary>정답 보기</summary>

   **정답: A) `families[].advertisements`의 label selector를 `CiliumBGPAdvertisement` 오브젝트의 `metadata.labels`와 매칭한다**

   ClusterConfig는 이름으로 PeerConfig를 참조하지만, PeerConfig는 advertisement 오브젝트의 레이블로 advertisement를 연결합니다. 매칭되는 advertisement가 없으면 세션은 올라오지만 아무것도 광고되지 않습니다.

   </details>

3. **BGP로 광고되는 `LoadBalancer` Service가 `externalTrafficPolicy: Local`일 때, VIP는 어느 노드에서 광고되나요?**
   - A) 해당 Service의 lease를 가진 노드만
   - B) 클러스터 설정이 선택한 모든 노드
   - C) ready 상태의 로컬 백엔드가 1개 이상 있는 노드만. 경로가 Pod를 따라간다
   - D) control-plane 노드만

   <details>
   <summary>정답 보기</summary>

   **정답: C) ready 상태의 로컬 백엔드가 1개 이상 있는 노드만. 경로가 Pod를 따라간다**

   `Cluster`에서는 선택된 모든 노드가 VIP를 광고하고, `Local`에서는 ready 로컬 엔드포인트가 없는 노드에서 withdraw됩니다. Lease는 BGP가 아니라 L2 announcements의 개념입니다.

   </details>

4. **Cilium 1.19에서 1.20으로 업그레이드한 뒤 BGP 세션 Grafana 패널이 비었습니다. 가장 가능성 높은 원인은?**
   - A) BGP 메트릭이 operator로 옮겨졌다
   - B) 인스턴스 레이블 `vrouter`가 `instance_name`으로 바뀌었고 1.20 업그레이드 노트에는 언급이 없다
   - C) `bgpControlPlane.metrics.enabled`를 설정하지 않으면 BGP 메트릭이 꺼진다
   - D) 메트릭 접두사가 `cilium_`에서 `bgp_`로 바뀌었다

   <details>
   <summary>정답 보기</summary>

   **정답: B) 인스턴스 레이블 `vrouter`가 `instance_name`으로 바뀌었고 1.20 업그레이드 노트에는 언급이 없다**

   1.19.8 메트릭 문서는 `vrouter`, 1.20.2는 `instance_name`을 씁니다. 예전 레이블로 필터링하는 쿼리와 알림은 조용히 매칭이 끊깁니다.

   </details>

5. **(Cilium 1.18 이상) 서로 다른 community와 `localPreference`를 가진 `CiliumBGPAdvertisement` 두 개가 같은 Service에 매칭되면 무엇이 광고되나요?**
   - A) community의 합집합과 `localPreference`의 최댓값
   - B) 마지막으로 적용된 advertisement의 속성
   - C) 알파벳순으로 첫 advertisement만
   - D) 충돌로 경로가 withdraw된다

   <details>
   <summary>정답 보기</summary>

   **정답: A) community의 합집합과 `localPreference`의 최댓값**

   "마지막 매칭 우선"은 1.18 이전 동작입니다. 또한 `localPreference`는 iBGP 피어에만 전송됩니다.

   </details>

6. **v1 `CiliumBGPPeeringPolicy`와 그 컨트롤 플레인은 어느 릴리스에서 제거되었나요?**
   - A) 1.18
   - B) 1.20
   - C) 1.21
   - D) 1.19

   <details>
   <summary>정답 보기</summary>

   **정답: D) 1.19**

   1.18에서 deprecated되었고 1.19에서 `pkg/bgpv1`과 함께 제거되었으므로, 1.19로 올리기 전에 `cilium.io/v2` CRD로 마이그레이션해야 합니다. v2 CRD의 v2alpha1 사본은 1.20과 1.21-pre에서 deprecated 상태로 계속 제공됩니다.

   </details>

7. **Cilium 1.20에서 다중 홉 BGP 세션의 빠른 장애 감지는 어떻게 처리해야 하나요?**
   - A) `CiliumBGPPeerConfig.spec.bfd`에서 BFD를 켠다
   - B) BFD는 지원되지 않는다. hold/keepalive timer를 낮추고(CRD 최솟값 3, 1) agent 재시작에는 Graceful Restart를 쓴다
   - C) `ebgpMultihop`을 255로 설정하면 빠른 failover가 활성화된다
   - D) `connectRetryTimeSeconds: 1`을 쓴다

   <details>
   <summary>정답 보기</summary>

   **정답: B) BFD는 지원되지 않는다. hold/keepalive timer를 낮추고(CRD 최솟값 3, 1) agent 재시작에는 Graceful Restart를 쓴다**

   1.18~1.21-pre의 어떤 CRD에도 BFD 필드가 없습니다. 흔히 인용되는 9/3은 권장되는 공격적 설정이지 CRD 최솟값이 아닙니다. `ebgpMultihop`은 TTL만 정하고, connect-retry는 재접속에 영향을 줄 뿐 장애 감지와는 무관합니다.

   </details>

8. **`v1alpha2` `TLSRoute` 오브젝트가 있는 상태에서 Cilium 1.20(Gateway API v1.6.1)으로 업그레이드하려 합니다. 무엇을 해야 하나요?**
   - A) 할 일 없음. standard 채널 CRD가 오브젝트를 자동 변환한다
   - B) TLSRoute를 삭제하고 업그레이드 후 다시 만든다
   - C) TLSRoute를 백업하고, Cilium 업그레이드 전에 `v1alpha2`를 포함하는 experimental 채널 v1.6.1 TLSRoute CRD를 설치한다
   - D) 모든 버전을 유지하는 standard 채널 v1.6 TLSRoute CRD만 설치한다

   <details>
   <summary>정답 보기</summary>

   **정답: C) TLSRoute를 백업하고, Cilium 업그레이드 전에 `v1alpha2`를 포함하는 experimental 채널 v1.6.1 TLSRoute CRD를 설치한다**

   standard 채널 v1.6 TLSRoute CRD를 설치하면 저장된 `v1alpha2` 오브젝트를 읽을 수 없게 되어 사라진 것처럼 보입니다.

   </details>

9. **L2 announcement lease 기본값(duration 15s, renew deadline 5s, retry 2s)에서 failover 구간은 대략 어느 정도인가요?**
   - A) 2~4초
   - B) 정확히 15초
   - C) 30~60초
   - D) 10~20초

   <details>
   <summary>정답 보기</summary>

   **정답: D) 10~20초**

   failover는 `leaseDuration - leaseRenewDeadline`에서 `leaseDuration + leaseRenewDeadline` 사이에서 일어납니다. 3s/1s/200ms로 튜닝하면 2~4초가 되지만 API QPS가 늘어나므로 클라이언트 rate limit을 올려야 합니다.

   </details>

10. **`CiliumEgressGatewayPolicy`의 `egressGateway.nodeSelector`에 매칭되는 노드가 없으면, 선택된 Pod에서 목적지 CIDR로 가는 트래픽은 어떻게 되나요?**
    - A) 드롭된다
    - B) 임의의 노드를 통해 전송된다
    - C) 일반 노드 masquerade로 fallback한다
    - D) 게이트웨이가 나타날 때까지 큐에 쌓인다

    <details>
    <summary>정답 보기</summary>

    **정답: A) 드롭된다**

    1.20.2와 1.21.0-pre.3의 Egress Gateway에는 health 기반 failover나 fallback이 없습니다. 매칭되는 게이트웨이가 없으면 목적지 CIDR로 가는 트래픽은 드롭됩니다.

    </details>
