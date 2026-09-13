# 컨테이너를 지탱하는 커널 기능

> **지원 버전**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.25+ (cgroup v2)
> **마지막 업데이트**: 2026년 9월 13일

## 이 문서에서 다루는 것

- 컨테이너는 커널의 어떤 기능들을 조합해 만들어지는가 — 그리고 "컨테이너"라는 커널 객체는 없다는 점
- cgroup v1에서 v2로 바뀌면서 운영에서 실제로 달라진 것 (특히 OOM 진단)
- netfilter와 conntrack이 Kubernetes 네트워킹의 어디에 끼어 있는가

## 먼저: 커널에 "컨테이너"는 없습니다

이것이 컨테이너를 이해하는 출발점입니다. 커널에는 `struct container` 같은 것이 없고, 컨테이너를 만드는 단일 시스템 콜도 없습니다.

컨테이너는 **여러 독립적인 커널 기능을 조합해 만든 관례**입니다. 런타임(containerd, runc)이 프로세스를 하나 띄우면서 다음을 함께 적용합니다.

| 목적 | 커널 기능 |
|---|---|
| **무엇을 볼 수 있는가** (격리) | namespace |
| **얼마나 쓸 수 있는가** (제한) | cgroup |
| **무엇을 할 수 있는가** (권한) | capabilities, seccomp, LSM (AppArmor/SELinux) |
| **파일시스템을 어떻게 합치는가** | overlayfs (union mount) |
| **트래픽을 어떻게 흘리는가** | veth, bridge/route, netfilter |

이 조합이라는 점에서 두 가지 실무적 결론이 나옵니다.

**첫째, 격리는 전부 또는 전무가 아닙니다.** 어떤 namespace는 공유하고 어떤 것은 격리할 수 있습니다. Kubernetes Pod가 정확히 그 예입니다 — 같은 Pod의 컨테이너들은 network·IPC namespace를 **공유하고** mount·PID namespace는 대개 **분리**합니다. 그래서 같은 Pod 안에서는 `localhost`로 서로를 부를 수 있고(network 공유), 파일시스템은 서로 안 보입니다(mount 분리).

**둘째, 빠뜨린 격리는 조용히 구멍이 됩니다.** 커널이 "컨테이너를 만들어라"를 모르므로, 런타임이 seccomp 프로필을 적용하지 않으면 그냥 적용되지 않은 상태로 돕니다. 컨테이너 보안이 런타임과 정책 설정의 문제인 이유입니다.

## Namespace — 무엇을 볼 수 있는가

namespace는 **커널 자원의 "이름 공간"을 분리**합니다. 같은 이름이나 번호가 namespace마다 다른 것을 가리키게 만드는 장치입니다.

| Namespace | 격리 대상 | Pod에서 |
|---|---|---|
| **mnt** | 마운트 지점 | 컨테이너별 분리 |
| **pid** | 프로세스 ID | 컨테이너별 분리 (`shareProcessNamespace: true`로 Pod 내 공유 가능) |
| **net** | 네트워크 인터페이스, 라우팅 테이블, netfilter 규칙, 소켓, 포트 | **Pod 단위로 공유** |
| **ipc** | System V IPC, POSIX 메시지 큐 | Pod 단위로 공유 |
| **uts** | hostname, domainname | Pod 단위로 공유 |
| **user** | UID/GID 매핑 | 기본 미사용 (아래 참고) |
| **cgroup** | cgroup 루트 경로 | 컨테이너별 분리 |
| **time** | 부팅 시각, 단조 시계 (5.6+) | 미사용 |

### net namespace가 Pod의 경계인 이유

Pod의 정체가 여기서 정해집니다. Kubernetes는 Pod마다 net namespace를 하나 만들고(pause 컨테이너가 보유), 그 Pod의 모든 컨테이너를 **같은 net namespace에 넣습니다.**

결과로 따라오는 것들:

