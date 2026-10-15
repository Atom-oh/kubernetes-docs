# Part 9: Overlay와 Native Routing 심층 분석

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

이 장은 [네트워킹 모델 및 VXLAN](03-networking.md)에서 다룬 모드 선택 이면을 설명합니다. 서로 다른 노드의 두 Pod 사이 패킷이 tunnel 모드와 native-routing 모드에서 실제로 어떻게 움직이는지, 어떤 BPF 프로그램이 무엇을 하는지, security identity가 캡슐화 안에 어떻게 실리는지, MTU와 masquerading이 어떻게 결정되는지, 어떤 조합에서 agent가 기동을 거부하는지를 다룹니다. 또한 kube-proxy replacement, DSR, Maglev, socket-LB, host-routing, netkit, bandwidth manager, 암호화가 같은 datapath의 어디에 놓이는지 설명하고, EKS 선택 가이드와 트러블슈팅 런북으로 마칩니다.

관련 장: [eBPF datapath 내부](08-ebpf-datapath-internals.md)(프로그램 attach, map), [IPAM 심화](10-ipam-deep-dive.md)(Pod CIDR의 출처), [BGP, LB, egress, edge](11-bgp-lb-egress-edge.md)(Pod CIDR 광고, 외부 LB), [mTLS, 암호화, identity](12-mtls-encryption-identity.md)(WireGuard/IPsec 상세), [ClusterMesh, 설치, 업그레이드](13-clustermesh-install-upgrade.md).

## 목차

1. 라우팅 모드 매트릭스
2. Cilium의 VXLAN과 Geneve
3. VNI에 identity가 실리는 방식
4. Control plane: CiliumNode에서 tunnel endpoint까지
5. 패킷 워크: 동일 노드, tunnel, native
6. Native routing: 경로는 누가 제공하는가
7. 기동 시 검증: hard failure와 silent fallback
8. MTU 계산
9. Masquerading
10. Host routing: legacy와 BPF
11. Datapath 장치: veth와 netkit
12. Datapath 안의 서비스 로드밸런싱
13. Bandwidth manager, BBR, BIG TCP
14. 암호화와의 상호작용
15. VTEP와 multicast (beta)
16. EKS 선택 가이드
17. 점검 치트시트
18. 실습
19. 버전별 변경 사항
20. 트러블슈팅
21. 검증 한계 및 출처

---

## 1. 라우팅 모드 매트릭스

1.20에서 `routingMode`는 `tunnel`(기본)과 `native` 두 값만 받습니다. 이 장의 나머지는 이 선택과, 스스로 tunnel 장치를 요청하는 몇몇 기능의 결과입니다.

| 상황 | Helm | 서로 다른 노드 Pod 간 경로 | Pod CIDR을 라우팅하는 주체 |
|---|---|---|---|
| Tunnel (기본) | `routingMode: tunnel`, `tunnelProtocol: vxlan`(기본) 또는 `geneve` | BPF가 tunnel metadata를 설정하고, 커널 `cilium_vxlan`/`cilium_geneve`가 UDP로 캡슐화 | 없음. 노드 간 IP 도달성과 UDP 8472/6081만 필요 |
| Native | `routingMode: native` | Pod IP 그대로 송출, 커널(또는 BPF host routing의 FIB redirect)이 라우팅 | 네트워크: 클라우드 라우터/ENI, `autoDirectNodeRoutes`, BGP, 정적 경로 |
| Native + 기능이 요청한 tunnel | `routingMode: native` + Egress Gateway 또는 `dsrDispatch: geneve` DSR | 일반 Pod 트래픽은 native, 해당 기능의 패킷만 tunnel 장치 사용 | native와 동일 |

세 번째 행이 중요합니다. native-routing 클러스터에서 `cilium_geneve` 장치가 보인다고 설정 오류는 아닙니다. 코드(`pkg/datapath/tunnel/tunnel.go`)에서 Egress Gateway와 Geneve DSR는 `routingMode`가 `native`여도 장치를 요청하는 "tunnel enabler"입니다.

성숙도(1.20.2 문서 기준): VXLAN/Geneve tunnel과 native routing은 stable입니다. BGP는 경로 광고 수단이지 forwarding 모드가 아닙니다. [BGP, LB, egress, edge](11-bgp-lb-egress-edge.md)를 참고하세요.

> **1.21 관찰 항목.** v1.21.0-pre.3 소스에는 Helm 차트에 노출되지 않은, 문서화되지 않은 또 다른 라우팅 모드의 미완성 scaffolding이 있습니다. 이 장에서는 이름도 내용도 다루지 않습니다. 1.21 GA에서도 `routingMode` 값이 두 개라고 가정하기 전에 GA 라우팅 문서를 다시 확인하세요.

## 2. Cilium의 VXLAN과 Geneve

둘 다 UDP 캡슐화입니다. Cilium은 어느 쪽이든 **flow-based(collect-metadata) 커널 netdev**를 사용합니다. 즉 BPF가 패킷마다 metadata를 붙이면 커널 드라이버가 outer 헤더를 만듭니다. Outer 헤더를 BPF에서 직접 만들지 않습니다.

| 항목 | VXLAN | Geneve |
|---|---|---|
| Helm 값 | `tunnelProtocol: vxlan`(기본) | `tunnelProtocol: geneve` |
| 기본 UDP 목적지 포트 | 8472 | 6081 |
| 장치 | `cilium_vxlan` | `cilium_geneve` |
| identity 위치 | VNI(24비트) | VNI(24비트), 동일 방식 |
| Cilium이 쓰는 옵션/TLV | 없음 | DSR 서비스 주소/포트 옵션뿐(class `0x014B`, type `0x81`) |
| DSR | 불가. VXLAN tunnel에서 `dsr`/`hybrid`는 agent가 거부 | `dsrDispatch: geneve` |
| 커널 설정 | `CONFIG_VXLAN` | `CONFIG_GENEVE` |

둘 다 `CONFIG_FIB_RULES`도 필요합니다. 8472는 IANA 지정 4789가 아니라 Linux 커널의 역사적 VXLAN 기본 포트이며 Cilium이 호환을 위해 유지합니다. `tunnelPort`로 바꿀 수 있지만 포트를 바꾸면 장치가 재생성되어 짧은 중단이 생기고, MTU 변경은 장치를 제자리에서 수정합니다.

관련 설정:

- `tunnelSourcePortRange: "0-0"`(기본)은 outer UDP 출발지 포트 범위를 커널 드라이버에 맡깁니다. 범위를 좁히면 underlay ECMP/필터가 보는 엔트로피를 제한할 뿐 identity에는 영향이 없습니다.
- `underlayProtocol: auto|ipv4|ipv6`(1.18에서 추가). `auto`는 IPv4가 켜져 있으면 IPv4, 아니면 IPv6를 선택합니다. IPv6 underlay는 overhead가 70바이트가 되고, XDP 가속이 금지되며, Egress Gateway는 IPv4 underlay가 필요합니다.
- `tunnelProtocol`을 바꾸면 다른 장치가 삭제되고 새 장치가 생성되므로 노드 단위의 중단 작업으로 계획하세요.

보안 그룹/방화벽 요건: **모든** 노드 간 UDP 8472(VXLAN) 또는 UDP 6081(Geneve), 그리고 health check용 TCP 4240과 ICMP echo. AWS에서는 인터넷에 열린 CIDR이 아니라 보안 그룹 간 참조(노드 SG가 자기 자신을 참조)로 표현합니다. WireGuard는 UDP 51871, IPsec은 ESP(IP 프로토콜 50)가 필요하며 AWS 보안 그룹은 ESP를 기본 허용하지 않습니다.

```yaml
# values: Geneve overlay (이후 Geneve DSR dispatch를 쓰려면 필요)
routingMode: tunnel
tunnelProtocol: geneve
```

## 3. VNI에 identity가 실리는 방식

Cilium이 캡슐화한 모든 패킷의 24비트 tunnel ID(VNI)는 송신 endpoint의 **source security identity**입니다. VXLAN과 Geneve 모두 같습니다. Geneve 옵션은 identity에 쓰이지 않습니다.

`bpf/lib/identity.h`, `bpf/lib/encap.h`, `bpf/bpf_overlay.c`(v1.20.2)의 규칙:

- dual-stack에서 예약 identity `world-ipv4`(9)와 `world-ipv6`(10)은 둘 다 `world`(2)로 전송되고, 수신 측이 inner L3 프로토콜로 복원합니다.
- `host` identity(1)는 전송되지 않습니다. 송신 측이 캡슐화 전에 `local-node`/`remote-node`(6)로 바꿉니다. tunnel로 들어온 패킷이 `host`를 주장하면 `DROP_INVALID_IDENTITY`로 drop됩니다.
- 수신 측에도 ipcache가 있습니다. upstream은 identity 전달을 원격 노드의 조회 한 번을 줄이는 최적화로 설명하며 유일한 진실의 원천이 아닙니다. 원격 노드 트래픽에 대해 `bpf_overlay.c`는 ipcache로 identity를 다듬습니다.

활용:

1. wire의 VNI는 `cilium-dbg endpoint list`의 IDENTITY 열 또는 `cilium-dbg identity list` 값과 같습니다. 실습 1에서 확인합니다.
2. ingress 정책 결정은 목적지 노드에서 전달된 identity로 수행되므로, ingress 집행에 출발지 IP를 다시 Pod로 해석할 필요가 없습니다.
3. VTEP 연동(15절)이 이에 의존합니다. 외부 VTEP 트래픽은 VNI 2(`world`)여야 합니다.

