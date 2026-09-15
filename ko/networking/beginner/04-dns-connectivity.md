# 04. DNS와 연결 문제 진단

> **지원 버전**: Ubuntu Server 24.04 LTS(기본), Rocky Linux 9(대안)
> **마지막 업데이트**: 2026년 9월 15일

“서버에 연결되지 않는다”는 말은 이름 해석 실패, 잘못된 경로, 방화벽의 연결 거부, 애플리케이션 오류 등 여러 상황을 포함합니다. 아래 검사는 각각 더 작은 질문 하나에 답합니다. 관측 결과와 그 한계를 기록한 다음 다음 검사를 선택하세요.

## 준비 사항과 학습 목표

[영구 네트워크 설정](03-persistent-configuration.md)을 완료하세요. [과정 실습 환경](README.md)은 같은 내부 가상망의 클라이언트 `192.0.2.10/24`와 서버 `192.0.2.20/24`입니다. **DHCP·게이트웨이·DNS 서버·업링크는 없습니다**. 각 게스트의 별도 NAT/DHCP 관리 NIC는 그대로 유지합니다.

게스트 콘솔을 사용하고, 하이퍼바이저 MAC과 `ip -br link`를 대조하여 실습 NIC를 식별합니다. 주 실습에는 공개 DNS나 인터넷 접근이 필요하지 않습니다. 공개 DNS 조회는 별도로 표시한 선택 실습입니다.

| 게스트에 미리 준비한 도구 | 용도 |
|---|---|
| `ip`, `ping`, `getent`, `grep`, `timeout`, 편집기, sudo | 로컬 설정·이름·횟수와 시간 제한 검사 |
| `dig` | DNS 프로토콜 응답 검사, BIND 유틸리티에 포함 |
| `tracepath` 또는 Linux `traceroute` | 홉 제한을 둔 probe에 대한 응답 관측 |
| `python3` 3.9+, `curl`, `ss` | 임시 페이지 제공, HTTP·수신 소켓 확인 |
| Ubuntu OpenBSD `nc` 또는 Rocky `ncat` | TCP 연결 검사 한 번 |
| systemd-resolved가 활성인 경우 `resolvectl` | 해당 resolver 확인, Rocky의 필수 조건 아님 |

`command -v ip ping getent timeout dig tracepath traceroute python3 curl ss nc ncat`으로 확인하세요. 선택하지 않은 대안 도구가 없는 것은 정상입니다. 선택한 실습에 필요한 도구가 없으면 환경 준비로 돌아갑니다. 이 장에는 패키지 설치 명령이 없습니다.

학습을 마치면 NSS와 DNS 조회를 구분하고, 권한 있는 응답과 캐시를 설명하며, 선택된 경로를 확인할 수 있습니다. ICMP·추적 결과를 해석하고 TCP와 HTTP를 나누어 검사하며 근거와 다음 조치가 있는 장애 기록을 작성합니다.

## 1. 이름·DNS·운영체제의 관계

DNS는 분산 데이터베이스입니다. **A** 레코드는 IPv4 주소, **AAAA**는 IPv6 주소, **CNAME**은 다른 이름을 가리키는 별칭, **PTR**은 역방향 조회에 사용합니다. 어떤 레코드도 목적지 애플리케이션의 실행 여부를 증명하지 않습니다.

