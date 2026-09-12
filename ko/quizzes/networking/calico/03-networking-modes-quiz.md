# Calico 네트워킹 모드 퀴즈

> **관련 문서**: [Calico 네트워킹 모드](../../../networking/calico/03-networking-modes.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. 옵션 없는 외부 IPv4 헤더를 사용하는 Calico IPIP의 헤더 오버헤드는?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>정답 보기</summary>

**정답: B) 20 bytes**

**설명:**
옵션 없는 외부 IPv4 헤더가 20바이트를 추가합니다. Calico IPIP는 IPv4 전용입니다. 헤더가 작다는 사실만으로 모든 NIC·커널·부하에서 지연이나 처리량이 더 좋다고 입증할 수는 없습니다.

</details>

2. 추가 내부 VLAN 태그가 없는 외부 IPv4 VXLAN이 Pod IP 패킷에 더하는 오버헤드는?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>정답 보기</summary>

**정답: C) 50 bytes**

**설명:**
외부 IPv4 20 + UDP 8 + VXLAN 8 + 내부 Ethernet 14 = 50바이트입니다. 외부 Ethernet은 언더레이 IP MTU 밖에 있습니다. 외부 IPv6이면 오버헤드는 70바이트이며 TCP와 UDP의 내부 전송 헤더 크기도 다릅니다.

</details>

3. CrossSubnet 모드의 동작 방식으로 올바른 것은?
   - A) 항상 캡슐화 사용
   - B) 항상 직접 라우팅 사용
   - C) 다른 서브넷만 캡슐화, 같은 서브넷은 직접 라우팅
   - D) 같은 서브넷만 캡슐화, 다른 서브넷은 직접 라우팅

<details>
<summary>정답 보기</summary>

**정답: C) 다른 서브넷만 캡슐화, 같은 서브넷은 직접 라우팅**

**설명:**
관련 노드 주소와 설정된 서브넷 마스크로 판단합니다. 같은 서브넷은 비캡슐화할 수 있고 다른 서브넷은 IPIP·VXLAN을 사용합니다. AZ·리전 감지나 사이트 간 연결 생성 기능이 아니며 같은 AZ 안의 다른 서브넷도 캡슐화 대상이 될 수 있습니다.

</details>

4. Direct (Unencapsulated) 모드를 사용하기 위한 요구 사항은?
   - A) VXLAN 지원 네트워크
   - B) Pod CIDR를 라우팅할 수 있는 네트워크 인프라
   - C) AWS VPC CNI
   - D) 특별한 요구 사항 없음

<details>
<summary>정답 보기</summary>

**정답: B) Pod CIDR를 라우팅할 수 있는 네트워크 인프라**

**설명:**
언더레이와 반환 경로가 Pod 주소를 라우팅해야 합니다. BGP는 한 방법이며 정적 경로나 지원되는 Felix 클러스터 경로 프로그래밍도 사용할 수 있습니다. Calico 3.32의 clusterRoutingMode는 비 VXLAN 경로에 Felix를 선택할 수 있지만 외부 BGP 광고에는 BGP가 필요합니다.

</details>

5. IPIP와 VXLAN을 비교할 때 VXLAN의 장점은?
   - A) 더 낮은 오버헤드
   - B) 더 좋은 성능
   - C) Azure에서의 더 나은 지원
   - D) IP 프로토콜 4만 필요

<details>
<summary>정답 보기</summary>

**정답: C) Azure에서의 더 나은 지원**

**설명:**
Calico 오버레이 가이드는 Azure를 IPIP가 지원되지 않고 VXLAN이 지원되는 환경으로 설명합니다. 실제 AKS·Azure CNI/정책 조합은 별도로 선택해야 합니다. UDP 캡슐화나 오프로드가 항상 더 빠르거나 모든 환경에서 지원된다는 뜻은 아닙니다.

</details>

6. 독립 IPPool의 spec.ipipMode 필드에서 유효하지 않은 값은?
   - A) Always
   - B) CrossSubnet
   - C) Never
   - D) Auto

<details>
<summary>정답 보기</summary>

**정답: D) Auto**

**설명:**
독립 IPPool의 ipipMode·vxlanMode 값은 Always·CrossSubnet·Never입니다. Operator pool의 encapsulation은 다른 필드이며 IPIPCrossSubnet·VXLANCrossSubnet 등의 값을 사용합니다. 두 API의 필드·값을 혼동하면 안 됩니다.

</details>

7. natOutgoing 설정의 역할은 무엇입니까?
   - A) 외부에서 Pod로의 인바운드 NAT
   - B) 해당 pool에서 모든 Calico IPPool 밖의 목적지로 가는 대상 트래픽의 SNAT
   - C) Pod 간 트래픽 NAT
   - D) Service IP NAT

