# Part 8: eBPF Datapath 내부 구조

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

이 장은 Cilium datapath를 안쪽에서 살펴봅니다. 어떤 BPF 프로그램이 어디에 attach되는지, 프로그램끼리 어떻게 호출하는지, 어떤 map을 읽는지, agent가 어떻게 컴파일하고 로드하는지, 패킷 하나가 hop마다 어떻게 처리되는지를 다룹니다. 일반 eBPF 입문(역사, verifier, map 유형)은 [Part 2: eBPF](02-ebpf.md)에 남아 있습니다. 오버레이/라우팅은 [Part 9](09-overlay-native-routing.md), IPAM은 [Part 10](10-ipam-deep-dive.md)을 참고하세요.

> **오래된 블로그 주의: `cilium_tunnel_map`은 더 이상 존재하지 않습니다.** 예전 글이나 일부 upstream 예제 출력에는 Pod CIDR을 원격 노드 IP로 매핑하는 `cilium_tunnel_map`이 나옵니다. Cilium 1.17까지는 BPF(`bpf/lib/encap.h`)에 이 map이 있었고 `cilium-dbg bpf tunnel list`로 덤프할 수 있었습니다. 1.18에서 datapath에서 빠졌고(1.18.14 BPF 트리에는 참조가 없으며 agent는 남아 있는 map을 unpin만 합니다), Go 패키지는 1.19에서 제거되었습니다. Cilium 1.20.2에서는 어떤 BPF 프로그램도 이 map을 참조하지 않습니다. 원격 노드(tunnel endpoint)는 `cilium_ipcache_v2`의 **value**(`tunnel_endpoint` 필드와 `flag_has_tunnel_ep` 플래그)에 들어 있습니다. 1.18과 1.20에는 `cilium-dbg bpf tunnel list` 명령도 없습니다. 오버레이 라우팅을 디버깅하라며 tunnel map을 `bpftool map dump`하라는 글을 만나면 대신 ipcache(`cilium-dbg bpf ipcache list`)를 보세요. upstream 개발 문서 하나는 예제 출력에 이 map을 아직 싣고 있지만, 살아 있는 map이라는 뜻은 아닙니다.

## 학습 목표

- Cilium BPF 오브젝트별 entry 프로그램과 attach 지점(device 또는 cgroup)을 설명합니다.
- tail call을 쓰는 이유와, 목적지 endpoint의 policy가 송신 측 프로그램에서 실행되는 방식을 설명합니다.
- policy, ipcache, conntrack, service map의 key/value 구조를 읽고 올바른 플래그로 크기를 조정합니다.
- agent 측 흐름(ELF template cache, `.rodata.config` 상수, map pinning, attach, commit)을 설명합니다.
- Pod -> ClusterIP -> Pod 연결을 추적하며 hop별 map lookup을 나열합니다.
- `cilium-dbg bpf ...`와 `bpftool`로 실제 노드를 점검합니다.

## 1. 프로그램 구성과 attach 지점

Cilium은 `bpf/` 아래의 소수 C 소스를 컴파일합니다. 소스마다 ELF 오브젝트 하나가 나오고, 각 오브젝트에는 **entry 프로그램**(ELF section `tc/entry`, `xdp/entry`, `cgroup/...`)과 여러 **tail 프로그램**(section `tc/tail`)이 있습니다. `bpftool prog show`의 프로그램 이름에는 `cil_` 접두사가 붙습니다.

### 1.1 1.20.2의 entry 프로그램

| ELF 오브젝트 | Entry 프로그램 | Attach 위치 | 역할 |
|---|---|---|---|
| `bpf_lxc.o` | `cil_from_container` | 호스트 측 `lxc*` veth의 ingress(Pod에서 나가는 트래픽). netkit에서는 netkit peer의 primary hook | endpoint별 egress 경로: identity, CT, egress policy, 서비스 LB(per-packet 모드), 전달 |
| `bpf_lxc.o` | `cil_to_container` | 호스트 측 `lxc*`의 egress(스택을 거쳐 Pod로 향하는 트래픽). endpoint가 egress 프로그램을 필요로 할 때만 attach | endpoint routes, L7 proxy 복귀 등 스택 전달 트래픽의 ingress policy |
| `bpf_lxc.o` | `cil_lxc_policy`, `cil_lxc_policy_egress` | **device에 attach되지 않음**. 전역 prog array `cilium_call_policy` / `cilium_egresscall_policy`에 저장 | 목적지 ingress / 출발지 egress policy. 다른 프로그램이 호출 |
| `bpf_host.o` | `cil_from_netdev` | 모든 native/외부 device의 ingress | 호스트 행 및 포워딩 트래픽, NodePort, ipcache 기반 identity, host firewall |
| `bpf_host.o` | `cil_to_netdev` | native device의 egress(masquerade, NodePort, WireGuard, IPsec이 필요할 때만 attach) | BPF masquerade, NodePort SNAT, EDT/bandwidth, 암호화 mark |
| `bpf_host.o` | `cil_from_host` | `cilium_host`의 egress | 호스트 스택 -> Pod |
| `bpf_host.o` | `cil_to_host` | `cilium_host`, `cilium_net`의 ingress | Pod -> 호스트, host firewall |
| `bpf_host.o` | `cil_host_policy` | prog array slot (host endpoint policy) | host firewall policy |
| `bpf_overlay.o` | `cil_from_overlay`, `cil_to_overlay` | `cilium_vxlan` 또는 `cilium_geneve`의 ingress / egress | tunnel ID를 출발지 identity로 읽음 |
| `bpf_wireguard.o` | `cil_from_wireguard`, `cil_to_wireguard` | `cilium_wg0` ingress(항상) / egress(필요 시) | 복호화된 트래픽 mark |
| `bpf_xdp.o` | `cil_xdp_entry` | native device의 XDP | CIDR prefilter, NodePort/DSR 가속 |
| `bpf_sock.o` | `cil_sock4_connect`, `cil_sock4_sendmsg`, `cil_sock4_recvmsg`, `cil_sock4_getpeername`, `cil_sock4_pre_bind`, `cil_sock4_post_bind`, IPv6 대응 프로그램, `cil_sock_release` | cgroup root의 **cgroup v2** sock_addr / sock hook | 소켓 수준 로드밸런싱 |
| `bpf_sock_term.o` | `cil_sock_{tcp,udp}_destroy_v{4,6}` | `bpf_sock_destroy` kfunc을 호출하는 BPF iterator(`iter/tcp`, `iter/udp`) | 삭제된 backend에 연결된 소켓 종료. kfunc을 쓸 수 없으면 agent가 netlink `sock_diag`로 대체 |
| `bpf_probes.o`, `bpf_alignchecker.o` | 해당 없음 | 시작 시 `BPF_PROG_RUN`으로 1회 실행 | 커널 기능 probe, C/Go struct 레이아웃 검사 |

`bpf_network.c`(`cil_from_network`, native device ingress에서 IPsec 복호화)는 1.18.14, 1.19.8에 있고 **1.20에서 제거**되었습니다.

```
                       node A                                   node B
 pod C eth0 ----veth---- lxc_C           lxc_B ----veth---- pod B eth0
   |  cgroup/connect4          |             ^
   |  (bpf_sock.o)             | tcx ingress |  redirect_peer
   |                           v cil_from_container
   |                    +-------------------+   (tail call, map)
   |                    |   bpf_lxc.o       |-------+
   |                    +-------------------+       | encap / FIB redirect
   |                           |                     v
   |        cilium_host  <-----+          cilium_vxlan (cil_to_overlay)  ==underlay==>
   |        cil_from_host/cil_to_host        eth0 (cil_from_netdev / cil_to_netdev)
   |                                         eth0 XDP (cil_xdp_entry, 선택)
```

### 1.2 tcx, legacy tc, netkit

device별 프로그램은 loader(`pkg/datapath/loader/tc.go`)가 다음 순서로 attach 방식을 고릅니다.

