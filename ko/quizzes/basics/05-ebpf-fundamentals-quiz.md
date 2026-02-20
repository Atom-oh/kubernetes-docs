# eBPF 기초 퀴즈

> **지원 버전**: Linux Kernel 4.18+, Kubernetes 1.25+
> **마지막 업데이트**: 2025년 2월

이 퀴즈는 eBPF(extended Berkeley Packet Filter)의 기본 개념부터 Kubernetes 환경에서의 활용까지 전반적인 이해도를 테스트합니다.

## 객관식 문제

1. eBPF 검증기(Verifier)가 확인하지 않는 항목은 무엇인가요?
   - A) 무한 루프 없음
   - B) 범위를 벗어난 메모리 접근 없음
   - C) 프로그램의 실행 속도
   - D) 초기화되지 않은 변수 사용 없음

<details>
<summary>정답 보기</summary>

**정답: C) 프로그램의 실행 속도**

**설명:**
eBPF 검증기는 프로그램의 안전성을 보장하기 위해 무한 루프 없음(DAG 구조 확인), 범위를 벗어난 메모리 접근 없음, 초기화되지 않은 변수 사용 없음, 올바른 헬퍼 함수 호출, 프로그램 종료 보장 등을 확인합니다. 프로그램의 실행 속도는 검증기의 검증 항목이 아닙니다.

</details>

2. XDP(eXpress Data Path) 프로그램의 반환 값 중 패킷을 같은 NIC로 다시 전송하는 것은 무엇인가요?
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>정답 보기</summary>

**정답: C) XDP_TX**

**설명:**
XDP 프로그램의 반환 값은 다음과 같은 의미를 가집니다:
- `XDP_DROP`: 패킷 드롭
- `XDP_PASS`: 커널 스택으로 전달
- `XDP_TX`: 같은 NIC로 패킷 반환
- `XDP_REDIRECT`: 다른 인터페이스로 전달
- `XDP_ABORTED`: 에러 처리

XDP_TX는 패킷을 수신한 네트워크 인터페이스로 다시 전송할 때 사용됩니다.

</details>

3. eBPF 맵(Maps)의 주요 역할이 아닌 것은 무엇인가요?
   - A) 커널과 사용자 공간 간 데이터 공유
   - B) 상태 저장
   - C) eBPF 프로그램 컴파일
   - D) 이벤트 데이터 전송

<details>
<summary>정답 보기</summary>

**정답: C) eBPF 프로그램 컴파일**

**설명:**
eBPF 맵은 커널과 사용자 공간 간 데이터를 공유하고 상태를 저장하는 데이터 구조입니다. 맵은 이벤트 데이터 전송(PERF_EVENT_ARRAY, RINGBUF), 키-값 저장(HASH), 통계 수집(PERCPU_ARRAY) 등에 사용됩니다. eBPF 프로그램 컴파일은 Clang/LLVM이 담당하며 맵의 역할이 아닙니다.

</details>

4. Cilium이 kube-proxy를 대체할 때 eBPF가 제공하는 주요 이점은 무엇인가요?
   - A) 서비스 수에 비례하는 O(n) 성능
   - B) iptables 규칙 평가 필요
   - C) 맵 조회를 통한 O(1) 성능
   - D) Netfilter 사용

<details>
<summary>정답 보기</summary>

**정답: C) 맵 조회를 통한 O(1) 성능**

**설명:**
기존 kube-proxy(iptables 모드)는 서비스 수가 증가하면 O(n)으로 성능이 저하됩니다. Cilium은 eBPF 맵을 사용하여 O(1)의 일정한 조회 성능을 제공합니다. 이를 통해 연결 설정 시간, CPU 사용량, 초당 연결 수 등 모든 측면에서 크게 향상된 성능을 제공합니다.

</details>

5. bpftrace의 주요 용도는 무엇인가요?
   - A) eBPF 프로그램을 C로 컴파일
   - B) 커널 모듈 로드
   - C) DTrace 스타일의 고수준 추적
   - D) 컨테이너 이미지 빌드

