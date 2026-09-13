# 컨테이너를 지탱하는 커널 기능 퀴즈

이 퀴즈는 namespace, cgroup v2, netfilter, conntrack에 대한 이해도를 테스트합니다.

## 객관식 문제

1. "커널에 컨테이너는 없다"는 서술의 의미와 그로부터 파생되는 실무적 결론은?
   - A) 컨테이너는 가상머신의 일종이므로 커널과 무관하다
   - B) 컨테이너는 namespace·cgroup·capabilities 등을 조합한 관례이므로, 격리가 선택적이고 런타임이 빠뜨린 격리는 조용한 구멍이 된다
   - C) 컨테이너는 사용자 공간 라이브러리로만 구현된다
   - D) 커널 6.x부터 `struct container`가 추가되었다

<details>

<summary>정답 보기</summary>

**정답: B) 컨테이너는 namespace·cgroup·capabilities 등을 조합한 관례이므로, 격리가 선택적이고 런타임이 빠뜨린 격리는 조용한 구멍이 된다**

**설명:**
커널에는 `struct container`도, 컨테이너를 만드는 단일 시스템 콜도 없습니다. 런타임이 프로세스를 띄우면서 namespace(격리), cgroup(제한), capabilities/seccomp/LSM(권한), overlayfs(파일시스템), netfilter(네트워크)를 함께 적용하는 것입니다. 조합이라는 성질에서 두 결론이 나옵니다 — 격리가 전부 또는 전무가 아니라 선택적이며(Pod가 network namespace는 공유하고 mount는 분리하는 것이 그 예), 커널이 "컨테이너를 만들어라"를 모르므로 런타임이 seccomp 프로필을 적용하지 않으면 그냥 적용되지 않은 상태로 돕니다.
</details>

2. Pod 안의 두 컨테이너가 `localhost`로 통신할 수 있고 같은 포트를 동시에 열 수 없는 이유는?
   - A) Kubernetes가 컨테이너 간 프록시를 자동 생성하기 때문
   - B) Pod 단위로 net namespace를 공유하므로 같은 IP와 포트 공간을 쓰기 때문
   - C) CNI가 컨테이너별 loopback을 연결하기 때문
   - D) kube-proxy가 Pod 내부 트래픽을 라우팅하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) Pod 단위로 net namespace를 공유하므로 같은 IP와 포트 공간을 쓰기 때문**

**설명:**
Kubernetes는 Pod마다 net namespace를 하나 만들고(pause 컨테이너가 보유) 그 Pod의 모든 컨테이너를 같은 net namespace에 넣습니다. 그래서 같은 IP·포트 공간을 공유하고 `localhost` 통신이 되며, 두 컨테이너가 8080을 동시에 열 수 없습니다. 이것이 사이드카 패턴의 기반입니다. 또한 netfilter 규칙도 net namespace별이므로, 사이드카 메시의 init container가 Pod 안에서 iptables를 심어도 노드 전체에 영향을 주지 않습니다.
</details>

3. cgroup v2에서 `memory.current`가 limit 근처인데도 정상일 수 있는 이유는?
   - A) `memory.current`는 예측값이므로 부정확하다
   - B) `memory.current`에 page cache가 포함되며, page cache는 회수 가능하므로 limit에 닿으면 커널이 버려서 공간을 만든다
   - C) cgroup v2는 limit을 강제하지 않는다
   - D) `memory.current`는 노드 전체 메모리를 표시한다

<details>

<summary>정답 보기</summary>

**정답: B) `memory.current`에 page cache가 포함되며, page cache는 회수 가능하므로 limit에 닿으면 커널이 버려서 공간을 만든다**

**설명:**
애플리케이션이 실제 붙잡은 메모리(anon/RSS)가 limit보다 훨씬 낮아도 파일을 많이 읽으면 page cache가 쌓여 `memory.current`가 limit에 닿습니다. 그런데 page cache는 회수 가능하므로 정상적인 경우 커널이 버려서 공간을 만들고 OOM은 나지 않습니다. 문제는 **회수 속도가 할당 속도를 못 따라갈 때**이고 이때 OOM killer가 동작합니다. 그래서 진단에는 `memory.stat`의 `anon`, `memory.events`의 `oom`, 그리고 PSI(`memory.pressure`)를 함께 봐야 합니다.
</details>

4. CPU 사용률이 20%로 낮은데 p99 지연이 튀는 경우, CPU limit이 원인인지 확인하는 방법은?
   - A) `top`으로 CPU 사용률 재확인
   - B) `cpu.stat`의 `nr_throttled`와 `nr_periods` 비율 확인
   - C) `memory.pressure` 확인
   - D) 노드의 `/proc/loadavg` 확인

<details>

<summary>정답 보기</summary>

**정답: B) `cpu.stat`의 `nr_throttled`와 `nr_periods` 비율 확인**

**설명:**
CPU limit은 대역폭 제한입니다. `cpu.max`가 `20000 100000`이면 "100ms 주기마다 20ms까지"이므로, 애플리케이션이 여러 스레드로 짧게 일하면 주기 초반에 할당량을 소진하고 주기가 끝날 때까지 강제로 멈춥니다. 평균 사용률은 20%로 낮게 보이는데 지연은 튑니다. `nr_throttled / nr_periods` 비율이 유의미하게 높으면 limit이 원인입니다. 근본 원인은 대개 애플리케이션이 인식하는 CPU 수와 할당량의 불일치이므로 `GOMAXPROCS`나 `-XX:ActiveProcessorCount`를 먼저 맞춰야 합니다.
</details>