**재귀 resolver**는 클라이언트를 대신해 캐시를 이용하거나 다른 DNS 서버에 물어 답을 구합니다. **권한 있는 서버(authoritative server)**는 자신이 담당하는 zone의 공개 데이터를 보유합니다. 캐시는 허용된 수명 동안 긍정·부정 응답을 재사용할 수 있습니다. DNS **TTL**은 초 단위 수명이며 IP TTL의 홉 제한과는 다릅니다. 지금 DNS TTL을 줄여도 이전 TTL로 이미 저장된 캐시가 즉시 사라지지는 않습니다. [DNS 개념](https://www.rfc-editor.org/rfc/rfc1034.html), [부정 응답 캐시](https://www.rfc-editor.org/rfc/rfc2308.html)를 참고하세요.

Linux 애플리케이션은 C 라이브러리의 **NSS(Name Service Switch)** 경로로 이름을 요청할 수 있습니다. `/etc/nsswitch.conf`가 조회 소스를 정합니다. `files`는 `/etc/hosts`, `dns`는 DNS, `resolve`는 설치·설정된 systemd-resolved를 사용합니다. 다른 모듈과 대괄호 안 반환 규칙에 따라 경로가 달라질 수 있습니다. DNS over HTTPS를 사용하는 브라우저처럼 자체 resolver를 가진 프로그램은 다르게 동작할 수도 있습니다.

| 도구 | 답하는 질문 |
|---|---|
| `getent ahostsv4 NAME` | 시스템의 NSS/getaddrinfo 경로가 반환하는 IPv4 주소는? |
| `getent hosts NAME` | NSS hosts 조회 결과는? 주소 계열 동작이 `ahostsv4`와 다름 |
| `getent -s files hosts NAME` | 파일 소스에만 이 이름이 있는가? |
| `dig @SERVER NAME A` | 지정한 서버의 DNS 응답은? 질의 이름에 NSS를 적용하지 않음 |
| `resolvectl query NAME` | systemd-resolved 자체 인터페이스가 반환하는 결과는? |

**클라이언트**에서 편집하지 않고 읽습니다.

```bash
grep '^hosts:' /etc/nsswitch.conf
cat /etc/hosts
ls -l /etc/resolv.conf
cat /etc/resolv.conf
systemctl is-active systemd-resolved
```

예를 들어 `hosts: files dns`는 hosts 파일을 먼저, DNS를 나중에 조회합니다. 실제 설정을 이 예시로 대체하지 마세요. `/etc/resolv.conf`는 생성된 stub 파일의 심볼릭 링크, 생성된 상위 서버 목록, 또는 다른 도구가 관리하는 파일일 수 있습니다. `nameserver 127.0.0.53`은 로컬 루프백 stub을 가리키며 라우터 주소가 아닙니다.

**systemd-resolved가 활성인 Ubuntu 클라이언트**에서는 다음도 읽습니다.

```bash
resolvectl status
resolvectl statistics
```

연결별 DNS 서버·검색 도메인과 캐시 통계를 확인하세요. 과정의 실습 NIC는 DNS를 제공하지 않아야 하지만 관리 DNS는 표시될 수 있습니다. **NetworkManager가 관리하는 Rocky 클라이언트**에서는 `nmcli -f GENERAL,IP4,IP6 device show`와 앞의 resolver 파일 확인을 사용합니다. Ubuntu와 같게 만들려고 resolved를 설치하거나 심볼릭 링크를 바꾸지 않습니다. 영구 수정은 03장에서 확인한 소유자의 설정에 해야 합니다.

## 2. 두 VM에 로컬 이름 붙이기

**클라이언트**의 `/etc/hosts`를 사용하면 외부 resolver 없이 실습할 수 있습니다. 이 이름은 로컬 별칭입니다. 게스트의 호스트명을 변경하거나 DNS 레코드를 만들거나 서버를 원격 설정하지 않습니다. `.test`는 시험용 예약 도메인입니다. multicast DNS에서 특별한 의미가 있는 `.local`은 피하세요.

먼저 충돌을 확인합니다.

```bash
grep -nE 'netlab\.test|BEGIN network-beginner-04|END network-beginner-04' /etc/hosts
```

최초 실행에서는 출력이 없고 종료 상태가 1이면 정상입니다. 항목이 있으면 중복 추가하지 말고 먼저 확인하세요. 새 복구 디렉터리와 백업을 만듭니다.

```bash
sudo mkdir -m 700 /root/network-beginner-04
sudo cp -a /etc/hosts /root/network-beginner-04/hosts-before
sudoedit /etc/hosts
```

디렉터리가 이미 있다면 이전 시도를 확인하고 멈춥니다. 기존 localhost·게스트 호스트명 항목은 보존하고 맨 끝에 아래 블록만 추가하세요.

```text
# BEGIN network-beginner-04
192.0.2.10 client.netlab.test
192.0.2.20 server.netlab.test
# END network-beginner-04
```

파일 전용 조회와 일반 애플리케이션 조회를 비교합니다.

```bash
getent -s files hosts server.netlab.test
timeout 5s getent ahostsv4 server.netlab.test
timeout 5s getent hosts server.netlab.test
```

앞의 두 명령에는 `192.0.2.20`이 나와야 합니다. `ahostsv4`가 `STREAM`, `DGRAM`, `RAW`별로 같은 주소를 반복할 수 있습니다. 서버 세 대가 아니라 소켓 유형입니다. `hosts`는 IPv4보다 IPv6 조회를 먼저 시도하여 경로나 소요 시간이 다를 수 있습니다. 시간 초과(상태 124)는 제한 시간 안의 관측이며 DNS가 이름 부재를 응답했다는 증거가 아닙니다.

파일 전용 조회는 성공하고 일반 조회는 실패한다면 NSS 순서·모듈, 정확한 철자와 주소 계열을 확인합니다. 이름 문제를 고치려고 경로를 바꾸지 마세요. 서버 자체에서 이 이름을 사용할 때만 서버에도 hosts 항목이 필요하며, 반복한다면 서버의 백업도 따로 만듭니다.

### 외부 의존 없이 dig와 비교

hosts 조회가 정상이고 resolved가 활성인 **Ubuntu 클라이언트**에서 실행합니다.

```bash
resolvectl --network=no -4 query server.netlab.test
dig -r @127.0.0.53 server.netlab.test. A +time=2 +tries=1
```

`--network=no`는 resolved의 네트워크 질의를 막으므로 로컬 소스·캐시로 답하거나 로컬 실패를 반환합니다. `dig -r`은 개인 `.digrc` 설정을 건너뛰고, `@127.0.0.53`은 stub을 지정하며, 끝의 점은 절대 DNS 이름을 뜻합니다. 나머지 옵션은 대기·재시도를 제한합니다. 일반적인 resolved 설정은 `/etc/hosts`도 읽으므로 **두 명령 모두** `.20`을 반환할 수 있습니다. Dig는 여전히 DNS 질의를 보냈으며 stub이 로컬 자료로 응답한 것입니다. 따라서 “dig에는 hosts 파일의 값이 절대 나오지 않는다”는 설명은 부정확합니다.

stub이나 resolved의 hosts 파일 읽기가 비활성인 경우에는 이 경로가 성공하지 않을 수 있습니다. 서비스를 켜는 대신 현재 resolver 구성을 조사하세요. **어느 배포판에서든** 다음 질의와 hosts 조회를 비교할 수 있습니다.

```bash
dig -r @192.0.2.20 server.netlab.test. A +time=2 +tries=1
```

이것은 **의도적인 실패 검사**입니다. 과정 서버에는 DNS 서비스가 없으므로 정답 대신 거부 또는 시간 초과를 예상합니다. 클라이언트의 hosts 항목은 서버를 DNS 서버로 만들지 않습니다. 예상 밖의 답이 오면 서버의 53번 포트 수신 서비스를 확인하세요. 일반 애플리케이션은 hosts 매핑을 사용하게 두며 시스템 DNS를 `.20`으로 지정하지 않습니다.

`@SERVER`를 생략하면 dig가 `/etc/resolv.conf`를 읽으므로 로컬처럼 보이는 검사도 관리망의 상위 resolver로 나갈 수 있습니다. 위 명령은 대상을 명시적으로 선택합니다.

### DNS 응답 읽기

다음은 **가상의 권한 있는 실습 DNS 서비스가 반환한 설명용 예시**입니다. 실제 측정 출력도, 이 장에서 만든 서비스도 아닙니다.

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1234
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; ANSWER SECTION:
server.netlab.test. 300 IN A 192.0.2.20
;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)
```

| 필드·상태 | 해석 |
|---|---|
| `SERVER` | 이번 질의에 답한 서버, 반드시 원본 권한 서버는 아님 |
| `300 IN A 192.0.2.20` | TTL 초, Internet 클래스, IPv4 타입, 주소 |
| `aa` | 관련 질의 이름에 권한 있는 답이라는 표시, 연결·신원 보장 아님 |
| `rd` / `ra` | 표시될 경우 재귀 요청 / 재귀 제공 가능, 새 상위 조회를 증명하지 않음 |
| `NOERROR`와 기대 레코드 | DNS 질의 성공, 실제 데이터도 확인 필요 |
| `NOERROR`지만 요청 데이터 없음 | NODATA일 수 있음, Authority·CNAME·위임 맥락 확인 필요 |
| `NXDOMAIN` | 이름이 없다는 DNS 응답, 캐시·정책에서 나온 답일 수도 있음 |
| `SERVFAIL` | 상위 서버·검증 문제 등으로 resolver가 실패 |
| `REFUSED` | 서버 정책이 질의를 거부 |
| 시간 초과 | 대기 시간 안에 유효 응답 없음, NXDOMAIN과 다름 |

`dig +short`는 중요한 상태·서버 정보를 숨기므로 진단에서는 전체 출력을 사용합니다. Dig는 `NXDOMAIN`을 수신해도 종료 코드 0을 반환할 수 있으므로 종료 코드만으로 주소 발견을 판단하지 않습니다.

캐시는 애플리케이션, 로컬 서비스, 상위 재귀 resolver에 각각 있을 수 있습니다. 두 번째 조회가 빠르다는 사실만으로 캐시 적중을 증명할 수 없습니다. resolved에서는 `resolvectl statistics`를 비교하되 hosts 기반 답이 DNS 캐시 레코드처럼 동작한다고 가정하지 마세요. `sudo resolvectl flush-caches`는 resolved의 로컬 DNS 캐시를 비울 뿐 hosts·애플리케이션·상위 캐시는 지우지 않습니다. 다시 조회하며 채워지는 일시 상태이므로 의미 있는 “이전 캐시 복원” 작업도 없습니다. 이 실습에는 필요하지 않으며 별도의 캐시 조사에서도 먼저 증거를 기록하세요.

## 3. 선택된 경로를 확인한 뒤 IP 검사

**클라이언트**에서 실습 MAC을 다시 대조하고 NIC 이름을 넣습니다.

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -br link
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
```

