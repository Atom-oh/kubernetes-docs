# Calico BGP 심화 퀴즈

> **관련 문서**: [Calico BGP 심화](../../../networking/calico/04-bgp-deep-dive.md)
> **마지막 업데이트**: 2025년 2월 22일

## 퀴즈

1. BGP의 약자는 무엇입니까?
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Broadcast Gateway Protocol
   - D) Bridge Gateway Protocol

<details>
<summary>정답 보기</summary>

**정답: B) Border Gateway Protocol**

**설명:**
BGP는 Border Gateway Protocol의 약자로, 인터넷에서 자율 시스템(AS) 간 라우팅 정보를 교환하는 데 사용되는 표준 프로토콜입니다.

</details>

2. iBGP와 eBGP의 차이점은 무엇입니까?
   - A) iBGP는 암호화를 사용하고 eBGP는 사용하지 않음
   - B) iBGP는 같은 AS 내에서, eBGP는 다른 AS 간에 사용
   - C) iBGP는 IPv4만, eBGP는 IPv6만 지원
   - D) iBGP는 더 빠르고 eBGP는 더 느림

<details>
<summary>정답 보기</summary>

**정답: B) iBGP는 같은 AS 내에서, eBGP는 다른 AS 간에 사용**

**설명:**
iBGP(Internal BGP)는 동일한 자율 시스템(AS) 내의 라우터 간 통신에 사용되고, eBGP(External BGP)는 서로 다른 AS 간의 라우터 간 통신에 사용됩니다.

</details>

3. Private AS 번호 범위는 무엇입니까?
   - A) 1-1000
   - B) 10000-50000
   - C) 64512-65534
   - D) 100000-200000

<details>
<summary>정답 보기</summary>

**정답: C) 64512-65534**

**설명:**
Private AS 번호 범위는 64512-65534입니다. 이 범위의 AS 번호는 인터넷에 광고되지 않으며, 내부 네트워크나 프라이빗 환경에서 사용됩니다.

</details>

4. Full-mesh BGP에서 N개 노드의 총 BGP 세션 수를 계산하는 공식은?
   - A) N * 2
   - B) N * (N-1) / 2
   - C) N^2
   - D) N * (N+1) / 2

<details>
<summary>정답 보기</summary>

**정답: B) N * (N-1) / 2**

**설명:**
Full-mesh BGP에서는 모든 노드가 서로 피어링하므로, 총 세션 수는 N*(N-1)/2입니다. 예를 들어 10개 노드는 10*9/2 = 45개의 BGP 세션이 필요합니다.

</details>

5. 100개 노드 클러스터에서 Full-mesh BGP를 사용할 때 필요한 총 BGP 세션 수는?
   - A) 100
   - B) 200
   - C) 4950
   - D) 10000

<details>
<summary>정답 보기</summary>

**정답: C) 4950**

**설명:**
100 * (100-1) / 2 = 100 * 99 / 2 = 4950개의 BGP 세션이 필요합니다. 이는 대규모 클러스터에서 Full-mesh가 비효율적인 이유입니다.

</details>

6. Route Reflector의 주요 역할은 무엇입니까?
   - A) 트래픽 로드 밸런싱
   - B) Full-mesh 없이 BGP 라우트 전파
   - C) 패킷 암호화
   - D) DNS 해석

<details>
<summary>정답 보기</summary>

**정답: B) Full-mesh 없이 BGP 라우트 전파**

**설명:**
Route Reflector는 iBGP에서 full-mesh 요구 사항을 제거합니다. 클라이언트 노드는 Route Reflector에게만 피어링하고, Route Reflector가 라우트를 다른 클라이언트들에게 반사(reflect)합니다.

</details>

7. Calico에서 Route Reflector를 설정할 때 사용하는 필드는?
   - A) routeReflectorEnabled
   - B) routeReflectorClusterID
   - C) routeReflectorMode
   - D) isRouteReflector

<details>
<summary>정답 보기</summary>

**정답: B) routeReflectorClusterID**

**설명:**
Route Reflector 노드는 Node 리소스의 spec.bgp.routeReflectorClusterID 필드를 설정하여 구성합니다. 이 ID는 Route Reflector 클러스터를 식별하는 데 사용됩니다.

</details>

8. BGPPeer의 nodeSelector 필드 용도는 무엇입니까?
   - A) 어떤 Pod가 BGP를 사용할지 선택
   - B) 어떤 노드가 이 피어와 BGP 세션을 맺을지 선택
   - C) BGP 라우트를 수신할 노드 선택
   - D) BGP 인증을 사용할 노드 선택

<details>
<summary>정답 보기</summary>

