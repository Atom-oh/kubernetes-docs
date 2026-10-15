# Part 10: IPAM 심화 퀴즈

> **Cilium 1.20.2 (안정, 2026-09-16) · 2026-10-15**. [1.21 pre-release] 표시 항목은 v1.21.0-pre.3 기준입니다.

1. **CNI ADD 중 `POST /ipam`으로 Pod IP를 할당한 직후 endpoint 생성 전에 CNI 플러그인이 죽었습니다. agent 재시작 없이 이 IP는 언제 해제되나요?**
   - A) 할당 시 설정된 10분 expiration 타이머가 만료되었을 때
   - B) agent가 재시작되어 endpoint를 복원할 때만
   - C) REST 연결이 닫히는 즉시
   - D) 180초 뒤(`--excess-ip-release-delay` 기본값)

   <details>
   <summary>정답 보기</summary>

   **정답: A) 할당 시 설정된 10분 expiration 타이머가 만료되었을 때**

   **설명:**
   CNI 플러그인은 expiration 플래그를 켜고 할당을 요청하므로 agent가 10분 타이머(`defaults.IPAMExpiration`)를 시작합니다. endpoint 생성이 타이머를 멈추고, 생성되지 않으면 타이머가 IP를 해제합니다. 180초는 operator의 ENI 초과 IP 해제 지연 값입니다.

   </details>

2. **cluster-pool의 1.20.2 Helm 기본값(`10.0.0.0/8`, IPv4 mask size 24)에서 이 CIDR로 PodCIDR을 받을 수 있는 노드 수와 노드 블록당 주소 수는?**
   - A) 노드 16,384개, 각 1,024주소
   - B) 노드 256개, 각 65,536주소
   - C) 노드 65,536개, 각 256주소
   - D) 노드 65,536개, mask 정의상 사용 가능 254주소

   <details>
   <summary>정답 보기</summary>

   **정답: C) 노드 65,536개, 각 256주소**

   **설명:**
   pool CIDR당 노드 수는 `2^(노드 mask - pool mask) = 2^(24 - 8) = 65,536`이고 블록당 주소는 `2^(32 - 24) = 256`입니다. 블록에서 network/broadcast 주소와 router, health, ingress 주소가 빠지므로 실제 사용 가능한 Pod IP는 더 적습니다.

   </details>

3. **1.20.2 allocator에서 IPv6 cluster-pool의 pool prefix 길이와 노드 mask 사이 차이를 제한하는 것은?**
   - A) 풀 크기와 관계없이 각 노드가 /64를 받도록 차이가 최소 64비트여야 한다
   - B) allocator가 압축하지 않은 bitmap을 쓰므로 차이가 16비트를 넘으면 안 된다(`clusterSubnetMaxDiff`)
   - C) 제한이 없고, bitmap이 압축되어 있어 노드 mask가 /128을 넘지 않기만 하면 된다
   - D) IPv4 기본값에 맞춰 차이는 정확히 8비트여야 한다

   <details>
   <summary>정답 보기</summary>

   **정답: B) allocator가 압축하지 않은 bitmap을 쓰므로 차이가 16비트를 넘으면 안 된다(`clusterSubnetMaxDiff`)**

   **설명:**
   `pkg/ipam/cidrset`은 pool prefix보다 16비트를 넘게 긴 IPv6 노드 mask를 거부합니다(`ErrCIDRSetSubNetTooBig`). IPv4는 노드 mask가 32 이하이기만 하면 됩니다. Helm 기본값 `fd00::/104`와 `/120`은 정확히 16비트 한계에 있습니다.

   </details>

4. **multi-pool IPAM에서 새 Pod의 pool을 고르는 순서는?**
   - A) CiliumPodIPPool selector, Pod 어노테이션, namespace 어노테이션, 그다음 `default` pool(`require-pool-match`가 없을 때)
   - B) 항상 `default` pool이며 어노테이션과 selector는 masquerade와 LB IPAM에만 영향
   - C) namespace 어노테이션, Pod 어노테이션, `default` 순이며 CiliumPodIPPool selector는 LB IPAM에만 쓰임
   - D) Pod 어노테이션(`ipv4-pool`/`ipv6-pool`이 `ip-pool`보다 먼저), namespace 어노테이션, CiliumPodIPPool selector, 그다음 `default`(`require-pool-match`가 없을 때)

   <details>
   <summary>정답 보기</summary>

   **정답: D) Pod 어노테이션(`ipv4-pool`/`ipv6-pool`이 `ip-pool`보다 먼저), namespace 어노테이션, CiliumPodIPPool selector, 그다음 `default`(`require-pool-match`가 없을 때)**

   **설명:**
   Pod 어노테이션이 namespace 어노테이션보다, namespace 어노테이션이 `podSelector`/`namespaceSelector` 일치보다 우선합니다. 일치가 없으면 `ipam-default-ip-pool`(기본 `default`)의 pool을 쓰되 Pod나 namespace에 `ipam.cilium.io/require-pool-match: "true"`가 있으면 할당이 막힙니다. 선택은 Pod 생성 시 한 번만 일어납니다.

   </details>

