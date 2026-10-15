# 7. 네트워크 관측과 성능의 첫걸음

> **학습 기준**: Ubuntu Server 24.04 LTS, Rocky Linux 9 대체 경로
>
> **마지막 업데이트**: 2026년 9월 15일

**선수 조건:** [1–6장](README.md#course-map)을 마치고 두 VM이 실습 NIC로 통신하며, 서버의 TCP 8000은 실습 클라이언트에서만 허용되어 있어야 합니다. 다른 실습 서버가 8000을 사용하고 있다면 소유자를 확인하고 해당 실습 절차로 종료합니다.

**학습 목표:** 리스너·연결·큐·패킷·트래픽 양을 구분하고, “느리다”는 문제를 검증 가능한 질문으로 바꿉니다. 예상 학습 시간은 실습을 포함해 2–3시간입니다.

## 도구와 관측 위치 {#observation-tools}

| 질문 | 도구 | 무엇을 알 수 없는가 |
|---|---|---|
| 프로그램이 어느 주소·포트에서 기다리는가? | `ss -ltnp` | 외부에서 실제로 도달할 수 있는지 |
| 연결 상태·큐는 어떤가? | `ss -tinm` | 단일 스냅샷만으로 손실의 원인 |
| 이 NIC를 어떤 패킷이 지났는가? | `tcpdump` | 캡처하지 않은 다른 NIC·네임스페이스 상황 |
| 어떤 호스트 쌍이 대역폭을 사용하는가? | `iftop` | 애플리케이션의 처리 시간이나 정확한 과금량 |
| HTTP 요청은 어느 단계에서 시간을 쓰는가? | `curl -w` | 서버 내부의 함수별 시간 |

`netstat`는 오래된 자료를 읽을 때 만날 수 있습니다. 이 과정의 소켓 관측은 `ss`를 기본으로 합니다. `netstat -lnt`와 `ss -ltn`은 비슷한 질문에 답하지만 출력 형식·필드는 동일하지 않습니다. `netstat`가 없다고 새 도구를 지우거나 시스템을 바꿀 필요는 없습니다.

서버에서 필요한 패키지를 확인합니다. Ubuntu:

```bash
sudo apt update
sudo apt install iproute2 tcpdump python3
```

Rocky:

```bash
sudo dnf install iproute tcpdump python3
```

클라이언트에는 `curl`이 필요합니다. [1장](01-linux-cli.md)의 패키지 관리자 설명을 참고해 설치합니다.

## 자신의 작은 HTTP 트래픽 만들기 {#small-http-workload}

**서버 콘솔 A:** 빈 임시 디렉터리에 실습용 파일 하나만 만듭니다.

```bash
LAB_WEB=$(mktemp -d /tmp/net-web.XXXXXX)
printf 'network lesson\n' > "$LAB_WEB/index.html"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

이 서버는 지정한 디렉터리의 파일을 제공하고 5분 뒤 종료합니다. `timeout`이 종료시켰을 때 종료 코드 124는 시간 제한의 결과입니다. 이는 TLS·사용자 인증을 갖춘 운영용 웹 서버가 아닙니다. 실습 디렉터리에 다른 파일이나 심볼릭 링크를 넣지 않습니다.

**클라이언트:** 요청 하나를 보내고, 이후 1초 간격으로 10개를 보냅니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
for n in $(seq 1 10); do
  curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
    -sS -o /dev/null http://192.0.2.20:8000/
  sleep 1
done
```

**성공 기준:** 첫 응답은 HTTP 200이며 본문에 `network lesson`이 있습니다. 뒤의 요청은 오류 없이 끝나고 서버 로그에 요청이 보입니다. 실패하면 부하를 늘리지 말고 [4장의 진단 순서](04-dns-connectivity.md)로 돌아갑니다.

## 소켓 상태와 큐 읽기 {#socket-observation}

**서버 콘솔 B:** 다른 터미널에서 다음을 실행합니다.

```bash
sudo ss -ltnp 'sport = :8000'
ss -tinm '( sport = :8000 or dport = :8000 )'
```

첫 명령에서 `192.0.2.20:8000` 리스너를 찾습니다. 두 번째 명령은 요청이 진행되는 동안 반복 관측할 수 있습니다. 짧은 연결은 스냅샷 사이에 끝날 수 있으므로 ESTABLISHED 행이 없다고 요청 실패로 판정하지 않습니다. 서버 로그와 패킷 캡처를 함께 봅니다.

| 상태 또는 필드 | 읽는 방법 |
|---|---|
| LISTEN `Recv-Q` / `Send-Q` | 수락을 기다리는 연결 수 / 최대 accept backlog |
| ESTABLISHED `Recv-Q` | 순서대로 도착했지만 애플리케이션이 읽지 않은 바이트 |
| ESTABLISHED `Send-Q` | 확인 응답되지 않은 스트림 바이트; 미전송 데이터도 포함 |
| `rtt` | TCP가 추정한 왕복 시간이며 HTTP 전체 시간과 다름 |
| `cwnd` | 송신 혼잡 윈도; `ss`에서 보통 세그먼트 단위 |
| `skmem` | 오버헤드를 포함한 소켓 메모리 회계; 큐의 페이로드 바이트와 같지 않음 |

이 작은 요청에서 큐가 0인 것은 정상입니다. 큐를 크게 만드는 것이 실습 성공 조건이 아닙니다. [Linux TCP 큐 실습](../07-linux-network-diagnostics.md#tcp-buffer-lab)에는 더 오래 유지되는 연결과 추가 해석이 있습니다.

## NIC를 지정한 패킷 캡처 {#packet-capture}

**서버 콘솔 B:** 가상화 설정에 기록한 실습 NIC의 MAC 주소를 다시 확인합니다.

```bash
ip -br link
```

확인한 이름을 넣습니다. 아래 `enp0s8`은 예시이며 관리 NIC를 선택하지 않습니다.

```bash
LAB_IF=enp0s8
ip -br address show dev "$LAB_IF"
sudo timeout 15 tcpdump -ni "$LAB_IF" -c 20 \
  'host 192.0.2.10 and tcp port 8000'
```

캡처를 시작한 뒤 **클라이언트에서 앞의 curl 요청을 다시 실행**합니다. `-n`은 이름 조회를 하지 않고, `-i`는 인터페이스, `-c 20`은 최대 캡처 패킷 수입니다. 15초가 먼저 지나 종료될 수도 있습니다.

설명용 TCP 플래그 표시는 `[S]`가 SYN, `[S.]`가 SYN+ACK, `[.]`가 ACK, `[F.]`가 FIN+ACK입니다. 데이터·ACK는 여러 방식으로 묶일 수 있습니다. “HTTP 요청 하나는 패킷 정확히 세 개”처럼 고정 개수로 외우지 않습니다.

파일로 남기려면 자신의 실습 트래픽만 짧게 저장합니다.

```bash
LAB_CAPTURE=$(mktemp -d /tmp/net-capture.XXXXXX)
sudo timeout 15 tcpdump -Z "$(id -un)" -ni "$LAB_IF" -c 20 \
  -w "$LAB_CAPTURE/http.pcap" 'host 192.0.2.10 and tcp port 8000'
sudo tcpdump -nn -r "$LAB_CAPTURE/http.pcap"
```

쓰기 명령을 실행하는 동안 다시 클라이언트 요청을 보냅니다. `-Z "$(id -un)"`은 캡처 장치를 연 뒤 현재 일반 사용자로 권한을 내려, 그 사용자가 소유한 임시 디렉터리에 파일을 쓰게 합니다. PCAP에는 주소와 실제 페이로드가 들어갈 수 있습니다. 이 실습용 문자열만 사용하고 SSH 자격 증명이나 실제 사용자 트래픽을 모으지 않습니다. 읽기 명령은 생성된 파일의 권한 차이를 고려해 `sudo`를 사용합니다.

**해석 기준:** 요청 방향과 응답 방향의 주소·포트를 구분합니다. 캡처가 비었다면 먼저 NIC·필터·시간대를 확인합니다. NIC offload 때문에 호스트에서 보이는 패킷 크기·체크섬이 선로의 모습과 다를 수 있습니다. 캡처 한 번의 체크섬 경고만으로 네트워크 장애를 확정하지 않습니다.

## 대역폭과 요청 시간 {#bandwidth-and-time}

`iftop`은 선택 사항입니다. Ubuntu에서는 `sudo apt install iftop`으로 설치할 수 있습니다. Rocky에서 기본 저장소에 없다면 이 실습을 건너뛰거나 [6장의 EPEL 전제](06-firewalls-host-security.md)를 먼저 확인합니다. `sudo dnf install iftop`이 실패했다고 임의의 외부 설치 스크립트를 실행하지 않습니다.

**서버:** 앞에서 확인한 `LAB_IF` 변수가 있는 터미널에서:

```bash
sudo iftop -nNP -i "$LAB_IF" -f 'host 192.0.2.10'
```

클라이언트 요청을 다시 보내 방향별 속도를 읽고 `q`로 종료합니다. 짧고 작은 요청은 거의 0으로 보일 수 있습니다. 이것은 링크 최대 속도나 인터넷 처리량 시험이 아닙니다.

**클라이언트:** HTTP 시간은 다음처럼 관측합니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -sS -o /dev/null \
  -w 'dns=%{time_namelookup} connect=%{time_connect} first_byte=%{time_starttransfer} total=%{time_total}\n' \
  http://192.0.2.20:8000/
```

값은 초 단위이며 시작점부터의 누적 시간입니다. 이 요청은 IP 리터럴을 사용하므로 DNS 성능을 측정하지 않습니다. 첫 바이트 시간에는 앞 단계와 서버 응답 준비가 포함되므로 각 값을 독립적인 구간 시간처럼 더하지 않습니다.

| 측정 대상 | 의미 | 통제할 조건 |
|---|---|---|
| 지연 | 작업이나 왕복에 걸린 시간 | 요청 크기, 경로, 서버 부하 |
| 처리량 | 단위 시간에 전달한 양 | 동시성, 방향, 바이트/비트, 실행 시간 |
| 손실·재전송 | 패킷 누락 관측 또는 TCP 복구 동작 | 캡처 지점·누락, 경로 변화, 시간대 |
| 자원 사용 | CPU·메모리·I/O 사용과 대기 | 프로세스, VM 자원, 다른 부하 |

`1 byte = 8 bits`입니다. `100 Mbit/s`와 `100 MB/s`를 같은 수치로 비교하지 않습니다. 반복 측정에는 조건과 최소·중앙·최댓값 또는 적절한 분포를 함께 기록합니다.

## 커널과 I/O는 다음 단계 {#kernel-next}

다음 명령은 **관측만** 합니다.

```bash
uname -r
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem
lsblk -o NAME,TYPE,SIZE
```

`sysctl`의 버퍼 값은 각 소켓의 현재 사용량이 아닙니다. 값을 높이기 전에 [소켓 버퍼·윈도·BDP](../../kernel/02-network-stack.md#tcp-buffer-policy)를 구분합니다. `lsblk`로 디스크를 식별한 뒤 `/sys/block/장치명/queue/scheduler`를 읽으면 지원/선택된 블록 I/O 스케줄러를 확인할 수 있지만, 모든 가상 장치가 동일한 선택지를 제공하지는 않습니다.

블록 I/O 스케줄러는 저장장치 요청을, 네트워크 qdisc는 네트워크 송신 큐를 다룹니다. 이름에 “스케줄러”가 있다고 같은 튜닝 항목이 아닙니다. 이번 장에서는 sysctl·MTU·qdisc·I/O 스케줄러를 변경하지 않습니다. 심화에서는 한 변수씩 바꾸고 측정·복구하는 별도 실험을 설계합니다.

## 정리와 완료 기준 {#completion}

서버 콘솔 A에서 Ctrl+C 또는 시간 제한으로 서버를 종료한 뒤, **같은 터미널**에서 자신의 파일만 제거합니다.

```bash
rm -- "${LAB_WEB:?}/index.html"
rmdir -- "${LAB_WEB:?}"
```

캡처한 터미널에서 파일도 지웁니다.

```bash
sudo rm -- "${LAB_CAPTURE:?}/http.pcap"
rmdir -- "${LAB_CAPTURE:?}"
```

`${변수:?}` 표기는 변수가 없거나 비어 있으면 명령을 중단합니다. 디렉터리가 비어 있지 않으면 원인을 확인합니다. 광범위한 재귀 삭제로 정리하지 않습니다.

- 리스너, TCP 연결, HTTP 성공은 서로 다른 증거임을 설명합니다.
- PCAP의 양방향 주소와 포트를 식별하고 캡처 지점을 기록합니다.
- 소켓 큐와 대역폭의 단위를 설명하고 IP 리터럴 요청의 DNS 측정 한계를 말합니다.
- 변경 없이 관측할 항목과 별도 실험이 필요한 튜닝을 구분합니다.

## 참고 자료와 다음 장

- [iproute2 ss 매뉴얼](https://man7.org/linux/man-pages/man8/ss.8.html)
- [tcpdump 매뉴얼](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [iftop 작성자 매뉴얼](https://www.ex-parrot.com/pdw/iftop/iftop.8.html)
- [curl 매뉴얼](https://curl.se/docs/manpage.html)
- [Python 3.12 http.server](https://docs.python.org/3.12/library/http.server.html)
- [Linux 블록 다중 큐](https://docs.kernel.org/block/blk-mq.html)

[이전: 방화벽과 호스트 보안](06-firewalls-host-security.md) · [퀴즈](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) · [다음: 종합 실습](08-container-cloud-capstone.md)