1. **tcx**(Helm `bpf.enableTCX: true`, 기본값): `link.AttachTCX`로 tail anchor에 붙이는 `bpf_link`. 링크는 `/sys/fs/bpf/cilium/endpoints/<id>/links/`(endpoint) 또는 `/sys/fs/bpf/cilium/devices/<dev>/links/`(device) 아래에 **pin**됩니다. 프로그램 갱신은 링크를 원자적으로 업데이트하므로 reload 중 프로그램이 비는 구간이 없습니다. 커널 6.6 이상이 필요합니다. tcx attach가 성공하면 남은 legacy filter는 제거됩니다.
2. **Legacy tc**: 커널이 지원하지 않거나 `enableTCX: false`이면 `clsact` qdisc + `cls_bpf`(direct-action)를 쓰고, 남은 tcx 링크는 detach합니다.
3. 둘 다 안 될 때만 치명적 오류: tc-bpf 또는 tcx(Linux 6.6 이상) 지원이 필요하다고 보고합니다.

**netkit**(성숙도 **beta**): `bpf.datapathMode: veth | netkit | netkit-l2 | auto`. 기본값은 `veth`입니다. netkit에서는 Pod별 프로그램이 netkit **peer** device 안에 attach되고, 다른 device는 계속 tcx를 쓰며, netkit을 고르면 tcx가 자동으로 켜집니다. 소스가 강제하는 전제 조건(`canUseNetkit`): 커널 probe 통과(upstream 문서는 6.8 이상, 소스의 probe 오류 문구는 6.7), BPF host routing(`bpf.hostLegacyRouting` 사용 안 함), BPF masquerade, kube-proxy replacement, **`bpf.tproxy` 사용 안 함**(`bpf_sk_assign`은 tc ingress에서만 유효). `auto`는 1.20 신규로, probe 후 경고와 함께 veth로 fallback합니다. 이미 veth로 만든 Pod가 있으면 netkit/`auto`로의 전환은 거부되므로 새 노드 그룹으로 교체하세요.

| 방식 | 커널 | Pin 오브젝트 | Reload 동작 | Cilium 성숙도 |
|---|---|---|---|---|
| Legacy tc (`clsact` + `cls_bpf`) | 5.10 기준선 | device의 filter | filter replace | stable, fallback |
| tcx | 6.6+ | `/sys/fs/bpf/cilium/...`의 `bpf_link` | 링크 원자 갱신 | stable, 가능하면 기본 |
| netkit | 6.8+ (문서) | peer의 netkit link | 링크 원자 갱신 | beta |

### 1.3 XDP와 cgroup hook

- **XDP**(`cil_xdp_entry`)는 `loadBalancer.acceleration`이 `native` 또는 `best-effort`일 때 attach됩니다(기본 `disabled`). CIDR prefilter(`cilium_cidr_v4_fix`/`dyn` LPM map)와 NodePort/DSR fast path를 실행합니다. 드라이버가 `EINVAL`을 반환하면 loader가 attach 조합(attach type, `XDP_HAS_FRAGS`) 4가지를 재시도합니다.
- **cgroup hook**은 cgroup root(agent 플래그 `--cgroup-root`, 기본 `/run/cilium/cgroupv2`)에 한 번 `bpf_link`로 attach되며 `/sys/fs/bpf/cilium/socketlb/links/cgroup`에 pin됩니다. `socketLB.hostNamespaceOnly=true`가 아니면 모든 Pod netns에서 실행됩니다.

## 2. Tail call과 policy 프로그램 구조

### 2.1 tail call을 쓰는 이유

tail call은 반환 없이 실행 중인 프로그램을 다른 프로그램으로 교체합니다. Cilium이 쓰는 이유는 세 가지입니다. 프로그램 하나의 복잡도 한계(100만 instruction), 512바이트 stack, 큰 선택 기능을 공통 경로에서 분리하는 구조입니다. 체인 최대 길이는 tail call 33회입니다. bpf-to-bpf 호출과 tail call의 혼용은 커널 5.10부터 가능하며, 이것이 5.10 기준선의 이유 중 하나입니다.

tail call 사이의 상태는 `skb->cb[]`(`CB_SRC_LABEL` 같은 `CB_*` slot)와 per-CPU 임시 map `cilium_tail_call_buffer4/6`(예: CT tail 프로그램이 계산한 conntrack tuple과 결과)로 전달됩니다.

### 2.2 endpoint별 call array

endpoint마다 `cilium_calls_<endpoint-id 5자리>`(예: `cilium_calls_00312`)라는 전용 `PROG_ARRAY`가 있습니다. host endpoint는 `cilium_calls_hostns_<id>`, native device는 `cilium_calls_netdev_<ifindex>`를 씁니다. 다른 loader는 `cilium_calls_overlay_2`(overlay device, 예약 identity `world`=2로 이름 지음), `cilium_calls_wireguard_<ifindex>`, `cilium_calls_xdp_<ifindex>`를 씁니다. 크기는 `CILIUM_CALL_SIZE`이며, pin 플래그는 "로드할 때마다 pin을 교체하고 기존 array는 재사용하지 않음"을 뜻합니다.

| 버전 | `CILIUM_CALL_SIZE` |
|---|---|
| 1.18.14 | 48 |
| 1.19.8 | 49 |
| 1.20.2 | 50 |
| 1.21.0-pre.3 | 50 |

slot은 **정적**입니다. 호출 지점이 상수 slot 번호를 가진 inline assembly입니다. loader는 각 `tc/tail` 프로그램의 BTF decl-tag(`tail:cilium_calls/<idx>`)를 읽어 array를 채우고, 상수 적용 후 **도달 불가능한 tail 프로그램을 제거**합니다(5절). 1.20의 slot 그룹은 다음과 같습니다.

| Slot | 의미 |
|---|---|
| 1-2, 4-5 | drop/error 알림, ICMPv6 neighbor solicitation, time-exceeded |
| 6 | ARP |
| 3 | 미사용(backport 충돌을 피하려고 남긴 번호 공백) |
| 7, 10 | IPv4 / IPv6 from-LXC (netdev, overlay, WireGuard entry도 alias) |
| 8-9 | IPv4-to-IPv6, IPv6-to-IPv4 변환(`CILIUM_CALL_IPV46_RFC6052`, `CILIUM_CALL_IPV64_RFC6052`; NAT46/NAT64) |
| 11-14 | to-LXC policy only, to-endpoint |
| 15-25, 36-39 | NodePort NAT, rev-NAT, DSR, SNAT forward, from-host |
| 26-27 | from-LXC 후반부(egress 경로 후반, verifier 복잡도 분할) |
| 28-33 | CT ingress / CT ingress policy-only / CT egress (IPv4, IPv6) |
| 34-35, 40 | SRv6, inter-cluster rev-SNAT |
| 41-47 | host/netdev 이어받기, "no service" ICMP unreachable, multicast 전달 |
| 48-49 | policy 거부 ICMP 응답(1.20 신규, `policy_deny_response` 활성 시 사용) |

### 2.3 전역 policy 프로그램 array

policy는 endpoint별 call array에 들어 있지 않습니다. `cil_lxc_policy`와 `cil_lxc_policy_egress`는 endpoint ID를 index로 하고 `ENDPOINTS_MAP_SIZE` 크기를 가진 **전역** prog array 두 개에 삽입됩니다.

| Array | Index | 실행 내용 |
|---|---|---|
| `cilium_call_policy` | 목적지 endpoint ID | 목적지 **ingress** policy |
| `cilium_egresscall_policy` | 출발지 endpoint ID | 출발지 **egress** policy |

loader는 tc/tcx 프로그램을 attach하기 **전에** 이 slot을 씁니다(`PolicyMap.Update(ep id, PolicyProg)`). 로컬 목적지에 대한 L3 rewrite를 마친 송신자는 `tail_call_policy(ep->lxc_id)`를 호출합니다. BPF host routing에서는 `bpf_redirect_peer`로 패킷을 목적지 Pod의 netns로 바로 옮겨 **목적지의 tc egress hook을 건너뛰기** 때문입니다. 송신자가 목적지의 policy 프로그램을 호출해야 같은 노드 안에서도 ingress policy가 적용됩니다. slot이 비어 있으면(endpoint 종료 중) `DROP_EP_NOT_READY`로 드롭됩니다.

`cil_to_container`는 스택 전달 트래픽을 위해 여전히 존재하므로, 목적지 ingress policy는 송신자의 tail call 또는 이 egress hook 중 한 곳에서 실행됩니다.