옵션을 쓰는 유일한 경우는 Geneve DSR입니다. 로드밸런싱 노드가 원래 서비스 주소와 포트를 담은 Geneve 옵션을 삽입해 backend 노드가 응답을 재작성할 수 있게 합니다. 12바이트가 추가되며 datapath에서 처리됩니다(8절).

## 4. Control plane: CiliumNode에서 tunnel endpoint까지

Tunnel 모드에서 송신 측은 목적지 Pod IP마다 (a) security identity, (b) 그 Pod를 호스팅하는 노드 IP(tunnel endpoint)를 알아야 합니다. 둘 다 하나의 BPF LPM map에 있습니다.

```text
 Kubernetes API                       cilium-agent                       BPF
 --------------                       ------------                       ---
 CiliumNode (원격 노드 IP,      -->   node manager: 노드 발견
             podCIDR)                    |- 원격 PodCIDR마다 커널 route
 CiliumEndpoint(Slice)/identity -->   ipcache listener                 cilium_ipcache_v2
   (Pod IP -> identity)                   기록: {identity,    ------>  key: prefix
                                                 tunnel_endpoint,      value: identity,
                                                 encrypt key,                 tunnel endpoint,
                                                 flags}                       flags (skip_tunnel...)
```

- `cilium_ipcache_v2`는 LPM map입니다. 값에는 identity, tunnel endpoint(원격 노드 IPv4/IPv6), 암호화 키 인덱스, `skip_tunnel` 같은 flag가 들어 있습니다. listener는 호스트 IP가 로컬 노드 IP와 다를 때만 tunnel endpoint를 채웁니다.
- 원격 PodCIDR마다 `cilium_host`를 경유하는 커널 route도 설치됩니다(`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`). BPF의 encap 결정은 ipcache를 쓰며, route는 호스트 발신 트래픽의 fallback입니다.
- **`cilium_tunnel_map`은 사라졌습니다.** 1.17까지는 BPF(`bpf/lib/encap.h`)에 남아 있었고 `cilium-dbg bpf tunnel list`로 덤프할 수 있었습니다. 1.18에서 datapath에서 빠졌고(1.18.14 BPF 트리에는 참조가 없으며 agent는 남아 있는 map을 unpin만 합니다), Go 패키지는 1.19에서 제거되었습니다. tunnel endpoint는 ipcache value에 있으므로 `cilium-dbg bpf ipcache list`(tunnel endpoint 열), `cilium-dbg bpf nodeid list`, `cilium-dbg node list`로 확인합니다.

## 5. 패킷 워크: 동일 노드, tunnel, native

프로그램 이름은 `bpf/bpf_lxc.c`, `bpf/bpf_overlay.c`, `bpf/lib/local_delivery.h`(v1.20.2) 기준입니다. attach 방식은 [eBPF datapath 내부](08-ebpf-datapath-internals.md)를 참고하세요.

### 5.1 Pod A(노드 1)에서 Pod B(노드 2)로, tunnel 모드

```text
 노드 1                                                          노드 2
 ------                                                          ------
 Pod A eth0
   |  (호스트 쪽 veth/netkit peer)
   v
 [bpf_lxc: cil_from_container]
   1. 서비스 DNAT (connect() 시점의 socket-LB, 또는 패킷별 lb4_local)
   2. conntrack 조회 (cilium_ct4_global)
   3. 목적지 ipcache 조회 -> 목적지 identity + tunnel endpoint (노드 2)
   4. egress 정책 (endpoint별 policy map, identity 기준)
   5. 목적지가 로컬이 아님 -> TUNNEL_MODE 분기:
        tunnel key { id = src identity, remote = 노드 2 IP } 설정
        (bpf_skb_set_tunnel_key) 후 cilium_vxlan ifindex로 redirect
   v
 [cilium_vxlan  (flow-based netdev)]
   egress의 cil_to_overlay: identity mark, SNAT 처리,
   EDT bandwidth (bandwidth manager 사용 시)
   커널 vxlan 드라이버가 outer Eth/IP/UDP(8472)/VXLAN(VNI) 생성
   v
 NIC  ==== underlay IP 네트워크, UDP 8472 ====>  NIC
                                                  |
                                                  v
                                       커널 vxlan 드라이버가 decap
                                                  v
                                       [cilium_vxlan ingress: cil_from_overlay]
                                         ethertype 검증, tunnel key 읽기
                                         -> src_sec_identity
                                         IPV4_FROM_OVERLAY tail call (handle_ipv4):
                                           VTEP 출발지 검사 (world여야 함)
                                           원격 노드 identity를 ipcache로 보정
                                           목적지 endpoint 조회
                                           ipv4_local_delivery(from_tunnel=true)
                                         cilium_call_policy tail call:
                                           전달된 identity로 Pod B의 ingress 정책 평가
                                         Pod B netns로 redirect (veth + BPF host routing이면
                                           redirect_peer)
                                                  v
                                                Pod B eth0
```

핵심:

- **커널이 캡슐화하고 BPF는 방향을 지정합니다.** BPF는 tunnel key(`BPF_F_ZERO_CSUM_TX`, TTL 64)를 설정하고 tunnel 장치로 redirect합니다. "eBPF가 패킷을 직접 캡슐화한다"는 흔한 단순화를 바로잡는 부분입니다.
- 암호화는 캡슐화 **이후**에 적용되므로(IPsec은 1.18부터, WireGuard는 별도 장치) 암호화가 켜져 있으면 물리 NIC에서는 VXLAN/Geneve가 아니라 ESP 또는 WireGuard가 보입니다.
- 응답은 conntrack으로 대칭 경로를 따르며, 목적지 노드가 Pod B의 identity를 VNI로 캡슐화합니다.
- Pod에서 **원격 노드** 주소로 가는 트래픽은 tunnel을 타지 않습니다. tunnel 모드에서는 masquerade됩니다(9절).

### 5.2 동일 노드

`__lookup_ip4_endpoint`가 로컬 목적지 endpoint를 찾고, `ipv4_local_delivery`가 `cilium_call_policy`(목적지의 ingress 정책)를 tail call한 뒤 `bpf_redirect_peer`(veth + BPF host routing) 또는 `bpf_redirect`로 전달합니다. netkit에서는 Pod 간에 egress에서 ingress로의 일반 `redirect`를 씁니다. 캡슐화는 없습니다.

### 5.3 Pod A에서 Pod B로, native routing

1~4단계는 같고 5단계에서 tunnel을 쓰지 않습니다.

- **BPF host routing**(KPR과 BPF masquerade가 갖춰지면 기본)이면 `fib_redirect_v4`가 FIB 조회 후 NIC로 바로 redirect하여 netfilter와 상위 스택을 우회합니다.
- **Legacy host routing**이면 프로그램이 `CTX_ACT_OK`(스택으로 전달)를 반환하고, Linux 커널이 존재하는 경로로 라우팅합니다. AWS ENI/endpoint route, `autoDirectNodeRoutes`, BGP 경로, 클라우드 라우터 등입니다.

외부 네트워크는 Pod IP를 그대로 보므로 라우팅할 수 있어야 하고, 비 ENI EC2의 source/destination check 같은 anti-spoofing과 보안 그룹이 이를 허용해야 합니다. ENI 기반 Pod IP는 VPC가 직접 소유합니다.

## 6. Native routing: 경로는 누가 제공하는가

`routing-mode: native`는 로컬이 아닌 패킷을 커널에 넘기고 IP forwarding을 켭니다. Cilium은 Pod CIDR의 위치를 네트워크에 알려주지 않습니다. 다음 중 하나가 해야 합니다.

| 경로 제공자 | Helm | 비고 |
|---|---|---|
| 클라우드 fabric | `eni.enabled`(AWS), `gke.enabled`, Azure IPAM | Pod IP가 클라우드 네트워크에 native. endpoint route(`enable-endpoint-routes`)는 차트가 설정 |
| Direct node route | `autoDirectNodeRoutes: true` | `<원격 podCIDR> via <원격 노드 IP>` 설치. 모든 노드가 같은 L2 세그먼트여야 함 |
| BGP | Cilium BGP control plane 또는 외부 데몬 | [11장](11-bgp-lb-egress-edge.md) |
| 정적 경로 | 없음 | 운영자 관리 |

`directRoutingSkipUnreachable`(기본 false)은 on-link가 아닌 노드로의 direct route 설치를 건너뜁니다. `autoDirectNodeRoutes`가 **필수**이며 없으면 agent가 종료됩니다. tunnel fallback이 아닙니다.

Helm guard: native routing에서 `enableIPv4Masquerade`가 true로 설정되어 있으면 다음 중 하나가 아닌 한 `helm template`이 "ipv4NativeRoutingCIDR must be set when routingMode is native"로 실패합니다. `ipam.mode`가 `eni` 또는 `alibabacloud`이거나, ip-masq-agent가 켜져 있거나, `nativeRoutingCIDRFromClusterPool: true`(1.20 신규, `ipam.mode=cluster-pool`이고 pool CIDR이 정확히 하나일 때). 차트의 `enableIPv4Masquerade` 기본값은 null(agent 자체 기본값은 true)이므로 값을 지정하지 않으면 agent는 masquerade를 하지만 이 guard는 **걸리지 않습니다**. IPv6 guard도 `ipv6.enabled`, `enableIPv6Masquerade`(차트 기본 true), `ipv6NativeRoutingCIDR`로 같은 방식입니다.

