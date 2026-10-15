# 커널 네트워킹 스택 퀴즈

이 퀴즈는 소켓/VFS 진입 경로, TCP 버퍼·윈도, 상태별 큐 관측값, 훅 지점, Pod 간 통신 경로에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 송신 packet을 NIC 앞에서 queue에 넣고 `tc -s qdisc`로 자신의 drop을 보여주는 구성요소는?
   - A) NIC의 물리 계층
   - B) qdisc — 노드 안에서 일어나는 드롭이며 `tc -s qdisc`의 `dropped`로 확인
   - C) VPC 네트워크
   - D) 애플리케이션의 소켓 버퍼

<details>

<summary>정답 보기</summary>

**정답: B) qdisc — 노드 안에서 일어나는 드롭이며 `tc -s qdisc`의 `dropped`로 확인**

**설명:**
qdisc는 송신 패킷을 큐에 넣고 스케줄링하며 큐 한도 또는 능동적 큐 관리에 따라 드롭할 수 있습니다. 증가하는 `dropped` 카운터는 해당 qdisc의 드롭을 나타내며 경로의 모든 손실을 뜻하지는 않습니다. 해당 시간대·트래픽을 인터페이스·드라이버·스택·원격 증거와 대조합니다. `overlimits`는 드롭 없는 셰이핑을 나타낼 수 있으므로 `dropped`와 같은 뜻이 아닙니다.
</details>

2. 조기 packet drop 성능을 설명할 때 어떤 XDP mode 구분이 중요합니까?
   - A) 커널 모듈이 아니라 하드웨어에서 실행되기 때문
   - B) Native/driver XDP는 skb 할당 전에 실행되지만 generic XDP에는 이미 skb가 있다
   - C) JIT 컴파일되기 때문
   - D) conntrack을 조회하지 않아도 되기 때문

<details>

<summary>정답 보기</summary>

**정답: B) Native/driver XDP는 skb 할당 전에 실행되지만 generic XDP에는 이미 skb가 있다**

**설명:**
조기 drop 장점은 mode별 설명입니다. BPF map은 상태를 유지할 수 있으며 성능은 보편적 최속 경로 보장이 아니라 kernel·program·driver·hardware에 달려 있습니다.
</details>

3. 수신 트래픽이 많은데 CPU 하나만 100%이고 나머지는 놉니다. 조사할 만한 원인 후보와 관련 기능은?
   - A) qdisc 큐 부족 — 큐 길이를 늘린다
   - B) 수신 처리가 집중됨 — RSS 큐·IRQ 분산, RPS 소프트웨어 분산, RFS 캐시 지역성을 확인
   - C) 소켓 버퍼 부족 — `tcp_rmem`을 늘린다
   - D) TCP 혼잡 제어 알고리즘 문제 — bbr로 전환

<details>

<summary>정답 보기</summary>

**정답: B) 수신 처리가 집중됨 — RSS 큐·IRQ 분산, RPS 소프트웨어 분산, RFS 캐시 지역성을 확인**

**설명:**
RSS는 플로우를 해시로 수신 큐에 배정하고, IRQ affinity는 어떤 CPU가 처리할지에 영향을 줍니다. RPS는 이후 수신 처리를 소프트웨어로 분산하며 RFS는 소비하는 애플리케이션 가까이 배치하려 합니다. 모두 하드웨어 인터럽트를 이동하는 것은 아니며 단일 플로우는 한 큐에 남을 수 있습니다. 원인을 정하기 전에 `/proc/interrupts`, `mpstat -P ALL`의 코어별 `%soft`, 애플리케이션 CPU 사용을 함께 확인합니다.
</details>

4. 일반적인 인터럽트 기반 NAPI는 어떻게 패킷당 오버헤드를 줄일 수 있습니까?
   - A) 커널이 자동으로 CPU 주파수를 올리기 때문
   - B) 드라이버가 해당 큐 인터럽트를 마스킹하고 작업량이 제한된 폴링을 예약해 배치에 비용을 분산
   - C) 패킷을 압축해서 처리하기 때문
   - D) GRO가 자동으로 활성화되기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 드라이버가 해당 큐 인터럽트를 마스킹하고 작업량이 제한된 폴링을 예약해 배치에 비용을 분산**

**설명:**
배치는 인터럽트·처리 오버헤드를 분산할 수 있습니다. 드라이버는 폴링이 예약된 동안 해당 인터럽트를 마스킹하고 완료 시 다시 활성화할 수 있으며, 모든 CPU 인터럽트를 끄지는 않습니다. 폴링에는 작업량 한도가 있고 과부하는 여전히 지연이나 드롭을 늘릴 수 있습니다. Busy polling과 threaded NAPI는 다른 실행 방식입니다.
</details>

