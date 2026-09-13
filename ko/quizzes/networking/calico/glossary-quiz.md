# Calico 용어집 퀴즈

> **관련 문서**: [Calico 용어집](../../../networking/calico/glossary.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. Felix의 역할로 올바른 것은?
   - A) BGP 라우팅 프로토콜 관리
   - B) 각 노드에서 네트워크 정책 적용 및 라우팅 테이블 프로그래밍
   - C) 데이터스토어 캐싱
   - D) Kubernetes API와 동기화

<details>
<summary>정답 보기</summary>

**정답: B) 각 노드에서 네트워크 정책 적용 및 라우팅 테이블 프로그래밍**

**설명:**
Felix는 각 노드에서 선택한 정책 데이터플레인과 필요한 경로를 설정합니다. 일반 Pod 인터페이스 생성/설정과 IPAM 호출은 CNI 플러그인의 역할입니다. Felix는 endpoint 상태를 추적하고 규칙을 설정하며 userspace에서 패킷마다 전달하는 프록시가 아닙니다.

</details>

2. BIRD의 약자와 역할로 올바른 것은?
   - A) Basic Internet Routing Daemon - HTTP 라우팅
   - B) BIRD Internet Routing Daemon - BGP 라우팅
   - C) Binary IP Routing Driver - IP 변환
   - D) Baseline Infrastructure Routing Daemon - DNS 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) BIRD Internet Routing Daemon - BGP 라우팅**

**설명:**
BIRD는 BGP가 활성화된 Calico 구성에서 경로를 교환합니다. 실제 direct routing과 터널 사용 여부는 라우팅/캡슐화 설계로 결정되므로 BGP가 있다고 overlay가 없다는 뜻은 아닙니다.

</details>

3. Typha의 주요 기능은?
   - A) Pod에 IP 주소 할당
   - B) 데이터스토어와 Felix 사이에서 캐싱 프록시 역할
   - C) Network Policy 정의
   - D) TLS 인증서 관리

<details>
<summary>정답 보기</summary>

**정답: B) 데이터스토어와 Felix 사이에서 캐싱 프록시 역할**

**설명:**
Typha는 데이터스토어 변경을 캐시하여 Felix에 배포하고 클라이언트별 watch 부하를 줄입니다. 여러 복제본과 syncer/watch가 있을 수 있으며 단일 watch나 정책 federation 서비스가 아닙니다. Operator가 실제 구성에 맞춰 규모를 관리하므로 50개 노드 이상에서만 필요한 것으로 단정하지 않습니다.

</details>

4. IPPool과 IPAM의 관계로 올바른 것은?
   - A) IPPool은 IPAM과 관련 없음
   - B) IPPool은 IPAM이 Pod에 할당할 수 있는 IP 주소 범위를 정의
   - C) IPAM이 IPPool을 자동 생성
   - D) IPPool은 Network Policy 정의에 사용

<details>
<summary>정답 보기</summary>

**정답: B) IPPool은 IPAM이 Pod에 할당할 수 있는 IP 주소 범위를 정의**

**설명:**
IPPool은 주소 범위와 캡슐화, NAT, 할당 적격성을 정의합니다. Calico IPAM이 지원 용도의 적격 pool에서 주소를 할당합니다. VPC CNI policy-only의 할당자가 아니며 Kubernetes Node PodCIDR과 같은 오브젝트도 아닙니다.

</details>

5. GlobalNetworkPolicy가 Kubernetes NetworkPolicy와 다른 점이 아닌 것은?
   - A) 클러스터 전체에 적용됨
   - B) 네임스페이스에 속하지 않음
   - C) Pod 선택자 사용
   - D) HostEndpoint에 적용 가능

<details>
<summary>정답 보기</summary>

**정답: C) Pod 선택자 사용**

**설명:**
워크로드 선택 개념은 Kubernetes NetworkPolicy와 GlobalNetworkPolicy에 모두 있지만 selector 문법/API는 다릅니다. GlobalNetworkPolicy는 클러스터 범위이며 selector로 실제 대상 워크로드/host endpoint를 정하고 Calico tier/order 등을 사용합니다.