5. **Pod에 pool 어노테이션이 없고 같은 주소 family에서 서로 다른 두 CiliumPodIPPool의 selector에 일치합니다. 어떻게 되나요?**
   - A) family당 정확히 하나의 pool만 일치해야 하므로 오류와 이벤트와 함께 할당이 실패한다
   - B) 이름이 알파벳 순으로 앞서는 pool이 쓰이고 이벤트가 기록된다
   - C) Pod가 일치하는 두 pool에서 주소를 하나씩 받고 둘 다 라우팅된다
   - D) `default` pool이 tie-breaker로 쓰이고 selector는 무시된다

   <details>
   <summary>정답 보기</summary>

   **정답: A) family당 정확히 하나의 pool만 일치해야 하므로 오류와 이벤트와 함께 할당이 실패한다**

   **설명:**
   selector 기반 선택은 family당 일치하는 pool이 정확히 하나여야 합니다. 여러 개가 일치하면 오류(`multiple CiliumPodIPPools match pod ...`)가 나고 Pod는 `ContainerCreating`에 머뭅니다. selector를 좁히거나 Pod/namespace에 명시적으로 어노테이션을 달아 해결합니다.

   </details>

6. **Cilium 1.20.2의 ENI prefix delegation에 대해 올바른 설명은?**
   - A) 모든 EC2 인스턴스 타입에서 동작하며 /24 prefix를 할당하고, 서브넷이 가득 차면 /28로 되돌아간다
   - B) 모든 인스턴스 타입에서 동작하며 한 노드에서 /32와 /28 할당을 서브넷 상황에 따라 Pod마다 자유롭게 섞는다
   - C) `ipam.mode=multi-pool`과, 위임할 prefix를 CIDR로 나열한 `CiliumPodIPPool`이 필요하다
   - D) Nitro 또는 bare-metal에서만 /28 prefix를 할당하고, 보조 /32 IP가 이미 있는 노드에서는 건너뛰며, 서브넷에 prefix가 부족하면 /32로 되돌아간다

   <details>
   <summary>정답 보기</summary>

   **정답: D) Nitro 또는 bare-metal에서만 /28 prefix를 할당하고, 보조 /32 IP가 이미 있는 노드에서는 건너뛰며, 서브넷에 prefix가 부족하면 /32로 되돌아간다**

   **설명:**
   operator는 Nitro hypervisor 또는 bare metal 여부를 확인하고, 이미 보조 IP가 있는 노드에서는 prefix 모드를 쓰지 않으며(혼합 불가), `InsufficientPrefixesInSubnet`이면 해당 노드의 prefix 할당을 멈추고 `AssignPrivateIpAddresses`를 씁니다. 단위는 /28(16주소, IPv6는 /80)입니다. ENI 모드에는 CiliumPodIPPool이 없습니다.

   </details>

7. **1.20 ENI allocator는 EC2 인터페이스 상태를 agent에 어떻게 전달하나요?**
   - A) 1.19처럼 operator가 개별 IP를 `spec.ipam.pool`에 쓰고 agent가 `status.ipam.used`에 사용량을 보고하며 ENI 상태 기록이나 CIDR 변환은 없다
   - B) agent가 자체 자격 증명으로 EC2 API를 직접 호출하고 operator는 ENI 가비지 컬렉션만 한다
   - C) operator가 ENI를 `status.eni.enis`에 기록하고, agent가 이를 /32와 /28 CIDR로 바꿔 `spec.ipam.pools.allocated`(pool `default`)에 쓰며 수요를 `spec.ipam.pools.requested`에 보고한다
   - D) 각 ENI가 operator가 만든 별도의 CiliumPodIPPool이 되고 `ip-pool` 어노테이션으로 선택된다

   <details>
   <summary>정답 보기</summary>

   **정답: C) operator가 ENI를 `status.eni.enis`에 기록하고, agent가 이를 /32와 /28 CIDR로 바꿔 `spec.ipam.pools.allocated`(pool `default`)에 쓰며 수요를 `spec.ipam.pools.requested`에 보고한다**

   **설명:**
   1.20은 ENI를 multi-pool allocator로 옮겼습니다. EC2를 호출하는 것은 operator뿐이고 agent는 ENI 인벤토리에서 할당 CIDR을 유도해 필요 용량을 되돌려 씁니다. `spec.ipam.pool` / `status.ipam.used` 모델은 1.19와 1.18의 CRD allocator입니다. ENI 모드에는 CiliumPodIPPool도 `ip-pool` 어노테이션도 없습니다.

   </details>