## 3. Policy 적용 경로

### 3.1 Policy map

endpoint마다 `cilium_policy_v3_<id>`(1.20, 1.18/1.19는 `cilium_policy_v2_`)가 있습니다. 유형은 `LPM_TRIE`, 플래그는 `BPF_F_NO_PREALLOC | BPF_F_RDONLY_PROG_COND`, 크기는 `--bpf-policy-map-max`(endpoint당 기본 16384)입니다.

```
policy_key  { lpm prefixlen; u32 sec_label;   /* 상대 identity, 0 = 와일드카드 */
              u8 egress:1;  u8 protocol;      /* 0 = any */
              be16 dport; }                   /* prefix 매칭 => 포트 범위 */
policy_entry{ be16 proxy_port;                /* != 0 이면 L7 proxy로 redirect */
              deny:1; lpm_prefix_length:5; auth_type:7; has_explicit_auth_type:1;
              u32 precedence; u32 cookie; }
```

LPM prefix는 `sec_label`과 `egress`를 정확히, `protocol`을 전부-또는-없음으로, `dport`를 비트 prefix로 비교합니다. 그래서 포트 범위가 소수의 entry로 표현됩니다.

### 3.2 Lookup 알고리즘

상대 identity `R`, 프로토콜 `P`, 포트 `D`인 flow에 대해:

1. `sec_label = R`로 specific lookup. hit가 최대 precedence(deny)이면 중단.
2. aggregate lookup: identity의 aggregate(예: CIDR 그룹), 그다음 `sec_label = 0`(와일드카드 L3).
3. 더 높은 `precedence`(deny > proxy redirect > allow)를 고르고, 같으면 더 긴 LPM prefix를 고릅니다. hit가 없으면 `DROP_POLICY`.

매칭 유형(L3+L4, L3 only, L4 only, protocol only, all)은 이벤트에 보고됩니다. ICMP rule이 켜져 있으면 ICMP type이 `dport`에 실리고, "fragmentation needed"는 항상 허용됩니다.

### 3.3 Verdict와 부수 효과

- deny는 `DROP_POLICY_DENY`와 drop 이벤트입니다. `proxy_port != 0`인 allow는 proxy로 redirect합니다(3.5). `auth_type != 0`인 allow는 `cilium_auth_map`에 유효한 entry가 없으면 `DROP_POLICY_AUTH_REQUIRED`입니다.
- **egress는 출발지 endpoint가 적용**(`handle_ipv4_from_lxc`)하며 `CT_NEW`, `CT_ESTABLISHED`에만 적용됩니다. 응답(`CT_REPLY`, `CT_RELATED`)은 policy를 건너뜁니다. **ingress는 목적지가 적용**(자신의 policy 프로그램의 `ipv4_policy()`)하고 allow 후 ingress CT entry를 만듭니다.
- policy-verdict 이벤트는 deny와 새로 허용된 연결에서 발생합니다. hairpin(Pod가 자기 service IP로 접속)은 policy를 건너뜁니다.
- entry별 카운터는 선택적으로 `cilium_policystats`(`--bpf-policy-stats-map-max` 65536)에 기록됩니다.

### 3.4 policy 변경은 재컴파일을 일으키지 않음

policy 갱신은 `cilium_policy_v3_<id>`에 대한 map 연산입니다(`applyPolicyMapChangesLocked`). endpoint 또는 노드 설정 hash가 바뀔 때만 오브젝트를 다시 만들어 reload합니다. 따라서 `CiliumNetworkPolicy`를 고쳐도 clang이 실행되지 않습니다.

### 3.5 L7과 FQDN redirect

`proxy_port != 0`이면 `ctx_redirect_to_proxy4()`가 flow를 Envoy 또는 DNS proxy로 보냅니다. 구현은 두 가지입니다.

| 방식 | 동작 | 성숙도 |
|---|---|---|
| iptables TPROXY(기본) | datapath가 `mark = MARK_MAGIC_TO_PROXY \| proxy_port << 16`을 설정하고 OK를 반환. `CILIUM_PRE_mangle` 규칙의 `xt_socket`/`TPROXY`가 listener로 유도 | stable |
| `bpf.tproxy: true` | tc ingress에서 `bpf_sk_assign`으로 listener 소켓 지정 | beta, 기본 off, **netkit과 비호환**(1.19.8, 1.20, 1.21.0-pre.3에서 agent가 시작을 거부, 1.18.14 소스에서는 해당 검사를 찾지 못함) |

proxy 포트는 `--proxy-portrange-min/max`(10000-20000)에서 할당됩니다. CT entry에 `proxy_redirect`가 기록되어 응답이 proxy로 돌아갑니다. L7 이벤트는 BPF가 아니라 Envoy와 DNS proxy가 agent에 보고하는 access-log 레코드입니다.

mutual authentication(`auth_type`)은 **1.20에서 deprecated**(ztunnel 사용)이고, **[1.21 pre-release]**에서는 `--bpf-auth-map-max`와 `cilium_auth_map`이 제거되며 entry의 auth 비트는 reserved가 됩니다.

## 4. Map 카탈로그

전역 map은 `/sys/fs/bpf/tc/globals/` 아래에 이름으로 pin되고, 링크와 plugin 오브젝트는 `/sys/fs/bpf/cilium/` 아래에 있습니다. Helm: `bpf.root`(기본 `/sys/fs/bpf`), `bpf.autoMount.enabled`.

### 4.1 핵심 map

| Map | 유형 | Key -> Value (핵심) | 비고 |
|---|---|---|---|
| `cilium_lxc` | HASH | endpoint IP(+family, cluster_id) -> `{ifindex, lxc_id, flags, mac, node_mac, sec_id, parent_ifindex}` | 로컬 endpoint와 호스트 IP. 65535 entry(`lxcmap.MaxEntries`) |
| `cilium_ipcache_v2` | LPM_TRIE | `{cluster_id, family, ip/prefix}` -> `{sec_identity, tunnel_endpoint, key, flag_skip_tunnel, flag_has_tunnel_ep, flag_ipv6_tunnel_ep, flag_remote_cluster}` | **identity와 tunnel endpoint**. 512000 entry(`ipcachemap.MaxEntries`) |
| `cilium_policy_v3_<id>` | LPM_TRIE | 3.1 참고 | endpoint별 |
| `cilium_calls_<id>`, `_hostns_`, `_netdev_` | PROG_ARRAY | slot -> 프로그램 | 전용, 로드마다 교체 |
| `cilium_call_policy`, `cilium_egresscall_policy` | PROG_ARRAY | endpoint ID -> policy 프로그램 | 전역 |
| `cilium_ct4_global`, `cilium_ct6_global` | LRU_HASH | 5-tuple + 방향 플래그 -> `ct_entry` | TCP |
| `cilium_ct_any4_global`, `cilium_ct_any6_global` | LRU_HASH | 동일 | non-TCP |
| `cilium_snat_v4_external`(+`v6`) | LRU_HASH | CT tuple -> NAT entry(`to_saddr/to_sport` 또는 `to_daddr/to_dport`) | masquerade, NodePort SNAT |
| `cilium_nodeport_neigh4/6` | LRU_HASH | next-hop IP -> MAC | |
| `cilium_node_map_v2` | HASH | `{family, ip}` -> `{node id, spi}` | IPsec/WireGuard/ClusterMesh 노드 ID(v1은 1.19에서 제거) |
| `cilium_devices`(1.20 신규) | HASH | ifindex -> `{mac, l3}` | agent가 동기화 |
| `cilium_runtime_config` | ARRAY | index -> u64(time offset, agent liveness) | `cilium-dbg bpf config list` |
| `cilium_metrics` | PERCPU_HASH | `{reason, direction, line, file}` -> `{count, bytes}` | forward/drop 카운터의 원천 |
| `cilium_events` | PERF_EVENT_ARRAY | CPU -> perf fd | monitor와 Hubble의 원천(8절) |
| `cilium_signals` | PERF_EVENT_ARRAY | datapath -> agent 신호 | 예: CT 가득 참 -> GC 트리거 |