경로 출력의 설명용 예시입니다.

```text
192.0.2.20 dev LAB_NIC src 192.0.2.10 uid 1000
```

`dev`는 출력 인터페이스, `src`는 선택한 출발지 주소, `via`가 있다면 다음 홉 라우터입니다. 여기서는 상대가 같은 링크에 있으므로 `via`가 필요 없습니다. `LAB_NIC`는 설명용 표기이며 실제 장치명이 아닙니다. `ip route get`은 로컬 경로 조회이며 ping을 전송하지 않습니다. 상대의 가용성이나 반환 경로도 증명하지 않습니다.

관리 NIC를 선택한다면 상대 검사를 멈추고 실습 주소·접두사와 저장 설정을 확인하세요. 관리 기본 경로는 삭제하지 않습니다. **서버**에서도 `ip -4 route get 192.0.2.10`이 실습 NIC와 출발지 `.20`을 선택해야 합니다. 응답에도 올바른 반환 경로가 필요합니다.

**클라이언트**에서 루프백·자신의 주소·상대를 비교합니다.

```bash
ping -n -c 3 -W 2 127.0.0.1
ping -n -c 3 -W 2 192.0.2.10
ping -n -c 3 -W 2 192.0.2.20
```

`-n`은 역방향 이름 조회를 생략하고, `-c 3`은 Echo Request 세 번, `-W 2`는 응답이 없을 때의 대기를 제한합니다. 숫자 목적지는 정방향 이름 조회도 제거합니다. `time`은 왕복 시간이지 대역폭이 아닙니다. 응답의 `ttl`은 수신한 패킷의 남은 TTL이며 초기값을 모르면 정확한 홉 수로 바꿀 수 없습니다.

