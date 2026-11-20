# 네트워크 기초 Part 5: 네트워크 장비, LAN과 WAN 기초

> **마지막 업데이트**: 2026년 11월 19일

::: tip 5부작 시리즈입니다
[Part 1: 계층 모델과 링크·라우팅](./06-network-fundamentals-part1.md) ·
[Part 2: 전송 계층과 TLS](./06-network-fundamentals-part2.md) ·
[Part 3: 애플리케이션 프로토콜](./06-network-fundamentals-part3.md) ·
[Part 4: 요청의 여정과 클라우드](./06-network-fundamentals-part4.md) ·
**Part 5: 네트워크 장비, LAN과 WAN** *(현재 문서)*
:::

Part 1~4가 프로토콜을 계층 순서로 다뤘다면, 이 문서는 그 프로토콜을 실제로 처리하는 **장비**와 장비를 엮는 **LAN·WAN 설계**를 다룹니다. Ethernet 프레임, ARP, 최장 프리픽스 일치, NAT의 기본 정의는 [Part 1](./06-network-fundamentals-part1.md)에서 설명했으므로 여기서는 반복하지 않고, 장비가 무엇을 보고 어떤 결정을 내리는지, 이중화와 주소 변환이 어디서 깨지는지에 집중합니다.

다루는 범위는 CCNA(200-301)의 Network Fundamentals·Network Access·IP Services 영역과 CompTIA Network+(N10-009) 1번 영역에 대응합니다. 시험 범위는 목차를 정하는 데만 썼습니다. 숫자와 프로토콜 동작은 맨 아래 참고 자료의 표준·벤더·AWS 문서로 확인했고, 허브·AP 같은 장비의 기본 동작은 일반적인 정의로 적었습니다.

각 항목은 Part 1과 같이 **정의 → 동작 → 실무 포인트** 순서를 따릅니다.

---

<a id="device-roles"></a>

## 1. 장비 역할: 누가 무엇을 보고 결정하는가

장비를 구분하는 가장 확실한 기준은 "포트로 들어온 데이터를 어디로 보낼지 결정할 때 **어떤 표를 조회하는가**"입니다.

| 장비 | 주로 보는 정보 | 조회하는 표 | 결정 결과 |
|---|---|---|---|
| 허브(리피터) | 없음 (비트 신호) | 없음 | 들어온 신호를 다른 모든 포트로 복제 |
| L2 스위치 | 목적지 MAC + VLAN | MAC 주소 테이블 | 알려진 유니캐스트는 한 포트, 브로드캐스트·미학습 목적지는 같은 VLAN 전체로 flooding |
| L3 스위치 | 같은 VLAN이면 MAC, 다른 서브넷이면 목적지 IP | MAC 테이블 + 라우팅(FIB) | VLAN 안은 스위칭, VLAN 사이는 VLAN별 가상 인터페이스(SVI)를 게이트웨이로 라우팅 |
| 라우터 | 목적지 IP | 라우팅 테이블에서 만든 FIB | 최장 프리픽스 경로의 다음 홉으로 전달, TTL 1 감소, L2 헤더 새로 작성 |
| 상태 기반 방화벽 / NGFW | 5-튜플과 연결 상태, NGFW는 애플리케이션 식별까지 | 정책 규칙 + 상태(연결) 테이블 | 새 연결은 규칙으로 판단, 이후 응답 패킷은 상태 테이블과 일치하면 통과 |
| 로드밸런서 | L4는 5-튜플, L7은 HTTP 호스트·경로·헤더 | 리스너 규칙, 대상 그룹 상태 | 정상 대상 중 하나를 골라 전달 |
| 무선 AP | 무선 단말 MAC, SSID | 연결(association) 단말 목록, SSID와 VLAN 매핑 | 802.11 프레임을 유선 분배망으로 브리징 |

장비별로 짚을 점은 다음과 같습니다.

- **허브**는 L1 장비라 주소를 보지 않습니다. 허브에 붙은 단말은 하나의 공유 매체를 반이중으로 쓰므로 동시에 보내면 충돌합니다.
- **L2 스위치**는 프레임의 **출발지 MAC**을 들어온 포트·VLAN과 함께 학습하고, **목적지 MAC**으로 포트를 고릅니다. 프레임 내용은 바꾸지 않습니다(트렁크로 나갈 때 802.1Q 태그를 붙이고 떼는 것은 예외).
- **L3 스위치**는 스위칭 하드웨어에 라우팅 기능을 넣은 장비입니다. Cisco 예시처럼 VLAN마다 SVI를 만들고 그 주소를 해당 VLAN의 기본 게이트웨이로 씁니다.
- **라우터**는 L2 브로드캐스트로 받은 패킷을 다른 인터페이스로 넘기지 않습니다(RFC 1812 §5.3.4, IP 멀티캐스트 목적지는 예외). 제한 브로드캐스트 `255.255.255.255`도 전달하지 않습니다(§5.3.5.1). 그래서 라우터 인터페이스(또는 SVI)가 브로드캐스트 영역의 경계가 됩니다. 라우팅되는 패킷은 TTL이 줄고 출발지·목적지 MAC이 바뀌지만, NAT가 없다면 IP 주소는 그대로입니다.
- **상태 기반 방화벽**은 연결을 추적하므로 응답 패킷에 대한 규칙을 따로 쓰지 않아도 됩니다. NIST SP 800-41은 패킷 필터, 연결마다 상태 테이블 항목을 두는 상태 검사, 애플리케이션 방화벽·프록시 게이트웨이를 구분하고, 방화벽에 악성코드 탐지 등을 묶은 장비를 UTM이라 부릅니다. "NGFW"는 NIST 문서의 용어가 아니라, 애플리케이션 식별·사용자 식별·침입 방지 같은 기능을 묶은 제품군을 부르는 벤더 용어입니다.
- **로드밸런서**는 동작 계층에 따라 결정 근거가 다릅니다. AWS 기준으로 ALB는 리스너 규칙을 우선순위 순서로 평가한 뒤 대상 그룹에서 대상을 고르고, NLB는 프로토콜·출발지/목적지 IP·포트·TCP 시퀀스 번호로 만든 흐름 해시로 대상을 고르며 TCP 연결 하나는 수명 동안 한 대상으로 갑니다.
- **AP**는 무선과 유선을 잇는 브리지입니다. SSID별로 다른 VLAN에 연결하는 구성이 흔해서, 무선 단말도 결국 위의 스위치·라우터 결정을 그대로 거칩니다.

