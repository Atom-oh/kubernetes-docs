# Calico 고급 주제 퀴즈

> **관련 문서**: [Calico 고급 주제](../../../networking/calico/07-advanced-topics.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. Calico IPAM의 기본 IPv4 블록 크기는 얼마입니까?
   - A) /24 (256 IPs)
   - B) /26 (64 IPs)
   - C) /28 (16 IPs)
   - D) /30 (4 IPs)

<details>
<summary>정답 보기</summary>

**정답: B) /26 (64 IPs)**

**설명:**
IPv4 기본 /26에는 주소 64개가 있습니다. 모든 플랫폼에서 Pod 주소 64개가 사용 가능한 것은 아니며 Windows는 블록당 네 개를 예약합니다. IPv6 기본은 /122로 역시 주소 64개입니다. blockSize는 풀 생성 시 정하며 기존 풀에서 변경하지 못합니다.

</details>

2. IP 블록 어피니티(Block Affinity)의 의미는 무엇입니까?
   - A) IP 블록이 특정 Pod에 영구적으로 할당됨
   - B) IP 블록이 특정 노드에 우선적으로 할당되어 해당 노드의 Pod에 IP 제공
   - C) IP 블록이 특정 네임스페이스에만 사용됨
   - D) IP 블록이 클러스터 전체에서 공유됨

<details>
<summary>정답 보기</summary>

**정답: B) IP 블록이 특정 노드에 우선적으로 할당되어 해당 노드의 Pod에 IP 제공**

**설명:**
노드는 어피니티 블록을 우선 사용하지만 여러 블록을 가질 수 있고 허용된 차용에는 more-specific 경로가 필요할 수 있습니다. BlockAffinity가 Node.spec.podCIDR과 같거나 한 노드의 모든 Pod가 단일 접두사를 공유한다는 보장은 아닙니다.

</details>

3. Calico에서 WireGuard 암호화를 활성화하는 올바른 FelixConfiguration 설정은?
   - A) wireguardEnabled: true
   - B) encryptionEnabled: true
   - C) ipsecEnabled: true
   - D) tlsEnabled: true

<details>
<summary>정답 보기</summary>

**정답: A) wireguardEnabled: true**

**설명:**
wireguardEnabled는 지원되는 IPv4 경로를 활성화하고 IPv6는 wireguardEnabledV6로 별도 제어합니다. 양쪽 peer의 커널·네트워크 조건이 필요하며 공개 키 정보를 배포합니다. 같은 노드 트래픽이나 지원하지 않는 peer가 자동으로 암호화되는 것은 아닙니다.

</details>

4. WireGuard/IPsec 비교에서 올바른 설명은?
   - A) WireGuard가 모든 하드웨어에서 항상 빠름
   - B) 25초 keepalive가 identity 키 교체 간격임
   - C) WireGuard는 제한된 암호 설계를 사용하며 성능은 실제 구현·부하에서 평가
   - D) 프로토콜 이름만으로 FIPS 준수 판단

<details>
<summary>정답 보기</summary>

**정답: C) WireGuard는 제한된 암호 설계를 사용하며 성능은 실제 구현·부하에서 평가**

**설명:**
WireGuard는 암호 선택을 제한한 설계를 사용합니다. CPU·처리량·roaming·가속은 구현과 부하에 따라 다릅니다. 25초 keepalive는 NAT 상태 유지이며 키 로테이션이 아닙니다. 버전 없는 코드 줄 수나 검증되지 않은 성능 범위로 보편적인 순위를 정하지 않습니다.

</details>

5. 문서화된 Calico Enterprise Egress Gateway의 주요 사용 사례는 무엇입니까?
   - A) 클러스터로 들어오는 트래픽 로드밸런싱
   - B) 특정 Pod의 외부 통신을 고정 IP로 SNAT하여 방화벽 규칙 단순화
   - C) DNS 쿼리 캐싱
   - D) TLS 인증서 관리

<details>
<summary>정답 보기</summary>

**정답: B) 특정 Pod의 외부 통신을 고정 IP로 SNAT하여 방화벽 규칙 단순화**

**설명:**
Transit gateway Pod가 선택한 클라이언트 흐름을 SNAT하여 통제한 소스 주소 집합을 사용합니다. 외부에서 보이는 주소는 풀·upstream NAT와 가용성에 영향을 받습니다. NetworkPolicy Allow나 BGP serviceExternalIPs만으로 이 기능을 만들지 못하며 고정 IP가 규정 준수 전체를 보장하지 않습니다.

</details>

6. 현재 Calico Enterprise Federation에 대한 잘못된 설명은?
   - A) 원격 endpoint 정보를 로컬 정책 계산에 사용
   - B) 별도 controller가 원격 Service 정보를 읽음
   - C) 원격 네트워크 정책이 로컬 endpoint에 자동 복제·적용됨
   - D) Pod IP 도달성과 소스 보존을 별도로 확보해야 함

<details>
<summary>정답 보기</summary>

