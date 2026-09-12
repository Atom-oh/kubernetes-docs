# Calico BGP 심화 퀴즈

> **관련 문서**: [Calico BGP 심화](../../../networking/calico/04-bgp-deep-dive.md)
> **마지막 업데이트**: 2026년 9월 12일

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

3. 16비트 Private AS 번호 범위는 무엇입니까?
   - A) 1-1000
   - B) 10000-50000
   - C) 64512-65534
   - D) 100000-200000

<details>
<summary>정답 보기</summary>

**정답: C) 64512-65534**

**설명:**
16비트 프라이빗 범위는 64512–65534이고 32비트 범위는 4200000000–4294967294입니다. ASN은 네트워크를 식별하는 번호이지 자체적으로 라우팅 불가능한 IP 주소가 아닙니다. 글로벌 인터넷에 경로를 광고하기 전에 프라이빗 ASN이 포함된 AS_PATH를 적절히 처리해야 합니다.

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
Calico Node의 spec.bgp.routeReflectorClusterID가 RR 역할을 지정합니다. Kubernetes datastore에서는 기존 Kubernetes Node의 projectcalico.org/RouteReflectorClusterID annotation을 사용하여 주소 등 다른 필드를 보존할 수 있습니다. 설정 즉시 해당 노드가 자동 mesh에서 제외되므로 전환 순서를 계획해야 합니다.

</details>

8. BGPPeer의 nodeSelector 필드 용도는 무엇입니까?
   - A) 어떤 Pod가 BGP를 사용할지 선택
   - B) 어떤 노드가 이 피어와 BGP 세션을 맺을지 선택
   - C) 수신 허용 경로의 CIDR 선택
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
Service 광고 필드는 serviceExternalIPs, serviceLoadBalancerIPs, serviceClusterIPs입니다. Pod IP는 Service IP가 아닙니다. Pod 경로 교환도 BGP 활성화, IPAM·라우팅 모드 및 export 정책에 좌우되며 모든 설치에서 자동 광고되는 것은 아닙니다.

</details>

11. 기존 full-mesh를 Route Reflector로 전환할 때 자동 mesh를 끄는 적절한 시점은?
    - A) RR 레이블을 붙이기 전에
    - B) 대체 RR 세션·경로·next hop·실제 트래픽을 검증한 후
    - C) BGPFilter 객체 하나를 만든 직후
    - D) RR의 실제 세션 상태와 무관하게

<details>
<summary>정답 보기</summary>

**정답: B) 대체 RR 세션·경로·next hop·실제 트래픽을 검증한 후**

**설명:**
준비된 RR 노드에 역할과 명시적 피어링을 구성하고 양쪽 RR·클라이언트에서 경로와 대표 트래픽을 검증한 뒤 mesh를 끕니다. RR 지정 노드는 자동 mesh에서 즉시 제외되지만 전환 중 일반 클라이언트의 mesh를 유지할 수 있습니다.

</details>

12. BGP 커뮤니티의 용도는 무엇입니까?
    - A) BGP 세션 암호화
    - B) 라우트에 메타데이터 태그를 추가하여 필터링/정책 적용
    - C) BGP 피어 인증
    - D) Pod의 MTU 변경

<details>
<summary>정답 보기</summary>

**정답: B) 라우트에 메타데이터 태그를 추가하여 필터링/정책 적용**

**설명:**
커뮤니티는 라우트에 태그를 추가하여 별도의 라우터 정책이 필터링·우선순위 등에 활용하게 합니다. 임의 태그 이름이나 값 자체로 우선순위·차단을 보장하지 않습니다. 표준 커뮤니티는 두 개의 16비트 값, large community는 세 개의 32비트 값입니다.

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
TCP MD5 signature는 공유 비밀을 사용하여 BGP 트래픽을 인증합니다. 암호화하거나 인증된 피어가 보낸 경로의 정당성을 보장하지 않으므로 경로 필터링도 필요합니다.

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
피어와 Graceful Restart capability를 협상하고 전달 경로가 계속 동작할 때 재시작 중 경로 유지가 도움이 됩니다. 전달 경로가 사라지면 stale 경로 때문에 blackhole이 생길 수 있으므로 무중단을 보장하지 않습니다.

</details>

15. BIRD 상태를 확인하는 명령어는 무엇입니까?
    - A) birdctl status
    - B) birdcl -s /var/run/calico/bird.ctl show protocols
    - C) bird --status
    - D) calicoctl bird status

<details>
<summary>정답 보기</summary>

**정답: B) birdcl -s /var/run/calico/bird.ctl show protocols**

**설명:**
대상 calico-node 컨테이너에서 IPv4 control socket을 명시하여 실행합니다. BGP 외 kernel·device 프로토콜도 조회되며 show protocols all과 실제 프로토콜 이름으로 상세 상태를 확인할 수 있습니다. IPv6는 birdcl6와 /var/run/calico/bird6.ctl을 사용하고 BGP 비활성화 설치에는 BIRD가 없을 수 있습니다.

</details>

16. IPv4 기본 경로만 수신 허용하려면 어떤 규칙을 사용합니까?
    - A) Accept와 In 0.0.0.0/0
    - B) Accept와 Equal 0.0.0.0/0
    - C) Reject와 NotIn 0.0.0.0/0
    - D) 빈 필터

<details>
<summary>정답 보기</summary>

**정답: B) Accept와 Equal 0.0.0.0/0**

**설명:**
Equal은 정확한 /0 경로만 매칭합니다. In /0은 모든 IPv4 경로, NotIn /0은 어떤 IPv4 경로도 매칭하지 않습니다. BGPFilter는 미일치 시 기본 Accept이므로 허용 목록에는 마지막 무조건 Reject도 필요합니다.

</details>

17. prefixAdvertisements에 10.244.0.0/16을 지정하면 무엇을 합니까?
    - A) 언제나 새 /16 경로 생성
    - B) 모든 /26을 /16으로 대체
    - C) 범위에 일치하는 기존 경로에 커뮤니티 추가
    - D) Service 주소 할당

<details>
<summary>정답 보기</summary>

**정답: C) 범위에 일치하는 기존 경로에 커뮤니티 추가**

**설명:**
현재 renderer는 Pod 경로를 포함해 일치하는 기존 경로에 커뮤니티를 추가하며 경로 생성·주소 할당·블록 집계는 하지 않습니다. 앞선 BGPFilter의 명시적 export Accept가 기본 태깅을 건너뛸 수 있으므로 규칙 내 operation이 필요할 수 있습니다.

</details>
