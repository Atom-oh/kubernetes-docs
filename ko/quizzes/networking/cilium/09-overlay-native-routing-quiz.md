# Part 9: Overlay와 Native Routing 심층 분석 퀴즈

> **Cilium 1.20.2 · 2026-10-15**

## Tunnel 동작 원리

1. **Cilium은 캡슐화된 패킷의 24비트 VNI에 무엇을 넣나요?**
   - A) 목적지 노드 ID
   - B) 송신 endpoint의 source security identity
   - C) Cilium cluster ID
   - D) 노드별 임의 값(수신 측이 `cilium_tunnel_map`으로 매핑)

   <details>
   <summary>정답 보기</summary>

   **정답: B) 송신 endpoint의 source security identity**

   VNI는 source identity를 담습니다(`world-ipv4`/`world-ipv6`은 `world`로, `host`는 `remote-node`로 바꿔 전송). 수신 측에도 ipcache가 있으므로 VNI는 최적화이며 유일한 진실의 원천이 아닙니다. `cilium_tunnel_map`은 1.18에서 datapath에서 빠졌고(agent는 남은 map을 unpin만 함) Go 패키지는 1.19에서 제거되었으며, tunnel endpoint는 ipcache value에 있습니다.

   </details>

2. **Cilium에서 identity 전송 방식에 관해 Geneve는 VXLAN과 어떻게 다른가요?**
   - A) Geneve는 TLV 옵션에, VXLAN은 VNI에 identity를 싣는다
   - B) Geneve는 identity를 싣지 않고 송신 측에서만 정책을 평가한다
   - C) Geneve는 outer UDP 출발지 포트에 identity를 싣는다
   - D) 다르지 않다. 둘 다 VNI에 identity가 있고 Geneve 옵션은 DSR 서비스 주소/포트에만 쓰인다

   <details>
   <summary>정답 보기</summary>

   **정답: D) 다르지 않다. 둘 다 VNI에 identity가 있고 Geneve 옵션은 DSR 서비스 주소/포트에만 쓰인다**

   Cilium이 삽입하는 유일한 Geneve 옵션(class `0x014B`, type `0x81`)은 DSR용입니다. Outer 출발지 포트 범위(`tunnelSourcePortRange`)는 엔트로피에만 영향을 주며 identity와 무관합니다.

   </details>

3. **Tunnel 모드에서 outer UDP/IP 헤더는 누가 만드나요?**
   - A) 패킷에 헤더를 직접 쓰는 `bpf_lxc` 프로그램
   - B) 사용자 공간의 cilium-agent
   - C) BPF가 tunnel key를 설정하고 redirect한 뒤, flow-based `cilium_vxlan`/`cilium_geneve` 장치 뒤의 커널 vxlan/geneve 드라이버
   - D) NIC 펌웨어

   <details>
   <summary>정답 보기</summary>

   **정답: C) BPF가 tunnel key를 설정하고 redirect한 뒤, flow-based `cilium_vxlan`/`cilium_geneve` 장치 뒤의 커널 vxlan/geneve 드라이버**

   BPF는 `bpf_skb_set_tunnel_key`를 호출하고 tunnel 장치 ifindex로 redirect하며, 캡슐화는 커널 드라이버가 합니다. 수신 측에서는 커널이 decap하고 `cil_from_overlay`가 tunnel key를 읽습니다.

   </details>

4. **Cilium 1.20.2에서 `routingMode: tunnel`과 `autoDirectNodeRoutes: true`를 함께 설정하면 어떻게 되나요?**
   - A) 패킷이 tunnel 장치를 거쳐야 하므로 agent가 fatal 오류로 종료한다
   - B) 서브넷 내부는 direct route, 서브넷 사이는 tunnel을 쓴다
   - C) 경고와 함께 flag가 무시된다
   - D) native routing으로 fallback한다

   <details>
   <summary>정답 보기</summary>

   **정답: A) 패킷이 tunnel 장치를 거쳐야 하므로 agent가 fatal 오류로 종료한다**

   `daemon_main.go`의 검사는 `TunnelingEnabled() && EnableAutoDirectRouting`입니다. 서브넷별 fallback은 없습니다. v1.21.0-pre.3의 메시지는 "requires native routing mode"로 바뀌지만 여전히 fatal입니다.

   </details>

## MTU, Masquerading, Host Routing