```yaml
# values: 단일 L2 세그먼트의 native routing
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16   # 모든 Pod CIDR을 포함해야 함
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
```

Native-routing CIDR 의미: 이 안의 목적지는 masquerade하지 않고 스택으로 넘깁니다. 설정하지 않으면 기본값은 로컬 노드의 PodCIDR입니다. ENI/Azure/AlibabaCloud에서는 operator가 클라우드에서 유도하며(primary VPC CIDR만), 직접 값을 주면 VPC CIDR 중 하나에 포함되어야 하고 아니면 "None of the VPC CIDRs contains the specified native routing CIDR"로 agent가 실패합니다.

### AWS ENI datapath의 라우팅 방식

ENI IPAM에서 Pod IP는 ENI의 secondary IP 또는 prefix입니다. Agent는 endpoint별 route와, Pod IP마다 두 개의 ip rule을 설치합니다. ingress rule `to <podIP> lookup main`(priority 20, `RulePriorityIngress`)과 egress rule `from <podIP> lookup <ENI table>`(priority 111, `RulePriorityEgressv2`. 이전 priority 110은 Azure IPAM 모드에서만 씁니다)입니다. egress rule의 `to <VPC CIDR>` 조건(VPC CIDR마다 rule 하나)은 masquerade가 켜져 있을 때만 붙고, ENI는 masquerade가 기본 꺼져 있으므로 기본 상태의 egress rule에는 `to` 조건이 없습니다. ENI table의 default route는 ENI 서브넷 라우터를 향합니다. 라우터 IP를 ENI 주소 공간에서 가져오므로 ICMP packet-too-big을 생성할 수 있습니다. 1.18부터 operator에 `ec2:DescribeRouteTables`가 필요합니다. 주소 할당은 [IPAM 심화](10-ipam-deep-dive.md)을 보세요.

## 7. 기동 시 검증: hard failure와 silent fallback

잘못된 조합 중 일부는 agent를 멈추고, 일부는 로그 한 줄만 남기고 약한 datapath로 계속 실행됩니다. 어느 쪽인지 알아 두면 시간을 아낍니다.

### Hard failure (agent 종료 또는 Helm 렌더 실패)

| 설정 | 결과 |
|---|---|
| `routingMode: tunnel` + `autoDirectNodeRoutes: true` | Fatal: "auto-direct-node-routes cannot be used with tunneling. Packets must be routed through the tunnel device." (1.20.2) |
| `ipam: eni` + tunnel | Fatal: "Cannot specify IPAM mode eni in tunnel mode." |
| `autoDirectNodeRoutes` 없이 `directRoutingSkipUnreachable` | Fatal |
| DSR 또는 hybrid + VXLAN tunnel | 오류: Node Port `dsr` mode cannot be used with `vxlan` tunneling |
| Tunnel + DSR/hybrid인데 `dsrDispatch: geneve` 아님 | 오류: `geneve` dispatch 필요 |
| `tunnelProtocol: geneve` 없이 `dsrDispatch: geneve` | 오류: Geneve tunnel protocol 필요 |
| XDP 가속 + IPv6 underlay | 오류 |
| Native routing + `enableIPv4Masquerade`가 true로 설정됐는데 native CIDR도 예외도 없음 | Helm template 실패(값 미지정, 차트 기본 null이면 실패하지 않음) |
| 조건 미충족 상태의 명시적 `bpf.datapathMode: netkit` | hard fail(11절) |
| 커널 5.18 `skb_set_tstamp` 없는 BBR, 또는 BPF host routing 없는 Pod용 BBR | agent 오류(13절) |
| BPF host routing/KPR/BPF masquerade 없는 BIG TCP, IPsec 또는 DSR IPIP과 함께 쓴 BIG TCP | 기동 오류 |
| BPF masquerade 없는 `enable-remote-node-masquerade` | 오류 |
| BPF masquerade 없는 `ip-masq-agent` | 오류 |

VXLAN과 서비스별 annotation 모드(`bpf.lbModeAnnotation=true`)를 함께 쓰면 validator는 `dsrDispatch: ipip`만 허용하며 전역 모드는 `snat`이어야 합니다.

**[1.21 pre-release]** `autoDirectNodeRoutes` 메시지는 "auto-direct-node-routes requires native routing mode."로 바뀝니다. 조건은 여전히 "tunneling 사용 중"입니다.

### Silent fallback (agent 실행, 약한 datapath)

| 설정 | 동작 |
|---|---|
| BPF host routing(기본)인데 iptables masquerade 또는 KPR off | "BPF host routing requires bpf-masquerade / kube-proxy-replacement ... Falling back to legacy host routing" 로그 후 legacy routing 사용 |
| `bpf.datapathMode: auto`인데 netkit 조건 미충족 | "datapath autodiscovery failed, reverting from netkit to veth" 로그 후 veth 사용 |
| Bandwidth manager + IPsec | 경고와 함께 manager 비활성화 |
| 미지원 커널의 BIG TCP | 경고 후 비활성화 |
| 필요한 BPF helper가 없는 커널에서 multicast 활성화 | "Disabled support for BPF Multicast" 로그 후 off 유지 |
| CNI chaining | 차트가 legacy host routing을 강제하고 no-conntrack iptables 규칙을 끔 |

코드의 의도적 비대칭입니다. host routing과 `auto`는 "best effort"이고, 이름으로 요청한 기능(netkit, BBR, BIG TCP)은 제공할 수 없으면 실패합니다. 변경 후에는 값만 믿지 말고 17절 명령으로 실제 적용 상태를 확인하세요.

## 8. MTU 계산

**감지.** 기준 MTU는 Cilium이 선택한 native 장치의 MTU 최솟값이며 `cilium_vxlan`, `cilium_geneve`, IPIP 장치, dummy 장치는 제외합니다. `MTU: 0`(기본)은 "감지"입니다. 0이 아닌 Helm `MTU`는 최종 Pod MTU가 아니라 **underlying network MTU**입니다. CNI 설정의 MTU도 우선합니다. 로컬 감지가 경로 전체의 최소 MTU를 보장하지는 않습니다.

**Pod 장치 MTU와 route MTU.** Pod의 veth/netkit 장치 MTU는 기준 MTU이고, Pod 안의 route MTU는 기준에서 overhead를 뺀 값입니다. 그래서 Pod의 `ip link`는 1500인데 `ip route`는 `mtu 1450`일 수 있습니다.

`pkg/mtu/mtu.go`(v1.20.2)의 overhead:

| 구성 요소 | 바이트 | 구성 |
|---|---|---|
| Tunnel, IPv4 underlay | 50 | IP 20 + UDP 8 + VXLAN 8 + inner Ethernet 14 |
| Tunnel, IPv6 underlay | 70 | IP 40 + 8 + 8 + 14 |
| IPsec (128비트 GCM, 기본 키 크기) | 77 | 키 크기에 따라 조정 |
| WireGuard | 95 | 상수 |
| Geneve DSR 옵션 | 12 | datapath에서 적용, route MTU에는 미포함 |

| 시나리오 (underlay 1500) | Pod의 route MTU | 계산 |
|---|---|---|
| Native, 암호화 없음 | 1500 | 기준값 |
| Tunnel VXLAN, IPv4 underlay | 1450 | 1500 - 50 |
| Tunnel VXLAN, IPv6 underlay | 1430 | 1500 - 70 |
| Native + WireGuard | 1405 | 1500 - 95 |
| Native + IPsec | 1423 | 1500 - 77 |
| Tunnel + IPsec | 1373 | 1500 - (50 + 77) |
| Tunnel + WireGuard | 1355 | 1500 - (95 + 50) |

표의 값은 상수와 `getRouteMTU` 함수로 계산한 것이며 클러스터에서 측정한 값이 아닙니다. Jumbo frame에서는 절대 overhead가 같아 비율이 훨씬 작습니다(underlay 9001에 IPv4 VXLAN이면 8951).

참고:

- **Geneve DSR**은 12바이트 옵션을 추가합니다. 옵션은 로드밸런싱 노드가 삽입하므로 큰 패킷이 경로 MTU를 넘을 수 있습니다. TCP에만 DSR을 쓰는 hybrid 모드(SYN에만 서비스 주소 인코딩, UDP는 SNAT)는 이를 줄이는 이유 중 하나입니다.
- **`pmtuDiscovery.enabled`**(기본 false)는 클라이언트에 ICMP fragmentation-needed를 보냅니다. `pmtuDiscovery.packetizationLayerPMTUDMode`(1.19 신규, 값 `always|blackhole|disabled|unset`, 기본 `blackhole`)는 Pod netns의 커널 RFC 4821 probing을 제어합니다. MTU를 알고 있으면 `disabled`로 두세요.
- **CNI chaining**: `cni.enableRouteMTUForCNIChaining: true`는 route MTU를 chained plugin의 Pod에 전달합니다(예: aws-cni 위 WireGuard).
- **IPv4/IPv6 fragment**는 기본으로 추적됩니다(`enable-ipv4-fragment-tracking`, `enable-ipv6-fragment-tracking`, map 크기 `bpf-fragments-map-max` 기본 8192, upstream에서 beta). [L2/L7 네트워킹](05-l2-l7-networking.md) 참고.
- AWS의 **XDP**는 ENA native XDP가 허용하는 낮은 MTU가 필요합니다(upstream 예시는 3498). Jumbo frame 노드는 MTU를 낮추지 않으면 쓸 수 없습니다.