- Pod 안의 컨테이너들은 **같은 IP, 같은 포트 공간**을 공유합니다 → 같은 Pod에서 두 컨테이너가 8080을 동시에 열 수 없습니다
- `localhost` 통신이 됩니다 → 사이드카 패턴의 기반
- **netfilter 규칙도 net namespace별입니다** → 사이드카 메시의 init container가 Pod의 net namespace 안에서 iptables를 심을 수 있는 이유이고, 그 규칙이 노드 전체에 영향을 주지 않는 이유입니다 ([VPC Lattice 커널 데이터패스](../service-mesh/vpc-lattice/07-kernel-datapath.md) 참고)
- 라우팅 테이블도 분리됩니다 → Pod 안에서 `ip route`를 보면 노드의 것이 아닙니다

### user namespace — 왜 오래 기본이 아니었는가

User namespace는 컨테이너 UID/GID를 다른 host 범위로 매핑합니다. 여러 탈출 동작의 권한을 줄이지만 kernel 취약점이나 추가 권한 상승 경로까지 **봉쇄한다고 보장하지는 않습니다**.

그런데 오래 기본이 아니었습니다. 이유는 **파일 소유권**입니다. 볼륨의 파일이 호스트 UID로 기록되어 있는데 컨테이너가 다른 UID로 보면 권한이 맞지 않습니다. 이를 해결하려면 마운트 시점에 UID를 변환해야 하고(idmapped mounts, 커널 5.12+), 스토리지 드라이버와 CSI도 이를 지원해야 합니다.

### Kubernetes의 user namespace 지원 현황

[KEP-127](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/kep.yaml) 기준으로 성숙 단계는 다음과 같습니다.

| 단계 | 버전 |
|---|---|
| alpha | v1.25 |
| beta | v1.35 |
| **stable (GA)** | **v1.36** |

feature gate는 `UserNamespacesSupport`이며 kubelet과 kube-apiserver에 적용됩니다. **1.36부터는 GA이므로 feature gate를 켜지 않아도 `hostUsers: false`를 쓸 수 있습니다.**

::: warning 확인 필요
위 성숙도는 Kubernetes 업스트림 기준입니다. **EKS가 해당 버전을 제공하는지, 그리고 사용 중인 컨테이너 런타임과 CSI 드라이버가 idmapped mounts를 지원하는지는 별개**입니다. 도입 전에 EKS 지원 버전과 런타임·스토리지 조합을 확인하십시오.
:::

## cgroup — 얼마나 쓸 수 있는가

cgroup(control group)은 프로세스 그룹의 **자원 사용을 측정하고 제한**합니다. Kubernetes의 `requests`/`limits`가 최종적으로 도달하는 곳입니다.

### v1과 v2의 구조적 차이

| 항목 | cgroup v1 | cgroup v2 |
|---|---|---|
| **계층 구조** | 컨트롤러(cpu, memory, blkio…)마다 **별개의 트리** | **단일 통합 트리** |
| **프로세스 소속** | 컨트롤러별로 다른 그룹에 속할 수 있음 | 하나의 그룹에만 속함 |
| **메모리+IO 협조** | 어려움 (별도 트리라 연계 불가) | 가능 (같은 트리) |
| **압력 정보** | 없음 | **PSI** (`cpu.pressure`, `memory.pressure`, `io.pressure`) |
| **CPU 제한 표기** | `cpu.cfs_quota_us` / `cpu.cfs_period_us` | `cpu.max` (한 파일에 "quota period") |
| **메모리 제한 표기** | `memory.limit_in_bytes` | `memory.max`, 여기에 `memory.high`(소프트 압력) 추가 |
| **AL2023 EKS AMI** | — | **기본값** |

v1의 "컨트롤러마다 별개 트리"가 실제로 문제였던 지점은 **메모리 회수와 IO의 연계**입니다. 메모리가 부족해 page cache를 비워야 할 때, 그 회수 작업 자체가 디스크 IO를 유발하는데 v1에서는 두 컨트롤러가 서로를 몰랐습니다. v2의 통합 트리는 이를 같은 계층에서 다룹니다.