5. **1500바이트 underlay, IPv4 underlay에서 VXLAN과 WireGuard를 모두 켜면 Pod가 보는 route MTU는 얼마인가요?**
   - A) 1450
   - B) 1405
   - C) 1373
   - D) 1355

   <details>
   <summary>정답 보기</summary>

   **정답: D) 1355**

   Route MTU는 기준 MTU에서 (WireGuard 95 + tunnel 50)을 뺀 값입니다. 1450은 VXLAN만, 1405는 native + WireGuard, 1373은 VXLAN + IPsec(50 + 77)입니다.

   </details>

6. **`routingMode: tunnel`에서 DSR을 쓰려면 어떤 설정이 필요한가요?**
   - A) VXLAN과 `dsrDispatch: opt`
   - B) `tunnelProtocol: geneve`와 `loadBalancer.dsrDispatch: geneve`
   - C) VXLAN과 `loadBalancer.mode: hybrid`
   - D) 아무 tunnel 프로토콜과 `dsrDispatch: ipip`만

   <details>
   <summary>정답 보기</summary>

   **정답: B) `tunnelProtocol: geneve`와 `loadBalancer.dsrDispatch: geneve`**

   Agent는 VXLAN tunnel에서 `dsr`/`hybrid`를 거부하고, tunnel 모드 DSR에 Geneve dispatch를 요구하며, Geneve dispatch에는 Geneve tunnel 프로토콜을 요구합니다.

   </details>

7. **netkit을 지원하지 않는 커널의 노드에서 `bpf.datapathMode: auto`로 설정하면 어떻게 되나요?**
   - A) Agent가 기동하지 못한다
   - B) `netkit-l2`로 전환한다
   - C) 경고를 로그로 남기고 veth로 fallback한다. 명시적 `netkit`이었다면 hard fail이다
   - D) netkit을 계속 재시도하며 Pod 생성을 막는다

   <details>
   <summary>정답 보기</summary>

   **정답: C) 경고를 로그로 남기고 veth로 fallback한다. 명시적 `netkit`이었다면 hard fail이다**

   1.20에서 추가된 `auto`는 probe 후 "datapath autodiscovery failed, reverting from netkit to veth" 로그와 함께 veth로 전환합니다. netkit에는 BPF masquerade, KPR, legacy host routing 미사용도 필요합니다.

   </details>

8. **BPF host routing이 기본인데 KPR을 켠 채 iptables masquerade를 그대로 두면 agent는 어떻게 동작하나요?**
   - A) BPF host routing에 BPF masquerade가 필요하다는 로그를 남기고 조용히 legacy host routing으로 fallback한다
   - B) 기동을 거부한다
   - C) BPF masquerade를 자동으로 켠다
   - D) kube-proxy replacement를 끈다

   <details>
   <summary>정답 보기</summary>

   **정답: A) BPF host routing에 BPF masquerade가 필요하다는 로그를 남기고 조용히 legacy host routing으로 fallback한다**

   Host routing은 best effort입니다. 이를 필요로 하면서 명시적으로 요청한 기능(netkit, Pod용 BBR, BIG TCP)은 대신 hard fail합니다. `cilium-dbg status`의 `Routing:` 줄 `Host:` 필드(`Host: Legacy`)로 확인합니다.

   </details>

9. **Bandwidth manager가 켜진 상태에서 `kubernetes.io/egress-bandwidth: "10M"`은 Pod를 어느 값으로 제한하나요?**
   - A) 10 MB/s
   - B) replica set당 10 Mbit/s
   - C) BBR도 켜지 않으면 아무 제한 없음
   - D) 10 Mbit/s

   <details>
   <summary>정답 보기</summary>

   **정답: D) 10 Mbit/s**

   값은 비트 단위 Kubernetes quantity입니다. Egress는 Pod 단위로 EDT와 FQ로 집행되며 BBR은 선택입니다. IPsec에서는 manager가 조용히 비활성화됩니다.

   </details>

10. **BPF masquerade와 기본 설정에서 Pod에서 원격 노드로 가는 트래픽은 어떻게 처리되나요?**
    - A) 항상 masquerade
    - B) masquerade 안 함
    - C) native routing에서는 masquerade하지 않고, tunnel 모드에서는 masquerade(ipcache 항목에 `skip_tunnel`이 없을 때)
    - D) 목적지가 RFC1918 밖일 때만 masquerade

    <details>
    <summary>정답 보기</summary>

    **정답: C) native routing에서는 masquerade하지 않고, tunnel 모드에서는 masquerade(ipcache 항목에 `skip_tunnel`이 없을 때)**

    `bpf/lib/nat.h` 결정 순서의 5단계입니다. `enable-remote-node-masquerade=true`(1.19+, `extraConfig`로 설정)이면 두 모드 모두 masquerade합니다.

    </details>
