# Calico eBPF 데이터플레인 퀴즈

> **관련 문서**: [Calico eBPF 데이터플레인](../../../networking/calico/06-ebpf-dataplane.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. Calico eBPF 모드를 사용하기 위한 최소 Linux 커널 버전은 무엇입니까?
   - A) 4.9+
   - B) 5.0+
   - C) 5.3+ (권장 5.8+)
   - D) 6.0+

<details>
<summary>정답 보기</summary>

**정답: C) 5.3+ (권장 5.8+)**

**설명:**
Calico eBPF 모드는 Linux 커널 5.3 이상에서 동작하며, 최적의 성능과 기능을 위해 5.8 이상을 권장합니다. 5.8 버전부터 추가된 eBPF 기능들이 Calico의 고급 기능을 더 잘 지원합니다.

</details>

2. eBPF 모드가 iptables 모드 대비 제공하는 처리량 향상은 대략 얼마입니까?
   - A) 5-10%
   - B) 20-40%
   - C) 50-70%
   - D) 100% 이상

<details>
<summary>정답 보기</summary>

**정답: B) 20-40%**

**설명:**
eBPF 모드는 iptables 모드 대비 처리량이 약 20-40% 향상되고, 지연 시간은 20-30% 감소합니다. 이는 eBPF가 커널 내에서 직접 패킷을 처리하여 컨텍스트 스위칭과 규칙 검색 오버헤드를 줄이기 때문입니다.

</details>

3. eBPF 모드를 사용하려면 호스트 시스템에서 어떤 파일시스템이 마운트되어 있어야 합니까?
   - A) /sys/fs/cgroup
   - B) /sys/fs/bpf
   - C) /proc/sys/net
   - D) /dev/shm

<details>
<summary>정답 보기</summary>

**정답: B) /sys/fs/bpf**

**설명:**
eBPF 프로그램과 맵을 저장하고 공유하기 위해 `/sys/fs/bpf` 파일시스템이 마운트되어 있어야 합니다. 이 BPF 파일시스템은 eBPF 오브젝트들을 영구적으로 저장하고 여러 프로그램 간에 공유할 수 있게 합니다.

</details>

4. BTF(BPF Type Format)의 주요 역할은 무엇입니까?
   - A) 네트워크 패킷 암호화
   - B) eBPF 프로그램의 타입 정보 제공 및 커널 구조체 접근
   - C) BGP 라우팅 테이블 관리
   - D) IP 주소 자동 할당

<details>
<summary>정답 보기</summary>

**정답: B) eBPF 프로그램의 타입 정보 제공 및 커널 구조체 접근**

**설명:**
BTF(BPF Type Format)는 eBPF 프로그램이 커널 데이터 구조에 안전하게 접근할 수 있도록 타입 정보를 제공합니다. 이를 통해 CO-RE(Compile Once - Run Everywhere) 기능이 가능해져, 한 번 컴파일된 eBPF 프로그램이 다양한 커널 버전에서 동작할 수 있습니다.

</details>

5. Direct Server Return(DSR)의 주요 장점은 무엇입니까?
   - A) 모든 트래픽을 암호화함
   - B) 응답 트래픽이 로드밸런서를 거치지 않고 클라이언트로 직접 반환됨
   - C) DNS 쿼리 속도 향상
   - D) Pod IP 주소 절약

<details>
<summary>정답 보기</summary>

**정답: B) 응답 트래픽이 로드밸런서를 거치지 않고 클라이언트로 직접 반환됨**

**설명:**
DSR(Direct Server Return)은 서버의 응답 트래픽이 로드밸런서를 거치지 않고 클라이언트에게 직접 전송되는 방식입니다. 이를 통해 로드밸런서의 부하를 줄이고, 지연 시간을 감소시키며, 전체 네트워크 대역폭을 절약할 수 있습니다.

</details>

6. Connect-time 로드밸런싱의 동작 방식으로 올바른 것은?
   - A) 패킷이 도착할 때마다 목적지를 결정
   - B) TCP 연결 설정 시점에 목적지 Pod를 결정하여 이후 모든 패킷을 동일 Pod로 전송
   - C) DNS 조회 시점에 목적지 결정
   - D) 매 초마다 목적지를 재계산

<details>
<summary>정답 보기</summary>

**정답: B) TCP 연결 설정 시점에 목적지 Pod를 결정하여 이후 모든 패킷을 동일 Pod로 전송**

**설명:**
Connect-time 로드밸런싱은 TCP 연결이 설정되는 시점(connect 시스템 콜)에 목적지 Pod를 결정합니다. 한 번 결정된 목적지는 해당 연결의 모든 패킷에 적용되어, NAT 테이블 조회 없이 효율적인 패킷 처리가 가능합니다.

</details>

