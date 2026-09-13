# EKS 노드 커널 튜닝

> **지원 버전**: Amazon Linux 2023 (커널 6.1 / 6.12 / 6.18), Kubernetes 1.33+ (Amazon EKS)
> **마지막 업데이트**: 2026년 9월 13일

## 이 문서에서 다루는 것

- EKS 노드에서 무엇을 건드려야 하고 무엇을 기본값으로 두어야 하는가 — 그리고 그 판단 기준
- 커널 파라미터를 EKS에서 실제로 적용하는 경로들과 각각의 함정
- AL2023의 커널 버전 전환(6.1 → 6.18)이 운영에 의미하는 것

## 먼저: 대부분은 건드리지 마십시오

이 문서의 가장 중요한 조언입니다.

커널 기본값은 **광범위한 워크로드에서 합리적으로 동작하도록** 정해져 있고, 상당수는 부하에 따라 커널이 자동 조정합니다(예: TCP 버퍼 자동 튜닝). 근거 없는 튜닝은 세 가지 방식으로 손해를 냅니다.

| 문제 | 예 |
|---|---|
| **재현 불가능한 구성** | 노드마다 값이 달라 장애 재현이 안 됨 |
| **커널 업그레이드 시 깨짐** | 6.1에서 유효했던 튜너블이 6.18에서 이름·위치가 바뀌거나 사라짐 |
| **자동 조정을 망가뜨림** | TCP 버퍼를 고정하면 커널의 자동 튜닝이 비활성화됨 |

**튜닝의 전제 조건은 측정입니다.** 아래 순서를 지키십시오.

1. 증상을 특정한다 (지연? 드롭? 처리량?)
2. **드롭 카운터를 먼저 본다** — `conntrack -S`의 `insert_failed`, `tc -s qdisc`의 `dropped`, `ethtool -S`의 NIC 드롭
3. 그 카운터가 증가하는 지점의 파라미터만 건드린다
4. 변경 전후를 같은 조건으로 측정한다
5. 변경 사유와 근거를 코드로 남긴다 (아래 적용 경로)

측정 방법은 [Pod 네트워크 실측 벤치마크](../networking/06-pod-network-benchmark.md)의 픽스처를 참고하실 수 있습니다.

## 적용 경로 — EKS에서 커널 파라미터를 바꾸는 방법

바꾸는 방법이 여러 개이고 **각각 범위와 함정이 다릅니다.** 이것을 먼저 정리하는 것이 실무에서 더 중요합니다.

| 경로 | 범위 | 지속성 | 비고 |
|---|---|---|---|
| **노드 부트스트랩 스크립트** (User Data / `nodeadm`) | 노드 전체 | 노드 교체 시 재적용됨 | AL2023은 `nodeadm` 구성 사용. 가장 표준적 |
| **Bottlerocket 설정** (`settings.kernel.sysctl`) | 노드 전체 | 노드 설정으로 관리 | Bottlerocket은 불변 OS라 이 경로만 사용 |
| **Pod `securityContext.sysctls`** | **Pod의 net namespace만** | Pod 스펙 | **namespace 지원 sysctl만** 가능. `net.*` 다수가 해당 |
| **privileged 초기화 DaemonSet** | 노드 전체 | Pod 재시작 시 재적용 | 흔히 쓰이지만 privileged 필요 — 보안 심의 대상 |
| **`kube-proxy-config` ConfigMap** | conntrack 관련 | kube-proxy가 관리 | **EKS에서 이것이 CLI 인자보다 우선** |
| **Karpenter `EC2NodeClass`** | 노드 그룹 | 노드 프로비저닝 시 | User Data를 선언적으로 관리 |

### 놓치기 쉬운 두 가지

**첫째, namespace 지원 sysctl과 그렇지 않은 것의 구분입니다.** `net.*` 중 상당수는 net namespace별로 설정 가능해서 Pod `securityContext.sysctls`로 바꿀 수 있습니다. 반면 `vm.*`, `fs.*`, 그리고 **`net.netfilter.nf_conntrack_max` 같은 일부 값은 노드 전역**이라 Pod 스펙으로는 바꿀 수 없습니다.

