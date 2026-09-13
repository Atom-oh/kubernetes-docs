# 커널 네트워킹 스택 퀴즈

이 퀴즈는 패킷 경로, 훅 지점, Pod 간 통신 경로에 대한 이해도를 테스트합니다.

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
qdisc는 패킷을 NIC로 보내기 전 큐에 넣고 순서와 속도를 정합니다. 큐가 가득 차면 패킷을 버리는데, 이것은 NIC나 네트워크의 문제가 아니라 **노드 안에서 일어나는 드롭**입니다. 그래서 "네트워크가 패킷을 잃었다"고 생각하고 밖을 찾다가 시간을 버리기 쉽습니다. `tc -s qdisc show dev <iface>`의 `dropped` 카운터가 증거이고, `ip -s link`의 송신 드롭도 함께 봅니다.
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

3. 수신 트래픽이 많은데 CPU 하나만 100%이고 나머지는 노는 현상의 원인과 해결 계층은?
   - A) qdisc 큐 부족 — 큐 길이를 늘린다
   - B) 수신 인터럽트가 특정 CPU에 몰림 — RSS(하드웨어), RPS(소프트웨어), RFS(캐시 지역성)로 분산
   - C) 소켓 버퍼 부족 — `tcp_rmem`을 늘린다
   - D) TCP 혼잡 제어 알고리즘 문제 — bbr로 전환

<details>

<summary>정답 보기</summary>

**정답: B) 수신 인터럽트가 특정 CPU에 몰림 — RSS(하드웨어), RPS(소프트웨어), RFS(캐시 지역성)로 분산**

**설명:**
수신 인터럽트는 특정 CPU에 전달되므로, 큐가 하나거나 분산이 설정되지 않으면 그 코어만 100%가 되고 전체 CPU 사용률 그래프는 낮게 보이는데 처리량이 막힙니다. 해결 계층이 세 개입니다 — RSS는 NIC가 해시로 여러 수신 큐에 분산하고, RPS는 커널이 수신 처리를 다른 CPU로 넘기며, RFS는 해당 소켓을 실제로 읽는 프로세스가 있는 CPU로 보내 캐시 지역성을 높입니다. 진단은 `/proc/interrupts`의 분포와 `mpstat -P ALL`의 `%soft`로 합니다.
</details>

4. NAPI가 고부하에서 오히려 효율이 좋아지는 이유는?
   - A) 커널이 자동으로 CPU 주파수를 올리기 때문
   - B) 첫 인터럽트 후 인터럽트를 끄고 폴링으로 전환해 배치로 수거하므로, 배치가 커지면 패킷당 오버헤드가 내려감
   - C) 패킷을 압축해서 처리하기 때문
   - D) GRO가 자동으로 활성화되기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 첫 인터럽트 후 인터럽트를 끄고 폴링으로 전환해 배치로 수거하므로, 배치가 커지면 패킷당 오버헤드가 내려감**

**설명:**
패킷마다 인터럽트를 걸면 고부하에서 인터럽트 처리만 하다 아무 일도 못 하는 상태(livelock)가 됩니다. NAPI는 첫 인터럽트가 오면 인터럽트를 끄고 폴링으로 전환해 큐에 쌓인 패킷을 한 번에 여러 개 수거하고, 큐가 비면 다시 인터럽트를 켭니다. 부하가 높을 때 자동으로 폴링 모드가 되는 구조이며, 배치가 커지면 패킷당 오버헤드가 내려가므로 효율이 개선됩니다.
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

6. "핸드셰이크는 되는데 데이터 전송에서 멈춘다"는 증상의 전형적 원인은?
   - A) conntrack 포화
   - B) PMTUD 실패 — 경로 MTU를 알려주는 ICMP가 차단되어 큰 패킷만 드롭됨
   - C) TCP 혼잡 제어 알고리즘 불일치
   - D) 소켓 수신 버퍼 부족

<details>

<summary>정답 보기</summary>

**정답: B) PMTUD 실패 — 경로 MTU를 알려주는 ICMP가 차단되어 큰 패킷만 드롭됨**

**설명:**
패킷이 경로 최소 MTU보다 크면 단편화되거나 드롭됩니다. PMTUD(Path MTU Discovery)는 ICMP로 경로 MTU를 알려주는데, 그 ICMP가 차단되면 송신 측은 계속 큰 패킷을 보내고 중간에서 드롭되면서 연결이 멈춘 것처럼 보입니다. 증상이 특징적인 이유는 **작은 패킷(핸드셰이크)은 통과하고 큰 패킷만 드롭**되기 때문입니다. 점보 프레임을 쓰거나 경로에 MTU가 섞인 환경에서 주의해야 합니다.
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

8. `cubic`과 `bbr`의 차이와 bbr이 유리한 환경은?
   - A) cubic은 UDP용, bbr은 TCP용이다
   - B) cubic은 패킷 손실을 혼잡 신호로 쓰고 bbr은 대역폭·RTT 추정을 쓴다. 손실이 혼잡과 무관하게 생기는 환경이나 긴 지연 경로에서 bbr이 유리
   - C) bbr은 항상 cubic보다 빠르다
   - D) cubic은 커널 6.x에서 제거되었다

<details>

<summary>정답 보기</summary>

**정답: B) cubic은 패킷 손실을 혼잡 신호로 쓰고 bbr은 대역폭·RTT 추정을 쓴다. 손실이 혼잡과 무관하게 생기는 환경이나 긴 지연 경로에서 bbr이 유리**

**설명:**
cubic의 전제는 "손실 = 혼잡"입니다. 유선 환경에서는 합리적이지만, 손실이 다른 이유로 나는 경로(무선, 버퍼가 얕은 경로)에서는 cubic이 불필요하게 물러섭니다. bbr은 손실 대신 실측 대역폭과 최소 RTT로 판단해 이 문제를 피합니다. VPC 내부 통신은 손실이 드문 품질 좋은 경로라 cubic으로도 대개 충분하고, **리전 간이나 인터넷 경유처럼 지연이 길고 손실이 섞이는 경로에서 bbr의 이점**이 나타납니다.
</details>