루프백 성공은 로컬 스택을 검사합니다. 자신의 실습 주소로 보내는 ping은 보통 로컬 처리되므로 가상 케이블 검사가 아닙니다. 상대 응답은 그 시점의 양방향 ICMP Echo 교환을 보여 주지만 TCP 포트 접근을 증명하지 않습니다. 세 번 무응답은 그 세 probe에 대한 증거입니다. 필터링·응답 속도 제한·주소 오류·반환 경로 문제를 조사해야 합니다.

상대 검사 후 **클라이언트**의 이웃 항목을 봅니다.

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip neigh show to 192.0.2.20 dev "$LAB_IF"
```

MAC과 `REACHABLE`, `STALE`은 알고 있는 이웃 매핑을 나타내며 `STALE` 자체는 장애가 아닙니다. `INCOMPLETE`, `FAILED`는 ARP 해석이 성공하지 못한 상황을 시사합니다. 두 어댑터의 내부망 연결, 상대 주소, carrier, 중복 IP 가능성을 확인하세요. DNS는 Ethernet 목적지 MAC을 제공하지 않습니다.

## 4. traceroute·tracepath의 한계까지 읽기

**클라이언트**에서 준비한 도구를 실행합니다.

```bash
traceroute -4 -n -m 4 -q 1 -w 1 192.0.2.20
timeout 15s tracepath -4 -n -m 4 192.0.2.20
```

Linux traceroute는 보통 UDP probe를 사용합니다. `-m 4`는 최대 TTL, `-q 1`은 TTL마다 probe 하나, `-w 1`은 probe 대기 제한입니다. Tracepath도 UDP를 사용하며 경로 MTU 정보도 표시합니다. 바깥의 `timeout`은 전체 실행 시간을 제한합니다. 직접 연결된 상대가 응답하도록 허용돼 있다면 TTL 1에서 목적지가 보입니다. 가상 Ethernet 스위치는 IP 라우터가 아니므로 traceroute 홉을 추가하지 않습니다.

라우터에서 TTL이 만료되면 ICMP Time Exceeded가 돌아올 수 있습니다. 목적지의 닫힌 UDP 포트에는 ICMP Port Unreachable이 돌아올 수 있습니다. 이런 제어 응답으로 경로 일부를 추론하는 것이며 모든 패킷의 이동을 기록한 것은 아닙니다.

traceroute의 `*`, tracepath의 `no reply`는 제한 시간에 일치하는 응답을 받지 못했다는 뜻입니다. 그 홉이 일반 애플리케이션 트래픽을 버렸다는 **증거는 아닙니다**. 필터링·속도 제한·서로 다른 probe 프로토콜·비대칭 반환 경로가 원인일 수 있습니다. 이후 홉이나 애플리케이션은 정상 응답할 수도 있습니다.

설치된 Linux traceroute가 지원한다면 같은 상대에 선택적인 **ICMP 비교**를 합니다.

```bash
sudo traceroute -4 -I -n -m 4 -q 1 -w 1 192.0.2.20
```

`-I`는 ICMP Echo probe이며 필요한 경우 sudo가 raw probe를 허용합니다. 결과 차이는 프로토콜별 정책을 반영할 수 있습니다. 영구 설정 변경은 없습니다. 추적 화면을 보기 좋게 하려고 방화벽을 끄지 마세요.

## 5. 로컬 서비스 하나로 TCP와 HTTP 구분

SSH나 웹 서버가 이미 설치됐다고 가정하지 않습니다. 기존 Python으로 **서버 실습 주소에만 바인딩한** 임시 HTTP 서비스를 만듭니다.

### 서버에서 시간 제한 서비스 시작

**서버 터미널 A**에서 `.20`이 실습 NIC의 주소인지, TCP 18080을 사용하는 기존 리스너가 없는지 확인합니다.

```bash
ip -br address
ss -ltn 'sport = :18080'
```

리스너가 있으면 정체를 확인하고 다른 서비스를 종료하지 마세요. 빈 포트를 선택해 이 절 전체를 일관되게 바꾸거나 이전 실습을 먼저 정리합니다.

같은 **서버 터미널 A**에서 새 디렉터리를 만들고 일반 사용자로 제공합니다.

```bash
LAB_HTTP_DIR=$(mktemp -d /tmp/network-beginner-04.XXXXXX)
printf '%s\n' "$LAB_HTTP_DIR"
printf 'network lab ok\n' > "${LAB_HTTP_DIR:?missing lab directory}/index.html"
timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"
```

`mktemp`가 실패하면 멈추세요. `${변수:?메시지}`는 빈 변수로 다음 경로를 사용하지 못하게 합니다. 출력된 디렉터리 경로를 기록합니다. 새 디렉터리의 실습 파일만 제공하며 홈 디렉터리를 제공하거나 심볼릭 링크를 추가하지 않습니다. `--bind`는 모든 주소 수신을 피하고, `--directory`는 콘텐츠 경로, `timeout`은 5분 뒤 종료입니다. Ctrl+C로 먼저 중단할 수 있습니다. 제한 시간으로 끝난 경우 종료 상태 124는 정상입니다.

Python 내장 HTTP 서버는 실습 도구입니다. 여기에는 인증·TLS가 없으며 운영 배포가 아닙니다. 시스템 서비스나 부팅 활성화도 만들지 않습니다.

A가 실행 중인 동안 **서버 터미널 B**에서 검사합니다.

```bash
ss -ltn 'sport = :18080'
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
```

`192.0.2.20:18080` 리스너와 HTTP 200, `network lab ok`를 예상합니다. Rocky의 Python 3.9를 포함하여 이 서버의 HTTP/1.0 응답은 정상입니다. 자기 요청은 로컬 애플리케이션 동작을 검증하며 클라이언트 경로를 검증하지 않습니다. 바인딩 시 “Cannot assign requested address”가 나오면 03장의 서버 주소를 확인하세요. 권한 거부가 나오면 SELinux를 끄지 말고 오류 원인을 조사합니다.

### 클라이언트에서 TCP 검사

**OpenBSD netcat이 있는 Ubuntu 클라이언트**:

```bash
nc -n -z -v -w 3 192.0.2.20 18080
```

**Ncat이 있는 Rocky 클라이언트**:

```bash
ncat -n -z -v -w 3 192.0.2.20 18080
```

`-n`은 DNS 생략, `-z`는 애플리케이션 데이터 없이 연결 검사, `-v`는 결과 출력, `-w 3`은 연결 대기 제한입니다. 성공은 그 끝점에 TCP 연결을 만들 수 있었다는 뜻이며 HTTP 동작까지 증명하지 않습니다. 거부는 보통 닫힌 포트나 적극적인 reject, 시간 초과는 필터링·이웃 해석 실패·상대 중단·반환 경로 문제일 수 있습니다.

게스트 방화벽, 특히 설정된 Rocky firewalld 정책은 새 포트를 막을 수 있습니다. 서버의 리스너·자기 요청과 클라이언트의 경로·이웃·TCP 증거를 비교하여 **정책 경계가 원인일 가능성**으로 기록하세요. 이 장에서는 방화벽 규칙을 바꾸지 않습니다. [06장](06-firewalls-host-security.md)에서 범위를 한정한 정책 변경을 배웁니다. 원격 검사가 막혀도 서버 터미널 B에서 HTTP 관측을 완료하고 클라이언트의 실패를 다음 실습에 보존할 수 있습니다. 서버 자기 요청 성공을 원격 HTTP 성공으로 기록하지 마세요.

### HTTP를 검사한 뒤 이름 비교

서비스가 실행 중일 때 **클라이언트**에서 검사합니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://server.netlab.test:18080/
```

