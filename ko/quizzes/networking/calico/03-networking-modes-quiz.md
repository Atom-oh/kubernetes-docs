# Calico 네트워킹 모드 퀴즈

> **관련 문서**: [Calico 네트워킹 모드](../../../networking/calico/03-networking-modes.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. IPIP 모드에서 캡슐화로 인한 MTU 오버헤드는 얼마입니까?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>정답 보기</summary>

**정답: B) 20 bytes**

**설명:**
IPIP 모드는 IP 패킷을 다른 IP 패킷 내에 캡슐화하며, 이로 인해 20 bytes의 오버헤드가 발생합니다. VXLAN의 50 bytes보다 오버헤드가 적어 성능이 약간 더 좋습니다.

</details>

2. VXLAN 모드에서 캡슐화로 인한 MTU 오버헤드는 얼마입니까?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>정답 보기</summary>

**정답: C) 50 bytes**

**설명:**
VXLAN 모드는 UDP 기반 오버레이 네트워크를 사용하며, 50 bytes의 오버헤드가 발생합니다. IPIP보다 오버헤드가 크지만 더 넓은 호환성과 하드웨어 오프로드 지원을 제공합니다.

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
CrossSubnet 모드는 하이브리드 접근 방식으로, 같은 서브넷의 노드 간에는 직접 라우팅을 사용하고, 다른 서브넷의 노드 간에만 캡슐화(IPIP 또는 VXLAN)를 사용합니다. 이를 통해 불필요한 캡슐화 오버헤드를 줄입니다.

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
Direct 모드는 캡슐화 없이 직접 라우팅을 사용하므로, 네트워크 인프라(라우터, 스위치)가 Pod CIDR를 라우팅할 수 있어야 합니다. 일반적으로 BGP와 함께 사용됩니다.

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
Azure에서 IPIP는 제한적으로 지원되지만 VXLAN은 지원됩니다. 또한 VXLAN은 UDP 기반이라 더 넓은 호환성을 가지며, 하드웨어 오프로드 지원도 더 광범위합니다. 단, 오버헤드는 IPIP(20 bytes)보다 VXLAN(50 bytes)이 더 큽니다.

</details>

6. IPPool 리소스에서 encapsulation 설정의 유효한 값이 아닌 것은?
   - A) Always
   - B) CrossSubnet
   - C) Never
   - D) Auto

<details>
<summary>정답 보기</summary>

**정답: D) Auto**

**설명:**
IPPool의 ipipMode 또는 vxlanMode 필드의 유효한 값은 Always, CrossSubnet, Never입니다. Auto는 유효한 옵션이 아닙니다.

</details>

7. natOutgoing 설정의 역할은 무엇입니까?
   - A) 외부에서 Pod로의 인바운드 NAT
   - B) Pod에서 외부로의 아웃바운드 NAT (SNAT)
   - C) Pod 간 트래픽 NAT
   - D) Service IP NAT

<details>
<summary>정답 보기</summary>

**정답: B) Pod에서 외부로의 아웃바운드 NAT (SNAT)**

**설명:**
natOutgoing이 true로 설정되면, 해당 IPPool의 Pod가 클러스터 외부로 트래픽을 보낼 때 노드 IP로 Source NAT(SNAT)됩니다. 이를 통해 외부 네트워크가 Pod IP를 알 필요 없이 통신할 수 있습니다.

</details>

8. VXLAN의 기본 UDP 포트 번호는 무엇입니까?
   - A) 4789
   - B) 8472
   - C) 6443
   - D) 10250

<details>
<summary>정답 보기</summary>

**정답: A) 4789**

**설명:**
VXLAN의 IANA 표준 UDP 포트는 4789입니다. 일부 구현에서는 8472를 사용하기도 하지만, Calico는 표준 포트 4789를 사용합니다.

</details>

9. 다음 중 Azure에서 Calico를 사용할 때 권장되는 캡슐화 모드는?
   - A) IPIP Always
   - B) IPIP CrossSubnet
   - C) VXLAN
   - D) Direct (No encapsulation)

<details>
<summary>정답 보기</summary>

**정답: C) VXLAN**

**설명:**
Azure에서는 IPIP 프로토콜 지원이 제한적이므로 VXLAN 모드를 사용하는 것이 권장됩니다. VXLAN은 UDP 기반이라 Azure 네트워크에서 잘 작동합니다.

</details>

10. IPPool의 nodeSelector 필드의 용도는 무엇입니까?
    - A) Pod를 특정 노드에 스케줄링
    - B) 특정 노드에만 이 IPPool의 IP 할당
    - C) Network Policy 적용 대상 선택
    - D) BGP 피어 선택

<details>
<summary>정답 보기</summary>

**정답: B) 특정 노드에만 이 IPPool의 IP 할당**

**설명:**
nodeSelector를 사용하면 특정 레이블이 있는 노드에서만 해당 IPPool의 IP가 Pod에 할당됩니다. 예를 들어, 특정 가용 영역이나 랙에 다른 IP 대역을 할당할 수 있습니다.

</details>

11. 네트워킹 모드 마이그레이션 시 고려해야 할 사항이 아닌 것은?
    - A) 기존 Pod의 재시작 필요 여부
    - B) MTU 변경에 따른 영향
    - C) 방화벽 규칙 변경
    - D) calicoctl 버전 업그레이드

<details>
<summary>정답 보기</summary>

**정답: D) calicoctl 버전 업그레이드**

**설명:**
네트워킹 모드 변경 시 기존 Pod 재시작, MTU 변경, 방화벽 규칙(예: VXLAN의 UDP 4789 허용) 등을 고려해야 합니다. calicoctl 버전은 네트워킹 모드와 직접적인 관련이 없습니다.

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
IPIP는 20 bytes의 오버헤드로 VXLAN(50 bytes)보다 효율적입니다. IP 프로토콜 4를 지원하는 네트워크 환경에서 최소한의 오버헤드가 필요할 때 IPIP가 유리합니다.

</details>