<details>
<summary>정답 보기</summary>

**정답: C) DTrace 스타일의 고수준 추적**

**설명:**
bpftrace는 DTrace 스타일의 고수준 추적 언어로, 간단한 원라이너 명령으로 시스템을 추적할 수 있습니다. 예를 들어 시스템 콜 카운트, 프로세스별 읽기 바이트 수, 파일 열기 추적, TCP 연결 추적 등을 쉽게 수행할 수 있습니다.

</details>

6. Tetragon의 TracingPolicy에서 악의적인 파일 접근 시 프로세스를 즉시 종료시키는 액션은 무엇인가요?
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>정답 보기</summary>

**정답: B) action: Sigkill**

**설명:**
Tetragon의 TracingPolicy에서 `matchActions`의 `action: Sigkill`은 정책에 일치하는 이벤트 발생 시 해당 프로세스를 SIGKILL 신호로 즉시 종료시킵니다. 이는 민감한 파일 접근이나 악의적인 네트워크 연결을 실시간으로 차단하는 데 사용됩니다.

</details>

7. Hubble의 주요 기능이 아닌 것은 무엇인가요?
   - A) 네트워크 플로우 관찰
   - B) DNS 쿼리 추적
   - C) eBPF 프로그램 컴파일
   - D) 정책 결정 모니터링

<details>
<summary>정답 보기</summary>

**정답: C) eBPF 프로그램 컴파일**

**설명:**
Hubble은 Cilium에 내장된 네트워크 관찰성 플랫폼으로, 네트워크 플로우, DNS 쿼리, HTTP 요청, 정책 결정 등을 수집하고 모니터링합니다. Hubble은 관찰성 도구이며 eBPF 프로그램 컴파일 기능은 제공하지 않습니다.

</details>

8. CO-RE(Compile Once, Run Everywhere)가 해결하는 문제는 무엇인가요?
   - A) eBPF 프로그램의 실행 속도 향상
   - B) 다양한 커널 버전에서의 이식성
   - C) 메모리 사용량 감소
   - D) 네트워크 지연 시간 감소

<details>
<summary>정답 보기</summary>

**정답: B) 다양한 커널 버전에서의 이식성**

**설명:**
CO-RE는 libbpf와 BTF(BPF Type Format)를 활용하여 한 번 컴파일된 eBPF 프로그램을 다양한 커널 버전에서 실행할 수 있게 합니다. 이를 통해 커널 헤더 의존성이 감소하고 구조체 재배치가 자동으로 처리되어 커널 버전별 재컴파일이 필요 없습니다.

</details>

9. Falco가 eBPF를 사용하여 탐지하는 것은 무엇인가요?
   - A) 네트워크 대역폭 사용량
   - B) 런타임 이상 동작
   - C) 디스크 용량
   - D) CPU 온도

<details>
<summary>정답 보기</summary>

**정답: B) 런타임 이상 동작**

**설명:**
Falco는 CNCF 프로젝트로, eBPF를 사용하여 런타임 이상 동작을 탐지합니다. 민감한 파일 읽기, 컨테이너에서 셸 실행, 권한 상승 시도 등의 보안 위협을 규칙 기반으로 탐지하고 경고합니다.

</details>

10. eBPF 프로그램의 스택 크기 제한은 얼마인가요?
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>정답 보기</summary>

**정답: C) 512 bytes**

**설명:**
eBPF 프로그램은 512 bytes의 스택 크기 제한이 있습니다. 이 제한을 우회하려면 PERCPU_ARRAY와 같은 맵을 사용하여 큰 버퍼를 할당해야 합니다. 이 제한은 커널 안전성을 보장하기 위한 것입니다.

</details>

## 단답형 문제

11. eBPF 바이트코드를 네이티브 머신 코드로 변환하는 컴파일러의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: JIT 컴파일러 (Just-In-Time 컴파일러)**