맨 앞의 `--disable`은 기본 curl 설정을 읽지 않고, `--noproxy '*'`는 상속된 HTTP 프록시를 피합니다. `--connect-timeout`은 연결 준비 시간, `--max-time`은 전체 시간, `-i`는 응답 헤더 포함입니다. 두 번째 명령은 클라이언트의 이름 조회를 사용합니다. 숫자 URL만 성공하면 경로를 바꾸기 전에 `getent ahostsv4`와 curl 오류를 비교하세요.

**이번 curl 한 번**의 이름 조회를 분리하려면 호스트명은 유지하고 알려진 실습 주소를 제공합니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve server.netlab.test:18080:192.0.2.20 \
  -i http://server.netlab.test:18080/
```

`--resolve`는 이 호스트명·포트의 curl 매핑만 바꿉니다. hosts 파일·DNS 레코드를 바꾸지 않으므로 원복도 필요 없습니다. HTTP Host 헤더에는 이름을 유지합니다. 실제 HTTPS에서는 이름 기반 인증서 검사와 TLS SNI도 중요하므로 호스트명을 IP로 바꾸는 것이 항상 동등한 애플리케이션 검사는 아닙니다. 인증서 검사를 건너뛰고 TLS를 “고쳤다”고 하지 마세요.

만든 적 없는 파일을 요청하여 무해한 애플리케이션 오류를 관측합니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/missing-page
```

