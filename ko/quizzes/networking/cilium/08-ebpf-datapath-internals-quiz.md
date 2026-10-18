# Part 8: eBPF Datapath 내부 구조 퀴즈

> **Cilium 1.20.2 · 2026-10-15**

1. **Cilium 1.20에서 커널이 지원할 때 device별 프로그램에 쓰는 attach 방식은 무엇이며, 지원하지 않으면 어떻게 되나요?**
   - A) 항상 legacy `clsact` filter. tcx는 netkit에서만 사용
   - B) tcx `bpf_link`(커널 6.6 이상). 아니면 `clsact` + `cls_bpf` direct-action
   - C) 모든 veth에 XDP. 아니면 agent가 시작을 거부
   - D) 모든 인터페이스에 cgroup hook. 아니면 iptables

   <details>
   <summary>정답 보기</summary>

   **정답: B) tcx `bpf_link`(커널 6.6 이상). 아니면 `clsact` + `cls_bpf` direct-action**

   `bpf.enableTCX`의 기본값은 true입니다. 링크는 `/sys/fs/bpf/cilium/...`에 pin되고 reload 시 원자적으로 갱신됩니다. tc-bpf와 tcx 둘 다 안 될 때만 agent가 실패합니다.

   </details>

2. **같은 노드의 pod-to-pod 트래픽이 BPF host routing과 `bpf_redirect_peer`를 쓸 때, 목적지 pod의 ingress policy는 어디서 적용되나요?**
   - A) 송신자의 `bpf_lxc` 프로그램이 `cilium_call_policy[목적지 endpoint ID]`로 tail call
   - B) 목적지 veth의 tc egress hook에서 송신자 endpoint에 pin된 policy map으로 검사
   - C) agent가 endpoint마다 목적지 netns에 설치한 iptables chain
   - D) 패킷이 어떤 veth에 닿기 전에 실행되는 노드 NIC의 XDP 프로그램

   <details>
   <summary>정답 보기</summary>

   **정답: A) 송신자의 `bpf_lxc` 프로그램이 `cilium_call_policy[목적지 endpoint ID]`로 tail call**

   `redirect_peer`는 목적지의 tc egress hook을 건너뛰므로, 목적지의 `cil_lxc_policy`를 전역 prog array에 두고 송신자가 호출합니다. slot이 비어 있으면 `DROP_EP_NOT_READY`가 발생합니다.

   </details>

3. **endpoint별 policy map `cilium_policy_v3_<id>`의 유형과 key 구조는 무엇인가요?**
   - A) 상대 pod IP와 목적지 포트를 key로 하는 HASH
   - B) 포트 번호를 index로 하고 protocol마다 slot이 하나인 ARRAY
   - C) policy rule 번호를 index로 해 rule마다 프로그램을 tail call하는 PROG_ARRAY
   - D) identity, 방향, protocol, 포트 prefix를 key로 하는 LPM_TRIE

   <details>
   <summary>정답 보기</summary>

   **정답: D) identity, 방향, protocol, 포트 prefix를 key로 하는 LPM_TRIE**

   key는 `sec_label`, `egress` 비트, `protocol`, `dport`입니다. 포트 prefix 덕분에 포트 범위를 소수의 entry로 저장할 수 있고, `sec_label` 0은 L3 와일드카드로 동작합니다.

   </details>

4. **어떤 튜토리얼이 Cilium 1.20에서 overlay 목적지의 원격 노드를 찾으려면 `cilium_tunnel_map`을 보라고 합니다. 올바른 설명은 무엇인가요?**
   - A) `cilium-dbg bpf tunnel list`로 노드와 endpoint 대응표를 덤프한다
   - B) map은 있지만 IPsec이나 WireGuard 암호화를 켰을 때만 채워진다
   - C) map은 더 이상 없고, tunnel endpoint는 `cilium_ipcache_v2` value의 필드다
   - D) map이 endpoint별 `cilium_tunnel_map_<id>`로 바뀌어 노드마다 항목 하나씩 둔다

   <details>
   <summary>정답 보기</summary>

   **정답: C) map은 더 이상 없고, tunnel endpoint는 `cilium_ipcache_v2` value의 필드다**

   1.20의 BPF 코드는 `cilium_tunnel_map`을 참조하지 않습니다. `cilium_ipcache_v2`(LPM_TRIE)가 `sec_identity`와 `tunnel_endpoint`(`flag_has_tunnel_ep` 포함)를 반환합니다. `cilium-dbg bpf ipcache list`를 사용하세요.

   </details>

5. **1.20.2에서 `--bpf-map-dynamic-size-ratio`의 기본값과 이 플래그가 크기를 조정하는 map은 무엇인가요?**
   - A) RAM의 0.0025. CT, NAT, NodePort neighbor, socket reverse-NAT map
   - B) 0(비활성). policy map만, `--bpf-policy-map-max`로 크기 결정
   - C) RAM의 0.25. LB map과 ipcache를 포함한 모든 BPF map
   - D) RAM의 0.0025. ipcache와 policy map만

   <details>
   <summary>정답 보기</summary>

   **정답: A) RAM의 0.0025. CT, NAT, NodePort neighbor, socket reverse-NAT map**

   동적 크기 조정은 기본으로 켜져 있습니다. `--bpf-ct-global-tcp-max` 같은 크기 플래그를 지정하면 그 map의 동적 조정만 꺼집니다. LB map은 `--bpf-lb-map-max`를 따릅니다.

   </details>