**설명:**
JIT 컴파일러는 eBPF 바이트코드를 네이티브 머신 코드로 변환합니다. 이를 통해 인터프리터 대비 4~5배의 성능 향상을 얻을 수 있으며, 아키텍처별 최적화가 적용됩니다. `/proc/sys/net/core/bpf_jit_enable`을 1로 설정하여 활성화할 수 있습니다.

</details>

12. 커널 함수 호출을 동적으로 추적하는 eBPF 프로그램 유형의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: Kprobes (또는 Kprobe)**

**설명:**
Kprobes는 커널 함수 호출을 동적으로 추적하는 eBPF 프로그램 유형입니다. 사용자 공간의 함수를 추적하는 Uprobes와 달리, Kprobes는 커널 내부의 함수를 추적합니다. 예를 들어 `tcp_connect` 함수를 추적하여 TCP 연결 정보를 수집할 수 있습니다.

</details>

13. Cilium에 내장된 네트워크 관찰성 플랫폼의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: Hubble**

**설명:**
Hubble은 Cilium에 내장된 네트워크 관찰성 플랫폼으로, eBPF 데이터플레인에서 네트워크 플로우, DNS 쿼리, HTTP 요청, 정책 결정 등의 데이터를 수집합니다. Hubble CLI, Hubble UI, Hubble Relay를 통해 클러스터의 네트워크 트래픽을 실시간으로 관찰할 수 있습니다.

</details>

14. eBPF 프로그램을 로드하기 위해 필요한 Linux 권한(capability)은 무엇인가요? (커널 5.8 이상)

<details>
<summary>정답 보기</summary>

**정답: CAP_BPF**

**설명:**
커널 5.8 이상에서는 eBPF 프로그램을 로드하기 위해 `CAP_BPF` 권한이 필요합니다. 이전 버전에서는 `CAP_SYS_ADMIN`이 필요했습니다. 추가로 성능 모니터링 이벤트 연결에는 `CAP_PERFMON`, XDP/TC 프로그램 연결에는 `CAP_NET_ADMIN`이 필요합니다.

</details>

15. 컨테이너의 에너지 소비를 eBPF로 모니터링하는 CNCF 프로젝트의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: Kepler (Kubernetes-based Efficient Power Level Exporter)**

**설명:**
Kepler는 eBPF를 사용하여 컨테이너의 에너지 소비를 모니터링하는 프로젝트입니다. `kepler_container_joules_total`(컨테이너별 에너지 소비), `kepler_container_gpu_joules_total`(GPU 에너지 소비) 등의 메트릭을 Prometheus 형식으로 제공합니다.

</details>

## 실습 문제

16. bpftool을 사용하여 현재 시스템에 로드된 eBPF 프로그램 목록을 확인하고, 특정 프로그램의 상세 정보를 조회하는 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```bash
# 로드된 eBPF 프로그램 목록 확인
sudo bpftool prog list

# 특정 프로그램(ID: 123)의 상세 정보 조회
sudo bpftool prog show id 123

# 프로그램의 바이트코드 덤프
sudo bpftool prog dump xlated id 123

# JIT 컴파일된 코드 덤프
sudo bpftool prog dump jited id 123
```

**설명:**
`bpftool prog list`는 현재 로드된 모든 eBPF 프로그램의 목록을 표시합니다. 각 프로그램의 ID, 유형, 이름, 연결된 위치 등을 확인할 수 있습니다. `bpftool prog show id <ID>`로 특정 프로그램의 상세 정보를 조회하고, `dump xlated`와 `dump jited`로 바이트코드와 JIT 컴파일된 네이티브 코드를 확인할 수 있습니다.

</details>