<details>
<summary>정답 보기</summary>

**정답: B) 해당 pool에서 모든 Calico IPPool 밖의 목적지로 가는 대상 트래픽의 SNAT**

**설명:**
일반적인 조건은 목적지가 모든 Calico IPPool 밖에 있는지이며 단순한 클러스터 경계가 아닙니다. 비활성 pool도 no-NAT 목적지 범위를 나타낼 수 있고 Felix의 추가 설정으로 호스트 IP를 제외할 수도 있습니다. NAT는 정책 허용이나 반환 라우팅을 보장하지 않습니다.

</details>

8. Calico의 기본 VXLAN UDP 포트는?
   - A) 4789
   - B) 8472
   - C) 6443
   - D) 10250

<details>
<summary>정답 보기</summary>

**정답: A) 4789**

**설명:**
Calico의 기본값은 UDP 4789이며 변경 가능합니다. 다른 현재 VXLAN 구현도 8472를 사용할 수 있습니다. IPIP의 4는 TCP·UDP 포트가 아니라 IP 프로토콜 번호입니다.

</details>

9. Calico가 직접 네트워킹을 맡는 Azure 환경에서 오버레이 가이드가 지원하는 캡슐화 선택은?
   - A) IPIP Always
   - B) IPIP CrossSubnet
   - C) VXLAN
   - D) Direct (No encapsulation)

<details>
<summary>정답 보기</summary>

**정답: C) VXLAN**

**설명:**
Calico 오버레이 가이드가 해당 Azure 환경에서 지원하는 선택은 VXLAN입니다. 이를 모든 AKS 설치가 Calico 오버레이를 사용한다는 뜻으로 일반화하면 안 됩니다. UDR만 추가해 미지원 IPIP 패턴을 지원되게 만들 수는 없습니다.

</details>

10. IPPool의 nodeSelector 필드의 용도는 무엇입니까?
   - A) Pod를 특정 노드에 스케줄링
   - B) 자동 IPAM 선택 시 노드 라벨에 맞는 pool을 고르는 데 사용
   - C) Network Policy 적용 대상 선택
   - D) BGP 피어 선택

<details>
<summary>정답 보기</summary>

**정답: B) 자동 IPAM 선택 시 노드 라벨에 맞는 pool을 고르는 데 사용**

**설명:**
nodeSelector는 자동 할당 후보 pool을 노드 라벨로 고르며 Pod 스케줄링을 제어하지 않습니다. 3.32.2 구현에서 명시적으로 요청한 활성 pool은 호환성을 위해 노드·네임스페이스 selector를 우회할 수 있습니다. 따라서 이를 보안 경계나 모든 요청의 절대 제한으로 설명하면 안 됩니다.

</details>

11. 네트워킹 모드 변경에 대한 설명으로 잘못된 것은?
   - A) MTU·주소 변경에 따라 워크로드 재생성이 필요한지 확인한다
   - B) MTU 변경의 영향을 확인한다
   - C) 필요한 방화벽 허용과 경로를 확인한다
   - D) calicoctl은 배포 버전과 무관하게 아무 버전이나 사용해도 된다

<details>
<summary>정답 보기</summary>

**정답: D) calicoctl은 배포 버전과 무관하게 아무 버전이나 사용해도 된다**

**설명:**
모드 변경만으로 항상 calicoctl 업그레이드가 필요한 것은 아니지만 배포와 호환되는 클라이언트 버전을 사용해야 합니다. MTU·방화벽·경로·필요한 워크로드 재생성을 확인하고, mode-only 변경과 CIDR·block size 이전을 구분합니다. Deployment 롤링 업데이트는 자체 전략을 따르며 PDB가 rollout을 제한하지 않습니다.

</details>

12. IPIP 모드가 VXLAN보다 유리한 상황은?
   - A) Azure 환경
   - B) 하드웨어 오프로드가 필요한 경우
   - C) 최소한의 오버헤드가 필요하고 IP 프로토콜 4를 지원하는 환경
   - D) 멀티캐스트가 필요한 경우

<details>
<summary>정답 보기</summary>

**정답: C) 최소한의 오버헤드가 필요하고 IP 프로토콜 4를 지원하는 환경**

**설명:**
IPv4 헤더 옵션이 없을 때 IPIP의 추가 헤더는 20바이트로 VXLAN의 50바이트보다 작습니다. 프로토콜 4와 해당 Calico 구성이 지원되는 환경에서 헤더 예산을 줄일 이유가 될 수 있지만, 실제 성능 우위는 측정해야 합니다.

</details>

---

[학습 자료](../../../networking/calico/03-networking-modes.md) | [이전 퀴즈](02-architecture-quiz.md) | [다음 퀴즈](04-bgp-deep-dive-quiz.md)
