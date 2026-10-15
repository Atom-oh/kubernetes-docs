# Linux 네트워크 진단 — HTTP, TCP 큐, 라우팅과 MTU

> **지원 환경**: Linux, Python 3.9+, curl, iproute2; 라우팅 실습에는 로컬 Docker Engine 필요
> **마지막 업데이트**: 2026년 9월 15일

Linux의 요청 하나에서 출발해 소켓과 다음 홉을 확인하고, 같은 패킷이 컨테이너 네임스페이스를 지나는 과정을 설명합니다. 쿠버네티스나 AWS 네트워크를 조사하기 전에 애플리케이션·전송·라우팅 계층의 증거를 구분하는 연습입니다.

CLI·IP 설정·DNS·SSH·방화벽부터 연습하려면 [입문 8장 과정](beginner/README.md)을 먼저 진행하세요. 이 문서는 그 이후 소켓·ICMP·PMTU를 더 깊게 관측하는 실습입니다.

[IPv4와 다음 홉 기초](../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet), [HTTP 메시지 구조](../basics/06-network-fundamentals-part3.md#http11-message-structure)를 함께 읽으세요.

- [HTTP 메시지](#http-message-lab)
- [TCP 큐와 버퍼](#tcp-buffer-lab)
- [라우팅과 ICMP](#routing-icmp-lab)
- [MTU, PMTU와 MSS](#mtu-mss-lab)
- [Docker 패킷 경로](#docker-packet-path)

## 범위와 준비 {#lab-scope}

이 저장소를 체크아웃한 루트 디렉터리에서 명령을 실행합니다. 안내에 따라 터미널을 나누어 사용하세요.

| 실습 | 필요 도구 | 범위 |
|---|---|---|
| HTTP | Python 3.9+, curl | `127.0.0.1:18080`의 서버 하나, 자동 종료 |
| TCP 관측 | HTTP 서버, Python, iproute2의 `ss` | 로컬 테스트 포트를 읽기 전용으로 관측 |
| 라우팅과 MTU | Linux Docker Engine, Docker CLI, 호스트 iproute2, 미리 받은 이미지 | 임시 컨테이너 세 개와 전용 브리지 두 개 |

실습 도우미는 [http_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/http_lab.py), [routing_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/routing_lab.py)입니다. 실행 전에 지원하는 동작과 [예제 README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md)를 확인하세요.

명령은 실습 절차이며 HTTP 응답 발췌는 **설명용 예시**입니다. 별도로 표시한 라우팅 발췌는 자신의 환경이 아닌 기록된 참조 실행의 결과입니다. 명시된 기준과 라우팅 도우미의 JSON 기록으로 자신의 실행을 판단하세요.

HTTP 도우미는 작은 교육용 HTTP/1.1 서버이며 운영용 서버나 완전한 RFC 구현이 아닙니다. 요청 본문은 최대 4096바이트이며 지원하는 `Content-Length` 프레이밍만 받고 전송 코딩은 거부합니다.

라우팅 도우미는 `unix:///var/run/docker.sock`만 사용하고 원격 Docker 호스트·컨텍스트 환경 설정은 무시합니다. 로컬 Linux Engine과 해당 소켓 접근 권한이 필요하며 원격 컨텍스트나 다른 위치의 rootless 소켓으로 대체할 수 없습니다.

`IMAGE` 상수는 다음 참조로 고정되어 있으며 해당 Engine에 이미지가 미리 있어야 합니다.

```text
nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
```

도우미는 이미지를 내려받지 않습니다. 리소스 생성 전에 고정 서브넷과 호스트에서 확인되는 IPv4 경로·기존 Docker 네트워크 범위의 중복을 검사합니다. 라우팅 실습은 한 번에 하나만 실행하며 충돌하면 공유 호스트 경로를 변경하지 말고 중단하세요.

## 실습 1: HTTP 메시지 읽기 {#http-message-lab}

**목적:** 요청·상태 줄, 필드, 헤더 종료 지점과 콘텐츠 바이트를 구분합니다.

터미널 A에서 서버를 시작합니다.

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

서버는 `127.0.0.1`에만 바인딩하고 120초 뒤 종료합니다. 허용되는 최대 실행 시간은 600초입니다. 포트가 사용 중이면 비어 있는 다른 로컬 포트를 선택하고 명령·필터의 포트를 모두 맞추세요. 관련 없는 리스너를 중지하면 안 됩니다.

터미널 B에서 GET과 HEAD를 요청합니다.

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 -i http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 5 --http1.1 -I http://127.0.0.1:18080/lesson
```

첫 옵션인 `--disable`은 기본 curl 설정을 건너뛰고 `--noproxy '*'`는 설정된 프록시를 경유하지 않도록 합니다. `-i`는 응답 헤더를 포함하고 `-I`는 HEAD를 전송합니다. 일반 GET의 본문 표시만 숨기는 옵션이 아닙니다.

아래는 GET 응답의 설명용 발췌이며 자동 생성되는 `Date`·`Server` 필드는 생략했습니다.

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 6

hello
```

실제 본문은 `b"hello\n"`이며 16진수로 `68 65 6c 6c 6f 0a`입니다. 마지막 LF가 여섯 번째 바이트입니다. HTTP/1.1 전송에서 헤더 줄과 헤더·본문 구분에는 CRLF를 사용하지만 이 Markdown 화면에는 LF로 표시합니다.

같은 6바이트를 echo 끝점에 보냅니다.

```bash
printf 'hello\n' | curl --disable --noproxy '*' --max-time 5 --http1.1 -i \
  -H 'Content-Type: text/plain' --data-binary @- \
  http://127.0.0.1:18080/echo
```

`--data-binary @-`는 LF를 제거하지 않고 표준 입력을 읽으며 POST를 선택합니다. 도우미는 바이트를 그대로 반환하고 `Content-Type: application/octet-stream`을 사용합니다. 텍스트·JSON·폼을 파싱하지 않습니다.

| 관측 | 기대 기준 | 해석 |
|---|---|---|
| GET `/lesson` | HTTP/1.1 200, 길이 6, 콘텐츠 6바이트 | 길이에는 시작 줄과 헤더가 포함되지 않음 |
| HEAD `/lesson` | HTTP/1.1 200과 길이 6, 응답 본문 없음 | 대응하는 GET 표현의 길이를 설명하는 필드 |
| POST `/echo` | HTTP/1.1 200, 길이 6, `hello`와 LF 그대로 반환 | 바이트 보존과 미디어 유형 해석은 별개 |

비ASCII 문자는 UTF-8에서 여러 바이트를 차지할 수 있습니다. 보이는 문자 수 대신 실제 개행까지 포함한 인코딩 바이트 수를 세세요.

요청 줄과 송신 필드를 클라이언트 디버그 추적으로 확인합니다.

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 --trace-ascii - \
  --output /dev/null http://127.0.0.1:18080/lesson
```

이것은 **curl의 클라이언트 디버그 출력**이며 패킷 캡처가 아닙니다. 출력의 주석은 전송 바이트나 TCP 세그먼트 경계가 아니고 라우터가 본 내용을 증명하지도 않습니다. 추적에는 실습용 데이터만 사용하세요.

HTTPS에서는 클라이언트가 표시하는 HTTP 평문을 세션 비밀값 없는 수동 네트워크 캡처에서는 읽을 수 없습니다. HTTP/2·HTTP/3의 바이너리 프레이밍도 다르므로 도구의 텍스트 표시가 실제 전송 인코딩은 아닙니다.

**정리:** 터미널 A에서 Ctrl+C로 서버를 종료하거나 타이머 종료를 기다립니다. 서버는 영속적인 애플리케이션 데이터를 만들지 않습니다. 다음 실습 전에 타이머가 만료되었다면 다시 시작하세요.

## 실습 2: TCP 큐와 버퍼 관측 {#tcp-buffer-lab}

**목적:** 지속 연결 하나를 소켓 상태·스트림 큐·메모리 집계와 연결합니다.

터미널 A에서 같은 120초 서버를 시작합니다. 터미널 B에서는 횟수가 제한된 다음 클라이언트를 실행합니다.

```bash
python3 - <<'PY'
import http.client
import time

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
try:
    for number in range(30):
        connection.request("GET", "/lesson")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == "6"
        assert body == b"hello\n"
        if number == 0:
            print("Client endpoint:", connection.sock.getsockname(), flush=True)
        time.sleep(1)
finally:
    connection.close()
PY
```

클라이언트는 응답을 모두 소비한 뒤 연결을 재사용합니다. 작은 GET을 1초 간격으로 30회 요청하므로 짧은 curl 프로세스를 각각 실행할 때보다 수립된 소켓을 관측하기 쉽습니다.

실행 중 터미널 C에서 확인합니다.

```bash
ss -ltn 'sport = :18080'
ss -tinm state established '( sport = :18080 or dport = :18080 )'
```

두 번째 명령을 몇 차례 반복하세요. 현재 네트워크 네임스페이스를 조회하며 테스트 포트로 제한합니다. 루프백 연결의 양 끝이 모두 로컬에 표시될 수 있으므로 서버 포트와 클라이언트 임시 포트를 구분하세요.

**기대 기준:** `127.0.0.1:18080`에 리스너가 있고 클라이언트 실행 중 수립된 연결이 보입니다. 큐·RTT·메모리 값은 환경마다 다르며 이 작은 워크로드에서 큐가 0인 것은 정상입니다.

| 필드·상태 | 의미 |
|---|---|
| ESTABLISHED `Recv-Q` | 순서대로 수신했지만 애플리케이션이 아직 소비하지 않은 바이트 |
| ESTABLISHED `Send-Q` | 아직 확인 응답되지 않은 스트림 바이트; 아직 전송하지 않은 바이트도 포함 |
| LISTEN `Recv-Q` | `accept()`를 기다리는 연결 수이며 페이로드 바이트 수가 아님 |
| LISTEN `Send-Q` | 최대 accept backlog이며 송신 버퍼 크기가 아님 |
| `skmem` `r` / `rb` | 수신 메모리 집계 / 수신 메모리 한도 |
| `skmem` `w` / `tb` | 대기 중인 송신 메모리 / 송신 메모리 한도 |
| `rtt`, `mss`, `cwnd` | RTT, TCP 데이터 크기, 혼잡 윈도 정보; `cwnd`의 단위는 보통 세그먼트 |

소켓 메모리에는 관리 비용이 포함되므로 스트림 큐 열과 같지 않을 수 있습니다. 리스너 backlog와 미완료 SYN 큐도 다릅니다. 필드 설명은 [ss(8) 매뉴얼](https://man7.org/linux/man-pages/man8/ss.8.html)을 참고하세요.

현재 버퍼 정책을 변경하지 않고 읽습니다.

```bash
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.ipv4.tcp_moderate_rcvbuf
```

`tcp_*mem`의 세 값은 최소·기본·자동 크기 조정 한도이며 각 소켓의 현재 점유량이 아닙니다. 수신 자동 조정과 애플리케이션의 명시적인 소켓 옵션이 결과에 영향을 줍니다. 메모리 한도는 광고되는 수신 윈도나 `cwnd`와도 다릅니다.

수신 큐가 커진다면 읽기 진행을 조사하고, 송신 큐가 계속 남는다면 애플리케이션·확인 응답·경로 증거를 함께 보세요. 한 번의 스냅샷이나 더 큰 버퍼만으로 처리량 개선을 증명할 수 없습니다.

이 6바이트 워크로드는 정상 동작 관측용이며 의도적으로 역압력을 만들거나 최대 처리량을 측정하지 않습니다. 튜닝을 제안하기 전에 [소켓과 버퍼 해석](../kernel/02-network-stack.md#tcp-buffer-policy)을 이어서 읽으세요.

**정리:** 클라이언트는 30회 반복 후 연결을 닫으며 중단되어도 `finally`에서 닫습니다. 터미널 A의 서버를 종료하거나 타이머 종료를 기다리세요. 되돌릴 sysctl 변경은 없습니다.

## 실습 3: 라우팅과 ICMP 추적 {#routing-icmp-lab}

**목적:** 선택된 다음 홉을 확인하고 이름 조회와 패킷 전달을 구분하며 TTL을 제한한 probe를 ICMP 응답과 연결합니다.

라우팅 도우미는 다음 임시 토폴로지를 만듭니다.

```text
client namespace          router namespace                 server namespace
192.0.2.2/29 --- left --- 192.0.2.3/29
                          198.51.100.2/29 --- right --- 198.51.100.3/29
left bridge: 192.0.2.0/29             right bridge: 198.51.100.0/29
```

두 전용 브리지 모두 `com.docker.network.bridge.enable_ip_masquerade=false`를 설정합니다. 도우미는 연결된 경로를 유지하면서 **자신의 컨테이너 세 개 안에서 IPv4 기본 경로를 모두 제거**한 뒤 명시적인 실습 경로를 추가합니다.

컨테이너는 모든 capability를 제거한 뒤 `NET_ADMIN`·`NET_RAW`만 추가하며 라우터 네임스페이스 안에서 전달을 활성화합니다. privileged 컨테이너나 host 네트워킹을 사용하지 않고 포트를 공개하거나 AWS 리소스를 만들지도 않습니다.

Docker는 호스트 브리지를 만들고 일반적인 네트워크 규칙을 관리합니다. 도우미가 호스트 경로·sysctl·iptables 규칙을 수동으로 변경하지는 않지만, 이것이 호스트에 변화가 없거나 에어갭을 구성한다는 뜻은 아닙니다.

클라이언트에는 `198.51.100.0/29`의 경로를 `192.0.2.3` 경유로, 서버에는 `192.0.2.0/29`의 반환 경로를 `198.51.100.2` 경유로 추가합니다.

아직 존재하지 않는 출력 경로를 선택하세요.

```bash
python3 examples/networking/foundations/routing_lab.py \
  --output ./routing-observation-01.json
```

도우미는 기존 파일을 덮어쓰지 않습니다. **한 번의 실행에 아래 MTU 실습도 포함**되므로 해당 절을 위해 두 번째 실행을 동시에 시작하지 마세요.

다음은 도우미가 **클라이언트 네임스페이스**에서 실행하는 명령입니다. 호스트 셸에 붙여 넣는 지시가 아니라 결과 해석을 위해 표시한 것입니다.

```text
ip -j route get 198.51.100.3
ip -j neigh show to 192.0.2.3
ip -j neigh show to 198.51.100.3
ping -n -c 1 -W 1 -t 1 198.51.100.3
traceroute -n -I -m 4 -q 1 -w 1 198.51.100.3
```

생성된 라우터 컨테이너 이름을 Docker DNS로 조회하기도 합니다. 이름은 실행별 접두부에 따라 달라지며 DNS 응답 자체는 도달 가능성 검사가 아닙니다.

| JSON 관측 항목 | 기대 기준 | 해석 |
|---|---|---|
| `defaultRoutes` | 클라이언트·라우터·서버 목록 모두 비어 있음 | 컨테이너 세 개 모두 IPv4 기본 경로를 유지하지 않음 |
| `route` | 게이트웨이 `192.0.2.3`, 출발지 `192.0.2.2` | 목적지에 라우터를 거쳐 도달 |
| `dns` | 왼쪽 네트워크에서 라우터 이름이 `192.0.2.3`으로 해석됨 | Docker 이름 조회 동작 |
| `nextHopNeighbor` | `192.0.2.3`의 MAC 주소 존재 | ARP로 다음 홉 확인 |
| `remoteNeighbor` | 비어 있음 | 원격 서버는 클라이언트의 Ethernet 이웃이 아님 |
| `ttlOne` | probe 실패, 캡처에 ICMP Time Exceeded 존재 | 의도대로 라우터에서 TTL 만료 |
| `traceroute` | 첫 홉 `192.0.2.3`, 목적지 `198.51.100.3` | ICMP probe로 IP 두 홉 도달 |

`ttlOne`을 확인할 때 도우미는 라우터 네임스페이스에서 필터 `icmp[0] == 11`로 실제 `tcpdump`를 시작합니다. 캡처 준비를 기다린 뒤 TTL-1 ping을 전송합니다. 기대하는 응답은 원래 probe 일부를 포함한 IPv4 ICMP Type 11 Code 0입니다.

이 캡처와 연결된다면 여기서 ping 실패는 진단을 위해 의도한 자극입니다. probe는 ICMP Echo이고 Time Exceeded는 별도의 반환 메시지입니다.

traceroute `-I`는 ICMP Echo probe를 사용합니다. UDP·TCP 방식은 필터링과 목적지 응답이 다를 수 있습니다. `*`는 대기 시간 안에 대응하는 응답이 없었다는 기록이며 그 자체로 종단 간 손실을 증명하지 않습니다. RTT에는 응답의 반환 경로도 포함됩니다.

도우미가 끝난 뒤 자신의 증거 파일을 확인합니다.

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(Path("routing-observation-01.json").read_text())
print("Status:", record["status"])
print("Checks:", record.get("checks", {}))
print("Cleanup:", record.get("cleanup", "not reported"))
PY
```

**성공 기준:** 도우미가 정상 종료하고 `status: passed`를 기록하며 명명된 검사 여덟 개가 모두 참이고 정리 결과가 보고되어야 합니다. 경로·DNS 조회 성공만으로 실패한 패킷 관측을 대체할 수 없습니다.

**정리:** 정상 완료·관측 실패·처리 가능한 중단 시 도우미는 자신이 만든 컨테이너·네트워크 ID를 제거하려고 시도합니다. 정리 오류도 실행 실패입니다. 강제 종료는 정리를 막을 수 있으므로 기록된 ID로 잔여 리소스를 확인하고 공유 Docker 리소스를 광범위하게 prune하지 마세요. 다음 절의 해석을 위해 JSON은 보관합니다.

### 기록된 참조 실행 {#routing-reference-run}

[예제 검증 기록](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md#validation)에서 연결하는 2026년 9월 14일 실행은 Linux Docker Engine 25.0.16에서 성공했습니다. 검사 여덟 개가 모두 통과했고 기본 경로 목록 세 개가 비어 있었으며 생성한 ID도 제거했습니다. traceroute는 `192.0.2.3` 다음에 `198.51.100.3`을 관측했습니다.

타임스탬프와 인터페이스 접두부를 생략한 실측 TTL 오류 패킷 내용입니다.

```text
IP 192.0.2.3 > 192.0.2.2: ICMP time exceeded in-transit, length 92
```

이것은 해당 환경의 기능 검증 증거입니다. 다른 호스트에서 동일한 시간·인터페이스 이름·MAC 주소나 호환성을 보장하지 않습니다.

## 실습 4: MTU, PMTU와 MSS 구분 {#mtu-mss-lab}

**목적:** 실제 ICMP 오류로 크기에 따른 실패를 설명하되 ICMP 페이로드 크기를 TCP MSS로 오해하지 않습니다.

같은 라우팅 실행과 JSON 기록을 사용합니다. 도우미는 경로 조회로 서버 방향의 라우터 인터페이스를 찾은 뒤 **그 컨테이너 인터페이스의 MTU를 1280으로 설정**합니다. 송신 인터페이스 이름을 `eth1`이라고 가정하지 않습니다.

첫 클라이언트 probe를 보낼 때 라우터에서 `icmp[0] == 3 and icmp[1] == 4`를 캡처합니다. 이어서 작은 probe를 전송합니다.

```text
ping -n -c 1 -W 1 -M do -s 1372 198.51.100.3
ping -n -c 1 -W 1 -M do -s 1200 198.51.100.3
```

`-M do`는 IPv4 Don't Fragment 동작을 요청합니다. 여기서 사용하는 일반적인 IPv4 헤더 20바이트와 ICMP 헤더 8바이트를 더하면 다음과 같습니다.

| Probe | IP 패킷 크기 | 기대 기준 |
|---|---|---|
| ICMP 데이터 1372바이트 | `1372 + 8 + 20 = 1400`바이트 | 송신 MTU 1280보다 커서 실패하고 ICMP Type 3 Code 4 캡처 |
| ICMP 데이터 1200바이트 | `1200 + 8 + 20 = 1228`바이트 | 해당 송신 MTU 안에 들어가 Echo Reply 성공 |

`pmtu.probeOutput`, `pmtu.capture`, `smallerPacket`, `routeAfterFeedback`을 확인하세요. 중요한 증거는 특정 RTT나 정확히 일치하는 출력 문구가 아니라 **Fragmentation Needed 피드백과 작은 패킷의 성공**입니다.

같은 기록에서 다음 ping 줄을 실측했습니다.

```text
From 192.0.2.3 icmp_seq=1 Frag needed and DF set (mtu = 1280)
```

데이터 1200바이트 probe는 응답을 받았고 `routeAfterFeedback`에는 MTU 1280이 표시되었습니다. 해당 실행의 관측이지 고정된 지연이나 캐시 만료 시간을 보장하지는 않습니다.

피드백 이후 Linux는 목적지 PMTU를 캐시할 수 있습니다. 다음 큰 전송은 라우터까지 가지 않고 로컬에서 “message too long”으로 실패할 수 있습니다. `routeAfterFeedback`에 학습한 MTU 정보가 표시될 수 있지만 필드와 만료 동작은 환경마다 다릅니다.

도우미의 캡처는 임시 클라이언트 네임스페이스에서 의도적으로 유발한 첫 실패에 대응합니다. 이후 ICMP 메시지가 없다는 이유만으로 앞선 피드백이 무효가 되지는 않습니다.

**MSS는 별개입니다.** MSS는 TCP 데이터 바이트 수를 제한합니다. Ethernet MTU 1500과 기본 IPv4·TCP 헤더에서는 `1500 − 20 − 20 = 1460`이 기본 MSS 계산입니다. IP·TCP 옵션과 경로 조건에 따라 실제 패킷의 데이터가 줄어들 수 있습니다.

위의 1372·1200은 ICMP 데이터 크기이며 **측정한 MSS 값이 아닙니다**. 루프백 TCP 실습에서도 MSS가 반드시 1460으로 보여야 하는 것은 아닙니다. 루프백에는 별도의 MTU와 커널 동작이 적용됩니다.

TSO·GSO·GRO와 체크섬 오프로드 때문에 호스트 캡처와 물리 링크의 패킷이 다를 수 있습니다. 큰 캡처 단위나 체크섬 오류처럼 보이는 결과를 전송 장애로 해석하기 전에 인터페이스·네임스페이스·관측 지점을 확인하세요.

IPv6 라우터는 전달하는 패킷을 단편화하지 않고 ICMPv6 Packet Too Big을 사용합니다. 전통적인 PMTUD와 패킷화 계층의 탐색은 피드백 의존성이 다릅니다. [ICMP 기초](../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation)를 참고하세요.

**정리:** 라우팅 도우미가 자신이 만든 다른 ID와 함께 임시 라우터를 제거하면 MTU 변경도 함께 사라집니다. 호스트 물리 인터페이스의 MTU는 변경하지 않습니다. 분석 뒤 자신의 증거 파일만 보관하거나 삭제하세요.

## Docker 패킷 경로 설명하기 {#docker-packet-path}

**목적:** 관측 결과를 Linux 네임스페이스·가상 Ethernet 링크·경로 조회와 연결합니다.

기존 라우팅 기록을 사용하며 추가 컨테이너는 필요하지 않습니다. `route`, 이웃 관측, ICMP 캡처, 기록된 명령을 대조하세요.

1. 클라이언트 네임스페이스에서 `198.51.100.0/29 via 192.0.2.3`을 선택합니다. 명시적인 경로가 다음 홉을 정합니다.
2. 클라이언트는 ARP로 라우터 왼쪽 MAC을 확인합니다. IP 목적지는 `198.51.100.3` 그대로입니다.
3. veth 쌍과 왼쪽 브리지가 Ethernet 프레임을 라우터로 전달합니다. L2 브리징은 IP TTL 홉을 소비하지 않습니다.
4. 라우터 네임스페이스가 IPv4 전달을 수행합니다. TTL을 줄이고 서버 경로를 조회하며 송신 MTU를 확인합니다.
5. 오른쪽 네트워크에서 라우터는 서버 MAC을 확인한 뒤 새 Ethernet 프레임을 보냅니다. 의도된 라우팅 경로에서는 이 출발지·목적지 IP를 변환하지 않습니다.
6. 서버의 명시적인 반환 경로는 `198.51.100.2`를 사용합니다. 요청 전달에 성공해도 응답 경로가 동작해야 합니다.

**기대 기준:** 기록에서 각 조회의 네임스페이스·IP 목적지·로컬 ARP 대상·반환 경로를 식별할 수 있어야 합니다. 다른 실행의 인터페이스 이름이나 MAC 값을 그대로 가정하지 마세요.

Docker DNS 이름 해석과 Linux 패킷 전달은 별도의 관측입니다. DNS 응답이 정확해도 경로·전달 정책·반환 경로가 잘못될 수 있습니다.

각 네트워크 네임스페이스에는 자체 루프백 장치도 있습니다. 컨테이너 안의 `127.0.0.1`은 호스트의 HTTP 도우미에 연결되지 않으며 이 실습은 이를 바꾸는 host-network 모드를 사용하지 않습니다.

구성은 **전용 사용자 정의 브리지 두 개와 명시적인 라우터**이며 masquerading을 끄고 컨테이너 세 개의 IPv4 기본 경로를 제거합니다. 이는 의도된 실습 경로를 정하는 것이지 일반적인 보안 격리를 보장하지 않습니다. 기본 Docker의 인터넷 NAT, 공개 포트 전달, 인터넷 처리량을 측정하는 실습이 아닙니다.

**정리:** 완료된 기록을 재사용하며 라우팅 도우미는 이미 리소스 정리를 시도했습니다. 실패하거나 불완전한 기록이라면 실패한 단계를 확인하고 공유 방화벽 제어를 비활성화하지 마세요.

[컨테이너 기술](../basics/03-container-technology.md)을 읽은 뒤 [Core 서비스와 네트워킹 실습](../labs/core/03-services-networking-lab.md)으로 이어가세요. 쿠버네티스 CNI·Service 변환·AWS VPC 라우팅에는 별도 규칙이 있으므로 Docker 토폴로지를 복사하기보다 각 계층에서 확인합니다.

## 참고 자료와 복습 {#references}

- [HTTP 의미: RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), [HTTP/1.1 프레이밍: RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)
- [curl 매뉴얼](https://curl.se/docs/manpage.html): HTTP 버전, HEAD, 바이너리 요청 데이터, 추적
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html), [socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html), [Linux TCP 버퍼 정책](https://docs.kernel.org/networking/ip-sysctl.html)
- [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html), [ip-neighbour(8)](https://man7.org/linux/man-pages/man8/ip-neighbour.8.html), [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [iputils ping 매뉴얼](https://github.com/iputils/iputils/blob/master/doc/ping.xml), [traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [ICMP: RFC 792](https://www.rfc-editor.org/rfc/rfc792.html), [IPv4 라우터 동작: RFC 1812](https://www.rfc-editor.org/rfc/rfc1812.html), [MSS: RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)
- [Docker 브리지 네트워킹과 드라이버 옵션](https://docs.docker.com/engine/network/drivers/bridge/)

[퀴즈로 이해도 확인](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