### 운영에서 가장 크게 달라진 것 — OOM 진단

cgroup v2에서 반드시 알아야 할 사실입니다.

> **`memory.current`는 page cache를 포함합니다.**

즉 애플리케이션이 실제로 붙잡고 있는 메모리(anon/RSS)가 limit보다 훨씬 낮은데도, 파일을 많이 읽어 page cache가 쌓이면 `memory.current`가 limit에 닿습니다.

여기서 중요한 구분이 있습니다. **page cache는 회수 가능(reclaimable)합니다.** 그래서 정상적인 경우 커널은 limit에 닿으면 page cache를 버려서 공간을 만들고, OOM은 나지 않습니다. 문제가 되는 것은 **회수 속도가 할당 속도를 못 따라갈 때**이고, 이때 OOM killer가 동작합니다.

실무적 함의:

| 오해 | 실제 |
|---|---|
| "`memory.current`가 limit 근처이면 OOM 직전" | 회수 가능한 file cache가 포함될 수 있으므로 구성을 가정하지 말고 anon/file/kernel 사용량·압력 확인 |
| "RSS만 보면 된다" | RSS가 낮아도 OOM이 날 수 있습니다 (회수 못 따라가는 경우) |
| "limit을 올리면 해결" | 원인이 회수 지연이면 올려도 재발합니다 |

**진단에 봐야 하는 값들:**

| 파일/값 | 의미 |
|---|---|
| `memory.current` | 현재 사용량 (page cache 포함) |
| `memory.stat`의 `anon` | 익명 메모리 — 애플리케이션이 실제 붙잡은 양 |
| `memory.stat`의 `file` | page cache |
| `memory.events`의 `oom` / `oom_kill` | OOM 발생·킬 횟수 |
| `memory.events`의 `high` / `max` | 소프트/하드 한계에 닿은 횟수 |
| `memory.pressure` (PSI) | 메모리 압박으로 **지연된 시간의 비율** |

**PSI가 특히 유용합니다.** 사용량(얼마나 쓰는가)이 아니라 **압박(그래서 얼마나 기다렸는가)**을 알려주기 때문입니다. `memory.pressure`의 `some avg10`이 올라가고 있으면 회수에 시간을 쓰고 있다는 뜻이고, 이는 사용량 그래프만으로는 보이지 않습니다.

### CPU limit과 throttling — 사용률이 낮은데 느린 이유

CPU limit은 **대역폭 제한**입니다. `cpu.max`가 `20000 100000`이면 "100ms 주기마다 20ms까지"를 뜻합니다.

여기서 직관에 반하는 일이 벌어집니다. 애플리케이션이 짧은 시간에 여러 스레드로 일하면, **주기 초반에 할당량을 다 쓰고 주기가 끝날 때까지 강제로 멈춥니다.** 평균 사용률은 20%로 낮게 보이는데 지연은 튑니다.

멀티스레드에서 더 심합니다. 4개 스레드가 동시에 돌면 20ms 할당량은 실제 시간 5ms에 소진됩니다. 나머지 95ms는 대기입니다.

**진단:** `cpu.stat`의 `nr_throttled`(throttling 당한 주기 수)와 `throttled_usec`(총 throttling 시간). `nr_periods`에 대한 `nr_throttled` 비율이 유의미하게 높으면 limit이 원인입니다.

**대응 방향** (자세한 request/limit 설계는 [리소스 최적화](../ops/10-resource-optimization.md)):

- limit을 올리거나 제거 (단 노드 안정성과 트레이드오프)
- 애플리케이션의 스레드 수를 limit에 맞게 조정 (JVM의 `-XX:ActiveProcessorCount`, Go의 `GOMAXPROCS` 등) — **컨테이너가 인식하는 CPU 수와 실제 할당량이 다른 것이 근본 원인인 경우가 많습니다**
- `cpu.pressure` PSI로 실제 대기 시간 확인