6. **`--bpf-lb-map-max`(기본 65536)는 무엇을 제어하나요?**
   - A) `cilium_lb4_services_v2` map만 제어하고 backend와 rev-NAT map은 각자 기본 크기를 씀
   - B) Service당 backend 수이며, 초과한 endpoint는 Service 생성 시점에 거부됨
   - C) Maglev lookup table 크기이며, 정해진 목록의 소수여야 함
   - D) LB map별 플래그 6개(services, backends, rev-NAT, affinity, source-range, Maglev)의 fallback 크기

   <details>
   <summary>정답 보기</summary>

   **정답: D) LB map별 플래그 6개(services, backends, rev-NAT, affinity, source-range, Maglev)의 fallback 크기**

   6개 플래그는 각각 기본 0이며 "`lb-map-max` 사용"을 뜻합니다. Maglev table 크기는 별도 플래그입니다. 크기를 바꾸면 map이 다시 만들어져 채워질 때까지 연결이 끊깁니다.

   </details>

7. **socket-LB가 켜져 있을 때 ClusterIP는 어디서 변환되고, 응답에서 애플리케이션은 어떻게 Service 주소를 계속 보나요?**
   - A) veth에서 모든 패킷을 DNAT하고, 응답 경로에서 `cilium_lb4_reverse_nat`와 conntrack으로 원래 주소를 복원
   - B) cgroup hook이 `connect()`/`sendmsg()`에서 변환하고, `recvmsg`/`getpeername` hook이 `cilium_lb4_reverse_sk`로 복원
   - C) host netns에서 kube-proxy iptables DNAT가 변환하고 conntrack이 원래 주소를 복원
   - D) 패킷이 stack에 들어가기 전에 NIC의 XDP가 변환하고 Hubble relay가 복원

   <details>
   <summary>정답 보기</summary>

   **정답: B) cgroup hook이 `connect()`/`sendmsg()`에서 변환하고, `recvmsg`/`getpeername` hook이 `cilium_lb4_reverse_sk`로 복원**

   wire에서는 DNAT이 없으므로 pod 안 `tcpdump`에는 backend IP가 보입니다. `cilium_lb4_reverse_nat`를 쓰는 per-packet 경로는 socket-LB가 적용되지 않는 경우(host-namespace-only, L7 LB, SCTP 등)에만 사용됩니다.

   </details>

8. **overlay 모드에서 `cilium_vxlan`에 패킷이 도착하면 `cil_from_overlay`는 출발지 identity를 어떻게 알아내나요?**
   - A) 송신자가 출발지 identity로 설정한 tunnel ID(VNI)를 `bpf_skb_get_tunnel_key`로 읽음
   - B) 바깥 출발지 IP를 `cilium_lxc`에서 조회하며, 이 map이 노드 IP를 identity로 대응시킴
   - C) 로컬 Envoy proxy가 요청에 삽입한 HTTP 헤더에서 identity를 읽음
   - D) endpoint 레이블 캐시를 이용해 출발지 pod 이름에서 identity를 파싱

   <details>
   <summary>정답 보기</summary>

   **정답: A) 송신자가 출발지 identity로 설정한 tunnel ID(VNI)를 `bpf_skb_get_tunnel_key`로 읽음**

   tunnel ID가 host identity이면 `DROP_INVALID_IDENTITY`로 거부됩니다. native routing에는 VNI가 없으므로 출발지 identity는 출발지 IP로 `cilium_ipcache_v2`에서 구합니다(IPsec/WireGuard는 mark 사용).

   </details>

9. **관리자가 CiliumNetworkPolicy를 수정하면 agent는 datapath에 무엇을 하나요?**
   - A) 영향받는 endpoint마다 clang으로 `bpf_lxc.c`를 다시 컴파일하고 veth의 프로그램을 reload
   - B) 모든 device의 pin된 tcx link를 교체해 새 policy가 한 번에 적용되게 함
   - C) `cilium_policy_v3_<id>` entry를 갱신하고, endpoint 또는 노드 config hash가 바뀔 때만 프로그램을 reload
   - D) 모든 endpoint가 프로그램을 재생성하도록 Cilium agent pod를 재시작

   <details>
   <summary>정답 보기</summary>

   **정답: C) `cilium_policy_v3_<id>` entry를 갱신하고, endpoint 또는 노드 config hash가 바뀔 때만 프로그램을 reload**

   policy 변경은 map 연산(`RegenerateWithoutDatapath`)입니다. template 오브젝트는 template 설정 hash별로 캐시되고, endpoint별 값은 `.rodata.config`에 있습니다.

   </details>

10. **1.20의 Hubble 이벤트 파이프라인에 대한 설명 중 맞는 것은 무엇인가요?**
    - A) BPF가 노드마다 ring buffer에 쓰고 Hubble Relay가 각 노드의 BPF 파일시스템에서 그 buffer를 직접 읽는다
    - B) 이벤트는 `cilium_events`(perf event array)에서 agent monitor와 Hubble 큐를 거쳐 메모리 ring(기본 4095 flow)에 저장된다
    - C) agent가 flow를 디스크에 저장하고 재시작 후 Hubble Relay에 재생한다
    - D) L7 이벤트는 proxy redirect map이 일치할 때 `bpf_lxc` tail 프로그램이 내보낸다

    <details>
    <summary>정답 보기</summary>

    **정답: B) 이벤트는 `cilium_events`(perf event array)에서 agent monitor와 Hubble 큐를 거쳐 메모리 ring(기본 4095 flow)에 저장된다**

    손실은 perf buffer(`perf_event_ring_buffer`)나 observer 큐(`observer_events_queue`)에서 발생할 수 있습니다. L7 레코드는 BPF가 아니라 Envoy와 DNS proxy가 agent 이벤트로 보냅니다.

    </details>
