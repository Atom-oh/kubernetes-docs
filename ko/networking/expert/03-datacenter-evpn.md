# 03. 데이터센터 EVPN: 격리와 데이터 평면 증거

> **마지막 업데이트**: 2026년 9월 15일
> **실습 경계**: 별도로 준비한 본인 소유의 일회용 Linux fabric VM. 운영 fabric이나 클라우드 리소스는 사용하지 않습니다.
> **검증 상태**: 공식 문서, upstream 토폴로지, FRR CLI/template 소스를 확인했으며 집필 중 실습을 **실행하지 않았습니다**.

EVPN BGP 세션 established는 관찰의 출발점이며 fabric 전체의 정상 동작을 보증하지 않습니다.
이 워크북에서는 frame 또는 packet이 VLAN, VNI, VRF, underlay를 통과하는 경로를 추적하고 격리와 복원을 증명합니다.
먼저 [입문 8개 장](../beginner/README.md)과 [라우팅 정책](02-routing-policy-convergence.md)을 완료합니다.
Bridge, neighbor, 커널 경로 증거를 해석할 때 [Linux 네트워크 스택](../../kernel/02-network-stack.md)을 활용합니다.

## 1. 계층별로 아키텍처 읽기

| 1차 자료 | 실습 전에 만들 산출물 |
|---|---|
| [netlab EVPN module](https://netlab.tools/module/evpn/) | 선택한 장치의 기능/provider 점검표 |
| [netlab platform 지원](https://netlab.tools/platforms/)과 [FRR 주의 사항](https://netlab.tools/caveats/#frrouting) | 컨테이너 FRR도 VM 커널에 의존하는 이유 |
| [FRR EVPN](https://docs.frrouting.org/en/latest/evpn.html) | Linux bridge, VXLAN 인터페이스, SVI, VRF와 EVPN 개념의 대응표 |
| [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.html), [RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html) | 캡슐화 그림과 경로 식별자/import 정책의 차이 |
| [RFC 9135](https://www.rfc-editor.org/rfc/rfc9135.html), [RFC 9136](https://www.rfc-editor.org/rfc/rfc9136.html) | IRB 설명과 prefix 광고/host 광고의 차이 |

**VLAN**은 로컬 L2 소속을 정의합니다. Access port의 VLAN과 trunk의 허용 VLAN은 서로 대체할 수 있는 설정이 아닙니다.
**LACP**는 링크 집성 그룹을 협상합니다. Member 상태와 hashing이 가용 용량에 영향을 주며 단일 flow가 모든 member를 쓰는 것은 아닙니다.
**STP**는 브리지 토폴로지의 루프를 방지합니다. 예상하지 못한 blocking port가 EVPN 이전 단계에서 트래픽 부재를 설명할 수 있습니다.
이 점검표와 함께 [netlab VLAN](https://netlab.tools/module/vlan/), [LAG](https://netlab.tools/module/lag/), [STP](https://netlab.tools/module/stp/)를 읽습니다.
선택한 소규모 lab은 LACP나 중복 STP 토폴로지를 **구성하지 않습니다**. “검증 성공” 대신 “구성하지 않음”으로 기록합니다.
다른 fabric으로 확장하기 전에는 access/trunk 소속, 의도한 LAG member, 예상 STP 포워딩 토폴로지를 먼저 확인합니다.

**Underlay**는 VTEP 사이의 IP 도달 가능성을 제공합니다. 라우팅, 반환 경로, 사용 가능한 MTU는 tenant 주소와 독립적으로 동작해야 합니다.
**Overlay**는 VTEP 사이에서 tenant 트래픽을 운반합니다. VXLAN은 외부 Ethernet/IP/UDP/VXLAN 캡슐화를 추가합니다.
외부 목적지는 tenant host가 아니라 원격 VTEP이며 VXLAN header의 VNI가 가상 세그먼트를 식별합니다.
VLAN ID는 로컬 의미를 가지므로 VNI와 숫자가 같다고 가정하지 말고 매핑을 확인합니다.

## 2. 식별자·경로·포워딩 구분

| 개념 | 의미 | 확인할 증거 |
|---|---|---|
| VTEP | 캡슐화/역캡슐화 끝점 | 로컬 주소, 원격 도달 가능성, VXLAN 인터페이스 |
| L2VNI / MAC-VRF | 브리지 tenant 세그먼트 | VLAN/bridge 매핑, 학습한 원격 MAC과 VTEP |
| L3VNI / IP-VRF | 라우팅 tenant 문맥 | VRF table, transit VNI, 원격 prefix |
| RD | 겹치는 VPN 경로의 식별자 구분 | 발신 경로의 RD |
| RT | Import/export 정책의 소속을 표현하는 extended community | 광고 export RT와 수신자의 유효 import RT 집합 |
| SVI / IRB | Bridge domain 경계의 라우팅 | Gateway 주소/MAC, SVI-to-VRF 연결, 라우팅 probe |

서로 다른 RD도 같은 VPN에 속할 수 있으며 RD가 같다고 소속이 허용되는 것은 아닙니다.
RT는 패킷 방화벽이 아닙니다. 의도하지 않은 경로 import가 도달 가능성을 만들 수 있지만 경로만으로 포워딩을 증명할 수는 없습니다.
Asymmetric IRB에서는 ingress가 라우팅하고 원격 측이 목적지 세그먼트로 bridging하므로 참여 gateway에 관련 목적지 L2 상태가 필요합니다.
Symmetric IRB에서는 양 끝이 L3VNI를 사이에 두고 tenant 라우팅을 수행합니다.
BGP에 EVPN address family가 있다는 이유만으로 symmetric IRB를 사용한다고 추정하지 않습니다.

| EVPN 경로 | 이 워크북에서의 역할 | 존재만으로 증명할 수 없는 것 |
|---|---|---|
| Type 2: MAC/IP advertisement | MAC과 선택적인 대응 IP를 광고하여 원격 host 정보 제공 | 모든 광고 MAC이 올바른 bridge에 설치되었는지 |
| Type 3: IMET | Ingress replication 같은 BUM 전달 구성에 필요한 참여 정보 | Unicast host 전달이나 tenant 라우팅의 성공 |
| Type 5: IP prefix | 특정 host MAC 광고와 독립적인 tenant IP 도달 정보 | 수신자의 prefix import 또는 VTEP 도달 가능성 |

BUM은 broadcast, unknown unicast, multicast를 뜻합니다. Type-3 경로와 함께 VTEP의 복제 상태도 중요합니다.
보고서에서 전역 EVPN 경로, VNI/VRF별 import 상태, 실제 포워딩 증거를 구분합니다.

## 3. 재현 가능한 upstream 실습 선택

[netlab 홈페이지](https://netlab.tools/)에서 연결한 예제 저장소의 revision **`7c4fa0dac160d3cc2eac41e11f20b74d083bb896`**을 사용합니다.

| 단계 | 정확한 upstream 경로 | 의도한 기준 동작 |
|---|---|---|
| A: L2 | [EVPN/vxlan-bridging](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/vxlan-bridging) | Red의 h1↔h2, blue의 h3↔h4 통신; inter-VLAN routing 없음 |
| B: L3 | [EVPN/l3vpn](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/l3vpn) | Red VRF의 h1↔h2, blue VRF의 h3↔h4 라우팅; cross-VRF import 없음 |

두 실습 모두 `clab`, 스위치 s1/s2 두 대, Linux host 네 대, OSPF underlay, AS65000 EVPN을 사용합니다.
Stage A upstream은 EOS와 Cumulus를 명시하고 Stage B는 EOS를 기본값으로 둡니다.
**이 워크북의 선택은 s1과 s2를 각각 `frr`로 덮어쓰는 것**입니다. 문서화된 `-s nodes.s1.device=frr -s nodes.s2.device=frr` [시작 옵션](https://netlab.tools/netlab/up/)을 사용합니다.
[EVPN 지원표](https://netlab.tools/module/evpn/#platform-support)는 FRR의 VLAN-based EVPN, symmetric IRB, iBGP/IGP 지원을 명시합니다.
이 표가 모든 오래된 이미지나 provider 조합의 동작을 보장하지는 않습니다.

**단계별 단독 VM 한 대**를 준비하거나, 증거를 내보낸 뒤 소유한 빈 VM checkpoint를 복원하여 단계를 바꿉니다.
공유 호스트에 node/lab 이름이 충돌하는 두 복사본을 함께 시작하지 않습니다.
Stage B는 routed host link와 transit VNI를 가진 L3VPN 실습이며 access-VLAN anycast gateway나 host mobility 실습이 **아닙니다**.
IRB 차이는 읽기 자료로 학습합니다. 선택한 L3-only 모델이 요구하지 않는 Type-2/3 또는 anycast 검사를 통과했다고 보고하지 않습니다.

## 4. 실습별 선행 조건과 기록

- 콘솔에 접근 가능한 본인 소유 x86-64 Ubuntu 24.04 Linux VM을 사용합니다. **활성화한 6-container 단계 하나당** 계획용 자원으로 4 vCPU, RAM 8 GiB, 여유 디스크 20 GiB를 잡고 실제 사용량을 측정합니다.
- [netlab Ubuntu 준비](https://netlab.tools/install/ubuntu/)와 [containerlab provider 준비](https://netlab.tools/labs/clab/)를 먼저 완료합니다. Docker, 필요한 Ansible 의존성, node 이미지도 포함합니다.
- 선택한 FRR EVPN/VXLAN/VRF 기능을 지원하는 netlab release를 사용하고 정확한 release, 예제 revision, node override 두 개를 기록합니다.
- 확인한 netlab [FRR 장치 정의](https://github.com/ipspace/netlab/blob/4d85d13365caf3962a72ba59ec57a2e4450f365f/netsim/devices/frr.yml)는 `quay.io/frrouting/frr:10.6.1`을 선택합니다. CLI 예제는 FRR 10.6.1과 대조했습니다. 실제 설치 release의 image와 digest를 기록하고 동일하다고 가정하지 않습니다.
- FRR/clab은 VM 커널의 bridge, VXLAN과 Stage B의 VRF 지원이 필요합니다. Upstream 준비 과정이 **이 소유 VM**에 모듈을 적재할 수 있습니다. 필요한 모듈을 적재할 수 없는 제한된 Codespace는 대체 환경이 아닙니다.
- VM에 iproute2, iputils, tcpdump, GNU `timeout`을 준비합니다. DF/크기 probe에는 VM의 iputils를 기록한 node namespace에서 사용하며 Alpine host image의 BusyBox `ping`이 같은 옵션을 지원한다고 가정하지 않습니다.
- 선택한 FRR/Linux host image에는 상용 라우터 라이선스가 필요하지 않습니다. EOS/Cumulus를 유지하면 image 접근, 라이선스, CLI 조건이 다른 별도 플랫폼 선택입니다.
- VM 소유자가 Docker/provider 권한을 준비하며 `vtysh`와 namespace 작업에도 적절한 실습 권한이 필요합니다. 관리 인터페이스, 작업용 PC 경로, 클라우드 설정은 변경하지 않습니다.

대상이 없는 **Stage A VM 셸**에서 실행합니다.

```bash
test ! -e "$HOME/expert-fabric-examples"
git clone --no-checkout https://github.com/ipspace/netlab-examples.git "$HOME/expert-fabric-examples"
git -C "$HOME/expert-fabric-examples" checkout --detach 7c4fa0dac160d3cc2eac41e11f20b74d083bb896
cd "$HOME/expert-fabric-examples/EVPN/vxlan-bridging"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

부재 확인이 실패하면 중단합니다. Clone은 새로 소유한 객체이며 VM 폐기 전까지 증거와 함께 보관합니다.
별도의 Stage B VM에서도 clone/revision 절차를 반복한 뒤 작업 디렉터리를 `EVPN/l3vpn`으로 선택합니다.
각 단계의 관찰 전에 소유자가 `clab` provider와 FRR node override 두 개로 공식 시작 절차를 완료해야 합니다.
빈 VM checkpoint, 생성된 lab 식별자, 정확한 시작 옵션, 정상 상태의 실험 전 checkpoint를 기록합니다.
Bridge/VTEP/VRF 생성은 이 준비 절차가 담당합니다. [FRR 자체는 Linux 인터페이스를 생성하지 않습니다](https://docs.frrouting.org/en/latest/evpn.html#the-linux-vxlan-dataplane).
빈 컨테이너에 BGP 설정만 붙여 넣고 overlay가 완성되었다고 하지 않습니다.

## 5. 식별자와 데이터 평면 준비 확인

활성 단계의 **VM 셸**에서 실행합니다.

```bash
netlab status
netlab inspect nodes.s1.interfaces
netlab inspect nodes.s2.interfaces
netlab connect --dry-run s1
netlab connect s1 --show version
netlab connect s1 --show running-config
netlab connect s1 --show ip ospf neighbor
netlab connect s1 --show bgp l2vpn evpn summary
netlab connect s1 --show evpn vni
netlab connect s1 --show bgp l2vpn evpn vni
netlab connect s1 ip -d link show
netlab connect s1 bridge link show
netlab connect s1 bridge fdb show
netlab connect s1 ip route show
```

s2에서도 읽기 전용 상태 검사를 반복합니다. [Inspect](https://netlab.tools/netlab/inspect/)와 [connect](https://netlab.tools/netlab/connect/) 문서로 node/interface 매핑을 해석합니다.
`netlab connect s1`은 **FRR 컨테이너의 Linux 셸**로 들어갑니다. `vtysh`를 입력하면 FRR CLI로 이동합니다.
`s1#`은 FRR 운영 모드이며 `configure terminal`은 설정 모드 진입, `end`는 운영 모드 복귀, 운영 모드의 `exit`는 Linux로 복귀입니다.
`ip`/`bridge`는 Linux, `show`는 FRR에서 실행하거나 위처럼 VM의 `--show` wrapper를 사용합니다.

정확한 컨테이너마다 `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`로 image를 기록합니다. 이름이 확인된 실습 객체를 개별 조회합니다.
로컬 VTEP 주소를 가진 실제 VXLAN 인터페이스, bridge 소속, 동작 중인 VNI, 원격 VTEP 도달 가능성이 필요합니다.
Stage B에는 `show vrf vni`, Linux VRF device/table, red/blue에 연결된 host link도 필요합니다.
현재 [FRR 주의 사항](https://netlab.tools/caveats/#frrouting)은 VLAN/VRF 초기화가 멱등적이지 않고 설정 수집에 Linux interface 상태가 포함되지 않는다고 설명합니다.
준비 실패를 초기화 반복 실행으로 고치려 하지 말고 실패 증거를 보존한 뒤 소유한 준비 checkpoint로 돌아갑니다.

다음 매핑은 기억이 아닌 실제 출력으로 작성합니다.

| Host | Data IP/prefix | Access VLAN 또는 routed link | VRF | L2VNI / L3VNI | 로컬 / 원격 VTEP | 캡처 인터페이스 |
|---|---|---|---|---|---|---|
| h1 | 기록 | Stage A red / Stage B routed | 기록 | 기록 또는 근거 있는 N/A | 기록 | 기록 |
| h2 | 기록 | Stage A red / Stage B routed | 기록 | 기록 또는 근거 있는 N/A | 기록 | 기록 |
| h3/h4 | 개별 기록 | Blue | 기록 | 기록 또는 근거 있는 N/A | 기록 | 기록 |

## 6. Stage A: L2 전달과 분리 증명

`netlab connect h1 ip address show`에서 host 이름을 하나씩 정확히 바꾸어 h1/h2/h3/h4의 data 주소를 읽습니다. 이 명령은 host 컨테이너 안에서 실행되므로 VM에 iproute2를 설치해도 컨테이너의 BusyBox 구현이 바뀌지는 않습니다.
관리 주소 또는 관리망을 선택할 수 있는 미확인 hostname 대신 data 주소를 사용합니다.
VM 셸에서 매핑을 이용해 placeholder를 바꿉니다.

```bash
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
fabric_h3='REPLACE_WITH_H3_DATA_IPV4'
fabric_h4='REPLACE_WITH_H4_DATA_IPV4'
netlab connect h1 ping -c 5 -W 1 "$fabric_h2"
netlab connect h3 ping -c 5 -W 1 "$fabric_h4"
netlab connect h1 ping -c 5 -W 1 "$fabric_h3"
netlab connect s1 --show bgp l2vpn evpn route type 2
netlab connect s1 --show bgp l2vpn evpn route type 3
netlab connect s1 bridge fdb show
```

원격 Type-2/MAC 학습을 기대하기 전에 의도한 host 트래픽을 발생시킵니다.
각 원격 MAC을 올바른 VNI/VTEP와 연결하고 Type-3/복제 상태도 의도한 세그먼트와 대응하는지 확인합니다.
첫 두 probe는 성공하고 cross-VLAN probe는 라우팅이 없는 설계에 따라 실패해야 합니다.
실패 하나만으로는 충분하지 않습니다. 두 긍정 대조군의 성공, 올바른 host 연결, 의도하지 않은 라우팅 경로 부재가 필요합니다.
부정 probe가 로컬 경로 부재로 실패했는지, 데이터 평면 경계까지 도달했는지를 구분해 기록합니다.

Inventory에서 s1의 스위치 간 인터페이스를 확인합니다. 고정 Stage A FRR 매핑에서는 `eth3`입니다.
다른 터미널에서 허용 probe를 반복하면서 해당 소유 인터페이스만 캡처합니다.

```bash
timeout 20s netlab capture s1 eth3 -nn -e -vv -l -c 30 udp port 4789
```

외부 VTEP 쌍, VNI, 내부 MAC/IP 쌍을 보존합니다. 빈 출력, 캡처 오류, 관리 트래픽은 증거가 아닙니다.
관찰된 캡슐화가 경로/FDB 증거와 어떻게 일치하는지 설명합니다.
이 bridging-only 실습에서 체크리스트를 채우기 위해 Type-5 tenant prefix가 반드시 있어야 한다고 기대하지 않습니다.

## 7. Stage B: VRF 라우팅 서비스 증명

별도로 준비한 Stage B VM으로 이동하고 식별자/주소 매핑을 다시 작성합니다.
`fabric_h2`, `fabric_h3`, `fabric_h4` 변수에는 **Stage B** 주소를 다시 넣습니다. Stage A 값은 재사용 가능한 증거가 아닙니다.
6절의 세 probe를 반복하여 red/blue 쌍의 성공과 cross-VRF 통신 차단을 확인합니다.
다음 상태도 조회합니다.

```bash
netlab connect s1 --show vrf vni
netlab connect s1 --show bgp l2vpn evpn route type 5
netlab connect s1 --show bgp vrf red ipv4 unicast
netlab connect s1 --show ip route vrf red
netlab connect s1 ip -d link show type vrf
netlab connect s1 ip route show vrf red
```

Type-5 테이블에서 h2의 실제 원격 subnet, RD/export RT, red로의 import, 대응 Linux 경로를 찾아 연결합니다.
Blue도 따로 확인합니다. Red가 blue를 import하지 않는지 확인하고 s2의 반환 경로도 조사합니다.
6절처럼 underlay를 캡처하되 `eth3`이라고 가정하지 말고 **Stage B의 실제 인터페이스**를 사용합니다.
Transit VNI와 VRF의 관계를 설명합니다. 관리 주소 ping 성공은 tenant 라우팅 서비스 증거가 아닙니다.

## 8. Stage B: import 소속 하나 제거 후 복원

소유 변경 객체는 **s1의 red VRF EVPN import-RT 목록**입니다. 정확한 실행 설정과 유효 RT 목록을 보존합니다.
`netlab connect s1 --show bgp l2vpn evpn vni RED_L3VNI`의 placeholder에 기록한 red transit VNI 숫자를 넣어 import/export RT 상세 정보를 확인합니다.
사전 상태는 아래에서 `RED_RT`라 부를 명시적 import RT 하나만 있고 같은 경로를 허용하는 wildcard/추가 자동 import가 없는 것입니다.
Lab 경로가 해당 값을 export하지 않고 기존 목록도 쓰지 않는 것을 증명한 뒤에만 `BAD_RT`로 `65000:424242`를 선택합니다.
사전 상태가 다르면 다른 항목을 임의로 삭제하지 않습니다.
s1의 **FRR CLI**에서 placeholder가 아닌 실제 `RED_RT`를 사용합니다.

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import 65000:424242
  no route-target import RED_RT
 exit-address-family
end
```

원래 RT를 지우기 전에 미사용 RT를 추가하면 명시적 목록이 유지됩니다.
이 조치 없이 유일한 수동 RT를 삭제하면 자동 RT가 다시 적용되어 실험 조건이 성립하지 않을 수 있습니다.
FRR release마다 자동 RT 제어가 다르므로 VNI 상세 출력과 [실행 버전에 맞는 RT 문서](https://docs.frrouting.org/en/latest/bgp.html)로 **유효** import 집합을 확인합니다.
원래 RT가 여전히 유효하면 장애 주입 미성립으로 분류하고 복원합니다. 격리 실험을 완료했다고 하지 않습니다.

예상 결과는 전역 Type-5 광고와 BGP 세션은 유지되지만 s1의 red VRF/FIB에서 h2의 원격 prefix가 빠지고 red probe가 실패하는 것입니다.
Blue 쌍은 계속 성공하고 h2는 로컬 red gateway에 도달해야 합니다. 죽은 host나 고장 난 underlay는 RT 격리를 증명하지 못합니다.
전역/import 테이블에서 정확한 prefix를 확인하고 부정 probe의 종료 상태와 출력을 보존합니다.
원래 소속을 먼저 추가하고 임시 소속을 제거하여 같은 객체를 복원합니다.

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import RED_RT
  no route-target import 65000:424242
 exit-address-family
end
```

원래 유효 RT 집합, 원격 경로, red probe, blue 대조군이 회복되어야 합니다. RD, neighbor, export RT는 바꾸지 않습니다.

## 9. Stage B: underlay MTU 동작 측정

소유 변경 객체는 **s1의 스위치 간 데이터 인터페이스 MTU**입니다. Stage B upstream은 해당 링크에 1600을 요청하므로 선택한 인터페이스의 실제 값도 1600인지 먼저 확인합니다.
관리/access/bridge/VXLAN 인터페이스가 아니고 peer가 s2라는 것을 기록합니다.
복원용 두 번째 VM 터미널을 확보합니다. 이 단계의 매핑에서 인터페이스, h1 namespace, h2 data 주소를 넣습니다.

```bash
fabric_underlay='REPLACE_WITH_S1_TO_S2_INTERFACE'
fabric_h1_ns='REPLACE_WITH_THIS_LABS_H1_NAMESPACE'
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
netlab connect s1 ip -d link show dev "$fabric_underlay"
sudo ip netns exec "$fabric_h1_ns" ip -br address
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1200 -c 5 -W 1 "$fabric_h2"
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1400 -c 5 -W 1 "$fabric_h2"
```

기준 상태에서 두 크기가 모두 성공해야 합니다. VM의 [iputils ping](https://github.com/iputils/iputils/blob/master/doc/ping.xml)이 `-M do`를 제공하며 host 컨테이너 안에 package를 설치했다고 가정하지 않습니다.
Untagged Ethernet과 외부 IPv4에서는 ICMP payload 1400바이트가 내부 IP 1428바이트, 캡슐화 후 외부 IP 약 1478바이트가 됩니다.
실제 tag/header를 기록합니다. IPv6 transport나 추가 캡슐화는 필요한 크기를 바꿉니다.

기록한 MTU만 변경한 뒤 두 probe를 반복하고 동시에 underlay를 캡처합니다.

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1400
timeout 20s netlab capture s1 "$fabric_underlay" -nn -vv -l -c 30 'ip proto 17 or icmp'
```

작은 probe는 유지되면서 큰 probe가 손실되거나 외부 패킷이 단편화될 수 있습니다. 내부 DF만으로 외부 DF 동작까지 보장되지는 않습니다.
IPv4 protocol 필터는 port 필터가 놓칠 수 있는 후속 UDP 단편도 포함합니다. 기록한 VTEP 쌍과 첫 단편으로 VXLAN을 식별합니다.
OSPF도 MTU 불일치에 반응할 수 있으므로 BGP가 반드시 established를 유지해야 한다고 정하지 말고 이웃 상태, 오류, 단편, ICMP 피드백을 기록합니다.
크기별 차이가 나타나지 않으면 그대로 보고하고 캡슐화/단편화/offload를 조사합니다. Black hole을 만들어 보고하지 않습니다.
제한된 수집이 끝나면 즉시 복원합니다.

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1600
netlab connect s1 ip -d link show dev "$fabric_underlay"
```

OSPF/BGP, 두 크기의 probe, 두 VRF 긍정 대조군, cross-VRF 부정 조건을 다시 확인합니다.
결과를 깨끗하게 보이게 하려고 route, neighbor table, 모든 bridge를 flush하지 않습니다.

## 10. 증거와 완료 기준

| 검사 | 긍정 대조군 | 의도한 부정 증거 | 복원 증거 |
|---|---|---|---|
| L2 분리 | 같은 VLAN 두 쌍 성공, 올바른 VXLAN/FDB | 라우팅 서비스 없이 cross-VLAN 차단 | 원래 매핑과 반복 probe |
| L3 VPN | 올바른 VRF에 Type-5 import, tenant probe 성공 | 다른 VRF의 import/FIB 부재와 probe 차단 | 원래 경로/probe 행렬 |
| RT 불일치 | Blue 정상, 대상 host/로컬 gateway 정상 | 전역 경로 유지, red import 부재, red probe 실패 | 정확한 RT 목록·경로·red probe 회복 |
| MTU 축소 | 두 기준 크기 성공, underlay 확인 | 크기/단편화/인접 관계 변화 측정 또는 명시적 미재현 | MTU 1600과 전체 기준 상태 재검사 |

행마다 단계, 시각, VM/lab 식별자, upstream revision, 도구/image 버전, node/interface, 기대 결과, 실제 출력, 결론을 보관합니다.
**PASS**, **FAIL**, **BLOCKED**, 근거 있는 **N/A**를 사용합니다. 빈 경로 테이블, probe 부재, 캡처 누락만으로 PASS를 선언하지 않습니다.
Type/기능의 N/A는 선택한 모델에서 도출하며 고장 난 필수 검사를 우회하는 수단으로 사용하지 않습니다.
모든 능동 변경은 이름이 확인된 객체에서 되돌립니다. 실패하면 증거를 보존하고 기록된 소유 VM checkpoint만 복원합니다.
실험 변경은 저장하지 않으며 비멱등 초기화 재실행, 모든 lab 제거, global prune을 수행하지 않습니다.
L2/L3 서비스를 추적하고 RD/RT와 route type을 설명하며 정상 대조군이 있는 격리와 복원을 증명하면 완료입니다.
[Linux 성능](04-linux-performance.md), [클라우드/CNI 설계](05-cloud-cni-design.md), [자동화 종합 실습](06-automation-capstone.md), [퀴즈](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md)로 이어갑니다.