또한 kubelet은 기본적으로 "안전하지 않은" sysctl을 거부합니다. 필요하면 `--allowed-unsafe-sysctls`로 명시적으로 허용해야 하고, 이것은 노드 설정입니다.

**둘째, conntrack은 kube-proxy가 덮어씁니다.** [컨테이너 커널 기능](./01-container-primitives.md)에서 언급한 내용인데, 실무에서 가장 자주 걸리는 함정이라 다시 씁니다 — EKS에는 `kube-proxy-config` ConfigMap이 기본 존재하고 **커맨드라인 인자보다 우선**합니다. 부트스트랩에서 sysctl로 올려놔도 kube-proxy가 자기 값으로 되돌릴 수 있습니다.

::: warning 확인 필요
Bottlerocket에서 `settings.kernel.sysctl`로 conntrack 상한을 올려도 적용되지 않는 이슈가 있습니다([bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221), 2024년 9월 등록). 원인은 **kube-proxy 설정 파일(`/var/lib/kube-proxy-config/config`)이 커맨드라인 인자보다 우선**하기 때문입니다.

알려진 우회책은 kube-proxy 인자에 **`--conntrack-max-per-core=0 --conntrack-min=0`**을 주는 것입니다 — 여기서 **0은 "변경하지 않음"**을 뜻하므로, kube-proxy가 conntrack을 건드리지 않고 노드 sysctl로 설정한 값이 살아남습니다.

**이 이슈가 특정 Bottlerocket 릴리스에서 해결되었는지는 확인하지 못했습니다.** 어느 경로로 설정하든 적용 후 노드에서 실제 값을 직접 확인하십시오.

```bash
# 노드에서 실제 적용값 확인
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count
conntrack -S | head
```
:::

## 커널 버전 — AL2023의 6.1 → 6.18 전환

운영상 지금 알아야 할 변화입니다.

| 시점 | 내용 |
|---|---|
| 2023년 3월 | AL2023 출시, 커널 **6.1** |
| 2025년 4월 | 커널 **6.12** 지원 추가 |
| **2026년 8월 17일** | **`al2023-ami-kernel-default` AMI의 기본 커널이 6.1 → 6.18로 변경** |

**함의가 두 갈래입니다.**

`al2023-ami-kernel-default-*` AMI를 쓰고 있다면, 그 날짜 이후 **새로 띄우는 노드는 커널 6.18**입니다. 노드 교체(오토스케일링, 업그레이드, 스팟 회수)만으로도 커널이 바뀝니다.

특정 커널에 고정해야 하면 **버전 지정 AMI**(`al2023-ami-kernel-6.1-*` 등)를 명시적으로 쓰십시오.

**커널이 바뀔 때 점검할 것들:**

| 항목 | 이유 |
|---|---|
| 튜너블의 존재와 위치 | 커널 버전 간에 이름이 바뀌거나 sysctl → debugfs로 이동한 것이 있음 |
| 커널 모듈 의존 컴포넌트 | eBPF 프로그램, 특정 CNI 기능, GPU 드라이버, 커스텀 모듈 |
| 스케줄러 거동 | 6.6+ EEVDF (아래 참고) — 지연 민감 워크로드에서 체감될 수 있음 |
| 성능 회귀 | 벤치마크를 커널 버전별로 다시 측정 |

**권고**: 커널 전환은 Kubernetes 버전 업그레이드와 **같은 무게로 다루십시오.** 스테이징에서 같은 커널로 먼저 검증하고, 성능 기준선을 다시 측정한 뒤 프로덕션에 적용하는 것이 안전합니다.

## CPU — 스케줄러와 throttling

### EEVDF — 6.6에서 바뀐 것

Linux 6.6에서 CFS의 태스크 선택 로직이 **EEVDF**(Earliest Eligible Virtual Deadline First)로 교체되었습니다.

정확히 이해할 가치가 있는 지점은 **무엇이 바뀌고 무엇이 안 바뀌었는가**입니다.

| 바뀐 것 | 안 바뀐 것 |
|---|---|
| 다음에 실행할 태스크를 **고르는 방식** (가상 데드라인 기반) | vruntime машинery, weight 계산 |
| 깨어난 태스크의 선점 판단 — 휴리스틱(`sched_wakeup_granularity_ns`) 대신 **데드라인 비교** | 그룹 스케줄링(cgroup cpu.weight), 로드 밸런싱 |