Pod에서 `kubectl exec <pod> -- ip route`, `ip link`로 확인하고 `ping -M do -s <크기>`로 양방향을 시험합니다.

## 9. Masquerading

Masquerading은 클러스터를 떠나는 Pod 트래픽의 출발지를 노드 IP로 바꿉니다. 구현은 두 가지입니다.

| | iptables(기본) | BPF(`bpf.masquerade: true`) |
|---|---|---|
| 필요 | iptables/ipset 모듈 | KPR(BPF NodePort), 장치 감지 |
| 범위 | `egressMasqueradeInterfaces`로 제한하지 않으면 non-Cilium 장치로 나가는 모든 트래픽 | 장치 감지 또는 `devices`가 고른 장치, CIDR로 예외 지정 |
| Host routing | legacy host routing 강제(silent fallback) | BPF host routing과 호환 |
| 프로토콜 | netfilter가 처리하는 모두 | TCP, UDP, ICMP(echo, echo-reply, frag-needed). IPv4 production, IPv6 beta |
| 부가 기능 | `enableMasqueradeRouteSource` | ip-masq-agent, `enableRemoteNodeMasquerade` |
| 포트 범위 | 커널 | NodePort 최댓값+1 .. 65535(`bpf/lib/nat.h`), NAT table `bpf.natMax` 기본 524288 |

기본값: `enableIPv4Masquerade: true`이지만 `eni.enabled=true`이면 **false**입니다(1.18부터). `enableIPv6Masquerade: true`이며 **[1.21 pre-release]**에서는 "ENI IPAM이 아니면 true"가 됩니다. `egressMasqueradeInterfaces`는 iptables masquerade에만 영향을 주므로 masquerade가 꺼진 ENI 프로필에서는 아무 효과가 없습니다.

### BPF masquerade 결정 순서

`bpf/lib/nat.h`(v1.20.2)에서 egress 패킷마다 이 순서로 평가합니다.

1. Egress Gateway 정책 일치: gateway IP로 SNAT.
2. 목적지가 SNAT 제외 CIDR(native-routing CIDR, 없으면 로컬 PodCIDR)에 속함: masquerade 안 함.
3. 로컬 endpoint에 `SKIP_MASQ` flag(multi-pool IPAM): masquerade 안 함.
4. 목적지가 `cilium_ipmasq_v4`(ip-masq-agent, LPM)에 있음: masquerade 안 함.
5. 목적지가 **원격 노드** identity:
   - `enable-remote-node-masquerade=true`: SNAT.
   - 아니고 native routing: masquerade 안 함.
   - 아니고 tunnel 모드: ipcache 항목에 `skip_tunnel`이 없으면 SNAT.
6. 출발지가 로컬 endpoint: egress 장치의 노드 주소로 SNAT, 아니면 통과.

결과 두 가지. 첫째, Pod에서 원격 노드로 가는 트래픽은 native routing에서 Pod IP를 유지하지만 tunnel 모드에서는 masquerade됩니다. 호스트 방화벽과 노드 수준 정책이 보는 출발지가 달라집니다. 둘째, upstream masquerading 문서는 5번을 느슨하게 표현("다른 클러스터 노드로 가는 패킷" 제외)합니다. 위 표는 BPF 코드를 기준으로 했습니다.

`enable-remote-node-masquerade`(1.19 신규)는 1.20.2에 전용 Helm key가 없습니다. `extraConfig: {enable-remote-node-masquerade: "true"}`로 설정합니다. BPF masquerade가 필요하고, 출발지가 노드 주소가 되어 host-firewall ingress 집행을 약화합니다.

### ip-masq-agent

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
    masqLinkLocal: false
```

차트는 릴리스 네임스페이스에 `config` key(JSON)를 가진 `ip-masq-agent` ConfigMap을 렌더링하고, agent가 마운트된 파일을 fsnotify로 감시합니다. 설정이 비어 있으면 내장 non-masquerade CIDR이 적용됩니다: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24, 240.0.0.0/4, 그리고 `masqLinkLocal`이 아니면 169.254.0.0/16, `masqLinkLocalIPv6`가 아니면 fe80::/10. `cilium_ipmasq_v4/v6` map은 각각 16384개 항목입니다. ip-masq-agent를 켜면 native-routing CIDR이 필수가 아닙니다.

확인: `cilium-dbg status | grep Masquerading`(예: `BPF (ip-masq-agent) [eth0] <cidr> [IPv4: Enabled, IPv6: Disabled]`)과 `cilium-dbg bpf ipmasq list`.

알려진 한계: BPF masquerade는 Pod에서 노드 External IP로 가는 트래픽을 masquerade하지 않습니다(upstream 이슈 17177). **[1.21 pre-release]** `nodePort.extendedNATPortRange`(`--node-port-nat-range-ext`)가 SNAT 포트 범위를 확장합니다.

기동 시 강제되는 비호환: `--masquerade-interfaces` 방식의 장치 선택과 `enable-masquerade-to-route-source`는 BPF masquerade와 함께 쓸 수 없습니다.

## 10. Host routing: legacy와 BPF

| | Legacy host routing | BPF host routing |
|---|---|---|
| 설정 | `bpf.hostLegacyRouting: true` | 전제 조건이 충족되면 기본 |
| 경로 | Pod -> veth -> 호스트 netfilter/routing -> NIC | Pod -> BPF FIB 조회 -> NIC, Pod netns로 `redirect_peer` |
| netfilter/iptables | 경로에 포함 | 우회 |
| 필요 | 특별한 것 없음 | KPR true + BPF masquerade(아니면 silent fallback) |
| 요구하는 기능 | 해당 없음 | netkit, Pod용 BBR, BIG TCP, FIB table annotation 기반 동적 egress routing |

BPF host routing은 netfilter와 상위 스택을 건너뛰므로 호스트 netns의 netfilter에 의존하는 기능은 깨집니다. 알려진 비호환은 Istio sidecar redirect(upstream 이슈 36022)와 GKE Workload Identity 같은 netfilter 의존 기능입니다. 우회책은 `bpf.hostLegacyRouting: true` 또는 Local Redirect Policy입니다. 1.19부터는 KPR과 BPF masquerade가 켜져 있으면 IPsec에서도 자동으로 쓸 수 있으며, 커널에 CVE-2025-37959 수정이 있어야 합니다.

Legacy 모드에서는 `installNoConntrackIptablesRules: true`(native routing, IPv4, socket-LB 포함 KPR, BPF masquerade)로 conntrack 비용을 줄일 수 있습니다. 차트는 eni, azure, gke, CNI chaining에서 이를 끕니다.

`cilium-dbg status`의 `Routing:` 줄에서 `Host:` 필드(`Host: BPF` 또는 `Host: Legacy`)로 확인합니다. Cilium 1.20.2는 별도의 "Host Routing" 줄을 출력하지 않습니다.

## 11. Datapath 장치: veth와 netkit

`bpf.datapathMode`는 `veth`(기본), `netkit`, `netkit-l2`, 그리고 1.20에서 추가된 `auto`를 받습니다.

- `netkit`(L3 모드, ARP 없음, upstream 권장 변형)과 `netkit-l2`는 peer 내부에 BPF를 attach하고 tcx를 쓰며 BIG TCP를 지원합니다. 1.20.2에서 **beta**이고, 문서상 커널 6.8+(`CONFIG_NETKIT`)이며 코드 주석은 6.7+라고 합니다. 문서를 하한으로, runtime probe를 최종 판단으로 취급하세요.
- 전제 조건(`canUseNetkit`): netkit probe 통과, `bpf.hostLegacyRouting` 없음, BPF masquerade 활성(iptables 아님), `kubeProxyReplacement: true`, `bpf.tproxy` 없음(1.19부터 비호환), `enableEndpointRoutes`를 쓰면 드라이버가 scrub 속성을 지원해야 함(커널 6.13 또는 backport).
- 조건이 안 맞는 명시적 `netkit`/`netkit-l2`는 **hard fail**이고, `auto`는 경고와 함께 veth로 내려갑니다. `cilium-dbg status`에는 "Device Mode: netkit [Configured: auto]" 형태로 설정된 모드와 실제 모드가 구분되어 표시됩니다.
- 노드에 이미 veth Pod가 있으면 전환(`auto` 포함)이 오류를 냅니다. `CiliumNodeConfig`로 노드별 설정을 쓰거나 노드를 drain하세요.

```yaml
# values: 안전한 netkit 탐색
bpf:
  datapathMode: auto
  masquerade: true
kubeProxyReplacement: true
routingMode: native
```

`cilium-dbg status | grep -E "Device Mode|Routing|Attach Mode"`로 확인합니다(host routing은 `Routing:` 줄의 `Host: BPF|Legacy`로 표시). Upstream은 커널이 보편화되면 veth를 deprecate할 수 있고 기본값이 바뀔 수 있다고 밝히므로 현재 기본값이 영구적이라고 가정하지 마세요.

## 12. Datapath 안의 서비스 로드밸런싱

5절의 Pod 간 경로에서 각 서비스 기능이 놓이는 위치:

```text
 클라이언트 Pod -> connect()  --[socket-LB: cgroup connect4/sendmsg/recvmsg hook]--> backend IP:port 선택
                |                                         (E/W, ClusterIP. 패킷이 생기기 전)
                v
 Pod에서 패킷 송출 -> bpf_lxc (socket-LB가 변환하지 않았다면 lb4_local)
                |
 외부 클라이언트 -> NIC -> [XDP, 선택: 드라이버 수준 LB] -> bpf_host (from-netdev)
                       -> NodePort/LB 조회 -> backend 선택: random 또는 Maglev
                       -> 전달 모드: SNAT, DSR(opt/ipip/geneve) 또는 hybrid
                       -> backend가 로컬이면 전달, 원격이면 native route / tunnel(+DSR용 Geneve 옵션)