## 권한 — 무엇을 할 수 있는가

격리(namespace)와 제한(cgroup)이 되어 있어도, 프로세스가 할 수 있는 **동작** 자체를 줄이는 것은 별개 계층입니다.

| 기능 | 무엇을 하는가 | Kubernetes에서 |
|---|---|---|
| **capabilities** | root 권한을 잘게 쪼갠 단위로 부여·제거 (`CAP_NET_ADMIN`, `CAP_SYS_ADMIN` 등) | `securityContext.capabilities.add/drop` |
| **seccomp** | 허용할 **시스템 콜** 목록 제한 | `securityContext.seccompProfile` (`RuntimeDefault` 권장) |
| **LSM** (AppArmor/SELinux) | 파일·네트워크 접근을 정책으로 통제 | `securityContext.appArmorProfile` 등 |
| **no_new_privs** | setuid 바이너리로 권한 상승 차단 | `allowPrivilegeEscalation: false` |

세 계층이 다른 질문에 답합니다 — capabilities는 "이 권한을 가졌는가", seccomp는 "이 시스템 콜을 부를 수 있는가", LSM은 "이 객체에 접근할 수 있는가". 그래서 **하나만으로는 부족하고 겹쳐 쓰는 것이 정석**입니다.

`CAP_NET_ADMIN`은 특별히 언급할 가치가 있습니다. 사이드카 메시의 init container가 iptables를 심으려면 이 권한이 필요하고, 그래서 메시 도입이 "왜 이 Pod가 NET_ADMIN을 갖고 있나"라는 보안 심의 질문을 만듭니다.

## netfilter와 conntrack — Kubernetes 네트워킹의 실체

### netfilter

netfilter는 커널 네트워크 스택의 정해진 지점에 **훅**을 제공하는 프레임워크입니다. `iptables`, `nftables`, `ipvs`는 모두 이 훅을 쓰는 사용자 공간 도구이거나 그 위의 구현입니다.

주요 훅 지점:

| 훅 | 언제 |
|---|---|
| `PREROUTING` | 패킷이 들어와 라우팅 결정 **전** — DNAT 지점 |
| `INPUT` | 로컬 프로세스로 향하는 패킷 |
| `FORWARD` | 통과하는 패킷 |
| `OUTPUT` | 로컬에서 나가는 패킷 |
| `POSTROUTING` | 라우팅 결정 **후** 나가기 직전 — SNAT/MASQUERADE 지점 |

Kubernetes에서 이 훅들이 쓰이는 곳:

- **Service의 ClusterIP → Pod IP 변환**: `PREROUTING`/`OUTPUT`에서 DNAT
- **Pod → 외부 통신의 출발지 변환**: `POSTROUTING`에서 MASQUERADE
- **NetworkPolicy**: CNI가 `FORWARD` 등에 규칙 삽입 (Calico의 iptables 데이터플레인)
- **사이드카 메시의 트래픽 인터셉트**: Pod net namespace 안의 `OUTPUT`/`PREROUTING` REDIRECT

### kube-proxy 모드 — iptables, IPVS, nftables

Service 구현 방식이 세 갈래이고, **2025~2026년에 지형이 바뀌었습니다.**

| 모드 | 룰 평가 | 상태 |
|---|---|---|
| **iptables** | Rule-chain 조회 비용은 배치에 따라 다르며 현재 kube-proxy는 갱신을 최적화 | 명시 변경하지 않은 환경의 기본값. 설치 구현 확인 |
| **IPVS** | 커널 L4 로드밸런서, 해시 기반 O(1) | **Kubernetes 1.35(2025년 12월)에서 deprecated**, 1.38 제거 목표 |
| **nftables** | O(1) 조회 + **증분 규칙 갱신** | **Kubernetes 1.33에서 GA** (1.29 alpha → 1.31 beta). 워커 노드에 **커널 5.13+** 필요 |

