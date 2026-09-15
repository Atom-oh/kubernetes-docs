# Linux 네트워크 성능: 설명하기 전에 측정하기

> **실습 기준**: 자신이 소유한 Ubuntu Server 24.04 LTS 또는 Rocky Linux 9 게스트, 범위가 제한된 루프백 관측
>
> **마지막 업데이트**: 2026년 9월 15일

## 목적과 선행 조건 {#purpose}

이 워크북은 느린 트랜잭션이 애플리케이션, 전송 계층, 커널, 경로 중 어디에서 기다리는지 묻습니다.
결과물은 경쟁하는 설명, 부정 증거, 복구 기록을 포함한 재현 가능한 측정 보고서입니다.
고정 지연 시간, 처리량 향상 또는 벤치마크 점수를 약속하지 않습니다.

[입문 과정](../beginner/README.md), 특히 [관측 장](../beginner/07-monitoring-performance.md)을 완료하세요.
[커널 네트워크 스택](../../kernel/02-network-stack.md)을 소켓/VFS부터 송수신과 훅 위치까지 읽습니다.
이후 [Linux 네트워크 진단](../07-linux-network-diagnostics.md#tcp-buffer-lab)에서 기존 HTTP 도우미와 소켓 상태별 해석을 복습합니다.
바이트 스트림과 증거 용어는 [프로토콜 프로젝트](01-protocol-projects.md)에서 이어집니다.
[기존 Pod 벤치마크 문서](../06-pod-network-benchmark.md)는 나중에 읽으세요. 루프백 수치는 CNI 벤치마크가 아닙니다.

Linux 프로세스·파일 다루기, 기본 Python, TCP 시퀀스·윈도 지식, 비트·바이트·초 단위 계산이 필요합니다.
C와 드라이버 개발은 선택 심화이며, 제한된 Python 실험의 선행 조건은 아닙니다.
이 장을 작성하면서 네트워크·클라우드 실험을 실행하지 않았습니다. 아래 기준은 이후 소유한 게스트에서 수행할 지침입니다.

## Bootlin과 일차 자료 읽기 지도 {#readings}

[Bootlin Linux 네트워킹 교육 페이지](https://bootlin.com/training/networking/)는 **2026년 9월 15일**에 접근 가능했습니다.
무료로 내려받을 수 있는 [슬라이드](https://bootlin.com/doc/training/networking/networking-slides.pdf)와 [EspressoBin 실습 지침](https://bootlin.com/doc/training/networking/networking-espressobin-labs.pdf)을 학습에 활용합니다.
공개 문서에는 무료 강사 지원, 보드 제공 또는 임의 하드웨어와의 호환성 보장이 포함되지 않습니다.

| 읽기 자료 | 필요한 배경 | 이 장에서 답할 질문 |
|---|---|---|
| Bootlin 네트워크 스택·사용자 공간 인터페이스 | Linux 관리, 소켓, 프로토콜 계층 | 애플리케이션 바이트가 어디에서 커널 작업으로 대기하는가? |
| Bootlin 드라이버·NAPI·하드웨어 실습 | 충분한 C, 커널·모듈 개발, 인터럽트, DMA, 해당 보드·도구 체인 준비 | 어떤 주장에 실제 드라이버와 NIC가 필요한가? |
| [커널 NAPI 문서](https://docs.kernel.org/networking/napi.html) | 인터럽트와 폴링 구분 | 무엇을 어떤 예산·실행 문맥으로 폴링하는가? |
| [커널 확장성 문서](https://docs.kernel.org/networking/scaling.html) | CPU 큐와 흐름 해시 | 처리 CPU 선택에 RSS와 RPS 중 무엇이 관여하는가? |
| [세그먼트 오프로딩](https://docs.kernel.org/networking/segmentation-offloads.html) | MTU·MSS와 관측 지점 | 캡처 단위가 실제 전송 프레임보다 클 수 있는 이유는? |
| [TCP sysctl 문서](https://docs.kernel.org/networking/ip-sysctl.html) | 소켓 메모리, 윈도, 자동 조정 | 어떤 한계가 정책이고 어떤 값이 개별 흐름 관측인가? |
| [iproute2 ss 원본 매뉴얼](https://github.com/iproute2/iproute2/blob/main/man/man8/ss.8), [tc 원본 매뉴얼](https://github.com/iproute2/iproute2/blob/main/man/man8/tc.8) | TCP 상태와 큐 카운터 | 출력한 양은 정확히 무엇을 세는가? |

Bootlin 하드웨어 경로에서는 실습 PDF 리비전, 요구 보드, 직렬 콘솔, 부트로더, 커널 트리·설정과 교차 도구 체인을 기록합니다.
확인한 과정은 Marvell Armada 3720 ARM64 프로세서의 EspressoBin을 사용합니다. 입문 VM이 이 명시된 환경을 대신한다고 가정하지 마세요.
환경을 갖추지 못했다면 패킷 경로 분석을 완료하고 하드웨어 관측은 이용 불가로 표시합니다.
교육 등록·인증서는 이 워크북의 증거 기반 완료와 별개입니다.

## 명령 전에 측정 설계 {#measurement-design}

시작 전에 실험 카드를 작성합니다. 빈칸은 해야 할 일이지 결과를 만들어 넣을 자리가 아닙니다.

| 항목 | 기본 실험의 선택 |
|---|---|
| 가설 | 클라이언트 본문 읽기를 늦추면 경로 손실 없이도 애플리케이션 완료 시간이 증가한다 |
| 자원 소유자·관측자 | 폐기 가능한 게스트의 자신의 사용자, 게스트 이름과 네트워크 네임스페이스 기록 |
| 클라이언트·서버 | Python 클라이언트와 저장소 HTTP 도우미, `127.0.0.1:18080`만 사용 |
| 변수 | 요청·echo 본문 64 또는 4096바이트, 클라이언트 읽기 대기 0 또는 0.15초 |
| 고정 조건 | 동시 요청 하나, 요청마다 새 TCP 연결, 동일 종단·도우미 |
| 예산 | 준비 요청 1개와 측정 요청 15개, 방향마다 페이로드 42 KiB 미만 |
| 마감 | 클라이언트 전체 60초, 소켓 작업 시간 제한 2초, 서버 180초 |
| 관측자 | 클라이언트 단조 시계 시간, 범위가 지정된 `ss`, 전후 인터페이스·qdisc 카운터 |
| 실패 규칙 | 콘텐츠·상태 실패, 예상 밖 수신 대기, 도구 누락, 마감 초과 시 중단 |
| 복구 | 자신의 클라이언트를 닫고 포그라운드 서버 종료 후 수신 대기 제거 확인 |

0.15초 대기는 **입력 매개변수**이며 측정된 네트워크 지연이 아닙니다.
이 부하는 수신 윈도 소진이나 루프백 포화를 강제하기에는 의도적으로 작습니다.
이 goodput으로 NIC 용량, 인터넷 지연 또는 라우팅 수렴을 주장하지 않습니다.
가능하면 게스트를 한가하게 유지하고 다른 부하를 기록하세요. 루프백 카운터에는 다른 프로세스도 포함됩니다.

## 도구·역할·범위 {#readiness}

누락된 패키지는 트랜잭션 미리 보기와 복구 기록을 포함한 [입문 게스트 도구 준비](../beginner/README.md#guest-tools)를 따릅니다.
선택한 경로에 필요한 도구만 자신의 게스트에 설치합니다. 기본 이미지에 존재한다고 가정하지 않습니다.

| 도구 | Ubuntu 공급자 | Rocky 공급자 | 역할·권한 |
|---|---|---|---|
| `python3` 3.9 이상 | `python3` | `python3` | 일반 사용자 클라이언트·서버 |
| `ip`, `ss` | `iproute2` | `iproute` | 일반 사용자 범위 지정 관측 |
| `tc` | `iproute2` | `iproute-tc` | 허용되는 환경에서 일반 사용자 qdisc 카운터 읽기 |
| `timeout`, `sha256sum` | `coreutils` | `coreutils` | 실행 제한·도우미 식별 |
| `tcpdump` | `tcpdump` | `tcpdump` | 선택 패킷 캡처, 캡처만 sudo |
| `ethtool` | `ethtool` | `ethtool` | 선택 기존 NIC 조사, 일부 조회는 권한 필요 |
| `pidstat` | `sysstat` | `sysstat` | 선택 프로세스 CPU 표본 |
| `bpftool`, `bpftrace` | 커널·배포판별 패키지 | 커널·배포판별 패키지 | 선택 사항, 공급자·커널 지원·권한 별도 확인 |

선택 행을 충족하기 위해 커널 패키지를 설치하거나 추적을 활성화하지 마세요.
BPF 도구는 설치 패키지 공급자, 도구·커널 버전, BTF 여부와 발생한 접근 오류를 기록합니다.
명령이 존재한다고 BPF 권한까지 사용할 수 있는 것은 아닙니다.

게스트의 저장소 루트에서 확인합니다.

```bash
command -v python3 ip ss tc timeout sha256sum
python3 --version
uname -r
ip -Version
ss -V
tc -V
sha256sum examples/networking/foundations/http_lab.py
ss -ltn 'sport = :18080'
```

필터에 수신 대기가 있으면 중단하고 다른 빈 포트를 일관되게 사용합니다. 관련 없는 서비스를 종료하지 마세요.
`mkdir -m 700 linux-evidence-01`로 새 비공개 디렉터리를 만들고 이미 있으면 새 이름을 씁니다.
저장소 리비전, OS 배포판, 도구 버전, 네임스페이스와 시작·종료 UTC 시각을 그 안에 기록합니다.
아래 모든 클라이언트·서버 명령은 같은 게스트와 네임스페이스의 일반 사용자로 실행합니다.

## 처리 경로 따라가기 {#packet-path}

기존 커널 장의 그림에 다음 구분을 덧붙입니다.
일반적인 native 드라이버 수신 경로는 NIC 큐 → NAPI poll → 선택적 native XDP → 스택·전송 계층 → 소켓 → 애플리케이션입니다.
드라이버·장치 오프로딩 모드와 generic XDP는 위치가 다릅니다. 모든 훅을 같은 지점에 그리지 말고 모드를 명시하세요.
송신은 소켓·전송 계층에서 라우팅과 해당 큐 처리를 거쳐 장치로 진행합니다.

| 메커니즘 | 바꾸는 것 | 관측과 반례 |
|---|---|---|
| NAPI | 주로 인터럽트와 연계하는 폴링 기반 드라이버 이벤트 처리 | 폴링 예산이 애플리케이션 지연을 보장하지 않음 |
| RSS | 하드웨어가 흐름을 수신 큐에 분산 | 한 흐름은 여전히 한 큐에 해시될 수 있음 |
| RPS | 소프트웨어가 수신 처리 CPU 선택 | CPU 분산만으로 NIC의 RSS 수행을 증명할 수 없음 |
| GSO / TSO | 소프트웨어·장치에서 큰 송신 단위 분할 | 큰 호스트 캡처 단위가 실제 대형 프레임일 필요는 없음 |
| GRO | 상위 계층 처리 전 수신 작업 결합 | 캡처 단위 수와 물리 프레임 수가 같을 필요는 없음 |
| qdisc | 적용되는 송신 작업을 대기·스케줄링 | 루프백의 `noqueue`가 다른 물리 NIC의 큐 부재를 뜻하지 않음 |
| 소켓 윈도 | 수신자 흐름 제어와 송신자 혼잡 허용량 | 큰 설정 버퍼가 두 윈도 모두의 가용성을 증명하지 않음 |

루프백에는 벤치마크할 물리 RSS 큐, 링크 직렬화, 스위치 경로가 없습니다.
루프백 처리 특성을 물리 드라이버에 그대로 적용하지 마세요.

**이미 존재하는 소유 VM 흐름**에서는 양쪽 종단, 기존 인터페이스·경로, 흐름 튜플, 소유자와 원래 트래픽 예산을 적은 관측 계획으로 대체합니다.
식별한 실습 인터페이스에서 지원되는 경우에만 읽기 전용 `ethtool -k`, `ethtool -l`, `ethtool -x`, `ethtool -S`로 관측합니다.
미지원·권한 거부를 기록하고 드라이버, 채널 수, 오프로딩을 변경하지 않습니다.
기본 경로에는 광범위한 인터페이스 명령이나 새 VM·클라우드 자원이 필요하지 않습니다.

## 제한된 루프백 실험 {#bounded-experiment}

도우미 시작 전에 상태를 보존합니다.

```bash
ip -s link show dev lo > linux-evidence-01/link-before.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-before.txt
ss -ltn 'sport = :18080' > linux-evidence-01/listener-before.txt
```

터미널 A에서 자신의 서버를 시작하고 준비 메시지를 기다립니다.

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

클라이언트 직전에 터미널 C에서 실행 횟수가 제한된 소켓 관측자를 시작합니다.

```bash
timeout 25s bash -c '
  for sample in {1..40}; do
    date -u +%FT%T.%NZ
    ss -tinm state established "( sport = :18080 or dport = :18080 )"
    sleep 0.5
  done
' > linux-evidence-01/sockets.txt
```

터미널 B에서 이 과정을 위해 작성한 측정 클라이언트를 실행합니다. DNS를 질의하거나 프록시 설정을 읽지 않습니다.
준비 요청을 포함한 최대 요청 수는 16개이고 연결은 `finally`에서 닫힙니다.
요청 사이의 0.25초 대기는 요청 빈도도 제한합니다.

```bash
timeout --signal=INT --kill-after=2s 60s python3 - <<'PY' \
  > linux-evidence-01/transactions.jsonl
import datetime
import http.client
import json
import time

phases = [("warmup", 64, 0.0, 1),
          ("small", 64, 0.0, 5),
          ("large", 4096, 0.0, 5),
          ("reader_pause", 4096, 0.15, 5)]
for phase, size, pause, count in phases:
    for sample in range(count):
        connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
        payload = b"x" * size
        row = {"phase": phase, "sample": sample, "bytes": size,
               "pause_s": pause,
               "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start = time.perf_counter()
        try:
            connection.request("POST", "/echo", body=payload,
                               headers={"Content-Type": "application/octet-stream"})
            response = connection.getresponse()
            headers_at = time.perf_counter()
            time.sleep(pause)
            body = response.read()
            finished = time.perf_counter()
            if response.status != 200 or body != payload:
                raise ValueError("Unexpected status or echo content")
            row.update(status=response.status, ok=True,
                       headers_ms=(headers_at - start) * 1000,
                       read_ms=(finished - headers_at) * 1000,
                       total_ms=(finished - start) * 1000)
        except Exception as error:
            row.update(ok=False, error=type(error).__name__,
                       detail=str(error))
            print(json.dumps(row), flush=True)
            raise SystemExit(1)
        finally:
            connection.close()
        print(json.dumps(row), flush=True)
        time.sleep(0.25)
PY
```

클라이언트 종료 상태를 즉시 저장하세요. 중단되거나 성공 행이 16개보다 적으면 불완전한 실행입니다.
전체 timeout은 마지막 JSON 행 없이 만료될 수 있으며 자료 누락은 지연 0이 아닙니다.
`headers_ms`는 연결·요청부터 응답 헤더 해석까지 포함하므로 순수 RTT나 curl TTFB 지표가 아닙니다.
`read_ms`에는 의도한 대기와 본문 소비가 포함되며 일부 콘텐츠는 라이브러리가 이미 버퍼링했을 수 있습니다.
`total_ms`는 응답 소비까지 측정하며 뒤의 요청 간 대기는 제외합니다.

클라이언트와 관측자 종료 후 상태를 수집합니다.

```bash
ip -s link show dev lo > linux-evidence-01/link-after.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-after.txt
ss -tinm state established '( sport = :18080 or dport = :18080 )' \
  > linux-evidence-01/sockets-after.txt
```

**예상 관측:** 완료된 모든 요청이 동일한 echo 바이트를 반환하고 읽기 대기 단계의 완료 시간에는 설정한 대기가 포함되어야 합니다.
**부정 관측:** 연결이 짧아 `ss` 표본이 비어 있을 수 있으며 큐 0이 관측자 고장을 증명하지 않습니다.
작은 echo에서는 눈에 보이는 역압이나 재전송이 발생하지 않을 수 있습니다.
카운터 차이는 루프백 인터페이스 전체를 포함하므로 증가분 전부를 이 클라이언트에 귀속하지 않습니다.
echo 실패 시 해당 행과 서버 상태를 보존한 뒤 진단하며 성공 결과만 남을 때까지 몰래 재시도하지 않습니다.

선택 패킷 증거는 새 증거 디렉터리에서 [프로젝트 B의 제한된 캡처](01-protocol-projects.md#stream-project)를 사용합니다.
20초·120패킷 제한으로 일부 연결이 누락될 수 있습니다. 누락을 손실로 간주하지 말고 부분 수집으로 기록하세요.
캡처 모양을 익숙하게 만들려고 체크섬·세그먼트 오프로딩을 끄지 않습니다.

**복구:** 자신의 포그라운드 서버만 Ctrl+C로 종료하거나 180초 마감 만료를 기다립니다.
클라이언트·관측자는 자체 상한으로 끝나며 필요하면 해당 포그라운드 프로세스만 중단합니다.
`ss -ltn 'sport = :18080'`에 수신 대기가 없는지 확인합니다. TIME_WAIT 소켓은 정상적으로 남을 수 있습니다.
증거 디렉터리를 유지하거나 검토 후 정확히 지정한 자기 파일만 제거합니다.
이 실험은 qdisc, sysctl, NIC 오프로딩, 경로, BPF 연결을 변경하지 않았습니다.

## 윈도·손실·지연 해석 {#interpretation}

[소켓 큐 의미](../../kernel/02-network-stack.md#ss-tcp-queues)를 원본 `ss` 표본과 비교합니다.
ESTABLISHED `Recv-Q`는 애플리케이션이 아직 소비하지 않은 수신 데이터이고 `Send-Q`는 아직 보내지 않은 데이터를 포함한 미확인 데이터입니다.
LISTEN 열은 페이로드 점유량이 아니라 accept 큐·backlog를 다룹니다.
`skmem`에는 메모리와 부가 비용이 포함되므로 스트림 바이트, 광고 윈도, `cwnd`와 같을 필요가 없습니다.
표시되는 `cwnd`는 보통 세그먼트 단위이므로 바이트와 비교하기 전에 해당 MSS와 단위를 확인하세요.

100 Mbit/s, RTT 40 ms인 **가상 사례**를 계산하면 다음과 같습니다.
`BDP = 100,000,000 bit/s × 0.040 s ÷ 8 = 500,000 bytes`
이는 산술 예시이며 실측값이나 버퍼 설정 명령이 아닙니다.
[BDP와 소켓 정책](../../kernel/02-network-stack.md#tcp-bdp-reasoning)에 연결해 설명하세요.
작은 유효 윈도는 처리량을 제한할 수 있지만 전역 상한을 높이는 행동이 이번 지연 원인이 윈도였다는 증거는 아닙니다.

준비 요청을 제외하고 실제 행에서 단계별 표본 수, 실패, 최솟값·중앙값·최댓값을 보고합니다.
표본 5개로 신뢰할 만한 p99 서비스 목표나 운영 용량을 주장할 수 없습니다.
응답 페이로드 비트를 트랜잭션 초로 나누면 연결·처리 지연을 포함한 해당 작업의 애플리케이션 goodput입니다.
이 값은 Ethernet 선속도도 혼잡의 직접 측정값도 아닙니다.

| 관측 | 가능한 설명 | 대안을 구분할 증거 |
|---|---|---|
| 완료 시간은 높지만 헤더 시간은 평범함 | 클라이언트 소비 지연 | 클라이언트 단계·시각, 총시간만으로 경로를 탓하지 않음 |
| 지속적인 수신 큐 | 느린 읽기 또는 스케줄링 | 읽기 진행, CPU 증거와 반복된 흐름별 표본 |
| 지속적인 송신 큐 | 미송신 데이터, ACK 부재, 수신자 제한 | 윈도·재전송 필드와 양쪽 종단 증거 |
| 재전송 증가 | 손실, 순서 변경, 불필요한 재전송 | 시퀀스·시간 증거, 카운터 하나로 드롭 위치 특정 불가 |
| tcpdump 캡처 드롭 | 관측자가 따라가지 못함 | 캡처 통계, 곧바로 TCP·경로 손실로 해석하지 않음 |
| qdisc 드롭 증가 | 로컬 큐 정책·부담 | 같은 구간·인터페이스와 트래픽 귀속 |

## eBPF/XDP 관측과 실패 설계 {#bpf-observation}

[커널 BPF 문서](https://docs.kernel.org/bpf/)와 Bootlin의 훅 설명을 읽은 뒤 도구를 선택합니다.
이미 준비된 소유 실습 환경에서 권한이 있으면 `bpftool prog show`, `bpftool net show`로 기존 프로그램·연결을 조사할 수 있습니다.
선택적인 읽기 전용 관측입니다. 권한 부재는 “미관측”이지 “BPF 없음”이 아닙니다.
프로그램이 존재한다는 사실만으로 이 흐름이 실행했거나 처리량이 좋아졌다는 결론을 낼 수 없습니다.

프로그램을 적재하지 않고 tracepoint/kprobe 관측 하나를 설계합니다. 훅, 튜플·네임스페이스 필터, 필드, 시간, 이벤트 수 상한과 부하 확인 방법을 정하세요.
해당 커널의 이벤트 형식·BTF에서 필드 존재를 확인하고 모든 환경에서 통하는 프로브 시그니처를 만들지 않습니다.
이벤트 손실 집계와 클라이언트 표본에 시간을 대응하는 방법을 명시합니다.
tracepoint, TC 프로그램, native XDP는 다른 단계를 관측하므로 한 훅의 부재가 모든 위치의 부재는 아닙니다.
이 워크북에서는 BPF 프로그램을 연결·해제·교체하지 않습니다.

**선택 netem 확장은 여기서는 설계만 합니다.** 호스트 전역 qdisc·sysctl·오프로딩 명령을 실행하지 마세요.
영향받는 인터페이스 밖에 관리 경로를 둔 별도의 소유 네임스페이스·VM 제안을 작성합니다.
네임스페이스·VM 식별자, 인터페이스, 원래 qdisc 계층·handle·옵션, 경로, 오프로딩과 모든 변경 예정 사항을 기록하세요.
변수 하나, 정확히 제한된 흐름·시간, 기준선과 예상 부정 결과를 명시합니다.
실행 전 정확한 복구 계획이 필요합니다. 루트 qdisc 삭제만으로 임의의 원래 계층을 재현할 수는 없습니다.
새 폐기형 환경에서는 기록한 자원 ID만 제거하는 것을 복구 경계로 삼을 수 있습니다.
사전 상태를 재구성할 수 없거나 소유권이 불확실하면 계속 설계 단계에 둡니다.

## 완료와 전달 {#completion}

- [ ] Bootlin 공개 자료·하드웨어 경계를 설명하고 출처·도구·도우미 버전을 기록했다.
- [ ] 실험 카드, 원본 행, 실패·종료 상태, 관측 범위와 전후 카운터를 보존했다.
- [ ] 입력 지연과 측정 시간, 큐 바이트와 메모리, BDP와 설정 버퍼를 구분했다.
- [ ] 느린 결과의 가능한 설명을 최소 두 개 제시하고 각각을 기각할 증거를 밝혔다.
- [ ] 없는 NIC·BPF·패킷 관측을 표시하고 측정하지 않은 처리량 향상을 주장하지 않았다.
- [ ] 서버 종료와 영구 설정 변경 부재를 확인했다.
- [ ] [퀴즈](../../quizzes/networking/expert/04-linux-performance-quiz.md)를 해설과 함께 완료했다.

결과물을 [자동화 종합 실습](06-automation-capstone.md)에 전달합니다.
오버레이·MTU 맥락은 [데이터센터 EVPN](03-datacenter-evpn.md), 추가 경로 경계는 [클라우드·CNI 설계](05-cloud-cni-design.md)로 연결하세요.
[전문가 과정 지도](README.md)에서 다음 전문 경로를 선택합니다.
