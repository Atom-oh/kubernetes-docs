# Calico 용어집 퀴즈

> **관련 문서**: [Calico 용어집](../../../networking/calico/glossary.md)
> **마지막 업데이트**: 2026년 2월 22일

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
Felix는 Calico의 핵심 에이전트로, 각 노드에서 DaemonSet으로 실행됩니다. 주요 역할은 Network Policy를 iptables/eBPF 규칙으로 변환하여 적용하고, Pod 인터페이스(veth pair) 관리, 라우팅 테이블 프로그래밍을 담당합니다.

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
BIRD(BIRD Internet Routing Daemon)는 오픈소스 라우팅 데몬으로, Calico에서 BGP 프로토콜을 통한 라우트 교환을 담당합니다. 노드 간 Pod CIDR 정보를 전파하고, 외부 라우터와의 BGP 피어링을 관리합니다.

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
Typha는 대규모 클러스터(50+ 노드)에서 필수적인 컴포넌트입니다. 데이터스토어(Kubernetes API 또는 etcd)에서 데이터를 읽어 캐싱하고, 여러 Felix 인스턴스에게 제공합니다. 이를 통해 API 서버 부하를 줄이고 확장성을 향상시킵니다.

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
IPPool은 CIDR 형식으로 IP 주소 범위를 정의하는 Calico 리소스입니다. IPAM(IP Address Management)은 IPPool에서 정의한 범위 내에서 Pod에 IP를 할당합니다. IPPool에는 캡슐화 모드, NAT 설정, 노드 선택자 등의 옵션도 포함됩니다.

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
Pod 선택자는 Kubernetes NetworkPolicy와 GlobalNetworkPolicy 모두 사용합니다. 차이점은 GlobalNetworkPolicy가 클러스터 전체에 적용되고, 네임스페이스에 속하지 않으며, HostEndpoint(노드 자체 트래픽)에도 적용할 수 있고, Tier와 order를 지원한다는 점입니다.

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
Tier는 Network Policy를 논리적 계층으로 그룹화합니다. 낮은 order의 Tier가 먼저 평가되며, Pass 액션으로 다음 Tier로 넘어갈 수 있습니다. 일반적으로 Security(보안) -> Platform(플랫폼) -> Application(애플리케이션) 순으로 구성하여 관심사를 분리합니다.

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
WorkloadEndpoint는 Calico가 관리하는 워크로드(주로 Pod)의 네트워크 엔드포인트를 나타냅니다. Pod의 IP 주소, MAC 주소, 인터페이스 이름, 적용된 프로필과 정책 정보를 포함합니다. `calicoctl get workloadendpoint`로 조회할 수 있습니다.

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
BGPPeer는 특정 BGP 피어(예: ToR 스위치)와의 연결을 정의합니다. peerIP, asNumber, nodeSelector 등을 지정합니다. BGPConfiguration은 로컬 AS 번호, Service IP 광고 설정, node-to-node mesh 활성화 여부 등 클러스터 전체 BGP 설정을 정의합니다.

</details>

9. Calico의 NetworkSet과 유사한 Cilium의 개념은?
   - A) CiliumNetworkPolicy
   - B) CiliumEndpoint
   - C) CiliumClusterwideNetworkPolicy with toFQDNs/toCIDRSet
   - D) CiliumIdentity

<details>
<summary>정답 보기</summary>

**정답: C) CiliumClusterwideNetworkPolicy with toFQDNs/toCIDRSet**

**설명:**
Calico NetworkSet은 IP 주소 집합을 정의하여 정책에서 재사용합니다. Cilium에서는 별도의 NetworkSet 리소스는 없지만, CiliumNetworkPolicy나 CiliumClusterwideNetworkPolicy에서 toCIDRSet이나 toFQDNs를 사용하여 유사한 기능을 구현합니다.

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
HostEndpoint는 Kubernetes 노드 자체의 네트워크 인터페이스(예: eth0)에 Network Policy를 적용할 수 있게 합니다. 이를 통해 노드로 들어오는 SSH 접근 제어, 호스트 레벨 방화벽 규칙 설정 등이 가능합니다. Pod 트래픽과 별개로 호스트 트래픽을 제어합니다.

</details>