즉 **CFS를 통째로 갈아낸 것이 아니라 선택 로직을 교체한 진화**로 보는 것이 정확합니다. `fair_sched_class` 안에서의 변경입니다.

운영 관점의 의미: **지연 민감 워크로드의 깨우기 지연 특성이 달라질 수 있습니다.** 대개 개선 방향이지만, 커널 6.1에서 6.18로 넘어갈 때 p99가 바뀌면 이 변화가 후보 중 하나입니다.

### 튜너블의 실제 위치

커널 소스(`kernel/sched/debug.c`)에서 확인한 결과입니다.

| 항목 | 상태 |
|---|---|
| `sched_latency_ns` | **제거됨** — `kernel/sched/fair.c`에 참조가 남아 있지 않음 |
| `sched_wakeup_granularity_ns` | **제거됨** — 동일 |
| **`/sys/kernel/debug/sched/base_slice_ns`** | **현재의 대응 튜너블.** 내부 변수는 `sysctl_sched_base_slice`이고 debugfs에 `base_slice_ns`로 노출됨 |

즉 CFS 시절의 지연·선점 휴리스틱 튜너블은 사라지고, **기본 타임슬라이스 하나(`base_slice_ns`)**로 정리되었습니다. 이름에 `sched_` 접두어가 없다는 점에 주의하십시오 — 경로는 `/sys/kernel/debug/sched/base_slice_ns`입니다.

EEVDF는 이와 별개로 `sched_setattr()` 시스템 콜로 **태스크가 자기 타임슬라이스를 직접 요청**할 수 있게 했습니다. 지연 민감 애플리케이션에는 전역 튜너블을 건드리는 것보다 이 경로가 맞습니다.

**그래도 스케줄러 튜너블은 권장 튜닝 대상이 아닙니다.** debugfs는 커널 디버그 인터페이스라 프로덕션에서 마운트되지 않을 수 있고, 대부분의 경우 애플리케이션의 스레드 수 조정이나 cgroup limit 조정이 더 나은 답입니다.

### CPU limit — throttling이 진짜 문제인 경우

[컨테이너 커널 기능](./01-container-primitives.md)에서 다룬 대로, CPU limit은 대역폭 제한이라 사용률이 낮아도 지연을 만듭니다.

**진단:**

```bash
# cgroup v2 — 컨테이너의 cgroup 경로에서
cat cpu.stat
# nr_periods, nr_throttled, throttled_usec
```

`nr_throttled / nr_periods` 비율이 유의미하게 높으면 limit이 원인입니다.

**대응의 우선순위** (자세한 설계는 [리소스 최적화](../ops/10-resource-optimization.md)):

1. **애플리케이션이 인식하는 CPU 수를 limit에 맞춥니다.** 가장 자주 놓치는 근본 원인입니다 — 컨테이너 안의 런타임이 노드의 전체 코어 수를 보고 그만큼 스레드를 만들면, 할당량을 순식간에 소진합니다. JVM `-XX:ActiveProcessorCount`, Go `GOMAXPROCS`, Node.js `UV_THREADPOOL_SIZE` 등을 limit에 맞춰 설정합니다
2. **limit을 올립니다** — 노드 안정성과의 트레이드오프
3. **지연에 극히 민감하면 limit 제거를 검토합니다** — 단 노이지 네이버 위험을 request와 노드 분리로 관리해야 합니다
4. `cpu.pressure` PSI로 실제 대기 시간을 확인합니다

**CPU Manager의 정적 정책**(전용 코어 할당)은 지연 민감 워크로드에 유효한 별개 수단입니다. 다만 노드 리소스 활용률이 내려가므로 근거가 필요합니다.

## 메모리 — OOM과 압박

### 무엇을 조정하고 무엇을 두는가