**실무 포인트:** 장애 위치를 좁힐 때 "이 장비가 조회하는 표"를 직접 보세요. Linux에서는 `bridge fdb show`로 브리지의 MAC 학습 결과를, `ip route get <목적지>`로 라우팅 결정을, conntrack 도구로 연결 추적(상태·NAT) 테이블을 확인할 수 있습니다. 표에 기대한 항목이 없다면 그 장비 앞 단계가 원인입니다.

### 충돌 영역과 브로드캐스트 영역

**정의:** **충돌 영역**은 동시에 송신하면 신호가 충돌하는 공유 매체의 범위이고, **브로드캐스트 영역**은 L2 브로드캐스트 프레임이 도달하는 범위입니다.

**동작:**

- 허브는 모든 포트를 하나의 충돌 영역으로 묶습니다.
- 스위치는 포트마다 충돌 영역을 나눕니다. 풀듀플렉스 링크에서는 송수신이 분리되어 충돌 자체가 일어나지 않습니다([Part 1의 Ethernet](./06-network-fundamentals-part1.md#ethernet) 참고).
- VLAN 하나가 브로드캐스트 영역 하나입니다. 같은 VLAN이 트렁크로 여러 스위치에 걸쳐 있으면 그 전체가 여전히 **하나의** 브로드캐스트 영역입니다.
- 라우터 인터페이스와 SVI는 브로드캐스트를 넘기지 않으므로 브로드캐스트 영역을 나눕니다.

**예시로 세어 보기:** 스위치 한 대에 VLAN 10·20·30을 만들고, 트렁크 하나로 라우터(하위 인터페이스 3개)에 연결했습니다. 스위치 포트 하나에는 허브를 달아 PC 4대를 붙였습니다.

| 질문 | 답 | 이유 |
|---|---|---|
| 브로드캐스트 영역 수 | 3 | VLAN마다 하나, 라우터가 VLAN 사이 브로드캐스트를 막음 |
| 허브에 붙은 PC 4대의 충돌 영역 | 1 | 허브는 공유 매체이므로 4대가 한 충돌 영역 |
| 스위치 포트 하나에 단말 하나 | 포트마다 1 | 스위치 포트가 충돌 영역을 분리하고, 풀듀플렉스면 실제 충돌은 없음 |

**실무 포인트:** 브로드캐스트 영역이 크면 ARP·DHCP 같은 브로드캐스트가 모든 단말의 CPU를 깨우고, 루프가 생겼을 때 피해 범위도 커집니다. VLAN을 작게 나누고 VLAN 사이를 라우팅하는 이유가 여기에 있습니다.

---

<a id="vlan-trunk"></a>

## 2. VLAN과 802.1Q 트렁크

VLAN의 정의와 "VLAN 간 통신에는 L3 장비가 필요하다"는 원칙은 [Part 1의 VLAN](./06-network-fundamentals-part1.md#vlan)에서 다뤘습니다. 여기서는 태그가 실제로 어떻게 생겼고, 트렁크에서 무엇이 잘못될 수 있는지를 봅니다.

### 802.1Q 태그

**정의:** IEEE 802.1Q는 Ethernet 프레임의 출발지 MAC 뒤에 4바이트 태그를 넣어 프레임이 속한 VLAN을 표시합니다.

**동작:** 태그는 네 필드로 이뤄집니다.

| 필드 | 크기 | 의미 |
|---|---|---|
| TPID | 16비트 | 값 `0x8100`: 이 프레임이 802.1Q 태그를 가졌다는 표시 |
| PCP | 3비트 | 우선순위 0~7 (802.1p) |
| DEI (예전 이름 CFI) | 1비트 | 혼잡 시 먼저 버려도 되는 프레임 표시 |
| VID | 12비트 | VLAN ID. 값은 0~4095이지만 0과 4095는 예약되어 실제 VLAN에는 1~4094를 사용 |

태그를 넣으면 프레임이 4바이트 커지므로 태그 프레임의 최대 크기는 1522바이트가 되고, 태그를 넣은 장비가 FCS를 다시 계산합니다.

### 액세스 포트, 트렁크 포트, 네이티브 VLAN

**정의:**

- **액세스 포트**는 VLAN 하나에 속하며 단말과 태그 없는 프레임을 주고받습니다.
- **트렁크 포트**는 여러 VLAN을 한 링크로 나르며 각 프레임에 VID를 태그로 붙입니다.
- **네이티브 VLAN**은 트렁크에서 **태그 없이** 오가는 VLAN입니다.

**동작:** Cisco Catalyst 문서 기준으로 네이티브 VLAN은 기본값이 **VLAN 1**이며, 장비는 트렁크로 받은 태그 없는 프레임을 네이티브 VLAN에 넣고 네이티브 VLAN 프레임은 태그 없이 내보냅니다. 트렁크 양쪽의 네이티브 VLAN은 **반드시 같아야** 합니다. 다르면 한쪽 VLAN의 태그 없는 프레임이 반대편에서 다른 VLAN으로 들어가 VLAN 분리가 깨지고, Cisco는 스패닝 트리 루프가 생길 수 있다고 경고합니다. 트렁크는 기본적으로 VLAN 1~4094를 모두 허용합니다.

**실무 포인트:**

- 트렁크마다 허용 VLAN 목록을 필요한 것만으로 줄이고, 네이티브 VLAN은 사용하지 않는 VLAN으로 바꾸고 양쪽을 맞추세요.
- Linux에서도 `ip link add link eth0 name eth0.10 type vlan id 10`으로 태그 하위 인터페이스를 만들 수 있습니다. 하이퍼바이저나 베어메탈 쿠버네티스 노드를 트렁크 포트에 연결할 때 쓰는 방식입니다.

### VLAN 간 라우팅: 라우터 온 어 스틱

트렁크 하나에 라우터의 하위 인터페이스(VLAN마다 하나)를 올리면, 라우터 한 대가 여러 VLAN의 게이트웨이가 됩니다. 아래 애니메이션은 VLAN 10의 PC-A가 VLAN 20의 PC-B로 보내는 프레임 하나를 따라갑니다. 같은 케이블을 올라갔다 내려오는 점이 핵심입니다.

![VLAN 간 라우팅 애니메이션. ① PC-A(VLAN 10, 10.0.10.5)는 목적지가 다른 서브넷이므로 게이트웨이 10.0.10.1의 MAC으로 프레임을 만든다. ② L2 액세스 스위치는 출발지 MAC을 포트 1·VLAN 10으로 학습하고, 프레임을 802.1Q 트렁크로 내보내며 VLAN 10 태그를 붙인다. ③ 라우터는 라우팅 테이블에서 10.0.20.0/24 경로로 .20 하위 인터페이스를 고르고, TTL을 64에서 63으로 줄인 뒤 L2 헤더를 새로 쓴다(IP 주소는 그대로). ④ 프레임은 같은 트렁크를 VLAN 20 태그로 내려온다. ⑤ 스위치는 태그를 떼고 VLAN 20 액세스 포트로 전달해 PC-B(10.0.20.7)가 받는다.](../.gitbook/assets/ko-basics-06-network-fundamentals-part5-anim-0.svg)

같은 일을 L3 스위치가 하면 트렁크를 오르내리는 대신 스위치 내부의 SVI 사이에서 라우팅합니다. 트렁크 대역폭을 VLAN 간 트래픽이 두 번 쓰지 않으므로, VLAN 간 트래픽이 많은 곳에서는 L3 스위치를 씁니다.

---

<a id="stp-lacp-fhrp"></a>

## 3. 루프 방지와 이중화: STP, LACP, FHRP

링크와 장비를 이중화하면 가용성은 올라가지만, L2에서는 루프가, L3 게이트웨이에서는 "누가 기본 게이트웨이인가"라는 문제가 생깁니다. 세 가지 기술이 각각 하나씩을 해결합니다.

### STP와 RSTP

**정의:** 스패닝 트리 프로토콜(STP, IEEE 802.1D)은 이중화된 스위치 링크 중 일부를 차단해 L2 토폴로지를 루프 없는 트리로 만듭니다. RSTP(802.1w, 이후 802.1D-2004에 통합)는 그 빠른 수렴 버전입니다.

**왜 필요한가:** IP 헤더에는 TTL이 있지만 **Ethernet 헤더에는 TTL이 없습니다.** 스위치 사이에 루프가 있으면 브로드캐스트 프레임은 사라지지 않고 계속 돌면서 복제되고(브로드캐스트 스톰), 같은 출발지 MAC이 여러 포트에서 보여 MAC 테이블이 계속 바뀝니다.

**동작:**

1. **루트 브리지 선출:** 브리지 ID(우선순위 + MAC)가 가장 낮은 스위치가 루트가 됩니다. 기본 우선순위는 32768이므로 아무것도 설정하지 않으면 MAC이 가장 낮은 스위치, 흔히 가장 오래된 장비가 루트가 됩니다.
2. **포트 역할:** 루트가 아닌 스위치는 루트로 가는 가장 좋은 포트를 **루트 포트**로, 각 세그먼트에서 가장 좋은 BPDU를 보내는 포트를 **지정(designated) 포트**로 정합니다. 남은 포트는 차단됩니다(RSTP의 alternate·backup 역할).
3. **수렴:** 802.1D는 타이머로 움직입니다. 기본값은 hello 2초, max age 20초, forward delay 15초이고, 포트가 listening과 learning을 거치는 데 forward delay 두 번, 약 30초가 걸립니다. RSTP는 상태를 discarding·learning·forwarding 세 개로 줄이고, 점대점 링크에서 proposal/agreement 교환으로 타이머를 기다리지 않고 포워딩으로 넘어갑니다. 단말 포트는 edge 포트(Cisco의 PortFast)로 지정해 바로 포워딩합니다.

**실무 포인트:** 루트 브리지는 기본값에 맡기지 말고 코어·분배 스위치의 우선순위를 낮춰 의도한 위치에 고정하세요. 엉뚱한 스위치가 루트가 되면 트래픽이 그 스위치를 돌아가는 비효율 경로가 생깁니다. 차단된 링크는 평소에 대역폭을 쓰지 못한다는 점도 기억하세요. 아래 LACP와 4장의 spine-leaf가 이 한계를 다른 방식으로 풉니다.

### LACP와 EtherChannel

**정의:** 링크 집선(IEEE 802.1AX)은 두 장비 사이의 병렬 풀듀플렉스 점대점 링크 여러 개를 하나의 논리 링크(LAG)로 묶습니다. LACP는 양쪽이 묶을 링크를 협상하는 제어 프로토콜이며, Cisco는 이 묶음을 EtherChannel이라 부릅니다.

**동작:** STP는 LAG를 링크 하나로 보므로 묶인 링크가 차단되지 않습니다. 프레임은 주소·포트 같은 값을 해시해 멤버 링크 하나에 배정하므로 **같은 흐름은 항상 같은 링크**로 갑니다. Cisco 문서는 호환되는 포트를 최대 8개까지 묶는다고 설명합니다.

**실무 포인트:** 10Gbps 링크 4개를 묶어도 TCP 연결 **하나**는 10Gbps를 넘지 못합니다. 합계 대역폭은 흐름이 많을 때만 쓸 수 있습니다. 백업 한 건이 느리다는 문의에 LAG 증설로 대응하면 효과가 없을 수 있습니다. AWS Direct Connect의 LAG도 LACP로 같은 엔드포인트의 연결 여러 개를 묶으며(멀티섀시 LAG는 미지원), 상세는 [전문가 과정 07: WAN과 하이브리드 연결](../networking/expert/07-wan-hybrid-connectivity.md#dx-lag)에서 다룹니다.

### FHRP: VRRP와 HSRP

**정의:** 첫 홉 이중화 프로토콜(FHRP)은 라우터 여러 대가 **가상 IP와 가상 MAC**을 공유해, 단말의 기본 게이트웨이 설정을 바꾸지 않고도 라우터 장애를 넘기게 합니다.

**왜 필요한가:** 단말은 기본 게이트웨이 주소를 하나만 가집니다. 그 라우터가 죽으면 같은 서브넷에 다른 라우터가 있어도 단말은 서브넷 밖으로 나가지 못합니다.

**VRRPv3 동작(RFC 9568, RFC 5798을 대체):**

- 같은 가상 라우터 ID(VRID)를 가진 라우터 중 하나가 **Active**(RFC 5798에서는 Master)가 되어 가상 IP로 오는 트래픽을 처리합니다. IPv4 가상 MAC은 `00-00-5E-00-01-{VRID}`, IPv6은 `00-00-5E-00-02-{VRID}`입니다.
- Active는 광고를 IPv4 멀티캐스트 `224.0.0.18`, IP 프로토콜 번호 112로 보냅니다. 광고 간격 기본값은 100센티초(1초)입니다.
- 우선순위는 가상 IP를 실제로 소유한 라우터가 255, 백업 기본값은 100입니다. Active가 우선순위 0을 보내면 VRRP 참여를 멈춘다는 뜻이며, 백업은 전체 다운 간격 대신 Skew_Time만 기다린 뒤 넘겨받습니다. preempt 기본값은 true입니다.
- 백업은 `Active_Down_Interval = 3 × 광고 간격 + Skew_Time`, `Skew_Time = ((256 − 우선순위) × 광고 간격) / 256` 동안 광고를 못 받으면 Active가 됩니다. 우선순위 100, 간격 1초라면 Skew_Time은 약 0.61초, 전환까지 약 **3.61초**입니다.

**HSRP:** Cisco의 FHRP이며 RFC 2281(정보성 문서)로 공개됐습니다. 기본 hello 3초, hold 10초이며 v1 가상 MAC은 `0000.0c07.acXX`(XX는 그룹 번호)입니다.

**실무 포인트:** 가상 MAC이 새 Active로 옮겨 가므로, 전환 직후 이웃과 스위치가 새 위치를 학습해야 합니다([Part 1의 ARP](./06-network-fundamentals-part1.md#arp)의 Gratuitous ARP 참고). 전환 시간은 FHRP 타이머와 STP 수렴, 상위 라우팅 수렴을 합쳐서 봐야 합니다.

---

<a id="lan-topologies"></a>

## 4. LAN 토폴로지: 계층형과 spine-leaf

### 캠퍼스: 2계층과 3계층

**정의:** 캠퍼스 LAN은 전통적으로 액세스·분배·코어 세 계층으로 나눕니다.

| 계층 | 역할 |
|---|---|
| 액세스 | 단말이 연결되는 망의 가장자리 |
| 분배(distribution) | 액세스 스위치를 모으고 L2/L3 경계, 접근 정책, 이중 경로를 제공 |
| 코어 | 모든 블록과 데이터센터·WAN을 잇는 백본 |

**동작:** Cisco 설계 가이드는 건물 하나 정도의 작은 사이트에는 분배와 코어를 합친 **2계층(collapsed core)** 을, 분배 블록이 여럿인 큰 사이트에는 장애 격리와 변경 통제가 쉬운 **3계층**이 적합하다고 설명합니다.

### 데이터센터: spine-leaf

**정의:** spine-leaf(Clos) 구조에서는 **모든 leaf가 모든 spine에 연결**되고(풀메시), 서버는 leaf에 붙습니다. 이 문서는 leaf끼리, spine끼리 직접 연결하지 않는 기본 2계층 구조를 가정합니다. Cisco ACI의 다계층 구성처럼 leaf 아래에 leaf를 한 단 더 두는 변형도 있습니다.

**동작:**

- leaf와 spine 사이 링크는 L3이고, ECMP로 모든 spine 경로에 흐름을 나눕니다. STP가 링크를 차단하지 않으므로 모든 업링크를 동시에 씁니다.
- 위 가정에서 다른 leaf에 있는 서버로 가는 트래픽은 항상 **leaf → spine → leaf**로, 스위치 3대(스위치 간 링크 2개)를 거칩니다. 어느 서버 쌍이든 거리가 같으므로, Cisco가 이 구조의 장점으로 드는 일관된 지연을 얻습니다.
- 포트가 더 필요하면 leaf를, 대역폭이 더 필요하면 spine을 추가합니다.

| 비교 | 전통 3계층 (L2 + STP) | spine-leaf (L3 + ECMP) |
|---|---|---|
| 이중 링크 | STP가 일부 차단 | ECMP로 모두 사용 |
| 서버 간 거리 | 위치에 따라 다름 | leaf → spine → leaf로 일정 |
| L2 확장 | VLAN을 넓게 펼침 | 필요하면 VXLAN/EVPN 오버레이 |

**실무 포인트:** spine-leaf에서 VLAN을 여러 leaf에 걸쳐야 하면 L3 underlay 위에 VXLAN/EVPN overlay를 올립니다. 식별자·경로·데이터 평면을 증거로 확인하는 방법은 [전문가 과정 03: 데이터센터 EVPN](../networking/expert/03-datacenter-evpn.md)에서 이어집니다.

---

<a id="nat-pat-cgnat"></a>

## 5. NAT, SNAT, PAT, CGNAT

NAT의 기본 정의와 "L3 장비가 L4 포트를 건드린다"는 특성은 [Part 1의 NAT](./06-network-fundamentals-part1.md#nat)에서 다뤘습니다. 여기서는 용어를 정리하고, 변환 테이블이 실제로 어떻게 채워지며 언제 고갈되는지 봅니다.

### 용어 정리

| 용어 | 바꾸는 것 | 예 |
|---|---|---|
| Basic NAT (정적 1:1 포함) | IP 주소만 | 사설 IP 하나 ↔ 공인 IP 하나. AWS 인터넷 게이트웨이의 공인 IPv4 처리 |
| NAPT / PAT | IP 주소 + 전송 식별자(TCP·UDP 포트, ICMP 쿼리 ID) | 여러 내부 호스트가 공인 IP 하나를 공유 |
| SNAT | 출발지 주소(와 포트) | 내부에서 인터넷으로 나가는 트래픽 |
| DNAT | 목적지 주소(와 포트) | 포트 포워딩, 로드밸런서의 대상 전달 |

RFC 3022는 Basic NAT와 NAPT를 "전통적 NAT"로 정의합니다. 세션은 사설망에서 바깥으로 시작하며, 첫 아웃바운드 패킷이 매핑을 만듭니다. SNAT·DNAT는 Linux netfilter의 대상 이름에서 온 용어로, PAT는 보통 SNAT의 한 형태로 구현됩니다.

### PAT 변환 테이블 따라가기

예시 주소는 내부 호스트에 RFC 1918 사설 대역을, 공인 IP와 서버에는 RFC 5737 문서용 대역(`203.0.113.0/24`, `198.51.100.0/24`)을 씁니다. 아래 애니메이션에서 두 내부 호스트는 일부러 **같은 출발지 포트 50000**을 씁니다. 공인 IP가 하나뿐이므로 NAT 장비는 공인 **포트**로 둘을 구분합니다.

![PAT 애니메이션. ① 사설망 10.0.1.0/24의 Host-A(10.0.1.10)가 출발지 10.0.1.10:50000으로 서버 198.51.100.20:443에 패킷을 보낸다. ② NAT 장비는 변환 테이블에 10.0.1.10:50000 → 203.0.113.10:30001 행을 만들고 출발지를 공인 주소 203.0.113.10:30001로 바꿔 내보낸다. ③ Host-B(10.0.1.20)도 출발지 포트 50000을 쓰므로, NAT는 같은 공인 IP의 다른 포트 30002를 배정해 10.0.1.20:50000 → 203.0.113.10:30002 행을 만든다. ④ 서버의 응답은 목적지 203.0.113.10:30002로 돌아오고, NAT는 공인 포트로 테이블을 찾아 2행과 일치시킨다. ⑤ NAT는 목적지를 10.0.1.20:50000으로 되돌려 Host-B에 전달한다.](../.gitbook/assets/ko-basics-06-network-fundamentals-part5-anim-1.svg)

응답 패킷이 돌아올 때 NAT가 보는 것은 **목적지(공인 IP:포트)** 입니다. 일치하는 행이 없으면, 예를 들어 외부에서 먼저 시작한 연결이거나 매핑이 이미 만료됐다면, 패킷은 어느 내부 호스트로도 갈 수 없습니다. NAT 뒤의 서버에 외부에서 접속하려면 정적 매핑(DNAT)이 따로 필요한 이유입니다.

### 포트 고갈

**동작:** 포트 필드는 16비트이므로 공인 IP 하나가 같은 목적지에 동시에 열 수 있는 연결 수에는 상한이 있습니다. AWS NAT 게이트웨이는 이 한계를 구체적으로 공개합니다.

- 공인 IPv4 주소 **하나당**, **고유 목적지 하나당**(목적지 IP·목적지 포트·프로토콜 조합) 최대 **55,000개** 동시 연결
- NAT 게이트웨이 하나에 IPv4 주소를 최대 8개(기본 1개 + 보조 7개) 연결 가능, 즉 같은 목적지에 최대 440,000개. 단 퍼블릭 NAT 게이트웨이의 Elastic IP는 기본 할당량이 2개라 증설 요청이 필요
- 포트를 배정하지 못하면 CloudWatch `ErrorPortAllocation` 지표가 0보다 커짐
- 350초 동안 유휴인 연결은 만료되며, 이후 그 연결로 보내면 NAT 게이트웨이가 RST를 돌려줌

**실무 포인트:** 쿠버네티스 노드 수백 대의 Pod가 **같은 외부 API 하나**(같은 IP:443)를 호출하면 목적지가 하나뿐이라 한도에 먼저 닿습니다. 연결 재사용(keep-alive, 커넥션 풀), 보조 IP 추가, 서브넷을 나눠 NAT 게이트웨이 분산, 지원되는 AWS 서비스는 VPC 엔드포인트로 NAT 경로에서 빼기([Part 4의 아웃바운드 경로](./06-network-fundamentals-part4.md) 참고) 순으로 검토하세요. 오래 유휴 상태로 두는 연결에는 350초보다 짧은 TCP keepalive를 설정합니다.

### CGNAT와 100.64.0.0/10

**정의:** CGNAT(Carrier-Grade NAT)는 통신사가 가입자 여러 명을 공인 IPv4 주소 하나 뒤에 두는 대규모 NAT입니다. 가입자 공유기에서 한 번, 통신사 CGN에서 한 번 변환되는 경우가 많습니다.

**동작:**

- RFC 6598은 CGN과 가입자 장비(CPE) 사이 구간에 쓰도록 **`100.64.0.0/10` 공유 주소 공간(Shared Address Space)** 을 할당했습니다. 이 대역은 RFC 1918 사설 대역(`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)과 **별개**이며, 가입자 내부망이 RFC 1918을 써도 겹치지 않게 하려는 목적입니다.
- 이 대역의 패킷과 경로 정보는 통신사 경계를 넘지 않아야 하고, 통신사는 유입되는 경로 광고를 필터링해야 합니다.
- RFC 6888은 CGN이 가입자별 외부 포트 수를 제한할 수 있어야 하고, 자원이 부족해 매핑을 못 만들면 기존 매핑을 지우지 말고 새 패킷을 버리도록 요구합니다. 가입자 식별 로그에는 외부 주소, 외부 포트, 시각이 필요합니다.

**실무 포인트:**

- 모바일·일부 가정용 회선의 사용자는 공인 IP를 공유할 수 있습니다. IP 하나만으로 차단하거나 속도를 제한하면 무관한 사용자까지 막힐 수 있고, 사고 조사에는 IP와 함께 **포트와 정확한 시각**이 필요합니다.
- CGNAT 뒤의 지점은 외부에서 먼저 연결을 열 수 없으므로, 사이트 간 VPN은 지점 쪽에서 시작하는 방식으로 설계합니다.
- AWS VPC는 `100.64.0.0/10` 범위의 CIDR 블록을 VPC에 연결하는 것을 허용합니다. 사설 주소가 부족할 때 후보가 되지만, 연결해야 하는 온프레미스망이나 통신사 구간이 같은 대역을 쓰지 않는지 먼저 확인하세요.

---

<a id="wan-types"></a>

## 6. WAN 유형

**정의:** WAN은 지리적으로 떨어진 사이트(본사, 지점, 데이터센터, 클라우드)를 잇는 망입니다. 대부분 통신사의 회선을 사서 쓰므로, 고르는 것은 "어떤 서비스를 사는가"입니다.

| 유형 | 사는 것 | 라우팅·주소 | 장점 | 주의점 |
|---|---|---|---|---|
| 전용회선(leased line) | 두 지점 사이의 고정 대역 점대점 회선 | 양 끝 라우터가 직접 경로를 교환 | 대역과 지연이 일정, 다른 고객과 공유 안 함 | 지점마다 회선이 필요하고 비용이 큼 |
| MPLS L3VPN | 통신사 MPLS 망 안의 고객 전용 가상 라우팅 | 통신사 PE 라우터가 고객 연결을 VRF에 묶음, CE–PE 간 정적·RIP·OSPF·BGP | 사이트 간 any-to-any, 통신사 SLA | 통신사에 종속, 인터넷 회선보다 비쌈 |
| 브로드밴드 인터넷 | 광·케이블 등 인터넷 접속 | 공인 또는 CGNAT 주소, 경로 제어 불가 | 대역 대비 저렴 | 최선 노력 품질, 기밀성은 IPsec 등 오버레이로 직접 확보 |
| LTE/5G | 이동통신 데이터 접속 | 보통 통신사 NAT 뒤, 외부 착신 어려움 | 배선 없이 빠르게 개통, 백업 회선 | 지연·대역 변동, 요금 체계 |
| SD-WAN | 위 회선들 위의 관리형 오버레이 | 애플리케이션 흐름별 정책으로 터널 경로를 선택 | 여러 회선을 묶어 애플리케이션별 경로 선택 | 하위 회선(underlay) 품질 한계는 그대로 |

**동작 포인트:**

- **MPLS L3VPN**(RFC 4364)에서 통신사 PE 라우터는 기본 포워딩 테이블과 별도로 VRF라는 라우팅 테이블을 두고, 고객 사이트가 연결된 회선을 VRF에 묶습니다. BGP로 나르는 고객 경로 앞에는 8바이트 Route Distinguisher를 붙여 VPN-IPv4 주소로 만들므로, 서로 다른 고객이 같은 사설 대역을 써도 경로가 섞이지 않습니다. CE와 PE는 정적 경로, RIP, OSPF, BGP 중 하나로 경로를 교환합니다.
- **SD-WAN**은 하나의 회선 종류가 아니라 서비스 모델입니다. MEF 70.2는 SD-WAN 서비스를 그 아래의 Underlay Connectivity Service(인터넷 접속, MPLS 등)와 구분해 정의하고, 사이트 사이를 잇는 터널을 Tunnel Virtual Connection(TVC)으로, 애플리케이션 흐름마다 적용할 경로 규칙을 정책(Policy)으로 정의합니다.
- 클라우드로 가는 WAN 진입점은 AWS Site-to-Site VPN과 Direct Connect입니다([Part 4의 클라우드 매핑](./06-network-fundamentals-part4.md) 참고). 이중화 설계, BGP 경로 선택, 터널 MTU, 비용 비교는 [전문가 과정 07: WAN과 하이브리드 연결](../networking/expert/07-wan-hybrid-connectivity.md)에서 다룹니다.

**실무 포인트:** WAN을 고를 때는 대역만 보지 말고 지연·지터, 장애 시 전환 방식, 회선이 다른 통신사·다른 경로로 들어오는지(물리적 다양성)를 함께 기록하세요. 같은 관로를 지나는 두 회선은 굴착 사고 한 번에 같이 끊깁니다.

---

## 7. 클라우드에서는

[Part 4](./06-network-fundamentals-part4.md)는 전통적 개념과 AWS의 대응을 넓게 비교했습니다. 이 표는 이 문서에서 다룬 **장비와 결정**에 한정해 무엇이 같고 무엇이 다른지 정리합니다.

| 전통 장비·기능 | AWS 대응 | 다른 점 |
|---|---|---|
| 서브넷 기본 게이트웨이(라우터, SVI) | VPC 라우터와 VPC 라우트 테이블 | 서브넷의 네트워크 주소 + 1을 AWS가 VPC 라우터용으로 예약. 라우트 테이블은 VPC CIDR의 `local` 경로를 자동으로 가짐 |
| FHRP(VRRP·HSRP) | 직접 구성하지 않음 | 게이트웨이 주소가 VPC 라우터이고 VPC는 브로드캐스트를 지원하지 않으므로, 가상 IP·가상 MAC을 넘겨받는 L2 방식이 아님. 이중화는 여러 AZ와 로드밸런서 상태 확인으로 설계 |
| 인터넷 경계 라우터 + 정적 1:1 NAT | 인터넷 게이트웨이(IGW) | 수평 확장·이중화된 VPC 구성 요소. 공인 IPv4를 가진 인스턴스에 논리적인 1:1 NAT 제공 |
| PAT 장비 | NAT 게이트웨이 | IP당·목적지당 55,000 동시 연결, IP 최대 8개, 대역 5Gbps에서 100Gbps까지 자동 확장, 보안 그룹 연결 불가, 유휴 350초 |
| 코어 라우터, WAN 허브 | Transit Gateway | 리전 단위 가상 라우터. 첨부(attachment)마다 라우트 테이블 하나에 연결(association)하고, 여러 테이블에 경로를 전파(propagation) |
| 상태 기반 방화벽 | 보안 그룹 | 상태 저장. 허용 규칙만 있고 모든 규칙을 평가. 인스턴스(네트워크 인터페이스) 수준 |
| 라우터 인터페이스의 무상태 ACL | 네트워크 ACL | 상태 비저장. 허용·거부 규칙을 번호 오름차순으로 평가해 처음 일치한 규칙 적용. 서브넷 수준. 응답용 임시 포트를 따로 허용해야 함 |

**보안 그룹과 NACL의 차이가 장애로 나타나는 지점:** NACL은 응답 트래픽을 자동으로 허용하지 않습니다. 서브넷 안의 인스턴스가 클라이언트로 외부에 요청하면 응답은 그 인스턴스 OS가 고른 **임시 포트**로 돌아오므로, 인바운드 NACL에 해당 범위를 허용해야 합니다. AWS 문서 기준으로 많은 Linux 커널은 32768–61000, Windows Server 2008 이후는 49152–65535, NAT 게이트웨이·ELB·Lambda는 1024–65535를 씁니다. 보안 그룹만 쓰는 구성에서는 응답이 자동 허용되므로 이 문제가 생기지 않습니다.

---

## 마무리

장비는 결국 표를 조회해 결정을 내리는 기계입니다. 스위치는 MAC 테이블, 라우터는 FIB, 방화벽은 상태 테이블, 로드밸런서는 리스너 규칙, NAT는 변환 테이블을 봅니다. 이중화는 L2에서는 루프(STP), 묶음 링크에서는 흐름 단위 분배(LACP), 게이트웨이에서는 가상 주소의 소유권 이전(FHRP)이라는 고유한 절충을 만듭니다.

장애를 조사할 때는 "패킷이 마지막으로 정상 처리된 장비의 표에 무엇이 있었는가"를 확인하세요. MAC 테이블의 학습 위치, 라우팅 조회 결과, 상태·NAT 테이블의 항목, NAT 게이트웨이의 `ErrorPortAllocation`처럼 표를 직접 보여 주는 증거가 추측보다 빠릅니다.

---

## 다음 문서

- [전문가 과정 03: 데이터센터 EVPN](../networking/expert/03-datacenter-evpn.md): spine-leaf 위의 VXLAN/EVPN 오버레이
- [네트워크 전문가 과정](../networking/expert/README.md): WAN과 하이브리드 연결, CDN과 엣지를 포함한 전체 워크북 지도
- [네트워킹 학습 경로](../networking/README.md#learning-path): 컨테이너·Service에서 CNI 구현으로
- [Part 4: 요청의 여정과 클라우드](./06-network-fundamentals-part4.md): AWS·쿠버네티스 매핑 전체

## 참고 자료

표준·RFC

- [IEEE 802.1Q-2022: Bridges and Bridged Networks](https://standards.ieee.org/ieee/802.1Q/10323/)
- [IEEE 802.1AX: Link Aggregation](https://1.ieee802.org/tsn/802-1ax-rev/)
- [RFC 9568: VRRP Version 3 for IPv4 and IPv6](https://www.rfc-editor.org/rfc/rfc9568.html) (RFC 5798 대체), [RFC 5798](https://www.rfc-editor.org/rfc/rfc5798.html)
- [RFC 2281: Cisco Hot Standby Router Protocol (HSRP)](https://www.rfc-editor.org/rfc/rfc2281.html)
- [RFC 3022: Traditional IP Network Address Translator](https://www.rfc-editor.org/rfc/rfc3022.html)
- [RFC 6598: IANA-Reserved IPv4 Prefix for Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598.html)
- [RFC 6888: Common Requirements for Carrier-Grade NATs](https://www.rfc-editor.org/rfc/rfc6888.html)
- [RFC 1918: Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918.html)
- [RFC 1812: Requirements for IP Version 4 Routers](https://www.rfc-editor.org/rfc/rfc1812.html)
- [RFC 4364: BGP/MPLS IP Virtual Private Networks](https://www.rfc-editor.org/rfc/rfc4364.html)
- [RFC 5737: IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737.html)
- [NIST SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/) ([PDF](https://www.mplify.net/wp-content/uploads/MEF-70.2.pdf))

벤더 문서

- [Cisco: Inter-Switch Link and IEEE 802.1Q Frame Format](https://www.cisco.com/c/en/us/support/docs/lan-switching/8021q/17056-741-4.html)
- [Cisco Catalyst 9300: Configuring VLAN Trunks](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-12/configuration_guide/vlan/b_1712_vlan_9300_cg/configuring_vlan_trunks.html)
- [Cisco: Configure InterVLAN Routing with Catalyst Switches](https://www.cisco.com/c/en/us/support/docs/lan-switching/inter-vlan-routing/41260-189.html)
- [Cisco: Understand Rapid Spanning Tree Protocol (802.1w)](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html)
- [Cisco: Understand and Tune Spanning Tree Protocol Timers](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/19120-122.html)
- [Cisco Meraki: Determining the RSTP/STP Root Bridge](https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Determining_the_RSTP%2F%2F%2F%2FSTP_Root_Bridge_on_an_MS_Switch_network)
- [Cisco: Understand EtherChannel Load Balance and Redundancy](https://www.cisco.com/c/en/us/support/docs/lan-switching/etherchannel/12023-4.html)
- [Cisco: Medium Enterprise Design Profile, LAN Design](https://www.cisco.com/en/US/docs/solutions/Enterprise/Medium_Enterprise_Design_Profile%28MEDP%29/chap2.html)
- [Cisco: Massively Scalable Data Center Network Fabric White Paper](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-743245.html), [Cisco ACI Multi-tier Architecture White Paper](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-742214.html)
- [Linux ip-link(8)](https://man7.org/linux/man-pages/man8/ip-link.8.html), [bridge(8)](https://man7.org/linux/man-pages/man8/bridge.8.html), [iptables-extensions(8): SNAT·DNAT 대상](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html)

AWS 문서

- [NAT gateway basics](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html), [Troubleshoot NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html), [NAT gateway CloudWatch metrics](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html)
- [Internet gateways](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [How AWS Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)
- [Compare security groups and network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html#VPC_Security_Comparison), [Custom network ACLs and ephemeral ports](https://docs.aws.amazon.com/vpc/latest/userguide/custom-network-acl.html)
- [VPC CIDR blocks](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html), [Subnet sizing (reserved addresses)](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [How Elastic Load Balancing works](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)
- [Direct Connect link aggregation groups](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)