접근 가능하다면 HTTP **404**를 예상합니다. HTTP 오류가 돌아올 만큼 이름·IP 경로와 TCP 전송은 동작했으며 요청한 페이지가 없는 것입니다. `--fail`을 쓰지 않으면 HTTP 404에도 curl이 0으로 끝날 수 있으므로 상태 줄을 읽으세요. `curl -I`는 **HEAD**를 보내며 GET 본문만 숨기는 옵션이 아닙니다.

## 6. 증거로 다음 검사 선택

다음 표를 순서대로 사용하되 새 증거가 가정과 충돌하면 앞 단계로 돌아갑니다. 원인 후보를 제시하는 것이며 자동 확진표는 아닙니다.

| 관측 | 확인된 사실 | 다음 구분 검사 |
|---|---|---|
| 파일 전용 조회에 `.20` 없음 | 로컬 매핑이 없거나 틀림 | 철자, hosts 블록, 중복 항목 |
| 파일 전용 성공, 일반 getent 실패 | 소스별 동작이 다름 | NSS 순서·반환 규칙·모듈·주소 계열 |
| getent 성공, `.20`으로 dig 실패 | 로컬 이름 정상, `.20`에는 DNS 서비스가 원래 없음 | hosts 사용 유지, DNS가 필요할 때만 실제 resolver 확인 |
| DNS `NXDOMAIN` | 부정 DNS 응답 수신 | 철자, resolver/view, 권한 서버 데이터, 부정 캐시 |
| DNS 시간 초과 | 제한 시간에 유효 DNS 응답 없음 | resolver까지 `ip route get`, 53번 포트, resolver 서비스·정책 |
| 경로가 관리 NIC·잘못된 출발지 선택 | 실습 목적지의 로컬 전달 선택 오류 | 실습 주소·접두사, 영구 설정 소유자, 경로·rule 목록 |
| 경로 정상, 이웃 `FAILED` | 다음 홉 MAC 해석 실패 | 가상망·케이블, 상대 주소, 링크 상태, 주소 충돌 |
| 이웃 존재, ping 실패 | MAC은 알지만 ICMP 응답 없음 | 서버 반환 경로, ICMP 정책, 의도한 TCP 포트 |
| ping 성공, TCP 거부 | ICMP 정상, TCP는 적극적 거부 | 서버 `ss`, 서비스 실행 시간·바인딩, reject 정책 |
| 서버 자기 HTTP 성공, 클라이언트 TCP 시간 초과 | 로컬 서비스 정상, 원격 경로 미검증 | 양쪽 경로·이웃·호스트 정책, 06장용 증거 기록 |
| TCP 성공, HTTP 지연·비정상 | 연결 수립 정상 | 올바른 프로토콜·포트, 애플리케이션 로그·응답 |
| HTTP 404/403/500 | HTTP 끝점이 애플리케이션 결과 반환 | 경로, 애플리케이션 권한·서비스 오류, DNS 수정 사유 아님 |
| 숫자 HTTP 성공, 이름 HTTP 실패 | 일반 조회 없이 알려진 끝점 정상 | getent, curl 이름 오류, `--resolve` 한 번 비교 |
| traceroute `*`, HTTP 정상 | 해당 probe 무응답, 애플리케이션 성공 | probe 프로토콜·속도 제한, 전체 패킷 손실 단정 불가 |

