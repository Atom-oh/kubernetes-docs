# Calico 소개 퀴즈

> **관련 문서**: [Calico 소개](../../../networking/calico/01-introduction.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. Project Calico는 언제 시작되었습니까?
   - A) 2010년
   - B) 2012년
   - C) 2014년
   - D) 2016년

<details>
<summary>정답 보기</summary>

**정답: C) 2014년**

**설명:**
Project Calico는 2014년 Metaswitch에서 시작되었습니다. 이후 2016년 Tigera가 설립되어 Calico를 상업화했습니다.

</details>

2. 현재 Calico를 관리하고 상업화하는 회사는 어디입니까?
   - A) Metaswitch
   - B) Tigera
   - C) Red Hat
   - D) VMware

<details>
<summary>정답 보기</summary>

**정답: B) Tigera**

**설명:**
Tigera는 2016년에 설립되어 Calico를 상업화했으며, Calico Enterprise와 Calico Cloud 서비스를 제공합니다.

</details>

3. Calico의 주요 특징으로 올바르지 않은 것은?
   - A) BGP 기반 라우팅
   - B) eBPF 데이터플레인 지원
   - C) Service Mesh 기본 내장
   - D) 멀티 환경 지원 (클라우드, 온프레미스, 하이브리드)

<details>
<summary>정답 보기</summary>

**정답: C) Service Mesh 기본 내장**

**설명:**
Calico는 Service Mesh를 기본 내장하지 않습니다. Service Mesh 기능은 Calico Enterprise에서 별도로 제공됩니다. Cilium과 달리 Calico 오픈소스 버전에는 Service Mesh가 포함되어 있지 않습니다.

</details>

4. Calico가 지원하는 데이터플레인 옵션은 무엇입니까?
   - A) iptables만
   - B) eBPF만
   - C) iptables와 eBPF 모두
   - D) nftables만

<details>
<summary>정답 보기</summary>

**정답: C) iptables와 eBPF 모두**

**설명:**
Calico는 전통적인 iptables 기반 데이터플레인과 최신 eBPF 기반 데이터플레인을 모두 지원합니다. eBPF 모드는 2020년에 도입되었으며, 더 나은 성능과 확장성을 제공합니다.

</details>

5. calicoctl 도구의 주요 역할은 무엇입니까?
   - A) Calico 설치 자동화
   - B) Calico 리소스 관리 및 상태 확인
   - C) 네트워크 트래픽 모니터링
   - D) BGP 라우터 설정

<details>
<summary>정답 보기</summary>

**정답: B) Calico 리소스 관리 및 상태 확인**

**설명:**
calicoctl은 Calico 리소스(NetworkPolicy, IPPool, BGPPeer 등)를 관리하고, 노드 상태, IPAM 정보, BGP 피어링 상태 등을 확인하는 CLI 도구입니다.

</details>

6. Calico Enterprise가 오픈소스 버전과 비교하여 추가로 제공하는 기능으로 올바른 것은?
   - A) 기본 Network Policy
   - B) BGP 라우팅
   - C) L7 Network Policy 및 Service Mesh
   - D) IPIP 캡슐화

<details>
<summary>정답 보기</summary>

**정답: C) L7 Network Policy 및 Service Mesh**

**설명:**
Calico 오픈소스는 L3-L4 Network Policy를 제공하지만, L7 Network Policy와 Service Mesh 기능은 Calico Enterprise에서만 제공됩니다.

</details>

7. Calico가 2020년에 도입한 주요 기능은 무엇입니까?
   - A) Kubernetes 네이티브 지원
   - B) eBPF 데이터플레인
   - C) Windows 지원
   - D) Calico Cloud 서비스

<details>
<summary>정답 보기</summary>

**정답: B) eBPF 데이터플레인**

**설명:**
2020년에 Calico는 eBPF 데이터플레인을 도입했습니다. 이는 기존 iptables 기반 방식보다 더 나은 성능과 확장성을 제공합니다.

</details>

8. Calico와 Cilium을 비교할 때, Calico의 강점으로 올바른 것은?
   - A) 기본 내장 Service Mesh
   - B) Hubble을 통한 관측성
   - C) 완전한 Windows 지원
   - D) L7 Network Policy 기본 제공

<details>
<summary>정답 보기</summary>

**정답: C) 완전한 Windows 지원**

**설명:**
Calico는 Windows 워크로드를 완전히 지원하는 반면, Cilium의 Windows 지원은 베타 단계입니다. 또한 Calico는 더 성숙한 솔루션으로, BGP 기반 온프레미스 환경에서 강점을 가집니다.

</details>

9. Calico를 선택해야 하는 환경으로 가장 적합한 것은?
   - A) L7 Network Policy가 필수인 환경
   - B) Service Mesh 내장이 필요한 환경
   - C) BGP 기반 온프레미스 환경
   - D) 고급 관측성이 필수인 환경

<details>
<summary>정답 보기</summary>

**정답: C) BGP 기반 온프레미스 환경**

**설명:**
Calico는 BGP 기반 온프레미스 환경, Windows 워크로드가 필요한 환경, 성숙한 솔루션을 선호하는 환경에서 적합합니다. L7 Policy, Service Mesh, 고급 관측성이 필요한 경우 Cilium이 더 적합할 수 있습니다.

</details>

10. EKS에서 Calico를 사용할 때 일반적인 구성 방식은 무엇입니까?
    - A) Calico로 네트워킹과 Policy 모두 처리
    - B) AWS VPC CNI로 네트워킹, Calico로 Network Policy
    - C) Calico로 네트워킹, AWS VPC CNI로 Policy
    - D) Calico와 VPC CNI를 동시에 네트워킹에 사용

<details>
<summary>정답 보기</summary>

**정답: B) AWS VPC CNI로 네트워킹, Calico로 Network Policy**

**설명:**
EKS에서는 AWS VPC CNI로 Pod 네트워킹을 처리하고, Calico는 Network Policy만 담당하는 "Policy only" 모드로 구성하는 것이 일반적입니다. 이렇게 하면 AWS 네이티브 네트워킹의 이점과 Calico의 강력한 정책 기능을 함께 활용할 수 있습니다.

</details>
