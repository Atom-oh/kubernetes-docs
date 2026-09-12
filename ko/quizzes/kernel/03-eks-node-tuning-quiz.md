# EKS 노드 커널 튜닝 퀴즈

이 퀴즈는 커널 파라미터 적용 경로, 커널 버전 전환, 근거 있는 튜닝에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 근거 없는 커널 튜닝이 만드는 문제 세 가지는?
   - A) 보안 취약점, 라이선스 위반, 지원 불가
   - B) 재현 불가능한 구성, 커널 업그레이드 시 파손, 커널 자동 조정 무력화
   - C) 네트워크 대역폭 감소, 디스크 용량 증가, 메모리 누수
   - D) Pod 스케줄링 실패, 이미지 풀 실패, 인증 실패

<details>

<summary>정답 보기</summary>

**정답: B) 재현 불가능한 구성, 커널 업그레이드 시 파손, 커널 자동 조정 무력화**

**설명:**
노드마다 값이 달라지면 장애 재현이 안 됩니다. 커널 버전 간에 튜너블의 이름과 위치가 바뀌므로(sysctl → debugfs 등) 6.1에서 유효했던 설정이 6.18에서 깨질 수 있습니다. 그리고 TCP 버퍼처럼 커널이 부하에 따라 자동 조정하는 값을 고정하면 그 자동 조정이 비활성화됩니다. 그래서 튜닝의 전제는 측정이며, 드롭 카운터로 증상을 특정한 뒤 그 지점만 건드려야 합니다.
</details>

2. AL2023의 커널 버전 전환에서 2026년 현재 알아야 할 사실은?
   - A) AL2023은 커널 6.1만 제공한다
   - B) 2026년 8월 17일부터 `al2023-ami-kernel-default` AMI의 기본 커널이 6.1에서 6.18로 변경되어, 노드 교체만으로도 커널이 바뀐다
   - C) 커널 버전은 EKS 컨트롤플레인 버전에 따라 자동 결정된다
   - D) AL2023은 커널 업그레이드를 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 2026년 8월 17일부터 `al2023-ami-kernel-default` AMI의 기본 커널이 6.1에서 6.18로 변경되어, 노드 교체만으로도 커널이 바뀐다**

**설명:**
AL2023은 2023년 3월 커널 6.1로 출시되었고, 2025년 4월에 6.12 지원이 추가되었으며, **2026년 8월 17일부터 기본 커널이 6.18로 변경**되었습니다. `kernel-default` AMI를 쓰면 오토스케일링·업그레이드·스팟 회수 같은 노드 교체만으로 커널이 바뀝니다. 특정 커널에 고정해야 하면 `al2023-ami-kernel-6.1-*` 같은 버전 지정 AMI를 명시적으로 써야 하고, 커널 전환은 Kubernetes 버전 업그레이드와 같은 무게로 다뤄야 합니다.
</details>

3. CPU throttling의 가장 흔한 근본 원인과 첫 대응은?
   - A) 노드 CPU 부족 — 인스턴스 타입 상향
   - B) 애플리케이션이 인식하는 CPU 수와 할당량의 불일치 — `GOMAXPROCS`, `-XX:ActiveProcessorCount` 등을 limit에 맞춤
   - C) 커널 스케줄러 버그 — 커널 업그레이드
   - D) cgroup v2 전환 문제 — v1으로 되돌림

<details>

<summary>정답 보기</summary>

**정답: B) 애플리케이션이 인식하는 CPU 수와 할당량의 불일치 — `GOMAXPROCS`, `-XX:ActiveProcessorCount` 등을 limit에 맞춤**

**설명:**
컨테이너 안의 런타임이 노드의 전체 코어 수를 보고 그만큼 스레드를 만들면, CPU limit의 할당량을 순식간에 소진합니다. 4개 스레드가 동시에 돌면 20ms 할당량이 실제 시간 5ms에 소진되고 나머지 95ms는 대기입니다. 그래서 첫 대응은 애플리케이션이 인식하는 CPU 수를 limit에 맞추는 것이고, 그 다음이 limit 상향, 그 다음이 극히 민감한 경우의 limit 제거 검토입니다.
</details>

4. 노드 안정성 확보에서 커널 튜닝보다 효과적인 것과 그 이유는?
   - A) Pod 수 제한 — 밀도를 낮추면 문제가 없다
   - B) kubelet의 리소스 예약과 축출 임계 — 예약이 부족하면 커널이나 kubelet이 OOM에 걸려 노드 전체가 NotReady가 되고, 축출이 커널 OOM보다 낫다
   - C) 노드 재시작 스케줄 — 주기적 재시작으로 메모리 정리
   - D) 이미지 크기 축소 — 디스크 여유 확보

<details>

<summary>정답 보기</summary>

**정답: B) kubelet의 리소스 예약과 축출 임계 — 예약이 부족하면 커널이나 kubelet이 OOM에 걸려 노드 전체가 NotReady가 되고, 축출이 커널 OOM보다 낫다**

**설명:**
`--system-reserved`와 `--kube-reserved`가 부족하면 Pod가 노드 메모리를 다 먹고 커널이나 kubelet 자체가 OOM에 걸립니다. 그러면 노드가 `NotReady`가 되고 그 위의 모든 Pod가 영향을 받아 개별 Pod OOM보다 훨씬 나쁜 결과가 됩니다. 축출은 Kubernetes가 통제된 방식으로 Pod를 옮기는 것이고 OOM killer는 커널이 프로세스를 갑자기 죽이는 것이므로, `--eviction-hard`를 적절히 설정해 커널 OOM 전에 Kubernetes가 개입하게 만드는 것이 목표입니다.
</details>