유용한 curl 종료 코드는 **6**(호스트 이름 해석 실패), **7**(연결 실패), **28**(작업 시간 초과)입니다. 실패 단계의 단서이며 반드시 근본 원인은 아닙니다. 명령, 실행 VM, 시각(`date -Is`), 목적지, 출력, 종료 상태(직후 `echo $?`), 기대 결과, 다음 검사를 기록하세요. “관측”과 “추정”을 구분합니다.

## 7. 선택: 공개 DNS 관측

**외부 의존성:** 클라이언트의 변경하지 않은 기존 관리망이 허용된 인터넷 접근과 선택한 resolver 질의를 이미 제공할 때만 실행합니다. 완료 필수 조건이 아니며 실패만으로 격리된 `.10` ↔ `.20` 실습망을 판단할 수 없습니다. 실습 NIC에 업링크나 공개 DNS를 추가하지 마세요.

```bash
ip -4 route get 1.1.1.1
dig -r @1.1.1.1 example.com. A +time=2 +tries=1
dig -r @1.1.1.1 example.com. AAAA +time=2 +tries=1
dig -r @1.1.1.1 example.com. NS +time=2 +tries=1
```

질의 전에 경로가 기존 관리 경로인지 확인하세요. 정책상 다른 승인된 resolver가 필요하면 그 주소로 일관되게 바꿉니다. 공개 IP가 고정이라고 기대하지 말고 상태·서버·레코드 유형·TTL을 읽습니다. A 조회를 한 번 반복해 TTL을 비교하되 시간만으로 캐시 위치를 추정하지 않습니다. 선택적으로 `+tcp`를 붙여 일반적인 UDP A 조회와 TCP DNS를 비교할 수 있습니다. 공개 resolver에 내부·비공개 이름을 질의하지 마세요.

NS 답은 권한 정보를 알려 줍니다. `1.1.1.1`의 재귀 응답이 곧 zone의 권한 서버가 직접 답한 응답은 아닙니다. `dig +trace`는 traceroute처럼 IP 라우터 홉이 아니라 DNS 위임을 따라가며 외부 의존성이 추가되므로 이 로컬 실습 범위에서는 사용하지 않습니다.