| 파라미터 | 권고 |
|---|---|
| `vm.swappiness` | Kubernetes는 전통적으로 swap 비활성을 전제. swap 지원이 성숙해 왔으나 **EKS에서 켜기 전에 지원 상태를 확인**해야 함 |
| `vm.overcommit_memory` | **기본값 유지 권장.** 바꾸면 컨테이너 할당 실패 양상이 예측하기 어려워짐 |
| `vm.min_free_kbytes` | 회수 여유 공간. 너무 낮으면 급격한 할당에서 OOM. **노드 메모리가 크고 버스트가 심할 때만** 검토 |
| `vm.max_map_count` | **Elasticsearch/OpenSearch 등에서 실제로 필요한 조정.** 기본값이 낮아 mmap 한도에 걸림 |
| `kernel.pid_max` | 고밀도 노드에서 PID 고갈 시 |

`vm.max_map_count`가 실제 사례로 자주 등장합니다 — OpenSearch 계열은 많은 파일을 mmap하므로 기본값에서 시작 실패합니다. 이것은 "근거 있는 튜닝"의 좋은 예입니다: 증상이 명확하고, 해당 파라미터가 직접 원인이며, 벤더 문서가 값을 제시합니다.

### kubelet의 예약 — 커널 파라미터보다 먼저

노드 안정성에서 커널 튜닝보다 효과가 큰 것이 **kubelet의 리소스 예약**입니다.

| 설정 | 용도 |
|---|---|
| `--system-reserved` | OS·시스템 데몬용 예약 |
| `--kube-reserved` | kubelet·컨테이너 런타임용 예약 |
| `--eviction-hard` | 이 임계에 닿으면 Pod 축출 |

예약이 부족하면 Pod가 노드 메모리를 다 먹고 **커널이나 kubelet 자체가 OOM에 걸립니다.** 이 경우 노드가 `NotReady`가 되고 그 위의 모든 Pod가 영향을 받습니다 — 개별 Pod OOM보다 훨씬 나쁜 결과입니다.

**축출이 OOM보다 낫습니다.** 축출은 Kubernetes가 통제된 방식으로 Pod를 옮기는 것이고, OOM killer는 커널이 프로세스를 갑자기 죽이는 것입니다. `--eviction-hard`를 적절히 설정해 커널 OOM 전에 Kubernetes가 개입하게 만드는 것이 목표입니다.

### PSI로 압박 관측

cgroup v2의 PSI가 사용량보다 나은 신호를 줍니다.

```bash
# 노드 전체
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# 특정 cgroup
cat /sys/fs/cgroup/<path>/memory.pressure
```

`some avg10`은 최근 10초간 **최소 하나의 태스크가 그 자원 때문에 지연된 시간의 비율**입니다. 사용량 그래프가 평온한데 이 값이 올라가고 있으면 회수나 경합에 시간을 쓰고 있다는 뜻입니다.

## 네트워크 — 근거 있는 조정 항목

### conntrack

앞서 다룬 대로 **가장 자주 실제 장애를 만드는 항목**입니다.

| 항목 | 내용 |
|---|---|
| 증상 | 새 연결이 조용히 드롭. 애플리케이션은 타임아웃/refused만 봄 |
| 직접 증거 | `conntrack -S`의 **`insert_failed`** 증가 |
| 보조 신호 | `dmesg`의 `nf_conntrack: table full`, `nf_conntrack_count` / `nf_conntrack_max` 비율 |
| 조정 경로 | **`kube-proxy-config` ConfigMap의 `conntrack.maxPerCore` / `conntrack.min`** (EKS에서 이것이 우선) |
| 비용 | 항목당 노드 메모리. 무한정 올릴 수 없음 |
| 근본 대응 | 연결 재사용(keepalive), headless Service, eBPF 데이터플레인으로 경로 우회 |

**`maxPerCore`를 쓰는 이유**를 알아둘 가치가 있습니다. 절대값이 아니라 코어당 값이라, 노드 크기가 달라도 같은 설정으로 비례 조정됩니다. 절대값(`nf_conntrack_max`)을 직접 박으면 작은 노드에서는 과다, 큰 노드에서는 부족해집니다.

타임아웃도 조정 대상입니다 — `nf_conntrack_tcp_timeout_established`(기본이 매우 길다)를 줄이면 항목이 빨리 회수됩니다. 단 정상적인 장수명 연결이 끊기지 않도록 주의해야 합니다.

### 소켓 버퍼와 큐