읽는 방법:

- **대규모 클러스터에서 iptables 모드의 병목은 룰 수와 갱신 비용**입니다. Service·Endpoint가 많을수록 kube-proxy의 동기화 시간이 늘고, 그 동안 규칙이 최신이 아닙니다.
- **IPVS를 쓰고 있다면 이전 계획이 필요합니다.** 1.38에서 제거가 목표이고, 권장 대체는 nftables 모드입니다.
- AL2023 노드는 커널 6.x라 nftables 모드의 커널 요건을 충족합니다.
- nftables가 GA여도 **기본값은 iptables**이므로 명시적으로 전환해야 합니다.

### conntrack — 가장 자주 사고를 내는 지점

netfilter가 NAT를 하려면 **연결을 기억해야** 합니다. 나갈 때 주소를 바꿨으면 돌아오는 패킷을 원래대로 되돌려야 하니까요. 이 기억을 담는 커널 테이블이 `nf_conntrack`입니다.

Kube-proxy netfilter mode의 Service NAT는 connection tracking에 의존하지만 **NAT 없는 트래픽도 추적될 수 있습니다**. Headless Service·외부 endpoint·eBPF 구현의 경로는 다르므로 모든 Kubernetes Service가 같은 DNAT 경로를 반드시 거친다고 보면 안 됩니다.

**포화되면 어떻게 되는가가 문제의 핵심입니다.** 에러 로그가 요란하게 나지 않습니다. 새 연결이 **조용히 드롭**되고, 애플리케이션은 연결 타임아웃이나 refused를 봅니다. 무엇이 원인인지 애플리케이션 쪽에서는 알 수 없습니다.

| 관측 지점 | 의미 |
|---|---|
| `/proc/sys/net/netfilter/nf_conntrack_count` | 현재 항목 수 |
| `/proc/sys/net/netfilter/nf_conntrack_max` | 상한 |
| `conntrack -S` → `insert_failed` | 삽입 실패. 단독으로 포화를 확정하지 말고 count/max·drop·kernel log와 함께 확인 |
| `conntrack -S`의 `drop` | 드롭된 패킷 |
| `dmesg`의 `nf_conntrack: table full, dropping packet` | 커널 경고 |

**EKS에서 주의할 점**이 하나 있습니다. kube-proxy도 conntrack 값을 관리하는데, **EKS에는 `kube-proxy-config` ConfigMap이 기본으로 존재하고 이것이 커맨드라인 인자보다 우선합니다.** 따라서 노드에서 sysctl만 올려놓고 kube-proxy가 다시 낮추는 상황이 생길 수 있습니다. 값을 바꾸려면 ConfigMap의 `conntrack.maxPerCore`·`conntrack.min`을 조정하고 kube-proxy DaemonSet을 재시작하는 것이 올바른 경로입니다.

`nf_conntrack_max`를 올리면 **노드 메모리 사용이 늘어납니다.** 항목당 메모리를 쓰므로 무한정 올릴 수 없고, 노드 크기에 맞춰야 합니다. 구체적 설정은 [EKS 노드 커널 튜닝](./03-eks-node-tuning.md)에서 다룹니다.

::: warning 실제 kube-proxy 설정 확인
과거 Bottlerocket 보고에는 kube-proxy가 node sysctl을 덮어쓴 사례가 있습니다. `--config` 사용 시 덮어써지는 CLI flag가 아니라 **활성 설정**의 `conntrack.maxPerCore`·`conntrack.min`을 수정합니다. 둘 다 0으로 설정하는 것은 node sysctl에 상한 관리를 맡기는 의도적 선택이므로 설치한 add-on/version의 동작과 실제 node 값을 검증하고 메모리 예산을 유지합니다.
:::