## 8. 정리와 완료 확인

**서버 터미널 A**에서 Ctrl+C 또는 타이머로 Python을 종료합니다. 터미널 B에서 `ss -ltn 'sport = :18080'`으로 이번 리스너가 없어졌는지 확인하세요.

디렉터리를 만들었던 **같은 터미널 A 셸**에서 경로를 확인하고 실습 파일과 빈 디렉터리만 지웁니다.

```bash
printf '%s\n' "$LAB_HTTP_DIR"
ls -la -- "${LAB_HTTP_DIR:?missing lab directory}"
rm -i -- "${LAB_HTTP_DIR:?missing lab directory}/index.html"
rmdir -- "${LAB_HTTP_DIR:?missing lab directory}"
unset LAB_HTTP_DIR
```

셸을 닫았다면 기록한 정확한 경로로 `LAB_HTTP_DIR`을 다시 설정하고 내용을 확인한 뒤 실행하세요. 넓은 와일드카드로 추측하지 않습니다. `rmdir`은 비어 있지 않은 디렉터리를 거부하므로 예상 밖 파일을 발견하는 데 도움이 됩니다.

`/etc/hosts`를 편집한 각 게스트에서 `sudoedit /etc/hosts`로 `# BEGIN network-beginner-04`부터 `# END network-beginner-04`까지 표식 두 줄을 포함하여 이번 블록만 제거합니다. `sudo diff -u /root/network-beginner-04/hosts-before /etc/hosts`로 비교하세요. 다른 편집이 없었다면 출력 없음이 원본 복원을 뜻합니다. 그동안 정당한 다른 변경이 있었다면 백업으로 덮어쓰지 말고 보존하세요.

`getent -s files hosts server.netlab.test`가 더 이상 실습 매핑을 반환하지 않는지 확인합니다. 모든 resolver가 즉시 이름을 잊어야 한다고 요구하지 않습니다. 03장의 정적 주소와 관리 설정은 SSH 학습을 위해 유지합니다.

다음 항목을 설명·수행할 수 있으면 다음 장으로 진행합니다.

- 게스트의 실제 소스로 getent/NSS, dig, resolved의 차이를 설명합니다.
- 공개 DNS 없이 `.20`을 해석하고 의도적인 dig 실패를 설명합니다.
- TTL·권한 표시·부정 응답을 포함한 DNS 출력을 해석합니다.
- 실습 경로·출발지를 확인하고 루프백·이웃·상대 검사 증거를 구분합니다.
- 추적의 별표가 애플리케이션 패킷 손실을 증명하지 않는 이유를 설명합니다.
- TCP 검사·HTTP 200·HTTP 404를 비교하고 각 결과의 실행 VM을 기록합니다.
- 원격 검사가 막혔다면 증거와 다음 검사를 기록하며 로컬 성공으로 대체하지 않습니다.
- 네트워크·방화벽 설정을 바꾸지 않고 임시 서버·파일·hosts 항목을 정리합니다.

## 공식 자료와 더 읽기

- [Ubuntu Server 이름 해석과 NSS](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/), [getent 매뉴얼](https://manpages.ubuntu.com/manpages/noble/en/man1/getent.1.html)
- [BIND dig 매뉴얼](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility), [Ubuntu 24.04 resolvectl](https://manpages.ubuntu.com/manpages/noble/en/man1/resolvectl.1.html)
- [DNS 개념: RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html), [부정 캐시: RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html), [시험 이름: RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)
- [ping](https://manpages.ubuntu.com/manpages/noble/en/man8/ping.8.html), [tracepath](https://manpages.ubuntu.com/manpages/noble/en/man8/tracepath.8.html), [Ubuntu가 제공하는 Linux traceroute 매뉴얼](https://manpages.ubuntu.com/manpages/noble/en/man1/traceroute.db.1.html)
- [OpenBSD nc](https://man.openbsd.org/nc), [Ncat](https://nmap.org/book/ncat-man.html), [curl 매뉴얼](https://curl.se/docs/manpage.html), [Python HTTP 서버](https://docs.python.org/3.12/library/http.server.html)
- 이후 [Linux 네트워크 진단](../07-linux-network-diagnostics.md)에서 패킷·TCP 큐·MTU 해석을 이어갈 수 있습니다.

[이전: 영구 네트워크 설정](03-persistent-configuration.md) · [퀴즈](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) · [다음: SSH 접속](05-ssh-access.md)