| 파라미터 | 언제 |
|---|---|
| `net.core.somaxconn` | **accept 큐 오버플로 시.** 연결 폭주를 받는 서버에서 흔한 조정 |
| `net.ipv4.tcp_max_syn_backlog` | SYN 폭주 시 |
| `net.core.netdev_max_backlog` | **수신 softirq가 못 따라갈 때** |
| `net.ipv4.tcp_rmem` / `tcp_wmem` | **기본값 유지 권장** — 커널 자동 튜닝이 동작 중. 고정하면 자동 튜닝이 꺼짐. BDP가 큰 장거리 경로에서만 상한 조정 검토 |
| `net.ipv4.ip_local_port_range` | **출발지 포트 고갈 시.** egress가 많은 노드에서 실제로 발생 |
| `net.ipv4.tcp_tw_reuse` | TIME_WAIT 누적 시. 거동을 이해하고 적용 |

**`somaxconn`과 `ip_local_port_range`가 실무에서 근거 있는 조정의 대표 사례**입니다. 전자는 accept 큐 오버플로 카운터(`nstat`의 `TcpExtListenOverflows`)로 증거를 잡을 수 있고, 후자는 포트 고갈이 연결 실패로 직접 나타납니다.

반면 **`tcp_rmem`/`tcp_wmem`은 건드리지 않는 것이 기본**입니다. 커널이 부하에 따라 자동 조정하고 있고, 값을 고정하면 그 자동 조정이 비활성화됩니다.

### qdisc

노드 내 드롭이 확인되면(`tc -s qdisc`의 `dropped`) 조정 대상입니다.

- **`fq_codel`**: 버퍼블로트 완화 — 지연이 문제일 때
- **`fq`**: 페이싱 — bbr과 함께 쓸 때
- 큐 길이(`txqueuelen`)를 늘리면 드롭은 줄지만 **지연이 늘어납니다.** 트레이드오프를 인지하고 결정해야 합니다

### 인터럽트 분산

`/proc/interrupts`에서 특정 코어 편중이 보이고 `mpstat -P ALL`의 `%soft`가 그 코어에서 튀면 RSS/RPS/RFS 설정을 봅니다. 다만 **최신 ENA 드라이버와 인스턴스 타입은 다중 큐와 RSS가 기본 구성**이라, 대개 문제가 되지 않습니다.

### kube-proxy 모드

노드 커널 파라미터는 아니지만 데이터패스 성능에 가장 큰 영향을 줍니다.

| 상황 | 권고 |
|---|---|
| Service 수가 많고 iptables 모드 | **nftables 모드 검토** — 1.33에서 GA, O(1) 조회 + 증분 갱신. 커널 5.13+ 필요(AL2023은 충족) |
| **IPVS 모드 사용 중** | **이전 계획 필요** — 1.35에서 deprecated, 1.38 제거 목표. 권장 대체는 nftables |
| 기본값 유지 | nftables가 GA여도 **기본은 여전히 iptables** — 전환은 명시적 결정 |

## 스토리지

| 파라미터 | 내용 |
|---|---|
| **I/O 스케줄러** | NVMe는 `none`(또는 `mq-deadline`)이 일반적. NVMe에서 복잡한 스케줄러는 이점이 적음 |
| `vm.dirty_ratio` / `dirty_background_ratio` | 쓰기 버퍼링 양. 쓰기 폭주 시 지연 특성에 영향 |
| **ephemeral storage** | 커널 파라미터보다 **overlayfs copy-up 비용**이 실제 문제 — 쓰기 많은 경로는 볼륨으로 분리 ([컨테이너 커널 기능](./01-container-primitives.md)) |
| **EBS 성능** | 커널이 아니라 볼륨 타입·IOPS·throughput 설정의 문제 ([EBS gp2 vs gp3 실측](../storage/01-ebs-gp2-gp3-benchmark.md)) |

## 워크로드별 정리

증상에서 출발하는 표입니다.