5. 같은 노드의 Pod 간 통신에서 단일 플로우가 29.97 Gbps까지 나오고 병목이 CPU였던 이유는?
   - A) 노드 내부에 전용 고속 네트워크가 있기 때문
   - B) 그림의 일반 veth/routed 동일 노드 경로는 물리 NIC를 거치지 않고 kernel 메모리에 머물 수 있다
   - C) 커널이 패킷을 압축하기 때문
   - D) 같은 노드 통신은 TCP를 쓰지 않기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 그림의 일반 veth/routed 동일 노드 경로는 물리 NIC를 거치지 않고 kernel 메모리에 머물 수 있다**

**설명:**
가상 장치에도 driver 처리가 있습니다. CNI·SR-IOV·overlay·service/policy 우회에 따라 경로가 바뀔 수 있으므로 실제 설정에 맞춰 판단합니다.
</details>

6. 작은 핸드셰이크 패킷은 통과하지만 DF가 설정된 큰 IPv4 패킷이 낮은 MTU의 홉에서 드롭되고 반환 ICMP도 차단됩니다. 정체를 설명하는 메커니즘은?
   - A) conntrack 포화
   - B) PMTUD 실패 — 경로 MTU를 알려주는 ICMP가 차단되어 큰 패킷만 드롭됨
   - C) TCP 혼잡 제어 알고리즘 불일치
   - D) 소켓 수신 버퍼 부족

<details>

<summary>정답 보기</summary>

**정답: B) PMTUD 실패 — 경로 MTU를 알려주는 ICMP가 차단되어 큰 패킷만 드롭됨**

**설명:**
DF가 설정되면 IPv4 라우터는 큰 패킷을 단편화할 수 없으며 일반적으로 ICMP "fragmentation needed"를 반환합니다. 이 피드백을 차단하면 PMTUD가 실패해 블랙홀이 생길 수 있습니다. IPv6 라우터는 단편화하지 않으며 ICMPv6 "Packet Too Big"을 사용합니다. 문제에 제시한 증거가 없다면 핸드셰이크 후 정체는 단서일 뿐 확정 증거가 아니고, 탐색으로 복구할 수도 있습니다.
</details>

7. 네트워크 문제 진단 시 권장되는 순서는?
   - A) 위에서 아래로 — 애플리케이션부터 NIC까지 순서대로
   - B) 드롭 카운터부터 — `conntrack -S`의 `insert_failed`, `tc -s qdisc`의 `dropped`, `ethtool -S`의 NIC 드롭을 먼저 확인
   - C) 항상 `tcpdump`로 패킷을 먼저 캡처
   - D) CPU 사용률부터 확인

<details>

<summary>정답 보기</summary>

**정답: B) 드롭 카운터부터 — `conntrack -S`의 `insert_failed`, `tc -s qdisc`의 `dropped`, `ethtool -S`의 NIC 드롭을 먼저 확인**

**설명:**
이 counter는 조사할 후보를 가리킬 뿐 진단을 완성하지는 않습니다. 영향을 받은 flow·시간대와 변화를 연결하고, conntrack은 `insert_failed`가 포화에만 발생하는 값이 아니므로 count/max·kernel log도 확인합니다. 집계 counter에는 무관한 트래픽이 포함될 수 있습니다. 로컬 counter가 그대로여도 원격 drop·인증·애플리케이션 실패를 배제할 수 없습니다. 증상에 따라 `ss -tin`의 RTT·cwnd, 반환 오류와 나머지 경로의 증거를 확인합니다.
</details>

8. 워크로드 벤치마크 없이도 타당한 `cubic`과 `bbr`의 비교는?
   - A) cubic은 UDP용, bbr은 TCP용이다
   - B) cubic은 손실·ECN 등의 이벤트에 따라 혼잡 윈도를 조정하고 bbr은 전달률·RTT 추정을 쓰며, 결과는 구현과 경로에 따라 다름
   - C) bbr은 항상 cubic보다 빠르다
   - D) cubic은 커널 6.x에서 제거되었다

<details>

<summary>정답 보기</summary>

**정답: B) cubic은 손실·ECN 등의 이벤트에 따라 혼잡 윈도를 조정하고 bbr은 전달률·RTT 추정을 쓰며, 결과는 구현과 경로에 따라 다름**

**설명:**
모델은 제어 동작의 차이를 설명하며 성능 순위를 보장하지 않습니다. BBR에도 손실·복구 동작이 있고 어느 알고리즘도 수신 윈도나 애플리케이션 한도를 없애지 않습니다. 비교를 해석하기 전에 커널 구현·사용 중인 알고리즘·RTT/cwnd·워크로드·경로를 확인합니다.
</details>