과거 issue만으로 모든 현재 Bottlerocket release가 같은 동작이라고 단정할 수 없습니다. Rollout 후 유효 설정과 실제 sysctl을 확인합니다.

### conntrack을 피하는 방향

conntrack 부하 자체를 줄이는 접근도 있습니다.

- Headless Service는 Service VIP DNAT를 피하지만 **conntrack을 본질적으로 우회하지는 않습니다**.
- Cilium은 kube-proxy/netfilter 기능을 eBPF map으로 대체할 수 있으며 자체 tracking/map 압력과 남은 netfilter 경로를 측정합니다.
- 연결 재사용은 churn을 줄이며 established 용량과 timeout 동작도 검증합니다.

## overlayfs — 이미지 계층이 합쳐지는 방식

컨테이너 이미지가 계층으로 되어 있고 그 계층들이 하나의 파일시스템으로 보이는 것은 **union mount**, 구체적으로는 `overlayfs`입니다.

구조는 세 부분입니다.

| 계층 | 역할 |
|---|---|
| **lowerdir** | 읽기 전용 — 이미지 계층들 (여러 개 겹칠 수 있음) |
| **upperdir** | 쓰기 가능 — 컨테이너의 변경분 |
| **merged** | 컨테이너가 보는 합쳐진 뷰 |

여기서 운영상 중요한 성질이 **copy-up**입니다. lowerdir의 파일을 수정하면 **파일 전체가 upperdir로 복사된 뒤** 수정됩니다. 그래서:

- **큰 파일을 조금 수정하는 것도 전체 복사 비용**을 냅니다. 1GB 파일의 1바이트 수정에 1GB 복사가 일어납니다
- 컨테이너 안에서 대용량 쓰기를 하면 노드 디스크를 먹습니다 (ephemeral storage)
- **쓰기가 많은 경로는 볼륨으로 빼는 것**이 정석입니다 — emptyDir, PVC 등

## 정리

- 커널에 "컨테이너"는 없습니다. namespace(격리) + cgroup(제한) + capabilities/seccomp/LSM(권한) + overlayfs(파일시스템) + netfilter(네트워크)의 **조합**입니다. 그래서 격리는 선택적이고, 빠뜨린 격리는 조용한 구멍이 됩니다.
- **net namespace가 Pod의 경계**입니다. 같은 IP·포트 공간, `localhost` 통신, Pod 범위의 netfilter 규칙이 모두 여기서 나옵니다.
- cgroup v2에서 **`memory.current`는 page cache를 포함**합니다. OOM 진단은 `memory.stat`의 `anon`과 `memory.events`, 그리고 **PSI(`memory.pressure`)**를 함께 봐야 합니다.
- CPU limit은 **대역폭 제한**이라 사용률이 낮아도 throttling으로 지연이 튑니다. `cpu.stat`의 `nr_throttled`가 증거입니다.
- kube-proxy는 **nftables가 1.33에서 GA, IPVS는 1.35에서 deprecated(1.38 제거 목표)**, 기본값은 여전히 iptables입니다.
- Conntrack 포화는 신규 연결을 드롭할 수 있습니다. Count/max·drop/insert counter·log로 진단하고 상한 변경 전 유효 kube-proxy 설정을 확인합니다.

다음: [커널 네트워킹 스택](./02-network-stack.md)에서 패킷이 지나는 전체 경로를 봅니다.

## 참고 자료

- [Control Group v2 — Linux kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [namespaces(7) — Linux manual](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [KEP-127: Support User Namespaces](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/README.md)
- [bottlerocket-os/bottlerocket#4221 — conntrack limit not applied](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [NFTables mode for kube-proxy (Kubernetes Blog)](https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/)
- [KEP-5495: Deprecate IPVS mode in kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [Running kube-proxy in nftables Mode — EKS Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [Increase nf_conntrack_max limit on EKS nodes](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Amazon EKS-Optimized Amazon Linux 2023 AMIs](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