**정답: B) 어떤 노드가 이 피어와 BGP 세션을 맺을지 선택**

**설명:**
nodeSelector를 사용하면 특정 레이블이 있는 노드만 해당 BGP 피어와 세션을 맺습니다. 예를 들어, 특정 랙의 노드만 해당 ToR 스위치와 피어링하도록 설정할 수 있습니다.

</details>

9. BGPConfiguration에서 설정하는 항목이 아닌 것은?
   - A) asNumber (AS 번호)
   - B) serviceExternalIPs (Service External IP 광고)
   - C) nodeToNodeMeshEnabled (노드 간 메시)
   - D) ipipMode (IPIP 캡슐화 모드)

<details>
<summary>정답 보기</summary>

**정답: D) ipipMode (IPIP 캡슐화 모드)**

**설명:**
ipipMode는 IPPool 리소스에서 설정합니다. BGPConfiguration에서는 AS 번호, Service IP 광고, 노드 간 메시 설정, BGP 커뮤니티 등을 설정합니다.

</details>

10. BGP를 통해 광고할 수 있는 Service IP 유형이 아닌 것은?
    - A) External IP
    - B) LoadBalancer IP
    - C) Cluster IP
    - D) Pod IP

<details>
<summary>정답 보기</summary>

**정답: D) Pod IP**

**설명:**
BGPConfiguration의 serviceExternalIPs, serviceLoadBalancerIPs, serviceClusterIPs를 통해 각각 External IP, LoadBalancer IP, Cluster IP를 광고할 수 있습니다. Pod IP는 별도 설정 없이 자동으로 BGP를 통해 교환됩니다.

</details>

11. nodeToNodeMeshEnabled를 false로 설정하는 상황은?
    - A) 클러스터가 10개 미만의 노드일 때
    - B) Route Reflector를 사용할 때
    - C) VXLAN 모드를 사용할 때
    - D) Network Policy를 비활성화할 때

<details>
<summary>정답 보기</summary>

**정답: B) Route Reflector를 사용할 때**

**설명:**
Route Reflector를 사용하면 노드들이 Route Reflector에게만 피어링하므로 full-mesh가 필요 없습니다. 이 경우 nodeToNodeMeshEnabled를 false로 설정하여 불필요한 피어링을 방지합니다.

</details>

12. BGP 커뮤니티의 용도는 무엇입니까?
    - A) BGP 세션 암호화
    - B) 라우트에 메타데이터 태그를 추가하여 필터링/정책 적용
    - C) BGP 피어 인증
    - D) 라우트 우선순위 설정

<details>
<summary>정답 보기</summary>

**정답: B) 라우트에 메타데이터 태그를 추가하여 필터링/정책 적용**

**설명:**
BGP 커뮤니티는 라우트에 태그를 추가하여 라우팅 정책을 적용하는 데 사용됩니다. 예를 들어, 특정 커뮤니티가 태그된 라우트만 특정 피어에게 광고하도록 필터링할 수 있습니다.

</details>

13. BGP MD5 인증의 목적은 무엇입니까?
    - A) 트래픽 암호화
    - B) BGP 세션의 무결성 및 피어 인증
    - C) 라우트 우선순위 설정
    - D) 대역폭 제한

<details>
<summary>정답 보기</summary>

**정답: B) BGP 세션의 무결성 및 피어 인증**

**설명:**
MD5 인증은 BGP 세션의 TCP 연결에 대한 무결성을 보장하고, 허가된 피어만 세션을 맺을 수 있도록 합니다. 이는 BGP 하이재킹과 같은 공격을 방지합니다.

</details>

14. BGP Graceful Restart의 역할은 무엇입니까?
    - A) BGP 세션 속도 향상
    - B) BGP 프로세스 재시작 시 라우팅 중단 최소화
    - C) 자동 피어 검색
    - D) 라우트 압축

<details>
<summary>정답 보기</summary>

**정답: B) BGP 프로세스 재시작 시 라우팅 중단 최소화**

**설명:**
Graceful Restart를 사용하면 BGP 프로세스가 재시작되는 동안 피어가 기존 라우트를 일정 시간 유지하여 트래픽 중단을 최소화합니다.

</details>

15. BIRD 상태를 확인하는 명령어는 무엇입니까?
    - A) birdctl status
    - B) birdcl show protocols
    - C) bird --status
    - D) calicoctl bird status

<details>
<summary>정답 보기</summary>

**정답: B) birdcl show protocols**

**설명:**
birdcl은 BIRD 클라이언트로, `birdcl show protocols` 명령으로 BGP 피어 상태를 확인할 수 있습니다. Calico 노드 Pod 내에서 실행합니다.

</details>