9. 한 프로세스가 TCP 소켓에서 `write(fd, ...)`와 `send(fd, ...)`를 모두 사용합니다. Linux 소켓/VFS 연결을 올바르게 설명한 것은?
   - A) 두 호출 모두 TCP에 진입하기 전에 디스크 파일시스템을 거쳐야 함
   - B) `send()`는 항상 `vfs_write()`를 호출하며 소켓은 디스크 파일임
   - C) FD는 소켓과 연결된 `struct file`을 참조하고, `write()`는 VFS 소켓 파일 연산을, `send()`는 소켓 전용 진입 경로를 사용
   - D) 소켓에는 파일 디스크립터 테이블 항목이 없음

<details>

<summary>정답 보기</summary>

**정답: C) FD는 소켓과 연결된 `struct file`을 참조하고, `write()`는 VFS 소켓 파일 연산을, `send()`는 소켓 전용 진입 경로를 사용**

**설명:**
버전을 고정한 Linux 예시에서 `file->private_data`는 `struct socket`을 가리킵니다. VFS의 `write()`는 `socket_file_ops.write_iter`를 통해 `sock_write_iter`로 전달되고, `send()`는 자체 시스템 콜 경로에서 FD로 소켓을 찾습니다. 두 경로 모두 소켓·프로토콜 연산으로 이어집니다. 파일 추상화를 공유한다고 디스크 I/O를 수행하는 것은 아니며, 송신 성공도 상대 애플리케이션의 소비를 입증하지 않습니다. [VFS 연결](../../kernel/02-network-stack.md#socket-vfs-bridge)을 복습합니다.
</details>

10. 연결된 TCP 소켓에 읽지 않은 페이로드가 있고 `ss -m`의 수신 메모리가 `Recv-Q`보다 큽니다. 타당한 설명은?
   - A) 메모리 회계에는 할당 오버헤드와 순서가 어긋난 데이터가 포함될 수 있고, `Recv-Q`는 순서대로 수신했지만 읽지 않은 스트림 바이트를 셈
   - B) 각 `sk_buff`가 소켓 수신 버퍼 전체임
   - C) 수신 메모리·`Recv-Q`·`rwnd`·`cwnd`는 항상 같음
   - D) 모든 skb는 전선상의 패킷 하나와 정확히 대응해야 함

<details>

<summary>정답 보기</summary>

**정답: A) 메모리 회계에는 할당 오버헤드와 순서가 어긋난 데이터가 포함될 수 있고, `Recv-Q`는 순서대로 수신했지만 읽지 않은 스트림 바이트를 셈**

**설명:**
skb는 패킷 데이터와 메타데이터를 기술하며 조각을 참조하거나 복제되거나 병합·분할할 데이터를 나타낼 수 있습니다. 소켓 메모리 한도·애플리케이션 페이로드·수신 측 광고 윈도·송신 측 혼잡 윈도는 서로 다른 한도나 양입니다. `ss -m`의 메모리 값을 `rwnd` 대신 사용할 수 없으며 로컬 버퍼 증가가 `cwnd`를 직접 늘리지도 않습니다. [큐 관측](../../kernel/02-network-stack.md#ss-tcp-queues)을 복습합니다.
</details>

11. `ss`가 `LISTEN`에 `Recv-Q=3, Send-Q=128`, `ESTABLISHED`에 `Recv-Q=4096, Send-Q=8192`를 표시합니다. 의미는?
   - A) 두 행 모두 현재 NIC 링의 패킷 수를 나타냄
   - B) 리스너가 3바이트를 수신하고 128바이트를 송신함
   - C) 리스너에 미완료 SYN이 3개 있고 연결된 소켓의 8192바이트 모두 전선상에 있음이 확인됨
   - D) 리스너에는 accept 대기 연결 3개와 최대 backlog 128이 있고, 연결된 소켓에는 순서대로 수신했지만 읽지 않은 4096바이트와 썼지만 아직 누적 ACK를 받지 않은 8192바이트가 있음

<details>

<summary>정답 보기</summary>

**정답: D) 리스너에는 accept 대기 연결 3개와 최대 backlog 128이 있고, 연결된 소켓에는 순서대로 수신했지만 읽지 않은 4096바이트와 썼지만 아직 누적 ACK를 받지 않은 8192바이트가 있음**