```

**kube-proxy replacement(KPR).** boolean입니다. `kubeProxyReplacement: true|false`(strict/partial은 폐지). `true`는 socket-LB를 강제로 켭니다. API ClusterIP를 해석할 kube-proxy가 없으므로 `k8sServiceHost`/`k8sServicePort`를 설정하세요. ClusterIP, NodePort, LoadBalancer, externalIPs, hostPort를 다루며 tunnel과 native 모두에서 동작합니다. KPR=false여도 패킷별 ClusterIP 로드밸런싱은 수행합니다. 1.19에서 제거: `--enable-node-port`, `--enable-host-port`, `--enable-external-ips`. 1.20에서 제거: `--node-port-mode`, `--node-port-algorithm`(`loadBalancer.mode`/`loadBalancer.algorithm` 사용).

**Socket-LB.** `socketLB.enabled`(KPR이면 켜짐), hook은 `connect`/`sendmsg`/`recvmsg`/`getpeername`. `socketLB.hostNamespaceOnly: true`는 호스트 네임스페이스로 제한하며 Istio sidecar, KubeVirt, Kata, gVisor에 필요합니다(`gatewayAPI.enabled`이면 강제). `socketLB.terminatePodConnections`(기본 true)는 커널 `CONFIG_INET_DIAG*`가 필요합니다. **1.20 동작 변경**: socket-LB가 꺼져 있거나 `hostNamespaceOnly=true`이면 Pod에서 NodePort로 가는 연결이 클라이언트 Pod의 egress에서 DNAT되므로, egress NetworkPolicy가 NodePort뿐 아니라 backend도 허용해야 합니다.

**알고리즘.** `loadBalancer.algorithm: random|maglev`. Maglev는 서비스별 lookup table을 map-in-map `cilium_lb4_maglev` / `cilium_lb6_maglev`에 만들고 5-tuple(ClientIP affinity이면 출발지 포트를 0으로)의 해시를 table 크기로 나눈 나머지를 씁니다. North/south 트래픽에만 적용되고 socket-LB를 쓰는 east/west는 Maglev를 우회합니다. `maglev.tableSize`는 251, 509, 1021, 2039, 4093, 8191, 16381, 32749, 65521, 131071 중 하나(기본 16381, 서비스당 backend 약 160개 기준)이고 `maglev.hashSeed`는 모든 agent에서 같아야 합니다.

```bash
SEED=$(head -c12 /dev/urandom | base64 -w0)   # 한 번만 생성해 values/secret 저장소에 보관
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set kubeProxyReplacement=true \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set maglev.hashSeed=$SEED
```

서비스별 override: `bpf.lbAlgorithmAnnotation=true`와 annotation `service.cilium.io/lb-algorithm: maglev`(생성 시점에만). 1.20 신규: EndpointSlice annotation `service.cilium.io/weight`(0-65535, Maglev 전용, 0은 유지보수).

**전달 모드.** `loadBalancer.mode: snat|dsr|hybrid`.

- `snat`: 요청을 받은 노드가 출발지를 바꾸므로 응답이 그 노드를 거칩니다.
- `dsr`: backend가 클라이언트에 직접 응답하며 서비스 IP/포트를 backend로 전달합니다. `hybrid`는 TCP에 DSR(SYN에만 서비스 주소 인코딩), UDP에 SNAT을 씁니다.
- Dispatch(`loadBalancer.dsrDispatch`, 기본 `opt`)는 전달 방법입니다.

| `dsrDispatch` | Native routing | Tunnel (Geneve) | Tunnel (VXLAN) |
|---|---|---|---|
| `opt` (IP option / IPv6 destination option) | 가능 | 불가 | 불가 |
| `geneve` | 가능(Geneve 장치 생성) | 가능 | 불가(VXLAN은 DSR 불가) |
| `ipip` (1.20에서 문서화) | 가능 | 불가 | annotation 모드의 validator 예외, 문서화된 동작 구성 아님 |

IPIP는 `cilium_ipip4/6`을 만들고, 서비스 포트와 target 포트가 같아야 하며, 선택적 RSS 출발지 CIDR(`--bpf-lb-rss-ipv4-src-cidr`)을 지원하고, BIG TCP와 비호환입니다. 클라우드 fabric은 IP option 패킷(`opt`)을 drop할 수 있으므로 거기서는 `geneve` 또는 `ipip`를 권합니다. AWS에서 DSR은 EC2 source/destination check를 꺼야 합니다. 따라서 tunnel 모드 DSR은 `tunnelProtocol: geneve`와 `dsrDispatch: geneve`가 필요합니다.

```yaml
# values: tunnel 모드, kube-proxy-free, Geneve DSR
routingMode: tunnel
tunnelProtocol: geneve
kubeProxyReplacement: true
k8sServiceHost: <API_SERVER_FQDN>      # 스킴 없이 호스트만
k8sServicePort: 443
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

Annotation 모드: `bpf.lbModeAnnotation=true`이면 Service마다 `service.cilium.io/forwarding-mode: dsr|snat`를 쓸 수 있으며 `loadBalancer.dsrDispatch`를 명시해야 합니다. EKS에서 annotation을 단 LoadBalancer Service는 반드시 internal(`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`)이어야 하며, 외부 공개는 CloudFront와 VPC origin을 통해서만 합니다.

**XDP 가속.** `loadBalancer.acceleration: disabled|native|best-effort`. 선택된 모든 장치에 native-XDP 드라이버가 필요하고(아니면 `best-effort`), direct-routing 장치만 가속되며, IPv6 underlay와 비호환이고, L2 neighbor discovery를 자동으로 켭니다. XDP에서 되돌려 보낸 패킷은 `tcpdump`에 보이지 않습니다. XDP로 가속된 N/S 트래픽과 Geneve 외 DSR은 WireGuard로 암호화되지 않습니다.

**알아 둘 known issue:** reverse socket map 고갈, socket-LB의 NFS/SMB 커널 패치, backend 종료 경합(`preStop` sleep 추가), TCP Fast Open이 DSR을 깨는 문제, 다중 장치 DSR의 rp_filter 경고. 비교표는 [L2/L7 네트워킹](05-l2-l7-networking.md)을 참고하세요.

## 13. Bandwidth manager, BBR, BIG TCP

**Bandwidth manager.** `bandwidthManager.enabled`(기본 false), `bandwidthManager.bbr`, `bandwidthManager.bbrHostNamespaceOnly`. Annotation `kubernetes.io/egress-bandwidth`(FQ를 쓰는 EDT, Pod의 호스트 쪽 장치와 tunnel 장치 egress에서 적용)와 `kubernetes.io/ingress-bandwidth`(BPF token bucket). 값은 **비트** 단위 Kubernetes quantity입니다. `"10M"`은 10 Mbit/s이지 10 MB/s가 아닙니다. Pod 단위이며 replica 그룹 단위가 아닙니다.

부작용: 호스트 sysctl `net.core.default_qdisc=fq`와 `net.ipv4.tcp_congestion_control`(`cubic` 또는 `bbr`)을 설정하고, `netdev_max_backlog`(>= 1000), `somaxconn`, `tcp_max_syn_backlog`(>= 4096) 하한을 올리며, 외부 장치에 FQ를 설치합니다. 전제 조건: BBR은 커널 5.18, Pod용 BBR은 BPF host routing(없으면 오류, `bbrHostNamespaceOnly` 제외), IPsec에서는 manager가 조용히 비활성화됩니다. 기존 Pod는 이전 congestion control을 유지하고 BBR은 새 Pod에 적용됩니다.

확인: `cilium-dbg status | grep BandwidthManager`(예: `EDT with BPF [BBR] [eth0]`), `cilium-dbg bpf bandwidth list`.

**BIG TCP.** `enableIPv4BIGTCP`, `enableIPv6BIGTCP`(둘 다 false). 커널은 IPv6 5.19+, IPv4 6.3+이며 upstream이 열거하는 NIC 드라이버는 mlx4, mlx5, ice입니다. BPF host routing, KPR, BPF masquerade가 필요하고 IPsec, DSR IPIP과는 비호환입니다. MTU 변경 없이 gso/gro 최대 크기를 192 KB로 올리며, 토글 후 Pod를 재시작해야 합니다. Upstream 문구는 "tunneling disabled"이지만 코드는 UDP-tunnel BIG TCP 커널 probe가 통과할 때만 VXLAN/Geneve에서도 허용하고, 아니면 "BIG TCP in tunneling mode requires pending kernel support"로 실패합니다. 실무 조언은 native routing입니다.