5. PSI(Pressure Stall Information)가 사용량 지표보다 나은 신호를 주는 이유는?
   - A) 더 정확한 사용량을 측정하기 때문
   - B) 사용량이 아니라 그 자원 때문에 지연된 시간의 비율을 알려주므로, 사용량 그래프가 평온한데도 회수·경합에 시간을 쓰는 상황이 보임
   - C) 커널이 아니라 하드웨어에서 수집하기 때문
   - D) 과거 데이터를 자동 보관하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 사용량이 아니라 그 자원 때문에 지연된 시간의 비율을 알려주므로, 사용량 그래프가 평온한데도 회수·경합에 시간을 쓰는 상황이 보임**

**설명:**
`memory.pressure`의 `some avg10`은 최근 10초간 최소 하나의 태스크가 그 자원 때문에 지연된 시간의 비율입니다. 메모리 사용량이 limit 아래로 평온하게 보이는데 이 값이 올라가고 있으면 page cache 회수에 시간을 쓰고 있다는 뜻이고, 이는 사용량 그래프만으로는 보이지 않습니다. cgroup v2에서 제공되며 노드 전체는 `/proc/pressure/*`, cgroup별은 `<cgroup>/memory.pressure`로 확인합니다.
</details>

6. 다음 중 "근거 있는 튜닝"의 대표 사례가 아닌 것은?
   - A) `vm.max_map_count` — OpenSearch 계열이 기본값에서 시작 실패
   - B) `net.core.somaxconn` — accept 큐 오버플로 카운터로 증거 확인 가능
   - C) `net.ipv4.tcp_rmem` / `tcp_wmem` — 기본값을 고정해 성능 향상
   - D) `net.ipv4.ip_local_port_range` — 출발지 포트 고갈이 연결 실패로 직접 나타남

<details>

<summary>정답 보기</summary>

**정답: C) `net.ipv4.tcp_rmem` / `tcp_wmem` — 기본값을 고정해 성능 향상**

**설명:**
`tcp_rmem`/`tcp_wmem`은 **건드리지 않는 것이 기본**입니다. 커널이 부하에 따라 자동 조정하고 있고, 값을 고정하면 그 자동 조정이 비활성화됩니다. BDP가 큰 장거리 경로에서 상한 조정을 검토할 수는 있지만 일반적인 튜닝 대상이 아닙니다. 반면 A·B·D는 모두 명확한 증상과 직접적인 증거 카운터가 있어 근거 있는 조정의 사례입니다 — `vm.max_map_count`는 시작 실패 로그, `somaxconn`은 `nstat`의 `TcpExtListenOverflows`, 포트 범위는 연결 실패입니다.
</details>

7. Pod의 `securityContext.sysctls`로 바꿀 수 없는 값은?
   - A) net namespace별로 설정 가능한 `net.*` 값 다수
   - B) `net.netfilter.nf_conntrack_max` — 노드 전역 값
   - C) Pod의 net namespace에 속한 TCP 관련 값
   - D) 위 모두 변경 가능

<details>

<summary>정답 보기</summary>

**정답: B) `net.netfilter.nf_conntrack_max` — 노드 전역 값**

**설명:**
`net.*` 중 상당수는 net namespace별로 설정 가능해 Pod `securityContext.sysctls`로 바꿀 수 있습니다. 반면 `vm.*`, `fs.*`, 그리고 `net.netfilter.nf_conntrack_max` 같은 일부 값은 노드 전역이라 Pod 스펙으로는 바꿀 수 없고 노드 부트스트랩이나 Bottlerocket 설정 경로를 써야 합니다. 또한 kubelet은 기본적으로 "안전하지 않은" sysctl을 거부하므로 필요하면 `--allowed-unsafe-sysctls`로 명시 허용해야 하고, 이것도 노드 설정입니다.
</details>

8. 커널 파라미터 변경을 관리하는 방법 중 장기적으로 가장 중요한 것은?
   - A) 최신 커널로 항상 업그레이드
   - B) 코드로 관리하고 변경 사유를 주석으로 남기며, 워크로드 성격별로 노드 그룹을 분리
   - C) 모든 노드에 동일한 튜닝 프로필 강제 적용
   - D) 변경 후 즉시 프로덕션 반영

<details>

<summary>정답 보기</summary>

**정답: B) 코드로 관리하고 변경 사유를 주석으로 남기며, 워크로드 성격별로 노드 그룹을 분리**

**설명:**
Karpenter `EC2NodeClass`, 시작 템플릿, Bottlerocket 설정 등으로 코드화하면 노드마다 값이 다른 상황을 막습니다. "왜 이 값인가"를 주석으로 남기지 않으면 6개월 뒤에 아무도 되돌리지 못합니다. 워크로드 성격이 다르면 튜닝도 달라야 하므로 한 프로필을 전체에 강요하지 않고 노드 그룹을 분리합니다. 여기에 커널 버전 고정·전환 계획, 적용 후 실제 값 검증(특히 conntrack), 변경 전후 동일 조건 측정이 더해집니다.
</details>