**설명:**
리스너에서는 연결 수를 세며 SYN 큐 점유량을 보여주지 않습니다. 연결된 TCP에서는 스트림 바이트를 세며 `Send-Q`는 아직 송신하지 않은 바이트와 송신 후 미확인 바이트를 모두 포함할 수 있습니다. 설정된 소켓 메모리 한도도 패킷 손실의 증거도 아닙니다. [상태별 TCP 큐](../../kernel/02-network-stack.md#ss-tcp-queues)를 복습합니다.
</details>

12. 애플리케이션이 `SO_RCVBUF`와 `SO_SNDBUF`를 명시적으로 설정했습니다. 이후 운영자가 `tcp_rmem[2]`와 `tcp_wmem[2]`만 높였습니다. 올바른 예상은?
   - A) 기존 모든 소켓이 두 새 최대값만큼 즉시 메모리를 할당
   - B) 소켓의 명시적 설정은 각각의 방향에서 일반적인 자동 조정에 대해 계속 잠겨 있음
   - C) Linux가 `tcp_rmem[2]`를 두 배로 만들어 바로 `rwnd`로 광고
   - D) 송신 버퍼 정책을 바꾸면 상대 수신 윈도가 직접 커짐

<details>

<summary>정답 보기</summary>

**정답: B) 소켓의 명시적 설정은 각각의 방향에서 일반적인 자동 조정에 대해 계속 잠겨 있음**

**설명:**
소켓 옵션은 뮤텍스가 아닌 정책 플래그인 `SOCK_RCVBUF_LOCK`과 `SOCK_SNDBUF_LOCK`을 설정합니다. 일반 옵션 요청에는 `net.core.rmem_max`/`wmem_max`가 적용됩니다. Linux는 보통 받아들인 요청을 회계 목적으로 두 배로 만들어 `getsockopt()`로 보고하지만, 그 메모리가 모두 할당되거나 페이로드로 사용 가능하다는 뜻은 아닙니다. sysctl 자동 조정 상한과 명시적 옵션 한도는 다른 제어입니다. [TCP 버퍼 정책](../../kernel/02-network-stack.md#tcp-buffer-policy)을 복습합니다.
</details>

13. 가상의 경로가 1 Gbit/s와 RTT 40 ms를 제공합니다. 타당한 BDP 계산과 결론은?
   - A) 40 MB이며 모든 소켓의 송신 버퍼를 이 값으로 정확히 설정
   - B) 5바이트이며 밀리초 지연을 초당 비트 수에 그대로 곱하면 됨
   - C) 5,000,000바이트(약 4.77 MiB)이며 바이트 단위로 환산한 윈도·애플리케이션 진행·메모리 오버헤드와 규모를 비교
   - D) 5 MB이므로 모든 호스트에서 버퍼 병목이 입증됨

<details>

<summary>정답 보기</summary>

**정답: C) 5,000,000바이트(약 4.77 MiB)이며 바이트 단위로 환산한 윈도·애플리케이션 진행·메모리 오버헤드와 규모를 비교**

**설명:**
`1,000,000,000 bit/s × 0.040 s ÷ 8 bit/byte = 5,000,000 bytes`입니다. RTT를 사용하며 이상적인 정상 상태의 전송 중 페이로드를 추정합니다. `ss`의 `cwnd`는 보통 세그먼트 단위이므로 바이트 비교에는 MSS를 사용합니다. 수신 윈도 제약·페이싱·손실·CPU·애플리케이션 동작도 여전히 중요하며 BDP는 보편적인 튜닝 지침이 아닙니다. [BDP 설명](../../kernel/02-network-stack.md#tcp-bdp-reasoning)과 [TCP 버퍼 실습](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab)을 참고합니다.
</details>

14. 인터페이스 IP MTU는 1500인데 호스트 캡처에 1500바이트보다 큰 TCP 단위와 잘못된 것처럼 보이는 송신 체크섬이 나타납니다. 먼저 내릴 판단은?
   - A) 캡처 지점과 오프로드를 확인. 옵션 없는 IPv4 TCP 페이로드 한도는 1460바이트지만 호스트 GSO/GRO 단위와 미완성 체크섬은 전선상의 패킷과 다를 수 있음
   - B) TCP MSS는 IP 헤더를 포함하므로 반드시 1500바이트임
   - C) 원격 IPv6 라우터가 반드시 패킷을 단편화했음
   - D) 캡처가 전선상의 손상을 입증하며 PMTUD는 무효임

<details>

<summary>정답 보기</summary>

**정답: A) 캡처 지점과 오프로드를 확인. 옵션 없는 IPv4 TCP 페이로드 한도는 1460바이트지만 호스트 GSO/GRO 단위와 미완성 체크섬은 전선상의 패킷과 다를 수 있음**

**설명:**
MSS는 IP/TCP 헤더를 제외하며 PMTU는 전체 경로에 달려 있습니다. 옵션 없는 IPv4는 `1500 - 20 - 20 = 1460`이고 IPv6 기본 헤더를 사용하면 1440바이트가 남습니다. 오프로드는 분할·체크섬 완성을 미루거나 수신 패킷을 병합할 수 있습니다. 호스트 캡처만으로 전선상의 패킷 크기나 손상을 확정할 수는 없습니다. [MTU/MSS 실습](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab)으로 이어집니다.
</details>