| 워크로드 | 자주 필요한 조정 | 근거 카운터 |
|---|---|---|
| **고연결 게이트웨이·프록시** | conntrack 상한, `somaxconn`, `ip_local_port_range` | `insert_failed`, `TcpExtListenOverflows`, 포트 고갈 |
| **지연 민감 (거래·실시간)** | CPU limit 재검토, CPU Manager 정적 정책, `fq_codel` | `cpu.stat` throttling, `cpu.pressure` |
| **대용량 처리 (배치·데이터)** | 버퍼 상한(장거리만), `netdev_max_backlog` | qdisc `dropped`, softirq 편중 |
| **검색·색인 (OpenSearch 등)** | **`vm.max_map_count`**, 파일 디스크립터 한도 | 시작 실패 로그 |
| **고밀도 노드** | `kernel.pid_max`, kubelet 예약, 축출 임계 | PID 고갈, 노드 `NotReady` |
| **블록체인 노드** | 파일 디스크립터, 디스크 IOPS, 소켓 버퍼 | [블록체인 노드 운영](../blockchain/02-nodes-on-eks.md) |

## 변경을 어떻게 관리할 것인가

튜닝 자체보다 **관리 방식이 장기적으로 더 중요합니다.**

| 원칙 | 이유 |
|---|---|
| **코드로 관리** (Karpenter `EC2NodeClass`, 시작 템플릿, Bottlerocket 설정) | 노드마다 값이 다른 상황을 막음 |
| **변경 사유를 주석으로 남김** | "왜 이 값인가"를 6개월 뒤에 알 수 없으면 아무도 되돌리지 못함 |
| **노드 그룹을 분리** | 워크로드 성격이 다르면 튜닝도 달라야 함. 한 프로필을 전체에 강요하지 않음 |
| **커널 버전을 고정하거나 전환을 계획** | `kernel-default` AMI는 조용히 커널이 바뀜 |
| **적용 후 실제 값 검증** | 특히 conntrack — 다른 주체가 덮어쓸 수 있음 |
| **변경 전후 같은 조건으로 측정** | 측정 없는 튜닝은 미신이 됨 |

## 정리

- **대부분은 기본값을 두십시오.** 커널은 부하에 따라 자동 조정하고 있고, 근거 없는 튜닝은 재현 불가능한 구성과 커널 업그레이드 시 파손을 만듭니다.
- 튜닝의 전제는 측정입니다. **드롭 카운터부터 보십시오** — `insert_failed`, qdisc `dropped`, NIC 드롭.
- **AL2023 기본 커널이 2026년 8월 17일부터 6.18**입니다. `kernel-default` AMI를 쓰면 노드 교체만으로 커널이 바뀌므로, 커널 전환을 Kubernetes 업그레이드와 같은 무게로 다루십시오.
- CPU throttling의 근본 원인은 대개 **애플리케이션이 인식하는 CPU 수와 할당량의 불일치**입니다. `GOMAXPROCS`/`ActiveProcessorCount`부터 맞추십시오.
- 노드 안정성에는 커널 튜닝보다 **kubelet 예약과 축출 임계**가 효과적입니다. 축출이 커널 OOM보다 낫습니다.
- 근거 있는 조정의 대표 사례는 **conntrack 상한, `somaxconn`, `ip_local_port_range`, `vm.max_map_count`**입니다. 모두 직접적인 증거 카운터가 있습니다.
- `tcp_rmem`/`tcp_wmem`은 **건드리지 않는 것이 기본**입니다 — 고정하면 커널 자동 튜닝이 꺼집니다.
- **IPVS 모드를 쓰고 있으면 이전 계획이 필요합니다** (1.35 deprecated, 1.38 제거 목표).

## 참고 자료

- [Amazon Linux 2023 — Updating the Linux Kernel](https://docs.aws.amazon.com/linux/al2023/ug/kernel-update.html)
- [Amazon EKS-Optimized Amazon Linux 2023 AMIs](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
- [Increase nf_conntrack_max limit on EKS nodes](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Running kube-proxy in nftables Mode — EKS Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [KEP-5495: Deprecate IPVS mode in kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [EEVDF Scheduler — Linux kernel documentation](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel/sched/debug.c — debugfs 튜너블 정의](https://github.com/torvalds/linux/blob/master/kernel/sched/debug.c)
- [bottlerocket-os/bottlerocket#4221 — conntrack limit not applied](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [Reserve Compute Resources for System Daemons (Kubernetes)](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Using sysctls in a Kubernetes Cluster](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)
- [리소스 최적화](../ops/10-resource-optimization.md) / [Pod 네트워크 실측 벤치마크](../networking/06-pod-network-benchmark.md)