conntrack 주소는 패킷 기준과 출발지/목적지가 뒤바뀐 형태로 저장됩니다. `ct_entry`에는 lifetime, `rx/tx_closing`, `rev_nat_index`, `proxy_redirect`, `from_l7lb`, `from_tunnel`, `src_sec_id`, 관찰된 TCP 플래그가 들어 있습니다. 한 map에 egress, ingress, service scope entry가 함께 있고 `tuple.flags`로 구분합니다. Cluster Mesh는 겹치는 IP를 위해 cluster별 inner map(`cilium_per_cluster_ct_*`)을 추가합니다.

timeout(agent 플래그, 1.20.2): TCP established 2h13m20s, SYN 1m, FIN 10s, non-TCP 1m, service TCP 2h13m20s, service grace 1m.

### 4.2 로드밸런싱 map

| Map | 유형 | Key -> Value | 비고 |
|---|---|---|---|
| `cilium_lb4_services_v2`(+`6`) | HASH | `{address, dport, backend_slot, proto, scope}` -> `{backend_id 또는 affinity/algorithm, count, rev_nat_index, flags, qcount}` | slot 0이 frontend, slot 1..count가 backend ID. `scope`는 external/internal(externalTrafficPolicy) 구분 |
| `cilium_lb4_backends_v3`(+`6`) | HASH | `backend_id` -> `{address, port, proto, flags, cluster_id, zone}` | |
| `cilium_lb4_reverse_nat`(+`6`) | HASH | `rev_nat_index` -> `{address, port}` | per-packet LB 응답 복원 |
| `cilium_lb4_reverse_sk`(+`6`) | LRU_HASH | `{socket cookie, backend addr, port}` -> `{원래 service addr, port, rev_nat_index}` | socket-LB 역변환 |
| `cilium_lb4_affinity`, `cilium_lb_affinity_match` | LRU_HASH / HASH | client(IP 또는 netns cookie) + rev_nat -> backend | `sessionAffinity` |
| `cilium_lb4_source_range` | LPM_TRIE | `{rev_nat_id, cidr}` -> flag | `loadBalancerSourceRanges` |
| `cilium_lb4_maglev` | HASH_OF_MAPS | `rev_nat_id` -> lookup table array | `--bpf-lb-algorithm maglev`, 크기 `--bpf-lb-maglev-table-size` |
| `cilium_lb4_health` | LRU_HASH | socket cookie -> peer backend | LB health datapath. 커널 5.12 |

service의 `affinity_timeout` 필드 상위 8비트가 선택 알고리즘(random 또는 maglev)을 담습니다.

### 4.3 기능별 map (한 줄 요약)

`cilium_ipmasq_v4/v6`(masquerade 제외 CIDR), `cilium_ipv4_frag_datagrams`(기본 8192), `cilium_vtep_map`, `cilium_srv6_*`, `cilium_egress_gw_policy_v4_v2`(1.20에서 `_v4`에서 개명), `cilium_l2_responder_v4/v6`, `cilium_mcast_*`, `cilium_cidr_v4_fix/dyn`(XDP prefilter), `cilium_encrypt_state`, `cilium_auth_map`, `cilium_policystats`, `cilium_ratelimit`, `cilium_throttle`, `cilium_lb_act`/`cilium_lb_fct`(active connection tracking, 기본 off), per-CPU 임시 map(`cilium_tail_call_buffer4/6`, `cilium_nodeport_nat_buffer`, `cilium_xdp_scratch`, `cilium_percpu_trace_id`).

### 4.4 크기 조정 플래그

| 플래그 (Helm) | 기본값 (1.20.2) | 영향 |
|---|---|---|
| `--bpf-map-dynamic-size-ratio` (`bpf.mapDynamicSizeRatio`) | 0.0025 (RAM의 0.25%). **동적 크기 조정이 기본으로 켜져 있음** | CT TCP/any, NAT, socket reverse-NAT. NodePort neighbor map은 NAT 크기를 따름(플래그 도움말은 "CT, NAT and policy BPF maps"라고 하지만 크기 계산 코드는 policy map을 조정하지 않음) |
| `--bpf-ct-global-tcp-max` (`bpf.ctTcpMax`) | 524288 | TCP CT |
| `--bpf-ct-global-any-max` (`bpf.ctAnyMax`) | 262144 | non-TCP CT |
| `--bpf-nat-global-max` (`bpf.natMax`) | 524288 | NAT. CT 합의 2/3로 제한되며 초과 시 경고 |
| `--bpf-neigh-global-max` (`bpf.neighMax`) | 524288 | NodePort neighbor |
| `--bpf-policy-map-max` (`bpf.policyMapMax`) | endpoint당 16384 (최대 65536) | policy |
| `--bpf-fragments-map-max` | 8192 | fragment |
| `--bpf-node-map-max` | 16384 | node map |
| `--bpf-lb-map-max` (`bpf.lbMapMax`) | 65536 | LB map별 플래그 6개(`--bpf-lb-service-map-max`, `-service-backend-map-max`, `-rev-nat-map-max`, `-affinity-map-max`, `-source-range-map-max`, `-maglev-map-max`)의 fallback. 각각 기본 0 = `lb-map-max` 사용. 소스(`pkg/loadbalancer/config.go`)에는 있으나 생성된 cmdref에는 `--bpf-lb-map-max`만 나열됨 |
| `--bpf-sock-rev-map-max` | 동적, 기본은 CT-any 크기 | socket reverse map |
| `bpf.distributedLRU.enabled` | false | per-CPU LRU free list. 큰 map과 함께 사용 |
| `bpf.preallocateMaps` | false | 메모리를 써서 insert 지연을 낮춤 |

동적 크기는 `entries = default_entries * (ratio * RAM) / total_default_bytes`로 계산하고, map별 하한(CT TCP 128Ki, CT any 64Ki, NAT 128Ki, socket reverse 64Ki)과 상한 16Mi(2^24)로 자릅니다. **플래그를 명시하면 그 map의 동적 크기 조정만 꺼집니다.** 적용되면 agent가 `option <name> set by dynamic sizing to <N>`을 로그에 남깁니다. upstream 성능 튜닝 프로필은 ratio 0.08을 씁니다.

> map 크기를 바꾸면 map이 새로 만들어지고 다시 채워질 때까지 entry가 사라집니다. 운영 중인 노드에서 LB map이나 CT map 크기를 바꾸면 기존 연결이 끊깁니다. 노드 롤링 작업으로 계획하세요.

`cilium_bpf_map_pressure{map_name}`(`--bpf-policy-map-pressure-metrics-threshold`, 기본 0.1 초과 시 발행), `cilium_bpf_map_capacity`, `cilium_bpf_map_ops_total`로 모니터링합니다.

## 5. agent에서 커널까지: 컴파일, 로드, attach

### 5.1 흐름

```
agent 시작
  |  노드 헤더 작성 (StateDir/globals: node_config.h, netdev_config.h, ...)
  |  노드 설정 hash -> 바뀌면 template cache(StateDir/templates) 삭제
  v
template 설정 hash (컴파일 시점 #define만)
  |  cache hit -> StateDir/templates/<sha>/bpf_lxc.o 재사용
  |  miss      -> clang -O2 --target=bpf -mcpu=v3|v2|v1 ... -> 새 ELF template
  v
LoadCollection (endpoint / device별)
  |  spec 복사 -> map patch -> map 이름 변경 (cilium_calls -> cilium_calls_<id>, cilium_policy -> cilium_policy_v3_<id>)
  |  .rodata.config 기록 (endpoint ID, IP, MAC, ifindex, 기능 스위치)
  |  dead-code 분석 -> 사용되지 않는 tail call과 map 제거
  |  BTF decl tag로 tail-call array 채움
  |  커널에 로드(verifier). pin된 전역 map 재사용, 호환되지 않으면 교체
  v
attach: policy 프로그램 -> cilium_call_policy/egresscall_policy
        -> tcx/tc/netkit entry 프로그램 -> commit()으로 map pin 확정 -> endpoint route
```

### 5.2 ELF template과 `.rodata.config`