5. 2026년 기준 kube-proxy 모드의 상태로 올바른 것은?
   - A) nftables가 기본값이고 iptables는 제거되었다
   - B) nftables는 1.33에서 GA, IPVS는 1.35에서 deprecated(1.38 제거 목표), 기본값은 여전히 iptables
   - C) IPVS가 기본값이고 nftables는 alpha다
   - D) 세 모드 모두 동일한 성능 특성을 가진다

<details>

<summary>정답 보기</summary>

**정답: B) nftables는 1.33에서 GA, IPVS는 1.35에서 deprecated(1.38 제거 목표), 기본값은 여전히 iptables**

**설명:**
nftables 모드는 1.29 alpha → 1.31 beta → **1.33 GA**로 성숙했고, O(1) 조회와 증분 규칙 갱신을 제공합니다(워커 노드에 커널 5.13+ 필요, AL2023은 충족). IPVS 모드는 **1.35(2025년 12월)에서 deprecated**되었고 1.38 제거가 목표이며 권장 대체는 nftables입니다. 다만 호환성을 위해 **기본값은 여전히 iptables**이므로 nftables 전환은 명시적 결정이 필요합니다. IPVS를 쓰고 있다면 이전 계획이 필요합니다.
</details>

6. Conntrack 포화 의심은 어떻게 검증해야 합니까?
   - A) 명확한 커널 패닉 — `dmesg`에서 즉시 확인
   - B) Conntrack count/max·insert/drop counter·kernel log를 연결하며 insert_failed만으로 포화를 확정하지 않는다
   - C) 모든 기존 연결이 즉시 끊김
   - D) CPU 사용률이 100%로 상승

<details>

<summary>정답 보기</summary>

**정답: B) Conntrack count/max·insert/drop counter·kernel log를 연결하며 insert_failed만으로 포화를 확정하지 않는다**

**설명:**
NAT 없는 트래픽에도 tracking이 적용될 수 있습니다. Headless Service DNS는 VIP DNAT를 피하지만 connection tracking을 본질적으로 우회하지는 않습니다.
</details>

7. EKS에서 conntrack 값을 조정할 때 주의할 점은?
   - A) 노드 부트스트랩의 sysctl 설정만으로 충분하다
   - B) EKS에 기본 존재하는 `kube-proxy-config` ConfigMap이 커맨드라인 인자보다 우선하므로, sysctl만 올려도 kube-proxy가 되돌릴 수 있다
   - C) conntrack은 조정할 수 없는 고정값이다
   - D) Pod의 `securityContext.sysctls`로 노드 전역 값을 바꿀 수 있다

<details>

<summary>정답 보기</summary>

**정답: B) EKS에 기본 존재하는 `kube-proxy-config` ConfigMap이 커맨드라인 인자보다 우선하므로, sysctl만 올려도 kube-proxy가 되돌릴 수 있다**

**설명:**
kube-proxy도 conntrack 값을 관리하며, EKS에는 `kube-proxy-config` ConfigMap이 기본으로 존재하고 이것이 커맨드라인 인자보다 우선합니다. 따라서 올바른 경로는 ConfigMap의 `conntrack.maxPerCore`·`conntrack.min`을 조정하고 kube-proxy DaemonSet을 재시작하는 것입니다. `maxPerCore`를 쓰는 이유는 절대값이 아니라 코어당 값이라 노드 크기가 달라도 비례 조정되기 때문입니다. D는 틀렸습니다 — `nf_conntrack_max`는 노드 전역이라 Pod 스펙으로 바꿀 수 없습니다.
</details>

8. overlayfs의 copy-up이 운영에 만드는 문제는?
   - A) 이미지 계층이 중복 저장되어 레지스트리 용량이 늘어난다
   - B) lowerdir의 파일을 수정하면 파일 전체가 upperdir로 복사되므로, 큰 파일의 작은 수정도 전체 복사 비용을 낸다
   - C) 컨테이너 시작 시간이 계층 수에 비례해 늘어난다
   - D) 읽기 성능이 계층 수에 비례해 저하된다

<details>

<summary>정답 보기</summary>

**정답: B) lowerdir의 파일을 수정하면 파일 전체가 upperdir로 복사되므로, 큰 파일의 작은 수정도 전체 복사 비용을 낸다**

**설명:**
overlayfs는 읽기 전용 lowerdir(이미지 계층)과 쓰기 가능 upperdir(변경분)을 합쳐 보여줍니다. lowerdir의 파일을 수정하려면 먼저 upperdir로 복사해야 하는데 이것이 **파일 전체 복사**입니다. 1GB 파일의 1바이트 수정에 1GB 복사가 일어납니다. 그래서 컨테이너 안에서 대용량 쓰기를 하면 노드 디스크(ephemeral storage)를 먹고, **쓰기가 많은 경로는 emptyDir이나 PVC 같은 볼륨으로 빼는 것**이 정석입니다.
</details>