17. bpftrace를 사용하여 시스템의 모든 프로세스에서 발생하는 TCP 연결을 실시간으로 추적하는 원라이너 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```bash
# TCP 연결 추적 (방법 1: kprobe 사용)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP 연결 추적 (방법 2: tracepoint 사용, 더 상세한 정보)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# 프로세스별 TCP 연결 수 카운트
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**설명:**
bpftrace는 DTrace 스타일의 고수준 추적 언어로, 간단한 원라이너로 시스템을 추적할 수 있습니다. `kprobe:tcp_connect`는 커널의 `tcp_connect` 함수가 호출될 때 트리거됩니다. `comm`은 프로세스 이름, `pid`는 프로세스 ID를 나타냅니다. tracepoint를 사용하면 소스/목적지 IP 주소와 포트 정보도 얻을 수 있습니다.

</details>

18. Hubble CLI를 사용하여 특정 네임스페이스의 드롭된 패킷만 필터링하여 관찰하는 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```bash
# 특정 네임스페이스의 드롭된 패킷 관찰
hubble observe --namespace production --verdict DROPPED

# 실시간 스트리밍으로 드롭된 패킷 관찰
hubble observe --namespace production --verdict DROPPED -f

# 드롭된 패킷의 상세 정보를 JSON으로 출력
hubble observe --namespace production --verdict DROPPED -o json

# 특정 Pod에서 드롭된 패킷 관찰
hubble observe --from-pod production/frontend --verdict DROPPED
```

**설명:**
Hubble은 Cilium에 내장된 네트워크 관찰성 도구입니다. `--namespace` 옵션으로 특정 네임스페이스를, `--verdict DROPPED`로 드롭된 패킷만 필터링합니다. `-f` 옵션은 실시간 스트리밍을, `-o json`은 JSON 형식 출력을 제공합니다. 드롭된 패킷을 분석하면 네트워크 정책 문제나 설정 오류를 진단할 수 있습니다.

</details>

## 심화 문제

19. eBPF가 커널 모듈 대비 가지는 주요 장점 3가지를 설명하고, 각각이 Kubernetes 환경에서 어떤 이점을 제공하는지 구체적으로 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

eBPF가 커널 모듈 대비 가지는 주요 장점과 Kubernetes 환경에서의 이점:

**1. 안전성 (검증기를 통한 안전성 보장)**
- **장점**: eBPF 검증기가 프로그램 로드 전에 무한 루프, 메모리 접근 위반, 초기화되지 않은 변수 등을 검사하여 커널 크래시를 방지합니다.
- **Kubernetes 이점**: 프로덕션 클러스터에서 CNI 플러그인(Cilium)이나 보안 도구(Tetragon, Falco)가 안전하게 실행됩니다. 커널 모듈과 달리 버그가 있어도 시스템 전체가 다운되지 않아 고가용성을 유지할 수 있습니다.

**2. 이식성 (CO-RE를 통한 커널 버전 독립성)**
- **장점**: CO-RE(Compile Once, Run Everywhere)와 BTF를 사용하면 한 번 컴파일된 eBPF 프로그램이 다양한 커널 버전에서 실행됩니다. 커널 버전별 재컴파일이 필요 없습니다.
- **Kubernetes 이점**: 이기종 노드 환경(다른 커널 버전의 노드들)에서도 동일한 네트워킹 및 보안 솔루션을 배포할 수 있습니다. 클러스터 업그레이드나 노드 추가 시 호환성 문제가 크게 감소합니다.

**3. 동적 로딩 (재부팅 없는 프로그램 로드/언로드)**
- **장점**: eBPF 프로그램은 시스템 재부팅 없이 동적으로 로드하고 언로드할 수 있습니다. 런타임에 기능을 추가하거나 변경할 수 있습니다.
- **Kubernetes 이점**: 네트워크 정책, 보안 규칙, 관찰성 설정을 노드 재시작 없이 즉시 적용할 수 있습니다. Cilium NetworkPolicy나 Tetragon TracingPolicy 변경이 실시간으로 반영되어 운영 중단 없이 보안 강화가 가능합니다.

**추가 장점:**
- **성능**: JIT 컴파일로 네이티브 코드 수준의 성능을 제공하여 kube-proxy 대체 시 O(1) 서비스 조회가 가능합니다.
- **개발 난이도**: 커널 모듈 개발보다 상대적으로 쉬워 빠른 기능 개발과 배포가 가능합니다.

</details>

20. Kubernetes 클러스터에서 eBPF 기반 보안 솔루션(Tetragon 또는 Falco)을 사용하여 컨테이너 내 민감한 파일 접근을 탐지하고 차단하는 방안을 설계하세요. TracingPolicy 또는 Falco 규칙 예시를 포함하여 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**eBPF 기반 민감한 파일 접근 보안 설계**

**1. 보안 요구사항 정의**
- 탐지 대상: `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/var/run/secrets/`(Kubernetes 시크릿)
- 대응 방안: 탐지 시 경고, 심각한 경우 프로세스 종료

**2. Tetragon TracingPolicy 구현**

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-protection
spec:
  kprobes:
    # 민감한 파일 열기 모니터링
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        # Kubernetes 시크릿 접근 탐지 및 로깅
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /var/run/secrets/kubernetes.io/
          matchActions:
            - action: Post  # 이벤트 로깅

        # 시스템 인증 파일 접근 차단
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/shadow
                - /etc/sudoers
          matchNamespaces:
            - namespace: default
              operator: In
          matchActions:
            - action: Sigkill  # 프로세스 즉시 종료
```