비용이 큰 컴파일 단계는 지금도 agent 안에서 실행됩니다(컨테이너 이미지에 clang/LLVM이 들어 있고, agent를 네이티브로 실행하려면 LLVM 18.1 이상이 필요합니다). Pod마다 다시 컴파일하지 않도록 Cilium은 코드 형태를 바꾸는 `#define ENABLE_*` 플래그, 즉 **template 설정**만 hash합니다. 같은 플래그를 가진 모든 endpoint가 `StateDir/templates/<sha>/` 아래의 오브젝트 하나를 공유합니다. 목록은 `cilium-dbg bpf sha list`로 봅니다.

endpoint별 값은 컴파일에 포함되지 않습니다. `DECLARE_CONFIG(type, name, desc)`로 선언하고 `CONFIG(name)`으로 읽는 `.rodata.config` 섹션의 전역 변수입니다. agent가 로드 전에 spec 사본에 값을 쓰고, 커널이 read-only 데이터를 freeze하므로 verifier는 이 값을 상수로 보고 **죽은 분기를 제거**합니다. dead-code-elimination 지원(커널 5.1 이상)이 필요합니다. Go 측 struct는 BTF decl-tag에서 `dpgen`이 생성합니다(`pkg/datapath/config/*_config.go`). 실제 적용된 상수는 endpoint/device별 JSON(예: `bpf_lxc.json`)으로 state 디렉터리에 덤프되며 `cilium sysdump`에 포함됩니다.

릴리스마다 더 많은 `#define`이 `.rodata.config`로 옮겨가므로 template 종류와 재컴파일이 줄어듭니다. BPF 트리에서 `DECLARE_CONFIG`/`NODE_CONFIG` 선언을 grep으로 세면 18(1.18.14), 43(1.19.8), 73(1.20.2), 104(**[1.21 pre-release]**, v1.21.0-pre.3)입니다. 각 태그 체크아웃에서 `grep -rE '^\s*(DECLARE_CONFIG|NODE_CONFIG)\(' bpf --include=*.h --include=*.c | wc -l`로 센 값입니다. 정확한 API가 아니라 대략적인 추세로 보세요.

### 5.3 재생성(regeneration)

endpoint를 재생성할 때 agent는 endpoint 헤더 hash를 계산합니다. 직전 값과 같으면 map만 동기화합니다(`RegenerateWithoutDatapath`, policy 변경의 경우). 다르면 헤더를 쓰고 datapath를 reload합니다. 관련 메트릭: `cilium_endpoint_regenerations_total`, `endpoint_regeneration_time_stats_seconds`(`bpfCompilation`, `bpfLoadProg`, `bpfWaitForELF` 단계), `cilium_endpoint_component_status`(1.20 신규).

순서가 중요합니다. map pin의 `commit()`은 모든 entry 프로그램이 attach된 뒤에 실행되어야 합니다. 그렇지 않으면 새 프로그램이 옛 array로 tail call하여 "missed tail call"이 발생할 수 있습니다.

### 5.4 verifier 테스트

Cilium은 기능을 최대로 켠 빌드를 커널 5.10, 6.1, net-next에 대해 컴파일 테스트합니다(`bpf/complexity-tests/`). 로드 시 verifier 실패는 전체 verifier 출력과 함께 로그에 남습니다.

## 6. 커널과 기능 매트릭스

### 6.1 시작 시 필수 요구사항(1.20.2)

다음이 없으면 agent가 시작하지 않습니다: `bpf()`와 JIT, tc-bpf 또는 tcx, `bpf_skb_change_tail`, `bpf_get_socket_cookie`, `bpf_get_current_cgroup_id`, `bpf_fib_lookup`, dead-code elimination, 쓰기 가능한 `skb->queue_mapping`, 대형(100만 instruction) 프로그램, `BPF_ADJ_ROOM_MAC`을 지원하는 `bpf_skb_adjust_room`, `bpf_jiffies64`, `BPF_MAP_LOOKUP_BATCH`, `bpf_get_netns_cookie`, `bpf_sk_assign`, `bpf_get_cgroup_classid`, cgroup sock_addr의 `bpf_perf_event_output`, `bpf_csum_level`, `bpf_skb_change_head`, `bpf_redirect_neigh`, `bpf_redirect_peer`. 그래서 문서화된 최소 버전이 **커널 5.10**입니다(4.18의 RHEL 8.10은 Red Hat backport 때문에 명시적 예외). helper별 헤더 probe는 이제 비어 있으며, 5.10 기준선이 모든 helper를 전제합니다.

upstream이 나열하는 커널 config에는 `BPF`, `BPF_SYSCALL`, `BPF_JIT`, `NET_CLS_BPF`, `NET_CLS_ACT`, `NET_SCH_INGRESS`, `CGROUPS`, `CGROUP_BPF`, `DEBUG_INFO_BTF`와 기능별 추가 항목(`VXLAN`, `GENEVE`, bandwidth manager용 `NET_SCH_FQ`, `NETKIT`)이 있습니다.

### 6.2 선택적 가속 기능

| 기능 | 최소 커널 | 성숙도 / 비고 |
|---|---|---|
| tcx link | 6.6 | 가능하면 기본. 아니면 legacy tc |
| netkit (`bpf.datapathMode`) | 6.8 (문서. 소스 probe 문구는 6.7) | beta |
| IPv6 BIG TCP | 5.19 | 지원 NIC 드라이버 필요 |
| IPv4 BIG TCP | 6.3 | |
| Bandwidth Manager의 BBR | 5.18 | |
| LB health-check datapath | 5.12 | |
| Multicast | AMD64 5.10, AArch64 6.0 | |
| `bpf_sock_destroy` kfunc | 소스에 명시 없음 | 자동으로 netlink `sock_diag` fallback |

datapath는 CO-RE relocation 헬퍼를 쓰지 않습니다(1.20.2 `bpf/` 트리에서 `preserve_access_index`를 검색하면 UAPI 헤더 주석만 나옵니다). 자체 헤더와 UAPI `__sk_buff`로 빌드합니다. BTF는 map 정의, `.rodata.config` 데이터 섹션, decl-tag에 쓰이며 `CONFIG_DEBUG_INFO_BTF=y`가 필요합니다.

EKS에서는 tcx나 netkit에 의존하는 설정을 켜기 전에 실제 노드의 `uname -r`과 `cilium-dbg status`를 확인하세요. 이 장은 어떤 AMI가 어떤 커널을 쓰는지 가정하지 않습니다.

## 7. 추적 예제: Pod -> Service -> Pod

예시 설정(숫자는 예시이고 구조는 소스 기준): 클라이언트 Pod `C` 10.0.1.10, identity 4711, endpoint ID 312, node A. Service `web` ClusterIP 10.100.0.20:80/TCP, `rev_nat_index` 42, backend 둘: B1 10.0.1.55(node A, endpoint 87), B2 10.0.2.77(node B). 둘 다 identity 9001. 설정: IPv4, veth, tcx, BPF host routing, `kubeProxyReplacement: true`(socket-LB가 강제로 켜짐), `socketLB.hostNamespaceOnly=false`.

### Hop 0: Pod 안의 `connect()`, `cgroup/connect4` (`cil_sock4_connect`)

1. `cilium_lb4_services_v2`를 `{10.100.0.20, 80, TCP, slot 0, scope 0}`으로 조회합니다. entry가 없으면 sockaddr를 건드리지 않습니다. 여기서는 `count=2`.
2. slot을 고릅니다(TCP는 random, UDP는 socket cookie). 그 slot의 service key로 `backend_id`를 얻고 `cilium_lb4_backends_v3[backend_id]`에서 10.0.2.77:80을 얻습니다. `sessionAffinity`가 있으면 `cilium_lb4_affinity`를 먼저 봅니다.
3. `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}] = {10.100.0.20, 80, 42}`를 기록합니다.
4. syscall의 `user_ip4/user_port`를 다시 씁니다. **wire에서는 DNAT이 일어나지 않습니다.** Pod 안 `tcpdump`에는 backend IP가 보이며 흔한 혼란 요인입니다. socket-LB tracing이 켜져 있으면 `trace_sock_notify` 이벤트가 발생합니다.

### Hop 1: SYN이 Pod를 떠남, 호스트 측 veth의 `cil_from_container`(tcx ingress)