7. eBPF 모드에서 kube-proxy를 대체하려면 FelixConfiguration에서 어떤 설정을 활성화해야 합니까?
   - A) bpfKubeProxyEnabled: true
   - B) bpfKubeProxyIptablesCleanupEnabled: true
   - C) kubeProxyReplacement: strict
   - D) bpfServiceMode: enabled

<details>
<summary>정답 보기</summary>

**정답: B) bpfKubeProxyIptablesCleanupEnabled: true**

**설명:**
`bpfKubeProxyIptablesCleanupEnabled: true` 설정은 kube-proxy가 생성한 iptables 규칙을 정리하고 eBPF가 Service 처리를 담당하도록 합니다. 이 설정과 함께 kube-proxy DaemonSet을 비활성화하거나 삭제해야 완전한 대체가 이루어집니다.

</details>

8. BPF 맵(Map)의 주요 역할은 무엇입니까?
   - A) 네트워크 패킷 캡처 및 저장
   - B) eBPF 프로그램과 사용자 공간 간 데이터 공유 및 상태 저장
   - C) BGP 라우팅 정보 교환
   - D) TLS 인증서 저장

<details>
<summary>정답 보기</summary>

**정답: B) eBPF 프로그램과 사용자 공간 간 데이터 공유 및 상태 저장**

**설명:**
BPF 맵은 키-값 저장소로, eBPF 프로그램이 상태를 저장하고 사용자 공간 프로그램과 데이터를 공유하는 데 사용됩니다. Calico에서는 연결 추적, 정책 규칙, Service 엔드포인트 정보 등을 BPF 맵에 저장하여 빠른 조회가 가능합니다.

</details>

9. XDP(eXpress Data Path)와 TC(Traffic Control) eBPF 프로그램의 주요 차이점은?
   - A) XDP는 드라이버 레벨에서 패킷을 처리하고, TC는 네트워크 스택에서 처리
   - B) XDP는 egress만, TC는 ingress만 처리
   - C) XDP는 IPv6만, TC는 IPv4만 지원
   - D) XDP와 TC는 동일한 레벨에서 동작

<details>
<summary>정답 보기</summary>

**정답: A) XDP는 드라이버 레벨에서 패킷을 처리하고, TC는 네트워크 스택에서 처리**

**설명:**
XDP는 네트워크 드라이버 레벨에서 패킷이 커널 네트워크 스택에 도달하기 전에 처리하여 최고의 성능을 제공합니다. TC(Traffic Control) eBPF는 네트워크 스택 내에서 동작하며, 더 많은 패킷 메타데이터에 접근할 수 있지만 XDP보다는 약간 느립니다.

</details>

10. FelixConfiguration에서 eBPF를 활성화하는 올바른 설정은?
    - A) ebpfEnabled: true
    - B) bpfEnabled: true
    - C) dataplane: ebpf
    - D) linuxDataplane: BPF

<details>
<summary>정답 보기</summary>

**정답: B) bpfEnabled: true**

**설명:**
FelixConfiguration에서 `bpfEnabled: true`를 설정하면 eBPF 데이터플레인이 활성화됩니다. 추가로 `bpfDataIfacePattern`으로 데이터 인터페이스 패턴을 지정하고, `bpfExternalServiceMode`로 외부 서비스 모드를 설정할 수 있습니다.

</details>

11. bpfExternalServiceMode 옵션에서 "DSR"과 "Tunnel"의 차이점은?
    - A) DSR은 응답이 직접 반환되고, Tunnel은 요청과 동일한 경로로 반환
    - B) DSR은 IPv6 전용, Tunnel은 IPv4 전용
    - C) DSR은 TCP만, Tunnel은 UDP만 지원
    - D) DSR과 Tunnel은 동일한 동작

<details>
<summary>정답 보기</summary>

**정답: A) DSR은 응답이 직접 반환되고, Tunnel은 요청과 동일한 경로로 반환**

**설명:**
`bpfExternalServiceMode: DSR`은 응답 트래픽이 원래 노드를 거치지 않고 클라이언트로 직접 반환됩니다. `Tunnel` 모드는 응답이 요청과 동일한 경로(원래 노드)를 통해 반환됩니다. DSR은 성능이 더 좋지만 일부 네트워크 환경에서 호환성 문제가 있을 수 있습니다.

</details>

12. eBPF 프로그램 디버깅에 사용되는 도구로 올바른 것은?
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables -L

<details>
<summary>정답 보기</summary>

**정답: B) bpftool**

**설명:**
`bpftool`은 eBPF 프로그램과 맵을 검사하고 디버깅하는 공식 도구입니다. `bpftool prog list`로 로드된 프로그램을 확인하고, `bpftool map dump`로 맵 내용을 확인할 수 있습니다. Calico는 추가로 `calico-bpf` 명령어를 제공하여 Calico 특화 eBPF 정보를 조회할 수 있습니다.

</details>