**Upstream 권장 성능 프로필**(in-place 업그레이드가 아님, 노드별 설정 사용):

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set routingMode=native \
  --set bpf.datapathMode=netkit \
  --set bpf.masquerade=true \
  --set bpf.distributedLRU.enabled=true \
  --set bpf.mapDynamicSizeRatio=0.08 \
  --set ipv6.enabled=true --set enableIPv6BIGTCP=true \
  --set ipv4.enabled=true --set enableIPv4BIGTCP=true \
  --set kubeProxyReplacement=true \
  --set bpfClockProbe=true
```

bandwidth manager가 필요하면 `bandwidthManager.enabled=true`와 `bandwidthManager.bbr=true`를 추가합니다. 7절과 연결하면, 이 프로필의 netkit과 BIG TCP는 BPF host routing이 필요하므로 KPR과 BPF masquerade가 있어야만 동작합니다.

## 14. 암호화와의 상호작용

여기서는 datapath 영향만 다룹니다. 키 관리는 [12장](12-mtls-encryption-identity.md)을 보세요.

| | WireGuard | IPsec |
|---|---|---|
| 전송 | UDP 51871 | ESP(IP 프로토콜 50) |
| Tunnel 모드 | 이중 캡슐화: VXLAN/Geneve 후 WireGuard | 오버레이 캡슐화 **이후** 암호화(1.18부터 항상) |
| Route MTU @1500 | tunnel 1355, native 1405 | tunnel 1373, native 1423 |
| Strict mode | `encryption.strictMode.ingress.enabled`(1.19+)는 WireGuard 필요(IPsec 불가), tunnel과 native routing 모두 지원. `strictMode.egress.allowRemoteNodeIdentities`는 egress 옵션으로, tunneling을 쓰거나 direct routing에서 노드 CIDR과 Pod CIDR이 겹칠 때 필요. `strictMode.egress.*`가 이전 key를 대체했고 이전 key는 1.20에서 제거 | 해당 없음 |
| Bandwidth manager | 동작 | 조용히 비활성화 |
| BIG TCP | 주의사항과 함께 동작 | 기동 오류 |
| Chaining | 암호화 미지원 | 암호화 미지원 |

그 외: IPsec `encryptedOverlay`는 1.18부터 no-op였고 1.20에서 제거되었습니다. IPsec은 direct-routing 구성에서 `ipv4NativeRoutingCIDR`이 필요하고 노드 65535 미만을 지원하며 tunnel당 단일 코어로 복호화합니다. XDP로 가속된 N/S 트래픽이나 Geneve 외 DSR은 WireGuard가 보호하지 않지만 Geneve DSR은 보호됩니다.

캡처할 때 순서를 기억하세요. NIC에서는 VXLAN/Geneve가 아니라 UDP 51871 또는 ESP가 보이고, Pod의 호스트 쪽 장치에서는 평문이 보입니다. 암호화나 캡슐화가 없다고 결론 내리기 전에 두 지점 모두에서 캡처하세요.

## 15. VTEP와 multicast (beta)

**VTEP 연동**은 Pod가 외부 VXLAN endpoint(예: 하드웨어 VTEP)와 통신하게 합니다.

- Helm: `vtep.enabled`, `vtep.endpoint`, `vtep.cidr`, `vtep.mask`, `vtep.mac`. `vtep.endpoint`, `vtep.cidr`, `vtep.mac`은 길이가 같은 공백 구분 목록(VTEP당 항목 하나)이고, `vtep.mask`는 모든 CIDR에 쓰이는 단일 mask입니다.
- 제한: VTEP 최대 8개, IPv4 전용, 동기화 간격 `--vtep-sync-interval`(1m), IPsec과 병용 불가, VTEP 장치 MTU는 1500 - 50으로 하드코딩.
- VTEP 장치는 **VNI 2**(`world`)를 써야 합니다. BPF는 VTEP 출발지 주소에서 온 overlay 패킷이 world가 아닌 identity를 가지면 drop합니다(`DROP_INVALID_VNI`). Egress에서는 `bpf_lxc`가 `cilium_vtep_map`을 조회해 목적지 identity `world`로 캡슐화합니다.
- `cilium-dbg bpf vtep list`로 확인합니다. Geneve에서 VTEP가 동작하는지는 문서화/검증되지 않았고, 문서화된 구성은 VXLAN tunnel 모드입니다.

**Multicast.**

- `cilium config set multicast-enabled true` 또는 `extraConfig: {multicast-enabled: "true"}`로 켭니다. 1.20.2에는 전용 Helm 값이 없습니다.
- 문서는 VXLAN 모드와 amd64 커널 5.10+ 또는 arm64 6.0+를 요구합니다. 코드는 추가로 `bpf_for_each_map_elem` helper(Linux 5.13+)를 probe하며 없으면 "Disabled support for BPF Multicast" 로그를 남기고 꺼진 상태로 유지됩니다. 5.10-5.12에서 어느 규칙이 우선하는지는 여기서 검증하지 못했습니다.
- IPv4 전용, `bpf_lxc`에서 IGMP v2/v3 처리, 한도 1024 그룹 x 1024 구독자, IPsec 비호환, 모든 노드에 설정 필요(`cilium-dbg bpf multicast group add <group>`과 `... subscriber add <group> <원격 CiliumInternalIP>`, 또는 upstream `multicast.rst`에 나온 `cilium multicast add --group-ip`로 클러스터 전체. 이 CLI 명령은 cilium-cli 소스로 확인하지 않았습니다).

## 16. EKS 선택 가이드

| 옵션 | 설정 | 선택 기준 | 주의 |
|---|---|---|---|
| **Cilium ENI IPAM**(VPC CNI 대체) | `eni.enabled=true`, `ipam.mode=eni`, `routingMode: native`(ENI 시 기본), IRSA/Pod Identity로 operator 권한, taint `node.cilium.io/agent-not-ready=true:NoExecute` | Pod가 VPC 라우팅 가능한 IP를 가져야 하고, VPC 내 SNAT이 없어야 하며, Pod IP 기준 SG/flow log가 필요할 때 | ENI와 tunnel 병용 금지. IPv4 masquerade 기본 off(1.18+). Pod 밀도는 ENI/IP 용량에 제한. operator에 `ec2:DescribeRouteTables` 필요. AWS 지원은 EC2 노드의 VPC CNI에 한정 |
| **EKS의 Overlay** | `ipam.mode=cluster-pool`, `routingMode: tunnel`, `eni.enabled=false` | VPC의 Pod IP 공간이 부족하거나 tunnel 기능이 필요할 때 | Pod IP가 VPC 라우팅 대상이 아니므로 관리형 control plane이 Pod에 도달하지 못함: **webhook backend(admission, conversion)는 `hostNetwork`를 써야 함**. 노드 SG는 UDP 8472(또는 6081) 자기 참조. MTU 1450(underlay 9001이면 8951) |
| **VPC CNI chaining** | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | VPC CNI의 IPAM/ENI를 유지하고 Cilium 정책, LB, Hubble을 추가 | 차트가 legacy host routing 강제, no-conntrack iptables 비활성. IPsec/WireGuard 불가, L7 제한, aws-node 1.11.2 이상, 활성화 후 Pod 재시작 |
| **EKS Auto Mode / Fargate** | 해당 없음 | 해당 없음 | 대체 CNI 미지원 |
| **EKS Hybrid Nodes** | Cilium이 지원되는 CNI | 온프레미스 노드 | webhook을 위해 Pod CIDR이 라우팅 가능해야 함. 이 저장소의 EKS Hybrid Nodes 절 참고 |

Overlay의 webhook 관련 서술은 AWS hybrid-nodes 안내(webhook을 위해 Pod CIDR이 라우팅 가능해야 함)와 Kubernetes control plane의 webhook 호출 방식에서 유도한 것입니다. 의존하기 전에 실습 5로 검증하세요.

Cilium ENI 프로필(masquerade가 꺼져 있으면 효과가 없는 `egressMasqueradeInterfaces` key는 의도적으로 뺐습니다):

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
# enableIPv4Masquerade: true   # NAT gateway 없이 Pod가 VPC 밖으로 나가야 할 때만
```

VPC CNI chaining:

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native
```

EKS 참고:

- Cilium을 CNI로 설치하기 전에 `aws-node` DaemonSet을 삭제하세요(aws-node가 routing table을 flush). 아니면 설치 후 Pod를 재시작합니다.
- 보조 VPC CIDR(예: 100.64.0.0/16): 자동 감지되는 native-routing CIDR은 **primary** VPC CIDR뿐입니다. masquerade가 켜져 있고 Pod가 보조 대역에 있으면 `ipv4NativeRoutingCIDR`을 포함 범위로 설정하고 `cilium-dbg status | grep Masquerading`을 확인하세요. 코드에서 유도했고 테스트하지 않았습니다.
- ENI IPv6: `eni.rst`는 노드당 /80 prefix와 dual-stack 서브넷을 문서화하지만 EKS 요구사항 페이지는 아직 IPv4 전용이라고 합니다. Upstream에서 정리되지 않은 상태로 보고 해당 리전에서 직접 확인하세요.
- Source/destination check: DSR에서는 끄도록 문서화되어 있습니다. 비 ENI EC2의 native routing도 원리상 같은 제약(Pod IP를 인스턴스가 소유하지 않음)이지만 이 부분은 추론입니다.
- 공개 경로 정책: 워크로드에는 CloudFront만 도달하며, CloudFront VPC origin 뒤의 internal ALB/NLB를 거칩니다. 이 장의 Cilium 예시는 public listener나 `0.0.0.0/0` 규칙이 필요하지 않습니다.

## 17. 점검 치트시트

```bash
# 실제 적용된 routing, device, host-routing, masquerade, KPR, bandwidth, BIG TCP, XDP
kubectl -n kube-system exec ds/cilium -c cilium-agent -- \
  cilium-dbg status --verbose | grep -E "Routing|Device Mode|Masquerading|KubeProxyReplacement|BandwidthManager|BIG TCP|XDP"