8. **[1.21 pre-release] 현재 Cilium operator에 `--aws-use-primary-address`를 직접 전달하고 있습니다. 1.21로 옮기기 전에 해야 할 일은?**
   - A) 없다. 플래그는 deprecated일 뿐 1.21에서도 operator 플래그로 계속 동작한다
   - B) 제거하고 `eni.nodeSpec.usePrimaryAddress=true`(agent 플래그 `--eni-use-primary-address`)를 설정한다
   - C) 기본 pool의 `CiliumPodIPPool`에서 `spec.ipv4.pool[]` 아래 `usePrimaryAddress`로 설정한다
   - D) 같은 이름 그대로 agent에 `--aws-use-primary-address`로 옮긴다

   <details>
   <summary>정답 보기</summary>

   **정답: B) 제거하고 `eni.nodeSpec.usePrimaryAddress=true`(agent 플래그 `--eni-use-primary-address`)를 설정한다**

   **설명:**
   operator 플래그는 1.21에서 제거되며 노드별 `CiliumNode.spec.eni.use-primary-address`가 단일 기준이 됩니다. 차트는 agent 쪽 값만 연결했으므로 Helm 사용자는 영향이 없습니다. 이는 pre-release(v1.21.0-pre.3) 변경입니다.

   </details>

9. **[1.21 pre-release] `cilium.io/v2` `CiliumPodIPPool`의 `spec.ipv4.pool[].reservedRanges`는 무엇에 쓰나요?**
   - A) 모든 노드 블록에서 주소를 제외해 LB IPAM pool이 고정 Service IP로 내줄 수 있게 하기 위해
   - B) 기존 노드 블록을 다시 만들지 않고도 실행 중인 pool의 `maskSize`를 변경 가능하게 하기 위해
   - C) 모든 노드 블록에서 router, health, ingress endpoint용 주소를 예약하기 위해
   - D) 옛 CIDR을 `cidrs`에 남겨 기존 노드 블록은 계속 동작하게 하고 그 범위에서는 새 블록을 만들지 않게 해 새 CIDR로 점진 이전하기 위해

   <details>
   <summary>정답 보기</summary>

   **정답: D) 옛 CIDR을 `cidrs`에 남겨 기존 노드 블록은 계속 동작하게 하고 그 범위에서는 새 블록을 만들지 않게 해 새 CIDR로 점진 이전하기 위해**

   **설명:**
   옛 CIDR 전체를 예약하면 Cilium이 기존 할당은 유지하고 새 PodCIDR 블록은 다른 CIDR에서만 할당합니다. 모든 노드 그룹이 이전한 뒤 옛 CIDR과 `pool` 항목을 제거합니다. 각 `pool[].cidr`은 `cidrs` 중 하나여야 하며 `maskSize`는 계속 변경 불가입니다.

   </details>

10. **두 `CiliumLoadBalancerIPPool`의 block이 겹칩니다. LB IPAM은 어떻게 동작하나요?**
   - A) 나중 pool을 Conflicting(`cilium.io/PoolConflict`)으로 표시하고 그 pool에서는 아무것도 할당하지 않는다
   - B) validating webhook으로 두 번째 pool을 admission 단계에서 거부하고 생성 요청을 실패시킨다
   - C) 하나의 pool로 합쳐 두 pool block의 합집합에서 할당한다
   - D) 겹치는 범위를 Service 수 기준으로 두 pool에 균등하게 나눈다

   <details>
   <summary>정답 보기</summary>

   **정답: A) 나중 pool을 Conflicting(`cilium.io/PoolConflict`)으로 표시하고 그 pool에서는 아무것도 할당하지 않는다**

   **설명:**
   LB IPAM은 겹치는 pool을 합치거나 거부하지 않습니다. 나중 pool이 Conflicting으로 표시되고(`Conflicting` 출력 열과 `lbipam_conflicting_pools` 메트릭(런타임 접두사 `cilium_` 또는 `cilium_operator_`는 미확인)에서 확인) 그 pool에서는 할당이 일어나지 않습니다. 실행 중인 pool을 수정하면 기존 Service IP가 재할당될 수 있으므로 pool을 추가하거나 `disabled: true`를 쓰는 편이 낫습니다.

   </details>