</details>

6. Calico에서 Tier의 개념은?
   - A) 노드의 물리적 위치
   - B) 정책을 계층화하여 순차적으로 평가하는 구조
   - C) IP 주소 할당 우선순위
   - D) Pod 리소스 제한

<details>
<summary>정답 보기</summary>

**정답: B) 정책을 계층화하여 순차적으로 평가하는 구조**

**설명:**
숫자가 낮은 tier order를 먼저, 그 안에서 policy order를 평가합니다. Allow/Deny는 최종 결정이고 Pass는 다음 적용 tier, 마지막에는 profile로 위임합니다. Security/Platform/Application은 설정 예시이며 필수 기본 계층 이름이나 순서가 아닙니다.

</details>

7. WorkloadEndpoint의 의미는?
   - A) Kubernetes Service의 엔드포인트
   - B) Calico가 관리하는 Pod의 네트워크 인터페이스 정보
   - C) 외부 로드밸런서 주소
   - D) BGP 피어의 IP 주소

<details>
<summary>정답 보기</summary>

**정답: B) Calico가 관리하는 Pod의 네트워크 인터페이스 정보**

**설명:**
WorkloadEndpoint는 주소/MAC/인터페이스, 레이블, profile 참조를 가진 워크로드 인터페이스 표현입니다. 일반적으로 plugin/orchestrator가 수명주기를 관리합니다. Service EndpointSlice 또는 모든 유효 정책 결정이 저장된 목록은 아닙니다.

</details>

8. BGPPeer와 BGPConfiguration의 차이점은?
   - A) 둘 다 동일한 리소스의 다른 이름
   - B) BGPPeer는 개별 피어 연결 정의, BGPConfiguration은 전역 BGP 설정
   - C) BGPPeer는 IPv4용, BGPConfiguration은 IPv6용
   - D) BGPPeer는 내부용, BGPConfiguration은 외부용

<details>
<summary>정답 보기</summary>

**정답: B) BGPPeer는 개별 피어 연결 정의, BGPConfiguration은 전역 BGP 설정**

**설명:**
BGPConfiguration default는 ASN, mesh, Service 광고 등의 클러스터 기본값을 정의하고 지원되는 노드 override는 별도 확인합니다. BGPPeer는 주소나 selector로 의도한 피어 관계를 정의합니다. 리소스 생성만으로 세션이나 필요한 경로가 성립하지는 않습니다.

</details>

9. 재사용 외부 CIDR 집합을 정의하는 Calico NetworkSet과 기능이 유사한 Cilium 리소스는?
   - A) CiliumNetworkPolicy
   - B) CiliumEndpoint
   - C) CiliumCIDRGroup with cidrGroupRef/cidrGroupSelector
   - D) CiliumIdentity

<details>
<summary>정답 보기</summary>

**정답: C) CiliumCIDRGroup with cidrGroupRef/cidrGroupSelector**

**설명:**
Calico NetworkSet은 네임스페이스 범위, GlobalNetworkSet은 클러스터 범위의 레이블/IP/CIDR 집합입니다. CiliumCIDRGroup은 클러스터 범위이며 CIDR 규칙의 cidrGroupRef 또는 cidrGroupSelector로 참조합니다. 관련 개념이지만 서로 다른 API로, DNS 규칙이나 교환 가능한 매니페스트가 아닙니다.

</details>

10. HostEndpoint의 사용 목적은?
    - A) Pod 네트워킹 설정
    - B) 노드 자체(호스트)의 네트워크 인터페이스에 정책 적용
    - C) 외부 서비스 연결
    - D) DNS 쿼리 제어

<details>
<summary>정답 보기</summary>

**정답: B) 노드 자체(호스트)의 네트워크 인터페이스에 정책 적용**

**설명:**
HostEndpoint는 호스트 인터페이스를 표현하여 host 트래픽과 설정된 forwarded 트래픽에 정책을 적용합니다. 생성/강제 전에 profile, failsafe, 관리 경로를 검토해야 합니다. 워크로드/호스트 정책 범위는 다르지만 전달되는 Pod 트래픽도 영향을 받을 수 있습니다.

</details>