**3. Falco 규칙 구현**

```yaml
# /etc/falco/rules.d/sensitive-files.yaml
- rule: Read Kubernetes Secrets
  desc: Detect reading of Kubernetes secret files in containers
  condition: >
    open_read and
    container and
    (fd.name startswith /var/run/secrets/kubernetes.io/ or
     fd.name startswith /etc/shadow or
     fd.name startswith /etc/sudoers) and
    not proc.name in (kubelet, containerd)
  output: >
    Sensitive file access detected
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name namespace=%k8s.ns.name
     pod=%k8s.pod.name)
  priority: WARNING
  tags: [security, filesystem]

- rule: Write to Sensitive System Files
  desc: Detect writing to sensitive system files
  condition: >
    open_write and
    container and
    fd.name in (/etc/passwd, /etc/shadow, /etc/sudoers)
  output: >
    Attempt to modify sensitive file
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name)
  priority: CRITICAL
  tags: [security, filesystem]
```

**4. 배포 및 모니터링**

```bash
# Tetragon 설치 및 정책 적용
helm install tetragon cilium/tetragon -n kube-system
kubectl apply -f sensitive-file-protection.yaml

# 이벤트 모니터링
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon \
  -c export-stdout -f | tetra getevents -o compact

# Falco 설치 (eBPF 드라이버)
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf

# Falco 알림 확인
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

**5. 아키텍처 설명**

```
┌─────────────────────────────────────────────────┐
│                  Kubernetes 클러스터              │
│  ┌─────────────────┐    ┌─────────────────┐    │
│  │   Application   │    │   Application   │    │
│  │      Pod        │    │      Pod        │    │
│  └────────┬────────┘    └────────┬────────┘    │
│           │                      │             │
│  ┌────────▼──────────────────────▼────────┐   │
│  │              eBPF 계층                  │   │
│  │  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Tetragon    │  │  Falco      │     │   │
│  │  │ TracingPol. │  │  Rules      │     │   │
│  │  └──────┬──────┘  └──────┬──────┘     │   │
│  │         │                 │            │   │
│  │         ▼                 ▼            │   │
│  │   [파일 접근 이벤트 캡처]              │   │
│  └────────────────────────────────────────┘   │
│                      │                         │
│  ┌───────────────────▼───────────────────┐   │
│  │           보안 대응                    │   │
│  │  • 이벤트 로깅 (Post)                 │   │
│  │  • 프로세스 종료 (Sigkill)            │   │
│  │  • SIEM 알림 전송                     │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

이 설계는 eBPF의 커널 레벨 가시성을 활용하여 애플리케이션 수정 없이 민감한 파일 접근을 실시간으로 탐지하고 대응할 수 있습니다.

</details>

---

[학습 자료로 돌아가기](../../basics/05-ebpf-fundamentals.md) | [다음 퀴즈: 컨테이너 기술](./02-container-technology-quiz.md)