| 단계 | 동작 | 접근 map |
|---|---|---|
| 1 | metadata 초기화, `send_trace_notify(TRACE_FROM_LXC)`(aggregation 적용) | `cilium_events` |
| 2 | slot 7 tail call(IPv4 from-LXC) | `cilium_calls_00312` |
| 3 | per-packet LB 건너뜀(socket-LB가 이미 변환) | 없음 |
| 4 | slot 30 tail call(CT egress): `CT_NEW`, tuple을 per-CPU buffer에 저장 | `cilium_ct4_global`, `cilium_tail_call_buffer4` |
| 5 | slot 26 tail call(`handle_ipv4_from_lxc`) | `cilium_calls_00312` |
| 6 | 목적지 identity 확인: 10.0.2.77의 LPM lookup으로 identity 9001과 (overlay) node B tunnel endpoint 획득. miss는 `world` | `cilium_ipcache_v2` |
| 7 | egress policy: `{egress=1, sec_label=9001, TCP, 80}` 2-pass lookup. allow 또는 drop. 새 허용 flow는 policy-verdict 이벤트 | `cilium_policy_v3_00312`, `cilium_events`, drop 시 `cilium_metrics` |
| 8 | `proxy_port != 0`이면 proxy용 mark, CT에 `proxy_redirect` 표시, 스택으로 전달(3.5절) | |
| 9 | `ct_create4(CT_EGRESS)`: entry 삽입. ACK 전까지 lifetime 1m(SYN), 이후 2h13m20s | `cilium_ct4_global`(+관련 ICMP용 CT-any) |
| 10 | 전달 경로 선택(아래) | |

10단계의 전달 선택:

- **같은 노드의 목적지**(B1): `cilium_lxc[dst]`가 `{ifindex, lxc_id=87, mac, node_mac}`을 반환하고 L2 헤더를 다시 쓴 뒤 metadata(`CB_SRC_LABEL=4711`, delivery flag)를 설정하고 `tail_call_policy(87)`로 `cilium_call_policy`에서 B1의 `cil_lxc_policy`를 실행합니다(Hop 3).
- **원격, overlay**: ipcache value에 `flag_has_tunnel_ep`가 있으므로 `bpf_skb_set_tunnel_key`로 `tunnel_id` = 출발지 identity 4711, `remote_ipv4` = node B를 설정하고 `cilium_vxlan`/`cilium_geneve`로 redirect합니다. 커널 encapsulation 전에 `cil_to_overlay`가 실행됩니다. Pod-to-Pod 트래픽은 masquerade되지 않습니다.
- **원격, native routing + BPF host routing**: `bpf_fib_lookup` 후 NIC로 redirect. `bpf.hostLegacyRouting=true`이면 패킷이 OK로 커널 스택과 netfilter로 돌아갑니다. VNI가 없으므로 수신 측은 출발지 IP로 ipcache에서(IPsec/WireGuard는 mark로) 출발지 identity를 다시 구합니다.

### Hop 2(원격만): node B 수신

- Overlay: `cil_from_netdev`가 UDP 8472(VXLAN) / 6081(Geneve)을 스택으로 넘기고, 커널이 decap해 `cilium_vxlan`으로 올립니다. `cil_from_overlay`가 `bpf_skb_get_tunnel_key`를 읽어 `tunnel_id`를 **출발지 identity**로 변환하고(host identity는 `DROP_INVALID_IDENTITY`로 거부), `CB_SRC_LABEL`에 저장하고 `TRACE_FROM_OVERLAY`를 내보낸 뒤 `cilium_lxc[10.0.2.77]`을 조회하여 `tail_call_policy(ep)`를 호출합니다.
- Native routing: `cil_from_netdev`가 같은 과정을 수행하되 출발지 identity는 `cilium_ipcache_v2[src ip]`에서 가져옵니다.

### Hop 3: 목적지 ingress policy와 전달

1. `cil_lxc_policy`가 CT-ingress tail call을 실행: `cilium_ct4_global` lookup, `CT_NEW`.
2. ingress policy: `cilium_policy_v3_00087`을 `{egress=0, sec_label=4711, TCP, 80}`으로 조회. verdict 이벤트 발생.
3. `ct_create4(CT_INGRESS)`가 `src_sec_id=4711`, `from_tunnel`, `proxy_redirect`를 기록.
4. 전달: Pod netns로 `bpf_redirect_peer`(veth) 또는 `redirect`(netkit), `TRACE_TO_LXC` 이벤트. backend 스택은 출발지 10.0.2.77로 응답하며 ClusterIP는 보지 못합니다.

### Hop 4: 응답과 종료

- B의 `cil_from_container`가 ingress CT entry를 `CT_REPLY`로 찾으므로 **policy를 건너뛰고**, VNI 9001로 encapsulation(또는 native 라우팅)하여 되돌립니다. node A에서는 `tail_call_policy(312)`가 C의 policy 프로그램을 실행하고 `CT_REPLY`라 policy를 건너뛰며 `redirect_peer`로 C에 전달됩니다.
- socket-LB 역변환: 앱은 10.100.0.20과 통신한다고 믿습니다. `getpeername`과 `recvmsg` hook이 `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}]`를 조회해 service 주소를 돌려줍니다.
- socket-LB가 없는 경우(host-namespace-only, L7 LB, SCTP): Hop 1에서 `bpf_lxc`가 DNAT을 수행하고 CT entry에 `rev_nat_index`를 저장하며, 응답은 `cilium_lb4_reverse_nat[rev_nat_index]`로 출발지를 복원합니다.
- FIN/RST는 `tx/rx_closing`을 설정하고 lifetime을 FIN timeout(10s)으로 낮추며 agent CT GC가 만료 entry를 삭제합니다. `cilium_lb4_reverse_sk` entry는 LRU 축출이나 `cil_sock_release`까지 남습니다.

### hop별 lookup 체크리스트

| Hop | 프로그램 | Lookup / 쓰기 |
|---|---|---|
| 0 | `cil_sock4_connect` | `lb4_services_v2` x2, `lb4_backends_v3`, `lb4_affinity`(선택), `lb4_reverse_sk` 쓰기 |
| 1 | `cil_from_container` + tail | `calls_<id>` x3, `tail_call_buffer4`, `ct4_global`(조회, 생성), `ipcache_v2`, `policy_v3_<src>`(egress), `cilium_lxc`, `call_policy`, `events`, `metrics` |
| 2 | `cil_from_overlay` / `cil_from_netdev` | tunnel key 또는 `ipcache_v2`, `cilium_lxc`, `call_policy` |
| 3 | `cil_lxc_policy`(목적지) | `ct4_global`, `policy_v3_<dst>`(ingress), `ct4_global` 생성, `events` |
| 4 | 역방향, `recvmsg` | `ct4_global`(reply), `lb4_reverse_sk` 또는 `lb4_reverse_nat` |

### 이 추적에 영향을 주는 1.20 동작 변경

kube-proxy replacement에서 `socketLB.enabled=false` 또는 `socketLB.hostNamespaceOnly=true`이면, 클러스터 내부 Pod -> NodePort 연결이 이제 **클라이언트 Pod의 tc hook**에서 로드밸런싱됩니다. 따라서 클라이언트 egress와 backend ingress NetworkPolicy가 해당 트래픽을 허용해야 합니다.

## 8. Hubble 이벤트 파이프라인

```
BPF 프로그램 --ctx_event_output--> cilium_events (PERF_EVENT_ARRAY, CPU별)
      |   trace_notify / drop_notify / policy_verdict_notify / debug / capture / trace_sock_notify
      v
agent monitor (pkg/monitor/agent): perf reader, CPU당 64 page, consumer가 있을 때만 open
      |-- lost sample (커널 버퍼 overrun) -> MonitorStatus.Lost
      |-- unix socket listener (cilium-dbg monitor), 큐 --monitor-queue-size
      v
Hubble consumer -> observer 큐 (--hubble-event-queue-size)
      |   가득 차면 LostEvent source=OBSERVER_EVENTS_QUEUE, hubble_lost_events_total
      v
Hubble parser (identity/endpoint/service 보강) -> ring buffer (--hubble-event-buffer-capacity)
      v
gRPC: hubble observe / Relay / UI
```

기억할 점:

- 이벤트 map은 1.20과 1.21-pre.3에서 BPF ring buffer가 아니라 **perf event array**입니다.
- datapath의 양 조절: `bpf.monitorAggregation`(Helm 기본 `medium`, agent 플래그 기본 `None`). `medium` 이상에서는 노드 내부 수신 trace가 억제되고, established flow는 `bpf.monitorInterval`(5s)이 지나거나 `bpf.monitorFlags`의 플래그가 보일 때만 보고됩니다. 종류별 토글: `bpf.events.drop.enabled`, `bpf.events.policyVerdict.enabled`, `bpf.events.trace.enabled`(모두 기본 true), 실험적 rate limit `bpf.events.default.rateLimit` / `burstLimit`(둘 다 설정하거나 둘 다 0).
- `hubble observe`의 flow는 메모리 ring에 있습니다(`hubble.eventBufferCapacity`, 2^n - 1이어야 하며 기본 4095, 최대 65535). best-effort이므로 perf buffer overrun과 observer queue overflow 모두 이벤트를 잃고, `source` 레이블(`perf_event_ring_buffer`, `observer_events_queue`)로 구분해 집계됩니다.
- L7 이벤트는 BPF에서 나오지 않고 proxy가 보내는 agent 이벤트로 들어옵니다.

## 9. 점검 도구

### 9.1 cilium-dbg

```bash
CILIUM_POD=$(kubectl -n kube-system get pod -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}')
kc() { kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- "$@"; }

kc cilium-dbg status --verbose         # KPR, datapath mode(configured vs operational), BPF map pressure
kc cilium-dbg bpf fs show              # bpffs mount
kc cilium-dbg map list -v              # pin된 map과 크기
kc cilium-dbg bpf endpoint list        # cilium_lxc
kc cilium-dbg bpf ipcache list         # IP/CIDR별 identity + tunnel endpoint
kc cilium-dbg bpf ct list global       # conntrack
kc cilium-dbg bpf nat list             # SNAT map
kc cilium-dbg bpf lb list --frontends  # --backends, --revnat, --source-ranges도 가능
kc cilium-dbg bpf lb maglev list       # Maglev 사용 시에만
kc cilium-dbg bpf policy get --all -n  # 모든 cilium_policy_v3_*, 숫자 identity
kc cilium-dbg bpf metrics list         # cilium_metrics
kc cilium-dbg bpf config list          # cilium_runtime_config
kc cilium-dbg bpf sha list             # 컴파일된 ELF template
kc cilium-dbg monitor -t drop -t policy-verdict --related-to <ENDPOINT_ID>
```

`cilium-dbg map get <name>`은 커널이 아니라 agent의 캐시 상태를 보여주고, `cilium-dbg map events <name>`은 갱신 로그를 보여줍니다. `bpf tunnel`과 `bpf calls` 하위 명령은 없습니다.

### 9.2 bpftool (노드에서 실행)

```bash
sudo bpftool net show                                     # device별 tcx/tc/xdp/netkit attach
sudo bpftool prog show | grep -E 'cil_|tail_'             # entry와 tail 프로그램
sudo bpftool map show pinned /sys/fs/bpf/tc/globals/cilium_ct4_global
sudo bpftool cgroup tree /run/cilium/cgroupv2             # socket-LB hook
sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links
```

pin된 map은 읽기 전용으로만 다루세요. Cilium map에 raw byte를 쓰면 agent의 캐시 상태와 어긋납니다. agent 이미지에 `bpftool`이 있는지는 이번 검토에서 확인하지 못했으므로, 없으면 노드나 디버그 Pod에서 실행하세요.

**[1.21 pre-release]** `--enable-bpf-stats`(Helm `bpf.stats.enabled`, 기본 false)는 커널 실행 시간 통계를 켜고, 프로그램별 실행 횟수와 평균 실행 시간을 보여주는 `bpf/stats/report` hive 명령을 추가하며, `cilium-dbg bpf stats report`(`--sort avg|total|runs`, `--pod`, `--device`, `--json`)로 호출합니다.

## 10. Datapath Plugins (beta, 1.20 신규)

Datapath Plugins는 Cilium datapath를 fork하지 않고도 외부 구성요소가 Cilium entry point 앞뒤로 자체 BPF 프로그램을 실행하게 합니다.

- Helm `datapathPlugins.enabled=true`로 켭니다(기본 false, agent `--enable-datapath-plugins`). state 디렉터리는 `datapathPlugins.stateDir`(기본 `/var/run/cilium/plugins`).
- `CiliumDatapathPlugin` CRD(`cilium.io/v2alpha1`)로 등록합니다: `spec.attachmentPolicy: Always | BestEffort`, `spec.version`.
- agent는 `<stateDir>/<name>/plugin.sock`의 gRPC로 각 plugin과 통신하며 `PrepareCollection`, `InstrumentCollection` 호출을 사용합니다. Cilium이 dispatcher를 생성하여 `BPF_PROG_TYPE_EXT`(freplace) 유형의 plugin 프로그램이 tc, XDP, cgroup sock hook의 Cilium entry 프로그램 앞 또는 뒤에서 실행됩니다.
- plugin Pod에는 `SYS_ADMIN`이 필요합니다. plugin CR을 생성, 수정, 삭제하면 datapath 전체가 재초기화됩니다. 버전 간 호환성은 보장되지 않습니다. 1.18과 1.19에는 없습니다.

실험이나 벤더 통합용으로 보고, 아직 운영 환경의 일반 확장 지점으로 쓰지 마세요.

## 11. 실습

모든 실습의 전제: kube-proxy replacement가 켜진 Cilium 1.20.2 일회용 Linux 클러스터, 노드 셸 접근(SSM 등), `kubectl`. 어떤 것도 클러스터 외부로 노출하지 않습니다.

### 실습 1: 노드의 모든 Cilium 프로그램 찾기

1. 노드에서 `sudo bpftool net show`와 `sudo bpftool prog show | grep cil_`를 실행합니다.
2. `sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links`로 pin된 링크를 나열합니다.
3. `kc cilium-dbg bpf sha list`를 실행합니다.

기대 결과: 각 native device에 `cil_from_netdev`, 각 `lxc*` device에 `cil_from_container`, `cilium_host`에 `cil_to_host`/`cil_from_host`, (overlay라면) `cilium_vxlan` 또는 `cilium_geneve`에 `cil_from_overlay`/`cil_to_overlay`가 보입니다. 커널 6.6 이상에서는 endpoint별 link pin이 있고, 더 오래된 커널에서는 `tc filter show dev <lxc> ingress`가 legacy filter를 보여줍니다. 정리: 없음(읽기 전용).

### 실습 2: policy 변경은 재컴파일하지 않음

1. `kc cilium-dbg bpf sha list`와 `kc cilium-dbg bpf policy get <ENDPOINT_ID>`로 endpoint의 map 상태를 기록합니다.
2. 테스트 backend에 대해 클라이언트 label의 TCP/80을 허용하는 `CiliumNetworkPolicy`를 적용합니다.
3. 두 명령을 다시 실행합니다.

기대 결과: backend endpoint의 policy map에 클라이언트의 숫자 identity를 가진 새 ingress entry가 나타나고 template 목록은 그대로입니다. 명시적 deny rule을 추가하면 deny 플래그가 있는 entry를 볼 수 있습니다. 정리: policy 오브젝트를 삭제합니다. 클러스터 전체 default-deny와 상호작용하므로 다른 policy가 없는 namespace에서 연습하세요.

### 실습 3: 연결 하나를 map으로 따라가기

1. 테스트 namespace에 replica 2개의 Deployment, ClusterIP Service, 클라이언트 Pod를 만듭니다.
2. 클라이언트에서 ClusterIP로 `curl`합니다. 다른 터미널에서 클라이언트 노드의 `cilium-dbg monitor -t trace -t policy-verdict --related-to <CLIENT_ENDPOINT_ID>`를 실행합니다.
3. `bpf lb list --frontends`, `--backends`, `bpf ct list global | grep <backend ip>`를 실행합니다.
4. 클라이언트 netns의 `tcpdump -ni eth0 port 80`에서 보이는 주소를 비교합니다.

