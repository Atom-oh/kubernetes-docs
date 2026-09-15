# 02. 라우팅 정책과 수렴 시간 측정

> **마지막 업데이트**: 2026년 9월 15일
> **실습 경계**: 별도로 준비한 본인 소유의 일회용 Linux 라우팅 VM 한 대와 로컬 FRRouting 컨테이너.
> **검증 상태**: upstream 문서·토폴로지·CLI 소스를 확인했으며, 집필 중 라우팅 실습을 **실행하지 않았습니다**.

이 워크북의 목표는 특정 prefix가 선택된 이유를 설명하고, next hop의 도달 가능성을 증명하며, 통제된 장애 중 실제 트래픽이 겪은 변화를 측정하는 것입니다.
먼저 [입문 과정 8개 장](../beginner/README.md)과 [컨테이너·클라우드 종합 실습](../beginner/08-container-cloud-capstone.md)을 완료합니다.
프로토콜 테이블만으로 패킷 경로를 설명할 수 없다면 [Linux 포워딩](../../kernel/02-network-stack.md)을 복습합니다.

## 1. 질문을 정하고 읽기

| 읽을 자료 | 자신의 말로 답할 질문 |
|---|---|
| [BGP Labs 개요](https://bgplabs.net/)와 [FRRouting 입문](https://bgplabs.net/basic/0-frrouting/) | Linux 셸에서 할 작업과 `vtysh`에서 할 작업은 무엇인가? |
| [Local preference 실습](https://bgplabs.net/policy/5-local-preference/) | 한 경계 라우터의 선호도 변경이 다른 경계 라우터에 영향을 주는 이유는? |
| [FRR BGP 매뉴얼](https://docs.frrouting.org/en/latest/bgp.html) | 수신 경로는 언제 유효해지고, 선택·광고·설치되는가? |
| [FRR OSPF 매뉴얼](https://docs.frrouting.org/en/latest/ospfd.html) | 인접 관계가 증명하는 것은 무엇이며 IGP가 운반하는 prefix는 무엇인가? |
| [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html)과 [RFC 4456](https://www.rfc-editor.org/rfc/rfc4456.html) | 일반 iBGP 광고 규칙과 route reflection은 어떻게 다른가? |

설정 전에 해당 절을 읽고 라우팅 세션과 포워딩 링크를 구분한 그림을 만듭니다.
BGP 세션은 speaker 사이의 TCP 연결이며, 광고된 모든 목적지에 그 연결을 통해 도달할 수 있다는 뜻은 아닙니다.

## 2. 제어 평면의 모델 만들기

**IGP와 BGP는 서로 다른 문제를 풉니다.** OSPF는 관리 영역 내부에서 링크 상태 정보를 배포하고 cost를 이용해 경로를 계산합니다.
이 실습에서는 iBGP에 사용하는 loopback을 포함한 내부 도달 가능성을 제공합니다.
BGP는 속성을 가진 목적지 도달 정보를 교환하고 정책을 적용하므로 OSPF를 단순한 최단 홉 방식으로 대체하는 프로토콜이 아닙니다.
두 프로토콜 사이에 모든 경로를 무분별하게 재분배하면 불필요한 경로, 불명확한 정책, 경로 피드백이 생길 수 있습니다.

**eBGP**는 보통 서로 다른 AS 사이에서 경로를 교환하고, **iBGP**는 한 AS 내부에 BGP 정보를 전달합니다.
AS_PATH는 AS 수준의 루프를 감지하며, 일반 iBGP의 광고 제한은 내부 재광고 루프를 방지합니다.
iBGP에서 배운 경로를 다른 iBGP peer에 일반적으로 다시 광고하지 않으므로 full mesh, route reflector 또는 별도 설계가 필요합니다.
이 세션 연결도만으로 실제 포워딩 토폴로지를 추정하지 않습니다.

**유용한 포워딩에는 next-hop 해석이 선행되어야 합니다.** BGP 테이블에 경로가 보여도 next hop으로 가는 경로가 없으면 사용할 수 없습니다.
next-hop-self 같은 설계가 없다면 iBGP next hop에 외부 주소가 그대로 남을 수 있습니다.
실제로 수신한 NEXT_HOP을 확인한 뒤 라우팅 테이블을 재귀적으로 따라 인터페이스와 이웃까지 해석합니다.
OSPF 인접 관계만으로 필요한 next-hop prefix가 광고되었다고 볼 수는 없습니다.

| 계층 | 증거 | 그 증거만으로 알 수 없는 것 |
|---|---|---|
| BGP 세션 | 상태와 협상된 address family | 의도한 prefix가 허용되었는지 |
| BGP RIB | 후보 경로, 속성, 유효성, best-path 표시 | 선택한 경로가 포워딩 평면에 설치되었는지 |
| Zebra 라우팅 테이블 | 선택 경로와 설치 상태 | 패킷이 의도한 인터페이스로 나갔는지 |
| Linux FIB 조회 | 목적지의 경로, 출력 인터페이스, next hop | 반환 경로가 있는지, 필터가 없는지 |
| 패킷 관찰 | 출발지를 지정한 probe와 인터페이스 캡처 | 모든 애플리케이션·크기·ECMP 경로가 동작하는지 |

보고서에는 둘 다 “라우팅 테이블”이라고 쓰기보다 “BGP 테이블”과 “커널 포워딩 테이블”을 구분합니다.
선택한 소프트웨어 데이터 평면에서 FRR은 Zebra를 통해 경로를 전달하고 Linux가 포워딩합니다.

## 3. 검증 전에 정책 설명하기

| 수단 | 운영 목적 | 흔한 오해 |
|---|---|---|
| Prefix filter | 의도한 prefix와 길이만 수신·광고 | `/24`를 허용하면 모든 more-specific도 허용된다 |
| LOCAL_PREF | AS 내부의 출구 선호도 표현; 큰 값 우선 | 외부 AS에 어느 입구를 쓰라고 명령한다 |
| Weight | 한 라우터에만 적용하는 구현별 선호도 | BGP 속성으로 다른 라우터에 전파된다 |
| AS_PATH / prepending | AS 통과 정보를 표현하고 허용된 정책 범위에서 선택에 영향 | 짧은 경로가 높은 local preference보다 항상 우선한다 |
| MED | 수신자의 비교 규칙 아래에서 입구 선호도 제안 | 모든 이웃 AS 사이에서 항상 비교된다 |
| Community | 수신 정책이 해석할 수 있는 표식 전달 | 일치하는 정책 없이도 표식이 동작을 강제한다 |
| Route reflector | 경로 반사로 필요한 iBGP 세션 수 감소 | 없는 next-hop 경로를 만들거나 반드시 데이터 트래픽을 운반한다 |

Reflector의 ORIGINATOR_ID와 CLUSTER_LIST는 루프 방지에 쓰이며, reflector의 경로 선택 때문에 client에 대안 경로가 보이지 않을 수 있습니다.
반사된 경로를 조사할 때는 client, reflector, next-hop 도달 가능성을 각각 확인합니다.
[Route reflector 실습](https://bgplabs.net/ibgp/3-rr/)은 나중에 별도 환경에서 수행하고 이 워크북의 토폴로지에 즉석으로 추가하지 않습니다.

설정하지 않고 다음 필터를 설계합니다. upstream으로 `192.168.42.0/24`만 광고합니다.
정확한 `/24` 일치는 해당 경로를 허용하고 `192.168.42.0/25`와 제공자에게서 배운 `192.168.100.0/24`는 거부해야 합니다.
별도 계약에서 허용하지 않았다면 `0.0.0.0/0`도 거부합니다.
암묵적 거부, 평가 순서, 적용 방향을 설명합니다.
능동 필터 실습은 [광고 prefix 필터링](https://bgplabs.net/policy/3-prefix/)으로 이어갑니다. 현재 실습에 자신이 설계한 필터가 이미 적용되었다고 가정하지 않습니다.

## 4. 이 실습의 환경 준비

선정한 upstream은 **`bgplab/bgplab`의 `policy/5-local-preference/topology.yml`**, revision **`5a9fab68658ce69317b147396481714ee3478482`**입니다.
라우터 네 대 중 c1/c2는 AS65000, x1/x2는 AS65100에 속합니다.
토폴로지가 OSPF, eBGP, iBGP와 경로 광고를 구성하며 학습자는 고객 측 정책을 변경합니다.
[원본 토폴로지](https://github.com/bgplab/bgplab/blob/5a9fab68658ce69317b147396481714ee3478482/policy/5-local-preference/topology.yml)는 **netlab 2.0.0 이상**을 요구합니다.

제공된 `https://bgplabs.net/install/`은 확인일에 404를 반환했습니다. 공식 [설치와 준비](https://bgplabs.net/1-setup/)를 사용합니다.
이 워크북 전에 별도 VM에서 연결된 [Ubuntu 설치 선행 절차](https://netlab.tools/install/ubuntu/)를 완료합니다.
입문 VM, 공유 Docker 호스트, Kubernetes 노드를 재사용하지 않습니다.

- 본인 소유 x86-64 Ubuntu 24.04 VM을 할당합니다. FRR 컨테이너 네 대와 도구를 위한 **계획용 여유 자원**은 4 vCPU, RAM 8 GiB, 여유 디스크 20 GiB입니다. upstream 최소 사양이나 측정 결과는 아닙니다.
- 공식 절차에 따라 netlab, 필요한 Ansible 의존성, Docker, containerlab(`clab` provider), Git, iproute2, iputils `ping`, GNU `timeout`, tcpdump를 준비합니다.
- 설치한 netlab과 provider 버전을 기록합니다. 해당 netlab이 선택한 FRR 이미지의 tag, image ID/digest, 실제 `show version`을 남깁니다.
- CLI 예제는 FRR **10.6.1** 소스와 대조했습니다. 다른 실행 버전은 변경 전에 명령 도움말을 확인해야 하며, 일반적인 “FRR 이미지”라는 이름은 호환성 보장이 아닙니다.
- FRR은 오픈 소스이므로 이 선택에는 상용 라우터 라이선스가 필요하지 않습니다. 이미지 다운로드와 도구 준비에는 네트워크 접근이 필요합니다.
- Provider 관리에는 이 일회용 VM의 권한이 필요합니다. FRR 컨테이너에서는 Linux 셸/`vtysh`를 root로 사용합니다. VM 콘솔을 확보하고 관리 인터페이스는 변경하지 않습니다.
- VM, clone 디렉터리, lab 이름의 단독 소유권을 확인합니다. 고객/제공자 링크는 로컬 모의 링크이며 실제 ISP나 인터넷 연결이 아닙니다.

**실습 VM 셸**에서 새 clone 하나를 만듭니다. 대상 디렉터리는 없어야 합니다.

```bash
test ! -e "$HOME/expert-routing-bgplab"
git clone --no-checkout https://github.com/bgplab/bgplab.git "$HOME/expert-routing-bgplab"
git -C "$HOME/expert-routing-bgplab" checkout --detach 5a9fab68658ce69317b147396481714ee3478482
cd "$HOME/expert-routing-bgplab/policy/5-local-preference"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

부재 확인에 실패하면 중단하고 기존 디렉터리에 나머지 clone 명령을 실행하지 않습니다.
출력은 clone 외부의 증거 기록에 보관합니다.
소유자가 이 디렉터리에서 `provider=clab`, 고객 장치 `frr`, 외부 장치 `frr`로 upstream 시작 절차를 완료해야 준비가 끝납니다.
Upstream 시작 작업은 실습을 생성·구성하는 선행 작업이며 읽기 전용 명령이 아닙니다.
VM 소유자는 생성된 node/container 식별자와 실험 전 소유 VM checkpoint를 기록합니다.
집필자는 시작, 설치, 호스트 설정, 실습 제거 작업을 실행하지 않았습니다.

## 5. 준비 완료 조건과 터미널 구분

**VM 셸의 같은 실습 디렉터리**에서 실행합니다.

```bash
netlab defaults --project
netlab status
netlab connect --dry-run c1
netlab connect c1 --show version
netlab connect c1 --show running-config
netlab connect c2 --show bgp ipv4 unicast summary
netlab connect c1 --show ip ospf neighbor
netlab connect c2 --show ip ospf neighbor
```

`netlab defaults --project`는 netlab 2.0.1 이상에 있습니다. 2.0.0에서는 clone의 `defaults.yml`을 읽습니다.
[접속 명령 문서](https://netlab.tools/netlab/connect/)에 단일 node 접속과 `--show` 사용법이 있습니다.
이 FRR/clab 조합에서 `netlab connect c1`은 **c1의 Linux 셸**, 이어서 `vtysh`는 **c1의 FRR CLI**를 엽니다.
다음 프롬프트는 구분 표시이므로 붙여 넣지 않습니다.

```text
lab-vm$ netlab connect c1
c1-linux# vtysh
c1# show version
c1# show running-config
c1# exit
c1-linux# exit
```

`ip`, `ping`, 셸 명령은 `c1#`이 아닌 Linux에서 실행합니다.
`configure terminal`은 FRR 설정 모드로 들어가며 `end`는 FRR 운영 프롬프트로 돌아옵니다.
VM에서 `netlab connect c1 --show ip route`를 실행하면 FRR wrapper를 사용합니다. Linux 셸에 bare `show` 명령을 전달하지 않습니다.

준비 완료에는 실제 iBGP/eBGP established 상태, 의도한 OSPF 이웃, c2의 유효한 제공자 후보 경로 두 개, 횟수를 제한한 probe 성공이 필요합니다.
**기록된 c1, c2, x1, x2 컨테이너 식별자 각각**에 `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`를 적용해 이미지를 확인합니다.
호스트 전체 컨테이너 목록을 이 node들의 버전 증명으로 대신하지 않습니다.

## 6. 기준 상태: 예측·관찰·설명

고정 revision에서 c1의 외부 peer는 `10.1.0.2`, c2의 외부 peer는 `10.1.0.6`입니다.
iBGP loopback은 `10.0.0.1`, `10.0.0.2`이며 고객 세그먼트는 `192.168.42.0/24`입니다.
사용 전에 실행 설정과 이 값을 대조합니다.
Probe 대상 `192.168.100.10`은 모의 제공자 세그먼트에 있는 x1 주소입니다.

```bash
netlab connect c2 --show bgp ipv4 unicast 192.168.100.0/24
netlab connect c2 --show ip route 10.0.0.1/32
netlab connect c2 --show ip route 192.168.100.0/24
netlab connect c2 ip route get 192.168.100.10
netlab connect c2 ping -I 192.168.42.2 -c 5 -W 1 192.168.100.10
netlab connect c1 --show bgp ipv4 unicast neighbors 10.1.0.2 advertised-routes
```

후보 두 개의 next hop, AS_PATH, LOCAL_PREF, best-path 이유와 커널 조회 결과를 기록합니다.
c2가 직접 연결된 upstream을 골랐는지, c1을 거치는 출구를 골랐는지 설명합니다.
광고 출력의 실제 prefix를 자신이 제안한 export allowlist에 대조합니다. 예상 밖 광고는 발견 사항이며 제안한 필터가 실행되었다는 증거가 아닙니다.
응답이 없을 때 송신 정책 탓으로 단정하기 전에 x1의 `192.168.42.0/24` 반환 경로를 확인합니다.

## 7. 고객 한 대의 출구 선호도 변경

사전 상태는 c1의 AS65000 instance에 명시적 `bgp default local-preference`가 **없고**, 유효 기본값이 100이며, 조사할 제공자 경로를 덮어쓰는 inbound 정책이 없는 것입니다.
c2의 기준 유효값도 100이어야 합니다. 두 설정을 보존합니다.
조건이 다르면 기존 정책을 지우지 말고 중단하여 적절한 기준 상태를 먼저 확립합니다.

소유 변경 대상은 **c1의 AS65000 BGP instance**이며 역연산은 여기서 추가한 설정만 제거하는 것입니다.
c1의 **FRR CLI**에서 실행합니다.

```text
configure terminal
router bgp 65000
 bgp default local-preference 200
end
show bgp ipv4 unicast 192.168.100.0/24
```

[10.6.1 CLI 구현](https://github.com/FRRouting/frr/blob/frr-10.6.1/bgpd/bgp_vty.c)에서 명령을 확인했으며, 이 구현은 해당 instance의 inbound 경로도 재평가합니다.
Upstream의 wildcard clear 예제를 공유 환경에 복사하지 않습니다.
c2에서 6절을 다시 실행합니다. c1 경로가 유효하고 LOCAL_PREF 200을 가지면 100인 경로보다 우선하며 FIB와 패킷 경로도 대응해야 합니다.
속성이 바뀌지 않으면 inbound 정책, next-hop 유효성, 실제 실행 버전을 확인합니다. 설정 한 줄만으로 PASS를 선언하지 않습니다.
이 워크북은 c1만 바꾸므로 upstream validator의 별도 c2=50 조건은 **이 워크북의 통과 기준이 아닙니다**.

## 8. Peer 하나의 장애 측정

선호도 실험 상태를 유지합니다. 사전 상태는 **c1의 이웃 `10.1.0.2`**가 established이고 `shutdown` 설정이 없는 것입니다.
역연산은 같은 BGP instance에서 `no neighbor 10.1.0.2 shutdown`입니다.
이 실험은 관리 명령으로 발생시킨 peer 장애이며 케이블 단절, 무응답 패킷 손실, BFD 실험이 아닙니다.

타임스탬프가 있는 probe에는 VM의 iputils를 **기록된 c2 컨테이너 network namespace** 안에서 사용합니다.
이 lab의 inventory/provider 매핑에서 이름을 얻고 `ip netns list`로 존재를 확인합니다. 느슨한 wildcard로 선택하지 않습니다.
Placeholder를 바꾼 후 두 번째 VM 터미널에서 실행합니다.

```bash
routing_c2_ns='REPLACE_WITH_THIS_LABS_C2_NAMESPACE'
sudo ip netns exec "$routing_c2_ns" ip -br address
sudo ip netns exec "$routing_c2_ns" ping -D -O -n -I 192.168.42.2 -i 0.2 -c 150 -w 40 -W 1 192.168.100.10
```

표시된 주소가 c2와 일치해야 합니다. 장애 주입 전 여러 개의 성공 응답을 확보합니다.
[Iputils의 `-O` 옵션](https://github.com/iputils/iputils/blob/master/doc/ping.xml)은 미수신 응답을 보고합니다. 모든 미수신 보고를 영구 손실로 처리하지 말고 sequence 번호로 늦게 도착한 응답과 대조합니다.
c1의 FRR CLI에서 조작 시각을 기록한 뒤 적용합니다.

```text
configure terminal
router bgp 65000
 neighbor 10.1.0.2 shutdown
end
```

제한된 probe 구간 동안 VM에서 6절의 c2 BGP prefix와 커널 경로를 샘플링합니다.
다른 터미널에서는 **확인된 c2의 backup 데이터 인터페이스**에 [캡처 명령](https://netlab.tools/netlab/capture/)을 적용합니다. 고정 FRR 토폴로지에서는 `eth2`입니다.

```bash
timeout 20s netlab capture c2 eth2 -nn -l -c 40 icmp
```

Timeout은 수집 시간을 제한합니다. 패킷이 없거나 접근 오류가 난 것은 캡처 성공이 아닙니다.
c2가 x2를 선택하고 제공자 내부 세그먼트를 거쳐 x1에 도달하는 것이 예상 동작입니다.
`t_action`, 최초 관찰된 경로 철회/변경, FIB 변경, 마지막 실패 probe, 지속적인 회복 시작을 구분합니다.
연속 5개 응답처럼 지속 회복 기준을 미리 정하고 샘플 간격과 불확실성을 보고합니다.
Probe와 조작 기록은 같은 VM 시계를 사용합니다. CLI 조작 직전에 VM 셸의 `date -u +%FT%T.%NZ`를 기록하고 수동 터미널 전환 지연도 불확실성에 포함합니다.
관찰된 손실이 0이면 해당 샘플링 해상도에서 중단을 포착하지 못했다는 뜻이며 수렴 시간이 0이라는 뜻은 아닙니다.
Hold timer, BFD, graceful restart, 장애 감지, 경로 처리, FIB 반영이 결과에 영향을 주므로 보편적인 고정 수렴 시간을 단정하지 않습니다.

## 9. 복원·반복·제출

c1의 FRR CLI에서 **peer부터** 복원합니다.

```text
configure terminal
router bgp 65000
 no neighbor 10.1.0.2 shutdown
end
```

Peer가 재수립되고 선호 경로와 probe가 회복되는지 확인합니다.
다음으로 **정책 객체**를 복원합니다.

```text
configure terminal
router bgp 65000
 no bgp default local-preference
end
```

실행 설정, 후보 경로 두 개, 유효 선호도, FIB 조회, 원래 출발지를 지정한 probe를 다시 확인합니다.
실험 설정을 startup configuration에 저장하거나 FRR을 재시작하거나 광범위한 정리 명령을 실행하지 않습니다.
복구가 실패하면 추가 실험을 중단하고 달라진 객체를 보고합니다. 소유자는 증거를 내보낸 뒤 이 일회용 VM 한 대의 기록된 checkpoint로 복구할 수 있습니다.
새 clone은 증거로 남기며, 최종 폐기는 소유자의 수명 주기 절차에 따라 이 VM에만 한정합니다.

| 단계 | 필요한 긍정 증거 | 보존할 부정·실패 증거 |
|---|---|---|
| 기준 상태 | 유효 경로 두 개, 사용 가능한 next hop, probe 성공 | 반환 경로 누락, 해석 불가능한 next hop, 준비 오류 |
| 선호도 변경 | c1의 LOCAL_PREF 200, 선택 출구, 대응 포워딩 | 속성 미변경 또는 RIB/FIB 불일치 |
| Peer 장애 | 관찰된 대체 경로와 지속적인 probe 회복 | 손실 구간, 대체 경로 부재, 캡처 오류 |
| 복원 | 원래 설정과 포워딩 동작 | 남은 shutdown, 정책 차이, 지속 손실 |

매번 복원 확인을 통과한 뒤에만 장애 측정을 세 번 반복하고 개별 결과와 관측 범위를 보고합니다.
평균만 남기지 말고 원시 타임스탬프와 출력을 보존하며 결과를 측정됨·계획됨·차단됨으로 구분합니다.
경로 누락, probe 기록 부재, 빈 캡처는 긍정 조건을 만족시키지 못합니다.
정책, next-hop 재귀 해석, “세션 정상=서비스 정상”의 반례, 측정 한계, 검증된 복원을 설명할 수 있으면 완료입니다.
[EVPN](03-datacenter-evpn.md)으로 이동하고, Kubernetes 전문 심화는 [Calico BGP](../calico/04-bgp-deep-dive.md)로 이어갑니다.
결과 행렬을 [자동화 종합 실습](06-automation-capstone.md)에 제출하고 [퀴즈](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md)를 풉니다.