**정답: C) 원격 네트워크 정책이 로컬 endpoint에 자동 복제·적용됨**

**설명:**
Federated endpoint identity는 원격 정보를 로컬 정책 계산에 사용하며 정책 객체 자체를 복제하지 않습니다. Federated Services Controller는 원격 Kubernetes API를 읽습니다. Typha 기반 공유 Federation Controller나 자동 라우팅/애플리케이션 failover를 가정하지 마세요.

</details>

7. Calico의 Windows 컨테이너 지원 상태로 올바른 것은?
   - A) 지원하지 않음
   - B) 베타 지원
   - C) HNS로 지원하지만 버전·플랫폼·기능 제약이 있음
   - D) 실험적 기능만 지원

<details>
<summary>정답 보기</summary>

**정답: C) HNS로 지원하지만 버전·플랫폼·기능 제약이 있음**

**설명:**
현재 Windows 가이드는 IPv4 VXLAN 또는 지원되는 비캡슐화 BGP를 제공하지만 IPv6/dual stack, eBPF, WireGuard, HostEndpoint 정책과 Service 광고를 제외합니다. Operator HostProcess와 OS/container build, provider 조건을 함께 맞춰야 합니다. 지원 여부를 모든 기능의 완전 지원으로 해석하지 않습니다.

</details>

8. Calico Open Source 3.32에도 이미 제공되는 기능 묶음은?
   - A) 모든 환경에 자동 고정 egress와 SaaS 관리
   - B) 설정 없이 원격 정책을 인증·복제하는 기능
   - C) Pod 네트워킹, Tier, Whisker, staged policy
   - D) 계약 없는 24/7 기업 SLA

<details>
<summary>정답 보기</summary>

**정답: C) Pod 네트워킹, Tier, Whisker, staged policy**

**설명:**
Open Source 3.32는 Tier, Whisker/flow 가시성, staged policy와 Istio/Dikastes를 통한 HTTP 정책을 지원합니다. DNS 도메인 정책, 지원되는 gateway/federated identity·Service, 보고·지원 상품은 제품별 조건을 확인해야 합니다.

</details>

9. Tigera Operator 1.42.6이 집계한 노드 1,000개에서 계산하는 Typha 목표 수는?
   - A) 5개
   - B) 7개
   - C) 10개
   - D) 3개

<details>
<summary>정답 보기</summary>

**정답: B) 7개**

**설명:**
N>4에서 max(3, floor(N/200)+2)를 사용하므로 1,000개이면 7개입니다. N<=2는 1개, N<=4는 2개입니다. 구현의 집계·배치 조건이 있는 목표값이지 Typha 하나가 항상 200노드를 처리한다는 용량 보장이 아닙니다.

</details>

10. Calico IPAM에서 IPv6를 추가할 때 필요한 주소 풀은?
    - A) IPv6용 별도의 IPPool 생성
    - B) 특별한 설정 없이 자동 지원
    - C) IPv6 전용 Calico 버전 설치
    - D) Linux 커널 재컴파일

<details>
<summary>정답 보기</summary>

**정답: A) IPv6용 별도의 IPPool 생성**

**설명:**
IPv6 주소 범위의 풀을 만들며 dual stack에는 IPv4 풀도 필요합니다. Kubernetes/CNI/노드/underlay 조건을 함께 구성해야 합니다. ipv6Support는 Enabled가 아닌 boolean true이며 풀이나 flag만으로 기존 클러스터의 IP family를 바꾸지 못합니다.

</details>

11. IP 고갈 상태를 확인하는 calicoctl 명령어는?
    - A) calicoctl get ippool
    - B) calicoctl ipam show
    - C) calicoctl node status
    - D) calicoctl get workloadendpoint

<details>
<summary>정답 보기</summary>

**정답: B) calicoctl ipam show**

**설명:**
ipam show와 --show-blocks로 사용량·블록을 확인하고 BlockAffinity에서 노드 연결을 확인합니다. 풀 자격, 예약, affinity·host 제한 때문에 다른 곳에 여유 주소가 있어도 할당에 실패할 수 있습니다. 해제는 새 보고서와 실제 소유 상태를 검증한 후 수행해야 합니다.

</details>

12. 대규모 클러스터에서 etcd 대신 Kubernetes datastore를 선택해야 하는 이유가 아닌 것은?
    - A) 별도의 etcd 클러스터 운영 불필요
    - B) Kubernetes API를 통한 통합 관리
    - C) 전용 etcd보다 언제나 빠른 읽기 성능 보장
    - D) 운영 복잡성 감소

<details>
<summary>정답 보기</summary>

**정답: C) 전용 etcd보다 언제나 빠른 읽기 성능 보장**

**설명:**
Kubernetes datastore는 별도 Calico etcd 운영을 줄이지만 고정된 읽기 속도 순위를 보장하지 않습니다. 배포 기능·운영·복구·실제 측정으로 선택하며 현재 eBPF는 Kubernetes datastore가 필요합니다. 노드 수만으로 전용 etcd를 선택하지 않습니다.

</details>