# Tunnel 장치 (포트, metadata 기반)
ip -d link show cilium_vxlan        # 또는 cilium_geneve
ip route | grep cilium_host         # 원격 PodCIDR route (tunnel 모드)

# Tunnel endpoint와 node ID (옛 tunnel map이 아니라 ipcache)
cilium-dbg bpf ipcache list | grep -i <원격-노드-ip>
cilium-dbg bpf nodeid list
cilium-dbg node list

# VNI와 비교할 identity 번호
cilium-dbg endpoint list
cilium-dbg identity list

# NAT와 masquerade
cilium-dbg bpf nat list
cilium-dbg bpf ipmasq list

# 서비스
cilium-dbg service list
cilium-dbg bpf lb list
cilium-dbg bpf lb maglev list
cilium-dbg bpf socknat list

# Bandwidth, VTEP
cilium-dbg bpf bandwidth list
cilium-dbg bpf vtep list

# Datapath 이벤트
cilium-dbg monitor -v --type trace      # to-overlay / from-overlay trace point
cilium-dbg monitor --type drop

# 노드에서의 wire 캡처 (kubectl을 실행하는 노트북이 아님)
sudo tcpdump -nni any -c 50 'udp port 8472'      # Geneve: 'udp port 6081'
sudo tcpdump -nni <nic> -vv 'udp port 8472'       # -vv가 VNI를 출력
```

`cilium-dbg status`는 `Network: Tunnel [vxlan]  Host: BPF`와 비슷한 `Routing:` 줄을 출력합니다. Map 출력의 열 배치는 버전마다 다를 수 있으므로 열 위치에 의존하는 스크립트를 작성하지 마세요.

## 18. 실습

일회용 클러스터(kind 또는 자기 참조 보안 그룹을 쓰는 2노드 EKS 테스트 클러스터)에서만 실행하세요. 모든 실습은 upstream 소스와 문서로 확인했으며 이번 검토에서 실제 클러스터에 실행하지는 않았습니다. 기대 결과는 캡처가 아니라 서술입니다.

### 실습 1: Overlay 해부와 VNI

**사전 조건:** 스케줄 가능한 Linux 노드 2개, `routingMode: tunnel`인 Cilium 1.20.2, 노드 shell 접근, 노드 간 UDP 8472 허용.

1. agent에서 `cilium-dbg status | grep Routing`: vxlan 프로토콜의 tunnel 네트워크가 나와야 합니다.
2. 노드에서 `ip -d link show cilium_vxlan`: flow-based(external) 속성과 목적지 포트 8472를 가진 vxlan 장치.
3. 노드 1에 서버 Pod, 노드 2에 클라이언트 Pod를 띄웁니다(nodeName 또는 anti-affinity). 클라이언트가 서버에 curl하는 동안 노드에서 `sudo tcpdump -nni <nic> -vv 'udp port 8472' -c 20`을 실행합니다.
4. 디코딩된 출력의 `vni`를 확인하고 노드 2의 `cilium-dbg endpoint list`에서 클라이언트 Pod의 identity와 비교합니다. 클라이언트에서 서버로 가는 패킷은 같고 응답은 서버의 identity여야 합니다.
5. `helm upgrade ... --set tunnelProtocol=geneve` 후 agent를 재시작하면 `cilium_vxlan`이 사라지고 `cilium_geneve`가 생기며 캡처 필터를 포트 6081로 바꿔야 합니다.

**정리/롤백:** `tunnelProtocol`을 `vxlan`으로 되돌리고 agent를 재시작합니다. 프로토콜 변경은 장치를 재생성하므로 그동안 노드 간 연결이 잠시 끊깁니다.

### 실습 2: tunnel 위 WireGuard의 MTU

**사전 조건:** 실습 1 클러스터, 노드 간 UDP 51871 허용(보안 그룹 자기 참조).

1. `encryption.enabled=true`, `encryption.type=wireguard`를 켜고 `MTU: 0`을 유지합니다.
2. Pod에서 `ip route`와 `ip link`를 실행합니다. 장치 MTU는 underlay 값, route MTU는 1500 underlay에서 1355(95 + 50 overhead)가 기대됩니다.
3. 한 Pod에서 `ping -M do -s 1327 <다른 pod ip>`와 `-s 1328`을 실행합니다. 첫 번째는 성공(1327 + 28 = 1355), 두 번째는 fragmentation-needed 계열 오류로 실패해야 합니다.
4. `cilium-dbg status | grep Encryption`이 WireGuard를 보고해야 합니다.

**정리:** 암호화를 끄고 agent를 재시작합니다. 새 Pod의 route MTU는 1450으로 돌아가며 기존 Pod는 재생성 전까지 MTU를 유지합니다.

### 실습 3: Masquerade 결정 트리

**사전 조건:** KPR on, `bpf.masquerade=true`, 관측된 출발지 IP를 기록하는 같은 VPC 내 테스트 echo 서버(노드 SG를 참조하는 보안 그룹으로만 접근 가능).

1. Pod에서 echo 서버로 요청합니다. echo 서버 IP가 native-routing CIDR과 ip-masq-agent 목록 밖이면 출발지는 노드 IP여야 합니다.
2. echo 서버 대역을 `nonMasqueradeCIDRs`에 넣어 `ipMasqAgent`를 켜고 agent를 재시작한 뒤 반복합니다. Pod IP가 유지되어야 합니다(VPC가 Pod IP로 응답을 돌려보낼 수 있어야 하며, overlay Pod IP라면 실패하는데 그것이 요점입니다).
3. `cilium-dbg bpf ipmasq list`가 CIDR을 보여주고 `cilium-dbg bpf nat list`가 활성 SNAT 항목을 보여줍니다.
4. Pod에서 원격 노드로: native 모드에서는 출발지가 Pod IP, tunnel 모드에서는 노드 IP입니다. `extraConfig: {enable-remote-node-masquerade: "true"}`를 설정하면 native 모드도 masquerade하는 것을 확인합니다.

**정리/롤백:** ip-masq-agent 블록과 extraConfig key를 제거합니다. Masquerade 모드 변경은 방화벽이 보는 출발지 주소를 바꾸므로 노드 단위로 롤백하세요.

### 실습 4: Maglev와 Geneve DSR을 쓰는 kube-proxy-free 서비스

**사전 조건:** kube-proxy 없이 설치된 클러스터, `routingMode: tunnel`, `tunnelProtocol: geneve`, KPR true, `loadBalancer.mode: dsr`, `dsrDispatch: geneve`, 12절의 `maglev` 설정, VPC 내 클라이언트 호스트, 접속하는 노드와 다른 노드에 backend가 있는 NodePort Service. 내부 네트워크 경로만 사용합니다.

1. 접속 노드에서 `iptables-save | grep KUBE-SVC`는 아무것도 반환하지 않아야 합니다.
2. `cilium-dbg bpf lb list`가 서비스를, `cilium-dbg bpf lb maglev list`가 lookup table을 보여줍니다.
3. Backend 노드 NIC에서 tcpdump: 요청은 DSR 옵션을 담은 Geneve(UDP 6081)로 도착하고, 응답은 서비스 IP를 출발지로 클라이언트에 직접 나갑니다.
4. `tunnelProtocol: vxlan`에 `loadBalancer.mode: dsr`를 설정하면 agent가 기동에 실패하는지 확인합니다(임시 클러스터에서 수행 후 되돌림).

**정리:** Helm 값을 되돌립니다. 운영 중 모드를 바꾸면 DSR 흐름이 끊깁니다.

### 실습 5: netkit/auto, host routing, EKS ENI

**사전 조건:** (a) 커널 6.8 이상 노드 하나와 그보다 오래된 노드 하나, (b) ENI 부분은 `aws-node` 없이 만든 임시 EKS 클러스터.

1. `bpf.datapathMode=auto`, `bpf.masquerade=true`, `kubeProxyReplacement=true`로 새 커널과 오래된 노드에서 `cilium-dbg status | grep -E "Device Mode|Routing"`을 비교합니다. `Device Mode`는 새 노드에서 netkit, 오래된 노드에서 fallback 로그와 함께 veth가 기대되며, `Routing:` 줄은 양쪽 모두 `Host: BPF`입니다. 이미 veth Pod가 있는 노드는 먼저 drain하세요.
2. `bpf.masquerade=false`로 두면 `Routing:` 줄이 `Host: Legacy`로 끝나고 agent 로그에 fallback이 기록됩니다. 되돌립니다.
3. Bandwidth manager를 켠 상태에서 Pod에 `kubernetes.io/egress-bandwidth: "10M"`을 적용하고 `cilium-dbg bpf bandwidth list`에 나타나는지 확인합니다.
4. ENI: 16절의 ENI 프로필로 설치합니다. `ip rule`에 Pod IP별로 ingress rule `to <podIP> lookup main`(priority 20)과 egress rule `from <podIP> lookup <ENI table>`(priority 111), 그리고 ENI별 route table이 보여야 합니다. ENI는 masquerade가 기본 꺼져 있으므로 masquerade를 켜지 않으면 egress rule에 `to <VPC CIDR>` 부분이 없습니다. 임시 클러스터에서 ENI와 `routingMode: tunnel`을 함께 지정하면 agent가 기동을 거부해야 합니다.
5. EKS의 overlay: overlay 클러스터에 일반 Pod를 backend로 하는 validating webhook을 배포해 API 서버가 도달하는지 관찰한 뒤 `hostNetwork`로 옮겨 봅니다.

**정리:** 테스트 워크로드를 제거하고 Helm 값을 되돌리며 임시 클러스터를 종료합니다. 워크로드가 있는 클러스터의 CNI 교체는 이 범위 밖이며 여기서 지원되는 in-place 마이그레이션이 아닙니다.

## 19. 버전별 변경 사항

| 주제 | 1.18 | 1.19 | 1.20 | 1.21-pre.3 |
|---|---|---|---|---|
| 커널 하한 | 5.10(RHEL 8.10은 4.18) | 동일 | 동일 | 동일 |
| `cilium_tunnel_map` | datapath에서 빠짐(agent가 남은 map을 unpin), CLI 제거됨 | Go 패키지 **제거**, tunnel endpoint는 ipcache value | 해당 없음 | 해당 없음 |
| `underlayProtocol`(IPv6 underlay) | **신규** | stable | 동일 | IPv6 overhead 계산이 tunneling flag를 사용 |
| ENI에서 `enableIPv4Masquerade` | 기본 **false** | 동일 | 동일 | 동일. IPv6 masquerade 기본은 ENI가 아니면 true |
| `bpf.datapathMode` | veth, netkit, netkit-l2 | tproxy는 netkit과 비호환 | **`auto`** 추가, status에 설정/실제 모드 구분 | 동일 |
| BPF host routing + IPsec | 해당 없음 | IPsec + KPR + BPF masquerade에서 자동(CVE-2025-37959 수정 필요) | 동일 | 동일 |
| `enable-remote-node-masquerade` | 해당 없음 | **신규** | 동일 | 동일 |
| `packetizationLayerPMTUDMode` | 해당 없음 | **신규**, 기본 `blackhole` | 동일 | 동일 |
| WireGuard strict mode | 이전 key | `strictMode.ingress` **신규** | 이전 `strictMode.enabled/cidr` key **제거** | 동일 |
| IPsec `encryptedOverlay` | no-op | deprecated | **제거** | 해당 없음 |
| DSR dispatch | `opt`/`ipip`/`geneve` flag 존재, IPIP는 문서 없음 | 동일 | IPIP 문서화, 서비스별 DSR/알고리즘 annotation, `bpf-lb-rss-*`, `service.cilium.io/weight` | 동일 |
| 제거된 flag | 해당 없음 | `--enable-node-port/host-port/external-ips` | `--node-port-mode`, `--node-port-algorithm` | 해당 없음 |
| Pod에서 NodePort로의 socket-LB | 해당 없음 | trace 형식 변경 | socketLB off 또는 `hostNamespaceOnly`이면 클라이언트 egress DNAT | 동일 |
| `nativeRoutingCIDRFromClusterPool`, `nodePort.enableDynamicSourceLookup` | 해당 없음 | 해당 없음 | **신규** | 동일 |
| `nodePort.extendedNATPortRange` | 해당 없음 | 해당 없음 | 해당 없음 | **신규 [1.21 pre-release]** |
| `l2NeighDiscovery.enabled` 기본값 | false(이전엔 true) | 동일 | 동일 | 동일 |
| autoDirectNodeRoutes + tunnel 메시지 | "cannot be used with tunneling" | 동일 | 동일 | "requires native routing mode" |

성숙도: stable: tunnel, native, BPF masquerade(IPv4), KPR, Maglev, DSR, XDP 가속, bandwidth manager, BBR, BIG TCP. Beta: netkit, IPv6 BPF masquerade, VTEP, multicast, fragment tracking. 제거됨: `cilium_tunnel_map`, `encryptedOverlay`, `--node-port-mode`.

## 20. 트러블슈팅

| 증상 | 가능한 원인 | 확인 / 조치 |
|---|---|---|
| 기동 시 "cannot be used with tunneling"으로 agent 종료 | tunnel + `autoDirectNodeRoutes` | native routing을 선택하거나 flag 제거 |
| "Cannot specify IPAM mode eni in tunnel mode"로 종료 | ENI IPAM + tunnel | `routingMode: native` 사용 |
| 노드 간 Pod 통신만 실패, 동일 노드는 정상 | UDP 8472/6081 차단, tunnel 포트 불일치, 노드 SG 자기 참조 누락 | 양쪽 노드에서 `tcpdump -nni <nic> 'udp port 8472'`, SG/NACL 점검, `Routing:` 줄 확인 |
| 큰 전송은 멈추고 작은 요청은 성공 | MTU black hole(tunnel overhead, ICMP 필터링) | Pod `ip route` MTU와 경로 MTU 비교, `ping -M do -s`, `pmtuDiscovery` 설정 검토 |
| native Pod의 외부 통신에서 출발지가 Pod IP이고 응답이 안 돌아옴 | Masquerade off(ENI 기본) 또는 native-routing CIDR 내 목적지 | `cilium-dbg status \| grep Masquerading`, 의도에 맞게 masquerade 또는 ip-masq-agent 활성화 |
| Pod에서 원격 노드로 갈 때 클러스터마다 출발지가 다름 | tunnel은 masquerade, native는 안 함(9절) | 의도적으로 결정, 일관성이 필요하면 `enable-remote-node-masquerade` |
| agent 로그에 "Falling back to legacy host routing" | iptables masquerade 또는 KPR off | `bpf.masquerade`와 KPR 활성화 또는 legacy 수용 |
| Istio sidecar 트래픽 우회/오동작 | Pod netns의 BPF host routing/socket-LB | `socketLB.hostNamespaceOnly=true` 또는 `bpf.hostLegacyRouting=true` |
| `bpf.datapathMode=netkit` 실패 | 커널 미지원, legacy routing, iptables masquerade, KPR off, tproxy | `auto`로 probe, 전제 조건 충족 |
| agent가 DSR을 거부 | VXLAN tunnel, Geneve dispatch 누락 | `tunnelProtocol: geneve`와 `dsrDispatch: geneve` 사용 |
| 노드 변경 후 서비스 흐름이 간헐적으로 reset | agent 간 Maglev seed 불일치 | `maglev.hashSeed`를 모든 곳에서 동일하게 |
| NodePort 트래픽이 `tcpdump`에 안 보임 | XDP 가속 | 다른 지점에서 캡처하거나 디버깅 중 가속 해제 |
| EKS overlay에서 webhook timeout | API 서버가 non-VPC Pod IP에 도달 불가 | webhook backend에 `hostNetwork` 사용 |
| NIC에서 암호화 패킷이 안 보임 | Bandwidth manager/IPsec/WireGuard 상호작용, 또는 XDP/비 Geneve DSR 경로 | `cilium-dbg status \| grep Encryption`과 14절 표 확인 |

일반 절차: (1) `cilium-dbg status --verbose`로 실제 설정 확인, (2) `cilium-dbg monitor --type drop`으로 drop 사유 확인(`DROP_INVALID_IDENTITY`, `DROP_INVALID_VNI`), (3) `cilium-dbg bpf ipcache list`에 목적지와 올바른 tunnel endpoint가 있는지 확인, (4) 양쪽 노드 NIC와 `cilium_vxlan`/`cilium_geneve`에서 캡처, (5) 기동 시 agent 로그에서 fallback 줄 검토.

## 21. 검증 한계 및 출처

이 장의 실습은 이번 검토에서 실제 클러스터에 실행하지 않았습니다. 실습과 위의 모든 동작 서술은 아래 태그의 upstream 소스와 문서로 확인했습니다. 본문에 추론으로 표시한 항목이 있습니다: EKS overlay의 webhook 도달성, 비 ENI 인스턴스에서 native routing의 EC2 source/destination check, 보조 VPC CIDR의 native-routing 동작, Geneve 위 VTEP, 5.10~5.13 사이 커널에서의 multicast 커널 하한(검증하지 못함). 1.21 pre-release에 scaffolding된 추가 라우팅 모드는 의도적으로 다루지 않습니다.

계산값(MTU 표)은 소스 상수에서 산술로 구한 것이며 측정값이 아닙니다.

출처(별도 표기가 없으면 v1.20.2):

- [Routing](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst), [masquerading](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst), [tuning](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst), [system requirements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Kube-proxy replacement](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst), [bandwidth manager](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst), [VTEP](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/vtep.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [AWS CNI chaining](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/cni-chaining-aws-cni.rst)
- [Overlay BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_overlay.c), [lxc BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_lxc.c), [identity helper](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/identity.h), [NAT](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/nat.h), [tunnel 옵션](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/tunnel.h), [MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go), [기동 검증](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go), [KPR 검증](https://github.com/cilium/cilium/blob/v1.20.2/pkg/kpr/initializer/kube_proxy_replacement.go), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- Pre-release: [v1.21.0-pre.3의 daemon_main.go](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/daemon/cmd/daemon_main.go), [v1.21.0-pre.3의 values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- AWS: [EKS alternate CNI plugins](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)

## 퀴즈

[Overlay와 native routing 이해도 확인](../../quizzes/networking/cilium/09-overlay-native-routing-quiz.md).

[메인 페이지로 돌아가기](README.md)
