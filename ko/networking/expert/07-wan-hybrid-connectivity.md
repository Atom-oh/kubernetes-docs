# 07. WAN과 하이브리드 연결 설계

> **마지막 업데이트**: 2026년 11월 19일
> **실습 경계**: 설계 검토(desk check)만 수행합니다. 이 워크북은 회선, VPN, Direct Connect, Transit Gateway를 만들지 않습니다.
> **검증 상태**: AWS Direct Connect·Site-to-Site VPN·Transit Gateway 사용자 가이드와 RFC를 확인했으며, 집필 중 실제 연결을 **구성하거나 측정하지 않았습니다**.

이 워크북의 목표는 온프레미스 사이트와 AWS 리전을 잇는 경로를 **방향별로 예측**하고, 링크 하나가 끊겼을 때 어떤 규칙이 다음 경로를 고르는지, 얼마나 걸리는지, 무엇이 작아지는지(대역, MTU)를 근거와 함께 설명하는 것입니다.

먼저 [라우팅 정책과 수렴 시간 측정](02-routing-policy-convergence.md)을 마칩니다. LOCAL_PREF, AS_PATH, MED, community의 의미는 그 장에서 다뤘으므로 여기서는 AWS가 그 속성을 **어디까지** 존중하는지만 봅니다. WAN 회선 종류는 [네트워크 기초 Part 5의 WAN 유형](../../basics/06-network-fundamentals-part5.md#wan-types)에서, NAT와 CGNAT는 [Part 5의 NAT, PAT, CGNAT](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)에서 복습합니다.

**준비 조건:** 계정이나 회선이 없어도 됩니다. 모든 과제는 이 장의 표와 공식 문서로 판정합니다. 같은 설계를 실제로 구축해 확인하려면 Direct Connect 포트, VPN 연결, Transit Gateway attachment, 데이터 전송 요금이 발생하며 그 **비용과 정리 책임은 학습자 본인**에게 있습니다. 승인된 기존 실습 계정 밖에서 자원을 만들지 않습니다.

## 1. 질문을 정하고 읽기

시험 범위는 읽을 범위를 정하는 데만 씁니다. 숫자와 동작은 오른쪽 열의 공식 문서로 확인합니다.

| 읽을 자료 | 대응하는 시험 범위 | 자신의 말로 답할 질문 |
|---|---|---|
| [MEF 70.2](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/), [Cisco Catalyst SD-WAN 고가용성 가이드](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html) | ENCOR 350-401 Architecture: SD-WAN 제어·데이터 평면 요소 | 오버레이의 제어 평면이 죽으면 데이터 터널은 어떻게 되는가? |
| [Site-to-Site VPN 터널 옵션](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [라우팅 옵션](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html) | ANS-C01 Domain 1 Network Design, Domain 2 Network Implementation | 터널 두 개 중 AWS는 어느 쪽으로 보내고, 그 선택을 무엇이 바꾸는가? |
| [Direct Connect 라우팅 정책과 BGP community](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html) | ANS-C01 Domain 1, Domain 2 | 같은 prefix를 VIF 두 개로 광고할 때 AWS의 비교 순서는? |
| [Transit Gateway 동작 방식](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) | ANS-C01 Domain 1, Domain 2 | 같은 CIDR이 DX와 VPN에서 동시에 들어오면 무엇이 이기고, 그때 AS_PATH는 의미가 있는가? |
| [Direct Connect 할당량](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html), [VPN 할당량](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html), [TGW 할당량](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) | ANS-C01 Domain 1 | 설계가 처음 부딪히는 한도는 대역, 경로 수, MTU 중 무엇인가? |
| [RFC 5880 (BFD)](https://www.rfc-editor.org/rfc/rfc5880.html), [RFC 7296 (IKEv2)](https://www.rfc-editor.org/rfc/rfc7296.html) | 프로토콜 원리 | 장애 감지 시간은 어떤 값의 곱으로 정해지는가? |

읽은 뒤 사이트, 회선, AWS 구성 요소를 그리고 **BGP 세션**과 **패킷이 실제로 지나는 링크**를 다른 선으로 표시합니다. [워크북 02](02-routing-policy-convergence.md)에서 본 것처럼 세션이 있다는 사실이 그 세션으로 데이터가 흐른다는 뜻은 아닙니다. 아래 Direct Connect 게이트웨이가 대표적인 예입니다.

## 2. 언더레이와 오버레이로 WAN 보기

WAN 설계는 두 층으로 나눠 기록합니다. **언더레이**는 패킷을 실제로 실어 나르는 회선(MPLS, 인터넷 접속, Direct Connect)이고, **오버레이**는 그 위에 만든 터널과 정책(IPsec VPN, SD-WAN)입니다. 오버레이는 언더레이의 지연, 손실, 물리적 공유 경로를 바꾸지 못합니다. 같은 관로를 지나는 두 회선 위에 터널 두 개를 올려도 단일 장애점은 그대로입니다.

| 방식 | 제어 평면 (경로를 누가 정하나) | 데이터 평면 (패킷이 무엇을 타나) | 설계에서 확인할 것 |
|---|---|---|---|
| MPLS L3VPN | 통신사 PE가 고객 경로를 VRF로 분리하고 BGP로 교환. CE–PE는 정적·OSPF·BGP 등 | 통신사 MPLS 망. 고객은 레이블을 보지 않음 | CE–PE 프로토콜, 통신사 SLA, 다른 통신사 회선과의 물리적 분리 |
| 인터넷 + IPsec | 양 끝 장비가 정적 경로나 터널 안 BGP로 결정 | 공인 인터넷 위 ESP. 품질은 최선 노력 | 터널 수, NAT 통과 여부, 암호 알고리즘에 따른 MTU |
| SD-WAN | 중앙 컨트롤러가 정책과 경로를 배포 | WAN 엣지 사이의 IPsec 터널, 여러 언더레이를 동시에 사용 | 컨트롤러 도달 불가 시 동작, 터널별 경로 품질 측정, 애플리케이션별 정책 |

**SD-WAN을 제어·데이터 평면으로 나눠 읽는 법:** MEF 70.2는 SD-WAN 서비스를 그 아래 언더레이 연결 서비스와 구분하고, 사이트 사이의 터널(TVC)과 애플리케이션 흐름별 정책을 따로 정의합니다(용어는 [Part 5](../../basics/06-network-fundamentals-part5.md#wan-types) 참고). Cisco Catalyst SD-WAN에서는 SD-WAN Controller가 제어 평면을 조율하고 OMP 피어링 세션으로 제어 정보를 주고받으며, Validator가 장비를 인증하고 Controller와 라우터 사이의 제어 연결을 조율합니다. 데이터는 라우터 사이의 IPsec 연결로 흐르고, 그 연결 위에서 BFD가 자동으로 돌며 연결 장애를 감지합니다. 따라서 "SD-WAN이 장애를 빨리 감지한다"는 말은 **데이터 터널 위 BFD**에 대한 말이고, 컨트롤러 이중화는 별도의 설계 항목입니다.

AWS 쪽에서 SD-WAN 장비를 VPC에 두고 Transit Gateway와 BGP로 연결할 때는 Connect attachment를 씁니다. Connect peer(GRE 터널) 하나는 최대 5 Gbps, attachment 하나에 peer를 최대 4개까지 둘 수 있습니다. 이 장의 과제는 Connect를 쓰지 않지만, 8절의 대역 비교에는 포함합니다.

## 3. IPsec Site-to-Site VPN

**정의:** AWS Site-to-Site VPN 연결 하나에는 **터널이 두 개** 있고, 각 터널은 고유한 공인 IP를 쓰며 서로 다른 가용 영역에서 종료됩니다. 둘 다 구성해야 이중화가 됩니다. 터널 하나가 유지 보수 등으로 내려가면 그 VPN 연결의 다른 터널로 트래픽이 자동으로 옮겨 갑니다.

**동작:**

- **IKE 버전:** 터널은 IKEv1과 IKEv2를 모두 허용할 수 있습니다. AWS는 IKEv2를 강하게 권장하며, 장비가 IKEv2를 지원하지 않을 때만 IKEv1을 씁니다.
- **방향에 따른 터널 사용:** 온프레미스에서 AWS로 가는 트래픽은 두 터널을 모두 씁니다. AWS에서 온프레미스로 가는 트래픽은 한 터널을 선호하고 AWS 쪽 장애 시 다른 터널로 넘어갑니다. 따라서 고객 게이트웨이는 **비대칭 라우팅을 허용**해야 합니다. 가상 프라이빗 게이트웨이(VGW)에서는 게이트웨이의 모든 VPN 연결을 통틀어 터널 하나가 송신 경로로 선택되고 ECMP를 지원하지 않습니다.
- **정적 대 BGP:** 장비가 BGP를 지원하면 동적 라우팅을 고릅니다. AWS는 BGP의 생존 확인이 두 번째 터널로의 전환을 돕는다는 이유로 BGP 장비를 권장합니다. BGP를 고르면 정적 경로를 지정할 수 없습니다.
- **ECMP:** Transit Gateway에 붙인 VPN은 **동적 라우팅일 때만** ECMP로 여러 터널을 묶어 대역을 늘릴 수 있습니다. 정적 라우팅 VPN은 ECMP를 지원하지 않습니다.
- **대역:** 표준 터널은 터널당 최대 1.25 Gbps(최대 140,000 PPS)입니다. Large Bandwidth Tunnel은 터널당 최대 5 Gbps이지만 Transit Gateway나 Cloud WAN에 붙인 VPN에서만 쓸 수 있고, 두 터널의 대역 설정이 같아야 하며 Accelerated VPN과 함께 쓸 수 없습니다.
- **생존 확인:** Dead Peer Detection 타임아웃은 30초 이상으로 지정하고, 타임아웃 시 동작은 `Clear`(IKE 세션 종료, 터널 중지, 경로 제거), `None`, `Restart` 중 고릅니다. AWS 지식 센터는 VPN BGP의 기본 hold time을 30초로 안내합니다.
- **NAT 뒤의 고객 게이트웨이:** 고객 게이트웨이가 NAT 뒤에 있으면 ESP를 UDP로 감싸는 NAT 통과(NAT-T, RFC 3948)가 쓰입니다. 7절의 MTU 표에서 보듯 NAT-T가 켜지면 같은 알고리즘에서도 MTU가 작아집니다. CGNAT 회선 뒤의 지점은 [Part 5](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)에서 본 대로 외부에서 먼저 연결을 열 수 없으므로, 그 지점 쪽에서 터널을 시작하는 설계로 둡니다.

**실무 포인트:** "VPN 터널이 두 개이니 이중화가 끝났다"고 보고하지 않습니다. 두 터널은 AWS 쪽 엔드포인트의 이중화이며, 고객 게이트웨이 장비 하나와 인터넷 회선 하나를 공유한다면 그 둘이 단일 장애점입니다. 고객 쪽 장비나 회선을 이중화하려면 고객 게이트웨이를 하나 더 두고 VPN 연결을 하나 더 만듭니다.

## 4. Direct Connect

**정의:** Direct Connect는 고객 네트워크를 표준 Ethernet 광 케이블로 Direct Connect 로케이션의 AWS 라우터에 연결하고, 그 위에 **가상 인터페이스(VIF)** 를 만들어 VPC나 AWS 공개 서비스에 도달하는 서비스입니다. 인터넷 서비스 제공자를 경로에서 거치지 않습니다. 고객 장비는 802.1Q VLAN, BGP, BGP MD5 인증을 지원해야 합니다.

**연결 종류:**

| 구분 | 속도 | VIF 수 | 비고 |
|---|---|---|---|
| 전용 연결(dedicated) | 1, 10, 100, 400 Gbps | public·private VIF 최대 50개 + transit VIF 최대 4개, 합계 51개 (늘릴 수 없음) | 단일 모드 광, 포트 속도별 트랜시버 규격 고정 |
| 호스티드 연결(hosted) | 50 Mbps부터 25 Gbps까지 파트너가 제공하는 값 | 1개 (늘릴 수 없음) | 1 Gbps 이상은 요건을 갖춘 파트너만, 25 Gbps는 100 Gbps 포트가 있는 로케이션만. AWS가 트래픽 폴리싱으로 초과분을 버림 |

**VIF 종류:**

- **Private VIF:** 사설 IP로 VPC에 접근합니다. VGW에 직접 붙이면 같은 리전의 VPC 하나, Direct Connect 게이트웨이에 붙이면 여러 계정·리전의 VGW에 닿습니다.
- **Public VIF:** 공인 IP로 AWS 공개 서비스에 접근합니다. 광고하는 공인 prefix는 고객 소유여야 하며, AWS는 수신 트래픽의 출발지가 광고한 prefix인지 검사합니다.
- **Transit VIF:** Direct Connect 게이트웨이에 연결된 Transit Gateway에 접근합니다. 어떤 속도의 전용·호스티드 연결에도 만들 수 있습니다.

**Direct Connect 게이트웨이:** 전역 자원이며 VGW, Transit Gateway, Cloud WAN 코어 네트워크와 연결됩니다. AWS 문서는 이 게이트웨이를 **분산된 BGP route reflector 집합**으로 설명하고, 데이터 경로 밖에서 동작하므로 단일 장애점이 되지 않는다고 적습니다. 워크북 02의 route reflector처럼 경로를 반사할 뿐 패킷을 운반하지 않습니다. 게이트웨이 하나에 VGW는 최대 20개, Transit Gateway는 최대 6개, private·transit VIF는 최대 30개까지 연결합니다.

**경로 수 한도:** 이 한도는 장애로 직결되므로 설계 표에 적습니다.

- 온프레미스에서 AWS로 private·transit VIF의 BGP 세션 하나에 광고하는 경로는 IPv4·IPv6 각각 기본 100개이고, prefix 제어로 각각 1,000개까지 늘릴 수 있습니다. **할당보다 많이 광고하면 BGP 세션이 idle 상태가 되어 DOWN으로 보고됩니다.**
- Public VIF의 BGP 세션당 경로는 1,000개입니다.
- AWS에서 온프레미스로 transit VIF에 광고하는 prefix는 Transit Gateway 하나당 IPv4·IPv6 합계 200개입니다.

**허용 prefix(allowed prefixes):** Transit Gateway 연결에서는 Direct Connect 게이트웨이에 입력한 허용 prefix **그대로** 온프레미스에 광고됩니다. VPC CIDR이 `10.20.0.0/16`이어도 허용 prefix를 `10.0.0.0/8`로 두면 온프레미스는 `10.0.0.0/8`만 받습니다. VGW 연결에서는 반대로 허용 prefix가 같거나 더 작은 CIDR을 통과시키는 필터로 동작합니다. 6절의 함정이 여기서 생깁니다.

<a id="dx-lag"></a>

**LAG:** LACP로 같은 Direct Connect 엔드포인트의 연결 여러 개를 하나의 논리 연결로 묶습니다. 규칙은 다음과 같습니다.

- 모든 연결은 전용 연결이고 같은 대역이어야 합니다.
- 100 Gbps 미만 포트는 최대 4개, 100 Gbps와 400 Gbps 포트는 최대 2개까지 묶습니다.
- 모든 연결은 같은 Direct Connect 엔드포인트에서 종료되어야 하며 멀티섀시 LAG(MLAG)는 지원하지 않습니다.
- 모든 연결은 Active/Active로 동작합니다. LAG에는 동작해야 하는 최소 연결 수 속성이 있고 기본값은 0입니다. 값을 정하면 동작 연결이 그보다 적어질 때 LAG 전체가 내려가므로, 남은 연결이 과부하되는 상황을 막을 수 있습니다.

LAG는 **용량**을 늘리지만 같은 장비·같은 로케이션에서 끝나므로 로케이션 장애를 막지 못합니다. Part 5에서 본 대로 흐름 하나는 구성 링크 하나의 속도를 넘지 못한다는 점도 같습니다. 로케이션 이중화는 Resiliency Toolkit의 모델로 설계합니다. **Maximum resiliency**는 SLA 99.99%를, **High resiliency**는 99.9%를 목표로 하며 둘 다 Direct Connect SLA의 요건을 모두 충족해야 합니다. **Development and test**는 한 로케이션 안에서 서로 다른 장비에 연결을 나눕니다.

**MACsec:** 일부 로케이션의 10, 100, 400 Gbps **전용** 연결에서 지원하며, 1 Gbps 전용 연결과 호스티드 연결에서는 지원하지 않습니다. 홉 단위 L2 암호화이므로 고객 장비가 AWS 장비와 직접 L2 인접해야 하고, 중간의 last-mile 구간이 L2에 투명해야 합니다. 256비트 키만 지원하며, 100·400 Gbps에서는 확장 패킷 번호(XPN)가 필요합니다. LAG에서는 한 시점에 MACsec 키 하나가 모든 링크에 쓰입니다.

## 5. Transit Gateway

**정의:** Transit Gateway는 VPC와 온프레미스 네트워크 사이의 트래픽을 라우팅하는 리전 단위 가상 라우터입니다. attachment는 패킷의 출발지이자 목적지이며, VPC, VPN 연결, VPN Concentrator, Direct Connect 게이트웨이, Connect, peering을 붙일 수 있습니다.

**라우트 테이블 규칙:**

- attachment 하나는 라우트 테이블 **하나에 연결(association)** 되고, 경로는 **여러 테이블로 전파(propagation)** 할 수 있습니다. 전파되는 경로를 필터링할 수는 없습니다.
- 동적 라우팅 VPN은 연결된 라우트 테이블의 경로를 BGP로 고객 게이트웨이에 광고합니다. Direct Connect 게이트웨이 attachment는 허용 prefix로 광고를 정합니다.
- 같은 목적지에 정적 경로와 전파 경로가 있으면 정적 경로가 우선하고, 전파 경로는 테이블에 나타나지 않습니다.
- Transit Gateway는 선호 경로만 보여 줍니다. DX와 VPN으로 같은 경로를 받으면 테이블에는 DX 경로만 보이고, VPN 경로는 DX 경로가 더 이상 광고되지 않을 때 나타납니다.
- peering attachment는 정적 경로만 지원합니다.

**경로 평가 순서:** 먼저 가장 구체적인 경로를 고릅니다. 같은 CIDR이 서로 다른 attachment 유형에서 오면 다음 순서로 우선합니다.

1. 정적 경로(예: Site-to-Site VPN 정적 경로)
2. 시스템 경로(1:1 NAT용)
3. prefix list 참조 경로
4. VPC 전파 경로
5. Direct Connect 게이트웨이 전파 경로
6. Transit Gateway Connect 전파 경로
7. private Direct Connect 위 Site-to-Site VPN 전파 경로
8. Site-to-Site VPN 전파 경로
9. Site-to-Site VPN Concentrator 전파 경로
10. Client VPN 전파 경로
11. Transit Gateway peering(Cloud WAN) 전파 경로

같은 CIDR이 **같은 유형**의 attachment에서 오면 그때 BGP 속성을 비교합니다. AS_PATH가 짧은 경로, MED가 낮은 경로, 지원하는 경우 iBGP보다 eBGP 경로 순입니다. MED 없이 광고된 경로에는 DX attachment에서 0, VPN·Connect attachment에서 100이 기본값으로 붙습니다. ECMP는 서로 다른 attachment 유형 사이에서는 지원하지 않으며(예: VPN과 VPC), 그때는 위 평가 순서로 한 경로가 고릅니다.

**MTU와 대역:** VPC, Direct Connect, Connect, peering 사이 트래픽의 MTU는 8500바이트이고 VPN을 지나는 트래픽은 1500바이트입니다. Transit Gateway는 모든 패킷에 MSS clamping을 적용합니다. Path MTU Discovery는 VPC와 Connect attachment로 들어오는 트래픽에만 지원하고 VPN, Direct Connect, peering attachment에서는 지원하지 않습니다. VPC attachment와 DX 게이트웨이 연결의 대역은 가용 영역당 각 방향 최대 100 Gbps입니다.

<a id="failover-design"></a>

## 6. 장애 조치 설계: DX 주 경로와 VPN 백업

이 절은 **방향별로** 읽습니다. 온프레미스에서 AWS로 가는 경로는 **고객 라우터의 정책**이 고르고, AWS에서 온프레미스로 가는 경로는 **AWS의 평가 순서**가 고릅니다. 한쪽만 바꾸면 비대칭 경로가 생기고, 상태 기반 방화벽이 응답을 버릴 수 있습니다.

![하이브리드 장애 조치 애니메이션. ① 온프레미스 라우터(AS 65010, 10.10.0.0/16)는 VPC 10.20.0.0/16으로 가는 BGP 경로를 DX와 VPN 두 개 배우고, LOCAL_PREF 200인 DX 경로를 골라 목적지 10.20.1.10인 패킷을 DX 연결의 802.1Q VLAN 101(transit VIF)로 보낸다. ② 패킷은 DX 로케이션을 지나 목적지가 그대로인 채 Transit Gateway에 도착하고, TGW 라우트 테이블에 따라 VPC attachment로 전달된다. DX 게이트웨이는 BGP 경로만 반사하며 데이터 경로에 있지 않다. ③ DX 링크가 끊긴다. BFD가 300 ms 간격으로 3번 응답을 받지 못하면 BGP 세션이 내려가고 DX 경로가 양쪽에서 철회되며, 온프레미스 라우터의 최적 경로는 LOCAL_PREF 100인 VPN 터널로 바뀐다. ④ 다음 패킷은 VPN 경로를 탄다. IPsec이 ESP와 바깥 IP 헤더(출발지 203.0.113.10, 목적지 198.51.100.10)를 붙여 인터넷을 지난다. ⑤ Transit Gateway의 VPN attachment에서 ESP가 제거되고 목적지 10.20.1.10인 원래 패킷이 VPC로 전달된다. 돌아오는 트래픽도 DX 경로가 사라졌으므로 VPN 전파 경로를 쓴다.](../../.gitbook/assets/ko-networking-expert-07-wan-hybrid-connectivity-anim-0.svg)

### AWS에서 온프레미스로: AWS가 고르는 경로

**Transit Gateway에서:** 5절의 평가 순서가 그대로 적용됩니다.

1. **가장 긴 prefix가 먼저입니다.** 온프레미스가 VPN으로 `10.10.1.0/24`를, DX로 `10.10.0.0/16`을 광고하면 `10.10.1.0/24`로 가는 트래픽은 VPN으로 갑니다. DX를 주 경로로 쓰려면 두 경로에 **같은 prefix**를 광고합니다.
2. **같은 CIDR이면 attachment 유형 순서가 AS_PATH보다 먼저입니다.** DX 게이트웨이 전파 경로는 VPN 전파 경로보다 항상 우선하므로, VPN 쪽 광고에 AS_PATH prepend를 붙이는 것은 DX와 VPN 사이의 선택에 영향을 주지 않습니다. 반대로 VPN에 **정적 경로**를 두면 정적 경로가 DX 전파 경로보다 우선하므로, VPN이 의도치 않게 주 경로가 됩니다. 백업 VPN은 BGP로 구성합니다.
3. **같은 유형 안에서만 BGP 속성이 비교됩니다.** DX VIF 여러 개 사이, 또는 VPN 연결 여러 개 사이의 선택이 여기에 해당합니다.

**VGW에서:** 순서가 다릅니다. 같은 prefix라면 Direct Connect BGP 경로, VPN 정적 경로, VPN BGP 경로 순으로 우선하고, VPN끼리는 짧은 AS_PATH, 이어서 첫 AS가 같을 때 낮은 MED를 고릅니다. 두 목록을 섞어 외우지 않습니다.

**DX VIF 여러 개 사이:** Private·transit VIF에서 AWS는 다음 순서로 비교합니다.

| 순서 | 기준 | 설계에서 쓰는 법 |
|---|---|---|
| 1 | 가장 긴 prefix | Active/passive를 더 구체적인 경로로 표현 |
| 2 | Local preference community | `7224:7300`(high), `7224:7200`(medium), `7224:7100`(low). 표준 community로 붙이며 AS_PATH보다 먼저 평가. route target 같은 확장 community는 우선순위에 평가되지 않고 제거될 수 있음 |
| 3 | AS_PATH 길이 | prefix와 local preference가 같을 때 prepend로 조정 |
| 4 | MED | 우선순위가 낮아 AWS가 권장하지 않음 |
| 동률 | ECMP | AS_PATH 길이와 속성이 같으면 여러 VIF에 분산 |

community를 붙이지 않으면 AWS 리전은 기본적으로 **같은 리전에 연결된(associated) DX 로케이션**을 선호합니다. Active/active로 쓰려면 모든 VIF에 같은 community(예: `7224:7200`)를, active/passive로 쓰려면 주 VIF에 `7224:7300`, 백업 VIF에 `7224:7100`을 붙입니다. 이 community는 AWS가 온프레미스로 **돌아오는** 트래픽에 쓰는 우선순위입니다.

**루프 방지:** AWS는 AS_PATH에 DX ASN `7224`가 두 번 이상 있는 경로를 루프로 보고 설치하지 않습니다. 한 VIF로 배운 AWS 경로를 다른 VIF로 다시 광고하면 생기므로, AWS에 광고하는 경로에서 AWS로부터 배운 경로를 걸러 냅니다.

### 온프레미스에서 AWS로: 고객 라우터가 고르는 경로

AWS는 같은 VPC 경로를 DX(허용 prefix)와 VPN(TGW 라우트 테이블의 경로)으로 각각 광고합니다. 고객 라우터는 두 경로를 워크북 02의 BGP 선택 규칙으로 비교하므로, DX로 배운 경로에 더 높은 LOCAL_PREF를 주면 DX가 주 경로가 됩니다. 애니메이션의 LOCAL_PREF 200/100이 이 정책입니다.

**허용 prefix 함정:** 허용 prefix를 `10.0.0.0/8`로 요약해 두었는데 VPN으로는 TGW 라우트 테이블의 `10.20.0.0/16`이 광고되면, 고객 라우터는 **prefix가 더 긴 VPN 경로**를 고릅니다. LOCAL_PREF는 같은 prefix 사이의 비교이므로 이 상황을 바꾸지 못합니다. 허용 prefix를 VPN 쪽과 같은 길이로 맞추거나, 고객 라우터에서 VPN 수신 경로를 같은 요약으로 맞춥니다.

### 감지 시간 예산

| 감지 수단 | 값 | 출처의 성격 |
|---|---|---|
| DX의 BFD | AWS 쪽에 비동기 BFD가 자동으로 켜져 있지만 고객 라우터에 구성해야 동작. 최소 간격 300 ms, 배수 3 | Direct Connect FAQ와 사용자 가이드 |
| BFD 없는 DX의 BGP | hold time 90초 동안 keepalive가 없어야 세션이 내려감 | AWS 지식 센터 |
| VPN의 BGP | 기본 hold time 30초 | AWS 지식 센터 |
| VPN의 DPD | 30초 이상으로 지정, 타임아웃 동작 `Clear`·`None`·`Restart` | VPN 사용자 가이드 |

BFD가 장애를 감지하면 BGP 이웃 관계가 hold time 만료를 기다리지 않고 빠르게 내려갑니다. RFC 5880에 따라 BFD 감지 시간은 상대가 알린 배수와 협상된 간격의 곱이므로, 300 ms × 3이면 약 0.9초입니다. 하지만 **감지 시간이 곧 복구 시간은 아닙니다.** 복구 시간은 감지, 경로 철회와 전파, 양쪽 라우터의 FIB 반영, 반대 방향 전환을 합친 값이며, 뒤의 항목들은 AWS가 고정 값을 공개하지 않습니다. 설계 문서에는 감지 값을 문서 근거로, 나머지는 **측정 전 가정**으로 표시합니다. 워크북 02의 측정 원칙(조작 시각, 첫 변화, FIB 변화, 지속 회복 기준)을 그대로 씁니다.

## 7. 터널을 지나는 MTU와 MSS

| 구간 | MTU | 비고 |
|---|---|---|
| Site-to-Site VPN | 최대 1446바이트, MSS 1406바이트 | 점보 프레임과 Path MTU Discovery를 지원하지 않음. 알고리즘과 NAT-T에 따라 더 작아짐 |
| Private VIF | 1500 또는 9001 | 링크 계층 프레임은 1522 또는 9023바이트 |
| Transit VIF | 1500 또는 8500 | Transit Gateway의 점보 프레임은 8500만 지원 |
| Transit Gateway | VPC·DX·Connect·peering 사이 8500, VPN 1500 | 모든 패킷에 MSS clamping. PMTUD는 VPC·Connect 유입에만 |

AWS가 권장하는 VPN MTU/MSS 예시입니다(IPv4 MSS 기준).

| 암호화 | 무결성 | NAT-T | MTU | MSS |
|---|---|---|---|---|
| AES-GCM-16 | 해당 없음 | 꺼짐 | 1446 | 1406 |
| AES-GCM-16 | 해당 없음 | 켜짐 | 1438 | 1398 |
| AES-CBC | SHA1/SHA2-256 | 꺼짐 | 1438 | 1398 |
| AES-CBC | SHA2-512 | 켜짐 | 1406 | 1366 |

**동작 포인트:**

- AWS는 고객 게이트웨이가 **암호화 전에** 단편화하도록 권장합니다. VPN은 받은 조각을 재조립한 뒤 다음 망으로 보내므로, 재조립된 패킷이 그다음 구간(예: Direct Connect)의 MTU를 넘지 않는지도 봅니다.
- VIF MTU를 점보로 바꾸면 물리 연결이 갱신될 수 있고, 그 연결의 모든 VIF가 최대 30초 동안 끊길 수 있습니다. 운영 중 변경은 변경 창에서 합니다.
- 두 private VIF가 같은 경로를 다른 MTU로 광고하거나, Site-to-Site VPN이 같은 경로를 광고하면 1500 MTU가 쓰입니다.

**설계 포인트:** 장애 조치 설계에서 **실제로 적용되는 MTU는 백업 경로의 MTU**입니다. DX 경로에서 큰 MSS로 맺어진 TCP 연결이 VPN으로 넘어가면, DF 비트가 켜진 큰 패킷은 PMTUD를 지원하지 않는 구간에서 오류 알림 없이 버려질 수 있습니다. 이 과제에서는 하이브리드 흐름의 MSS를 VPN 값(선택한 알고리즘 기준)에 맞춰 고객 라우터에서 clamping하거나, VPN이 백업인 동안 VIF를 1500으로 유지하는 두 안을 비교합니다.

## 8. 대역·지연·비용 절충

| 연결 | 대역 (공식 한도) | 지연·품질의 성격 | 이중화 단위 | 비용 요소 |
|---|---|---|---|---|
| DX 전용 연결 | 1·10·100·400 Gbps, LAG로 묶음 | 인터넷 서비스 제공자를 거치지 않는 전용 경로 | 연결, 장비, 로케이션 (Resiliency Toolkit 모델) | 포트 시간, 아웃바운드 데이터 전송 |
| DX 호스티드 연결 | 50 Mbps에서 25 Gbps | 파트너 망을 거치고 AWS가 계약 속도로 폴리싱 | 호스티드 연결 단위, 파트너 망 | 위와 같은 AWS 요소 + 파트너 요금 |
| VPN 표준 터널 | 터널당 최대 1.25 Gbps, 140,000 PPS | 인터넷 경로, 최선 노력 | 터널 2개(AWS 쪽), 고객 게이트웨이와 회선은 별도 | 연결 시간, 아웃바운드 데이터 전송, 터널 공인 IPv4 |
| VPN Large Bandwidth Tunnel | 터널당 최대 5 Gbps (TGW·Cloud WAN만) | 표준 터널과 같음, MTU 한도도 같음 | 위와 같음 | 별도 연결 시간 요금 |
| TGW 위 VPN ECMP | 동적 라우팅 터널 여러 개의 합 | 흐름 단위 분산, 흐름 하나는 터널 하나의 한도 | 터널·연결 단위 | VPN 요금 + TGW attachment 시간, GB당 처리 |
| Connect (SD-WAN) | peer당 5 Gbps, attachment당 peer 4개 | 하부 전송(VPC 또는 DX)의 성격을 따름 | peer·attachment 단위 | TGW attachment 시간과 하부 전송의 처리 요금 |

Transit Gateway는 attachment 시간당 요금과 VPC, Direct Connect, VPN에서 들어오는 GB당 데이터 처리 요금을 받습니다. 구체적인 단가는 리전과 시점에 따라 다르므로 설계서에는 **요금 요소**만 적고, 금액은 학습자가 요금 페이지에서 그날 확인한 값으로 계산합니다.

## 9. 설계 과제: 사이트 두 곳과 리전 하나

실제 자원을 만들지 않는 desk check입니다. 결과는 **설계 검토**로 표시합니다.

**입력:**

| 위치 | 주소와 ASN | 연결 |
|---|---|---|
| 사이트 A (본사 데이터센터) | `10.10.0.0/16`, AS 65010 | 서로 다른 DX 로케이션 두 곳에 10 Gbps 전용 연결 하나씩(DX-1, DX-2), 각 연결에 transit VIF 하나. 인터넷 회선 하나에 고객 게이트웨이 하나 |
| 사이트 B (지점) | `10.30.0.0/16`, AS 65030 | 서로 다른 통신사 인터넷 회선 두 개, 회선마다 고객 게이트웨이 하나와 VPN 연결 하나. DX 없음 |
| 리전 | VPC `10.20.0.0/16`, Transit Gateway(예시 Amazon ASN 64512), Direct Connect 게이트웨이(예시 ASN 64513) | DX 게이트웨이와 VPN 세 개가 같은 TGW에 붙음 |

사이트 A와 B 사이의 트래픽은 기존 MPLS를 쓰며 이 과제의 범위 밖입니다. 모든 VPN은 BGP와 IKEv2, AES-GCM을 쓰고 NAT-T는 꺼져 있다고 가정합니다.

**서비스 목표(SLO):** 학습자의 설계 목표이며 AWS SLA가 아닙니다.

- 사이트 A → VPC: DX 연결·장비·로케이션 하나가 장애를 겪어도 5 Gbps 이상을 유지하고, 장애 감지부터 양방향 데이터 경로 회복까지 5초 이내를 목표로 합니다. DX 두 개가 모두 끊기면 VPN으로 축소 운영을 허용합니다.
- 사이트 B → VPC: 회선이나 고객 게이트웨이 하나가 장애를 겪어도 연결을 유지합니다. 전환은 BGP hold time 안에 이뤄지면 됩니다.

**과제:**

1. **광고표:** 경로마다 누가 어떤 prefix를 광고하는지 적습니다. DX 게이트웨이의 허용 prefix, 각 VPN이 받는 TGW 라우트 테이블 경로, 사이트 A·B가 AWS로 광고하는 prefix를 포함합니다. 할당량(DX BGP 세션당 기본 100개, TGW당 200개)과 비교합니다.
2. **정책표:** 사이트 A 라우터의 LOCAL_PREF(DX-1, DX-2, VPN), DX VIF에 붙일 local preference community, TGW 라우트 테이블의 연결·전파 관계를 정합니다. DX 두 개를 active/active로 할지 active/passive로 할지 SLO의 5 Gbps 조건으로 판단합니다.
3. **경로 예측:** 아래 시나리오마다 사이트 A → VPC, VPC → 사이트 A, 사이트 B → VPC, VPC → 사이트 B의 경로를 적고, 그 경로를 고른 **규칙의 단계**(예: "TGW 평가 순서 5단계, DX 게이트웨이 전파")를 함께 적습니다.
4. **시간 예산:** 시나리오마다 감지 수단과 그 값, 측정 전 가정으로 둘 항목을 적고 SLO 충족 여부를 판정합니다.
5. **MTU 결정:** transit VIF MTU와 사이트 A의 MSS clamping 값을 정하고 이유를 씁니다.

| 시나리오 | 사이트 A → VPC | VPC → 사이트 A | 적용 규칙 | 감지 | 남는 대역 | 판정 |
|---|---|---|---|---|---|---|
| 정상 | | | | | | |
| DX-1 연결 장애 | | | | | | |
| DX 로케이션 1 전체 장애 | | | | | | |
| DX-1·DX-2 모두 장애 | | | | | | |
| 사이트 A 고객 라우터에 BFD 미구성 상태에서 DX-1 장애 | | | | | | |
| 사이트 B 회선 하나 장애 | | | | | | |
| DX-1 복구 | | | | | | |

**검토 기준:** 칸마다 근거 문서의 규칙을 하나 이상 인용해야 합니다. 다음 항목을 스스로 확인합니다.

- 정상 상태에서 VPC → 사이트 A가 DX를 쓰는 이유를 "DX가 빠르니까"가 아니라 TGW 평가 순서로 설명했는가?
- VPN에 정적 경로를 두지 않았는가? 두었다면 정상 상태에서도 VPN이 이긴다는 점을 찾았는가?
- 허용 prefix와 VPN 광고 prefix의 길이가 같은가? 다르면 어느 방향이 VPN으로 새는가?
- BFD 미구성 시나리오가 5초 SLO를 지키지 못한다는 점(BGP hold time 90초)을 찾았는가?
- DX 두 개가 모두 끊긴 상태의 대역이 VPN 한도(표준 터널 1.25 Gbps, ECMP 시 터널 합)로 줄어든다는 점과, 흐름 하나는 터널 하나의 한도를 넘지 못한다는 점을 적었는가?
- MTU를 백업 경로 기준으로 정했는가?

## 10. 장애와 복구를 관찰하는 방법

실제 환경이 없으므로 이 절은 **무엇을 보면 판정할 수 있는지**를 정하는 연습입니다. 승인된 기존 환경에서 같은 시나리오를 재현할 기회가 생기면 아래 증거를 모읍니다.

| 계층 | 보는 것 | 그 증거만으로 알 수 없는 것 |
|---|---|---|
| 고객 라우터 BGP 테이블 | 후보 경로 두 개, LOCAL_PREF, 선택 표시 | AWS 쪽 반환 경로 |
| 고객 라우터 FIB와 캡처 | 실제 송신 인터페이스, 터널 인터페이스의 ESP | 애플리케이션 흐름 전체의 성공 |
| TGW 라우트 테이블 | 현재 선호 경로 하나. 백업 VPN 경로는 DX 경로가 철회된 뒤에만 보임 | 패킷이 실제로 지나간 경로 |
| CloudWatch | VPN `TunnelState`, DX VIF의 `VirtualInterfaceBgpStatus` | 데이터 평면 손실의 시작과 끝 |
| 출발지를 지정한 probe | 손실 구간, 지속 회복 시작 | 큰 패킷이나 모든 포트의 동작 |

**복구(failback)도 장애입니다.** DX가 돌아와 BGP 세션이 다시 수립되면 TGW에서는 DX 게이트웨이 전파 경로가, 고객 라우터에서는 LOCAL_PREF가 높은 DX 경로가 다시 이깁니다. 즉 트래픽이 **자동으로** DX로 되돌아가며, 이때도 경로 변경과 MTU 변화가 생깁니다. 링크가 불안정하면 경로가 반복해서 바뀔 수 있으므로, 복구를 판정할 지속 회복 기준(예: 연속 응답 수와 관찰 시간)을 미리 정합니다. 워크북 02의 원칙대로 관찰 손실 0은 그 샘플링 해상도에서 중단을 포착하지 못했다는 뜻일 뿐입니다.

## 11. 산출물과 완료 기준

| 산출물 | 완료 조건 |
|---|---|
| 토폴로지 그림 | 세션과 데이터 링크를 구분하고 DX 게이트웨이를 데이터 경로 밖에 그림 |
| 광고표와 정책표 | 허용 prefix, VPN 광고, LOCAL_PREF, community, TGW 연결·전파를 모두 적고 할당량과 비교 |
| 시나리오 표 | 일곱 시나리오의 양방향 경로, 적용 규칙, 감지 값, 남는 대역, SLO 판정 |
| MTU 결정 | 백업 경로 기준 MSS 값과 그 근거 표 |
| 미확인 목록 | 경로 전파와 FIB 반영 시간처럼 문서가 고정 값을 주지 않는 항목을 측정 전 가정으로 표시 |

방향별 경로 선택 규칙, attachment 유형 순서와 AS_PATH의 관계, 허용 prefix 함정, 감지 시간과 복구 시간의 차이, 백업 경로가 정하는 MTU를 근거 문서와 함께 설명할 수 있으면 완료입니다. 결과 표를 [자동화 종합 실습](06-automation-capstone.md)의 변경 검토서 입력으로 쓰고, 클라우드 내부 경로는 [클라우드·CNI 설계](05-cloud-cni-design.md)로 이어 갑니다. 조직 간 VPC 연결의 선택지는 [Cross-Org VPC 연결](../05-cross-org-vpc-connectivity.md)에서, EKS 하이브리드 노드의 네트워크 요구 사항은 [하이브리드 노드 네트워크 구성](../../eks-hybrid-nodes/02-network-configuration.md)에서 확인합니다. 마지막으로 [퀴즈](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md)를 풉니다.

## 참고 자료

AWS Direct Connect

- [What is Direct Connect?](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html) (VIF 종류, 네트워크 요건, BFD, 요금 요소)
- [Direct Connect quotas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)
- [Hosted connections](https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html)
- [Virtual interfaces and MTU](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)
- [Routing policies and BGP communities](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)
- [Direct Connect gateways](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html), [Allowed prefixes interactions](https://docs.aws.amazon.com/directconnect/latest/UserGuide/allowed-to-prefixes.html)
- [Link aggregation groups](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html), [MAC Security](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html), [Resiliency Toolkit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)
- [Direct Connect FAQ](https://aws.amazon.com/directconnect/faqs/) (BFD 기본값, MACsec 지원 연결)
- [AWS 지식 센터: Direct Connect BFD 구성](https://repost.aws/knowledge-center/enable-bfd-direct-connect) (BFD가 없을 때 BGP hold time 90초)
- [CloudWatch metrics for Direct Connect virtual interface BGP health](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudwatch-metrics-for-aws-direct-connect-virtual-interface-bgp-health-and-prefix-count/)

AWS Site-to-Site VPN

- [Tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [Configure tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/tunnel-configure.html)
- [Routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html), [Static and dynamic routing](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-static-dynamic.html), [Route tables and route priority](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-route-priority.html)
- [Site-to-Site VPN quotas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html) (대역, PPS, MTU, 경로 수)
- [Best practices for a customer gateway device](https://docs.aws.amazon.com/vpn/latest/s2svpn/cgw-best-practice.html) (IKEv2, 암호화 전 단편화, 알고리즘별 MTU/MSS)
- [Monitor VPN tunnels using CloudWatch](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [AWS 지식 센터: BGP 로그로 VPN 터널 장애 분석](https://repost.aws/knowledge-center/vpn-bgp-logs-troubleshoot-tunnel) (기본 hold time 30초)
- [AWS VPN pricing](https://aws.amazon.com/vpn/pricing/)

AWS Transit Gateway

- [How AWS Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) (attachment, 연결·전파, 경로 평가 순서, ECMP)
- [Transit Gateway quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) (대역, MTU, MSS clamping, PMTUD)
- [AWS Transit Gateway pricing](https://aws.amazon.com/transit-gateway/pricing/)

표준·벤더 문서

- [RFC 5880: Bidirectional Forwarding Detection](https://www.rfc-editor.org/rfc/rfc5880.html)
- [RFC 7296: IKEv2](https://www.rfc-editor.org/rfc/rfc7296.html), [RFC 4303: ESP](https://www.rfc-editor.org/rfc/rfc4303.html), [RFC 3948: UDP Encapsulation of IPsec ESP Packets](https://www.rfc-editor.org/rfc/rfc3948.html)
- [RFC 4271: BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html), [RFC 1997: BGP Communities](https://www.rfc-editor.org/rfc/rfc1997.html), [RFC 6996: Autonomous System Reservation for Private Use](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (예시 주소)
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)
- [Cisco Catalyst SD-WAN High Availability Configuration Guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html)

시험 범위 (목차를 정하는 데만 사용)

- [AWS Certified Advanced Networking - Specialty (ANS-C01) 시험 안내](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
- [Cisco 350-401 ENCOR](https://www.cisco.com/site/us/en/learn/training-certifications/exams/encor.html)