기대 결과: service frontend에 backend들이 나열되고, 선택된 backend의 CT entry가 있으며, socket-LB가 켜져 있으면 캡처에 ClusterIP가 아니라 backend IP가 보입니다. 선택 사항: `socketLB.hostNamespaceOnly=true`에서는 캡처에 ClusterIP가 보입니다(per-packet LB). 이 설정은 클러스터 전체의 로드밸런싱 방식을 바꾸므로 테스트 클러스터에서만 적용하고, 이전 Helm 값을 복원해 되돌립니다.

### 실습 4: Hubble 손실 집계

1. 테스트 클러스터에서 `hubble.eventQueueSize`를 의도적으로 작게 설정합니다(롤백: 이전 값 복원, agent가 재시작됨).
2. 테스트 namespace에서 트래픽 도구로 부하를 발생시킵니다.
3. agent 메트릭에서 `source`별 `hubble_lost_events_total`을 조회합니다.

기대 결과: 큐가 넘치면 `observer_events_queue`가 증가하고 agent가 "hubble events queue is full"을 로그에 남깁니다. perf buffer overrun은 대신 `perf_event_ring_buffer`로 나타납니다.

### 실습 5 (고급): 새 노드 그룹에서 netkit

netkit을 지원하는 커널의 노드에서만 수행합니다. 새 노드 그룹을 `bpf.datapathMode=auto`로 설치하거나 업그레이드한 뒤, `cilium-dbg status`의 configured/operational mode, `ip -d link show`의 device 유형, `bpftool net show`의 netkit attach를 확인합니다. netkit과 함께 `bpf.tproxy=true`를 설정하면 1.19 이후 agent가 netkit을 거부합니다(`auto`는 veth로 fallback). 롤백: 기존 veth Pod를 제자리에서 전환하지 말고 노드를 drain하여 교체하세요.

## 버전별 변경점

| 항목 | 1.18.14 | 1.19.8 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|---|---|
| 최소 커널(문서) | 5.10 (RHEL 8.10은 4.18) | 5.10 | 5.10 | 5.10 |
| `bpf_network.c` | 있음 | 있음 | **제거** | 제거 |
| `CILIUM_CALL_SIZE` | 48 | 49 | 50 | 50 |
| config 변수(grep 개수) | 18 | 43 | 73 | 104 |
| Policy map 이름 | `cilium_policy_v2_` | `cilium_policy_v2_` | `cilium_policy_v3_` | `cilium_policy_v3_`(auth 비트 reserved) |
| Node map | v1 + v2 | v2만 | v2 | v2 |
| Egress gateway map | `..._v4` | `..._v4` | `..._v4_v2` | `..._v4_v2` |
| `cilium_devices` map | 없음 | 없음 | 있음 | 있음 |
| `--datapath-mode` 값 | veth, netkit, netkit-l2 | 동일 | + `auto` | + `auto` |
| `bpf.tproxy` | beta(netkit 검사 못 찾음) | beta, netkit과 함께 쓰면 거부 | beta, netkit과 함께 쓰면 거부 | beta, netkit과 함께 쓰면 거부 |
| Datapath Plugins | 없음 | 없음 | 있음(beta) | 있음 |
| Mutual auth map(`--bpf-auth-map-max`) | 있음 | 있음 | 있음, mutual auth deprecated | 제거 |
| `--enable-bpf-stats` | 없음 | 없음 | 없음 | 있음 |
| `--node-port-mode`, `--node-port-algorithm` | 있음 | 있음 | 제거(`--bpf-lb-mode`, `--bpf-lb-algorithm` 사용) | 제거 |
| policy 거부 ICMP 응답 | 없음 | 없음 | 있음(tail slot 48-49) | 있음 |

pre-release 트리의 1.21 업그레이드 노트는 아직 1.20 내용 그대로이므로 권위 있는 1.21 변경 목록은 아직 없습니다.

## 문제 해결

| 증상 | 가능한 원인 | 확인 |
|---|---|---|
| `DROP_EP_NOT_READY`(코드 -203) drop | endpoint 생성/삭제 중 policy slot이 비어 있음 | `cilium-dbg endpoint list`. endpoint 변동 중 일시적이면 정상, 지속되면 regeneration 실패 |
| "Missed tail call" drop | reload 실패 후 array 미채움 또는 commit 순서 문제 | agent 로드 오류 로그, `cilium-dbg endpoint log <id>`, agent Pod 재시작 |
| 신규 연결 실패, CT map의 `cilium_bpf_map_pressure`가 1에 근접 | CT/NAT map 가득 참 | `cilium-dbg map list -v`. `bpf.mapDynamicSizeRatio` 또는 명시적 최대값 증가, NAT는 CT의 2/3 이하, 크기 변경 시 entry 손실 유의 |
| 서비스가 늘어난 뒤 매칭 안 됨 | LB map 한도 도달 | `bpf.lbMapMax`(map 6개에 영향). 크기 변경은 연결을 끊음 |
| agent 시작 안 됨, "Require support for tcx links" 또는 helper 오류 | 커널이 기준선 미만 | `uname -r`, `cilium-dbg status`. 지원되는 AMI로 이동 |
| tcx가 아니라 legacy tc 사용 | 커널 6.6 미만 또는 `enableTCX: false` | `bpftool net show`, `tc filter show` |
| netkit 거부 | 전제 조건 누락(host routing, BPF masquerade, KPR, tproxy, 커널) | agent 로그의 사유, `cilium-dbg status`의 configured vs operational mode |
| 로드 시 verifier 거부 | 특이한 기능 조합 또는 커널 한계 | agent stderr의 전체 verifier 로그. 5.10/6.1/net-next 테스트 빌드와 비교 |
| `hubble observe`에 flow 누락 | perf buffer 또는 observer queue 손실, aggregation 과다, ring 부족 | `source`별 `hubble_lost_events_total`, `bpf.monitorAggregation`, `hubble.eventBufferCapacity` |
| 옛 가이드가 `cilium_tunnel_map` 덤프를 권함 | map이 제거됨 | `cilium-dbg bpf ipcache list` 사용 |
| socket-LB off/host-namespace-only에서 1.20 업그레이드 후 Pod -> NodePort 실패 | LB가 클라이언트 Pod tc hook으로 이동 | 클라이언트 egress와 backend ingress policy에서 허용 |

## 검증 한계 및 출처

실습은 이번 검토에서 실제 클러스터에 실행하지 않았고, 명령과 플래그를 upstream 소스와 문서에 대조해 확인했습니다. trace의 ID, IP, identity는 예시입니다. 소스 사실은 Cilium v1.20.2 트리(예: `bpf/bpf_lxc.c`, `bpf/lib/tailcall.h`, `bpf/lib/policy.h`, `bpf/lib/eps.h`, `pkg/datapath/loader/tc.go`, `pkg/bpf/collection.go`, `Documentation/cmdref/cilium-agent.md`)에서 읽었으며, 줄 번호는 릴리스마다 움직이므로 사용하는 태그에서 다시 확인하세요. 확인하지 못한 항목: agent 이미지의 `bpftool` 포함 여부, `bpf_sock_destroy` kfunc이 도입된 정확한 커널 버전, **[1.21 pre-release]** stats report는 소스(`cilium-dbg/cmd/bpf_stats_report.go`)에서 읽었을 뿐 실행하지 않았습니다.

- Cilium v1.20.2 시스템 요구사항: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst
- Map 레퍼런스: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/ebpf/maps.rst (문서에는 `cilium_ct_{4,6}_global`로 적혀 있으나 실제 이름은 `cilium_ct4_global`, `cilium_ct6_global`)
- BPF 소스: https://github.com/cilium/cilium/tree/v1.20.2/bpf
- Datapath loader: https://github.com/cilium/cilium/tree/v1.20.2/pkg/datapath/loader
- Agent 플래그: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/cmdref/cilium-agent.md
- Datapath Plugins: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/contributing/development/plugins.rst
- 업그레이드 노트: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc
- 성능 튜닝(netkit, BIG TCP): https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst
- **[1.21 pre-release]** BPF stats: https://github.com/cilium/cilium/tree/v1.21.0-pre.3/pkg/bpf/stats

## 퀴즈

[Part 8 퀴즈](../../quizzes/networking/cilium/08-ebpf-datapath-internals-quiz.md)로 이해도를 확인하세요.
