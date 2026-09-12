# Calico eBPF 데이터플레인 퀴즈

> **관련 문서**: [Calico eBPF 데이터플레인](../../../networking/calico/06-ebpf-dataplane.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. Calico 3.32 eBPF 가이드의 일반 Linux 최소 커널은 무엇입니까? (명시된 RHEL 백포트 예외 제외)
   - A) 4.9+
   - B) 5.0+
   - C) 5.10+
   - D) 6.0+

<details>
<summary>정답 보기</summary>

**정답: C) 5.10+**

**설명:**
일반 기준은 5.10이며 RHEL 8.4의 4.18.0-305 이상은 문서화된 백포트 예외입니다. eBPF Log 규칙은 5.16, 문서화된 QoS 대역폭 제어는 6.6/TCX가 필요합니다. OS·커널 이름만으로 전체 플랫폼 호환성을 보장하지 않습니다.

</details>

2. Calico eBPF 전환의 성능 향상은 어떻게 판단해야 합니까?
   - A) 5-10%
   - B) 실제 부하·설정에서 측정하며 보편적인 고정 비율은 없음
   - C) 50-70%
   - D) 100% 이상

<details>
<summary>정답 보기</summary>

**정답: B) 실제 부하·설정에서 측정하며 보편적인 고정 비율은 없음**

**설명:**
iptables와 eBPF는 모두 커널에서 패킷을 처리합니다. 차이는 트래픽 경로·규칙·conntrack·CPU/NIC·로그·부하에 좌우됩니다. 기존의 서로 다른 보고값은 원자료가 없으며 20–40% 향상이나 일정한 정책 비용을 보장하지 않습니다.

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
bpffs는 pin한 BPF 객체를 프로세스 사이에서 유지·공유하게 합니다. 영구 디스크 저장소는 아니므로 호스트 재부팅 후에도 객체가 자동 보존되는 것은 아닙니다. Calico가 필요한 프로그램·맵을 다시 구성해야 합니다.

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
BTF는 CO-RE relocation과 도구가 사용하는 타입 정보입니다. verifier의 안전성 검사와는 별개이며 모든 커널에서 바이너리가 동작한다고 보장하지 않습니다. Calico 릴리스의 기능 검사·객체 선택과 실제 노드 조건을 확인해야 합니다.

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
원격 backend 노드가 Kubernetes Service 요청을 처음 전달한 노드를 거치지 않고 응답할 수 있습니다. 소스 변환은 Calico가 처리하며 호환되는 fabric과 반환 경로가 필요합니다. 모든 외부 클라우드 로드 밸런서를 우회하거나 지원한다는 뜻은 아닙니다.

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
지원되는 TCP connect() 시점에 Service 목적지를 backend로 바꿉니다. Enabled 모드에는 UDP 소켓 hook도 포함할 수 있습니다. 해당 Service DNAT 경로를 줄이는 기능이며 모든 정책·라우팅·conntrack·다른 NAT를 제거하지는 않습니다. DSR과도 별도 기능입니다.

</details>

7. kube-proxy가 만든 iptables 규칙의 정리를 제어하는 Felix 필드는 무엇입니까?
   - A) bpfKubeProxyEnabled: true
   - B) bpfKubeProxyIptablesCleanupEnabled: true
   - C) kubeProxyReplacement: strict
   - D) bpfServiceMode: enabled

<details>
<summary>정답 보기</summary>

**정답: B) bpfKubeProxyIptablesCleanupEnabled: true**

**설명:**
bpfKubeProxyIptablesCleanupEnabled는 기존 kube-proxy 규칙 정리만 제어하며 Service 처리 활성화 스위치가 아닙니다. kube-proxy를 유지해야 하는 플랫폼은 cleanup을 false로 하고 health-server 충돌도 피해야 합니다. 삭제를 일반적인 대체 절차로 사용하지 마세요.

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
맵에는 route·NAT·conntrack·affinity와 프로그램/counter/IP-set 보조 데이터를 저장합니다. 해시·LRU 해시·LPM trie 등 유형이 다르며 정책 전체를 하나의 O(1) tuple→action map으로 처리하는 것은 아닙니다.

</details>

9. Native driver XDP와 TC eBPF 프로그램의 주요 차이점은?
   - A) XDP는 드라이버 레벨에서 패킷을 처리하고, TC는 네트워크 스택에서 처리
   - B) XDP는 egress만, TC는 ingress만 처리
   - C) XDP는 IPv6만, TC는 IPv4만 지원
   - D) XDP와 TC는 동일한 레벨에서 동작

<details>
<summary>정답 보기</summary>

**정답: A) XDP는 드라이버 레벨에서 패킷을 처리하고, TC는 네트워크 스택에서 처리**

**설명:**
Native XDP는 skb 할당 전 처리할 수 있고 TC는 skb 문맥을 사용합니다. Generic XDP에는 이미 skb가 있으며 더 뒤에서 실행됩니다. driver·하드웨어·프로그램 지원에 따라 달라지므로 항상 더 빠르다고 보장하지 않습니다.

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
Felix 필드는 bpfEnabled: true이며 독립 manifest 설치에서 사용합니다. Operator 설치는 Installation.spec.calicoNetwork.linuxDataplane: BPF를 통해 전환합니다. 설치 소유권·직접 API 접근·kube-proxy 조정·클러스터 전환 조건을 유지해야 합니다.

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
원격 backend의 Tunnel 모드는 요청·응답이 ingress 노드/터널 경로를 사용하고 DSR은 요청을 터널링한 뒤 응답을 직접 반환합니다. 두 모드 모두 VXLAN·MTU를 고려해야 하며 DSR에는 소스 검증·외부 로드 밸런서 경로 제약도 있습니다.

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
bpftool은 실제 BPF program/map ID와 상태를 조회합니다. node 이미지의 Calico 전용 도구는 calico-node -bpf로 실행하며 help 하위 명령을 사용합니다. policy dump에는 인터페이스와 hook을 모두 지정하고 단순 목록만으로 통신 성공을 판단하지 마세요.

</details>
