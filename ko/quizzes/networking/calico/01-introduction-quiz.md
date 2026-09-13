# Calico 소개 퀴즈

> **관련 문서**: [Calico 소개](../../../networking/calico/01-introduction.md)
> **마지막 업데이트**: 2026년 9월 12일

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
Project Calico의 시작은 2014년 Metaswitch이며 Tigera는 2016년에 설립되었습니다. 프로젝트 시작과 이후 제품 출시·Calico 버전 공개 날짜를 구분해야 합니다.

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
Tigera가 커뮤니티 기여자와 Calico를 유지관리하며 Enterprise·Cloud 제품을 제공합니다. CNCF Landscape 등재는 CNCF가 프로젝트를 관리하거나 졸업시켰다는 뜻이 아닙니다.

</details>

3. Calico 기본 설치에 대한 설명으로 올바르지 않은 것은?
   - A) BGP 기반 라우팅
   - B) eBPF 데이터플레인 지원
   - C) 모든 Pod에 Istio 사이드카를 자동 주입한다
   - D) 멀티 환경 지원 (클라우드, 온프레미스, 하이브리드)

<details>
<summary>정답 보기</summary>

**정답: C) 모든 Pod에 Istio 사이드카를 자동 주입한다**

**설명:**
네트워킹·정책·데이터플레인 선택은 Calico의 기능이지만 이 실습 설치가 모든 Pod에 Istio 사이드카를 자동 주입하지는 않습니다. 메시 통합은 별도 기능과 구성이 필요하며 Cilium 역시 모든 메시 기능이 기본 활성화되는 것은 아닙니다.

</details>

4. Calico가 지원하는 Linux 데이터플레인 선택지를 포함한 것은?
   - A) iptables만
   - B) eBPF만
   - C) iptables·nftables·eBPF
   - D) nftables만

<details>
<summary>정답 보기</summary>

**정답: C) iptables·nftables·eBPF**

**설명:**
Calico는 이 Linux 데이터플레인 선택지를 지원합니다. VXLAN·IPIP 캡슐화 방식은 다른 선택 축입니다. 커널·플랫폼·기능 요구사항에 맞춰 선택해야 하며 이 실습은 iptables를 명시합니다. eBPF가 모든 환경에서 항상 더 빠르다는 보장은 없습니다.

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
calicoctl은 정책·IPPool·BGPPeer 등의 Calico 리소스와 진단 기능을 제공하는 CLI입니다. 일치하는 버전을 사용해야 하며 API 서버가 있으면 많은 일반 작업은 kubectl로도 가능합니다. calicoctl node status에는 적절한 노드 환경이 필요합니다.

</details>

6. 현재 Open Source와 비교해 해당 Enterprise/Cloud 에디션에서 추가로 제공하는 기능은?
   - A) 기본 Network Policy
   - B) BGP 라우팅
   - C) 애플리케이션 계층 정책과 DNS/FQDN 정책 등 에디션별 추가 기능
   - D) IPIP 캡슐화

<details>
<summary>정답 보기</summary>

**정답: C) 애플리케이션 계층 정책과 DNS/FQDN 정책 등 에디션별 추가 기능**

**설명:**
현재 에디션 표에서 애플리케이션 계층·DNS/FQDN 정책은 해당 Enterprise/Cloud 기능입니다. 정책 tier와 Goldmane/Whisker 관측성은 Open Source에도 있습니다. WireGuard도 지원되는 Open Source Linux 구성에 제공되므로 모든 고급 기능을 유료로 분류하면 안 됩니다.

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
2020년 2월 25일 공식 발표는 Calico 3.13용 eBPF tech preview 소개이며 GA 발표가 아닙니다. eBPF는 Linux 커널 안에서 실행됩니다. 기존 패킷 처리 일부를 대체할 수 있지만 커널 자체를 우회하거나 모든 부하의 성능 우위를 보장하지 않습니다.

</details>

8. Calico와 Cilium의 Windows 지원을 정확하게 비교한 것은?
   - A) 기본 내장 Service Mesh
   - B) Hubble을 통한 관측성
   - C) Calico는 제약이 있는 Windows IPv4 구성을 지원하며 Cilium 1.20 에이전트는 Linux를 요구한다
   - D) L7 Network Policy 기본 제공

<details>
<summary>정답 보기</summary>

**정답: C) Calico는 제약이 있는 Windows IPv4 구성을 지원하며 Cilium 1.20 에이전트는 Linux를 요구한다**

**설명:**
Calico의 Windows 지원은 명시된 IPv4 VXLAN·BGP 구성에 한정되며 Linux eBPF·IPIP·IPv6/dual stack·WireGuard를 모두 제공하지 않습니다. Cilium 1.20은 Linux 에이전트이며 Windows beta라고 설명하면 안 됩니다. 지원 범위와 운영 복잡도를 실제 요구사항으로 비교해야 합니다.

</details>

9. Calico의 BGP 라우팅 기능과 직접 관련된 요구사항은?
   - A) L7 Network Policy가 필수인 환경
   - B) Service Mesh 내장이 필요한 환경
   - C) BGP 기반 온프레미스 환경
   - D) 고급 관측성이 필수인 환경

<details>
<summary>정답 보기</summary>

**정답: C) BGP 기반 온프레미스 환경**

**설명:**
BGP 인프라와 Pod 라우트를 연동하는 요구는 Calico BGP 기능의 직접적인 사용 사례입니다. 이것만으로 Calico가 모든 환경에서 최선이라고 결론 내릴 수는 없습니다. L7 정책·관측성도 에디션별로 제공되므로 기존의 단순한 제품 순위는 적절하지 않습니다.

</details>

10. 기존 AWS VPC CNI의 Pod 네트워킹을 유지하면서 Calico 정책을 추가하려는 EKS 구성은?
   - A) Calico로 네트워킹과 Policy 모두 처리
   - B) AWS VPC CNI로 네트워킹, Calico로 Network Policy
   - C) Calico로 네트워킹, AWS VPC CNI로 Policy
   - D) Calico와 VPC CNI를 동시에 네트워킹에 사용

<details>
<summary>정답 보기</summary>

**정답: B) AWS VPC CNI로 네트워킹, Calico로 Network Policy**

**설명:**
이 목표에는 AmazonVPC CNI가 네트워킹·IPAM을 유지하고 Calico가 정책을 맡는 policy-only 구성이 맞습니다. VPC CNI 기본 정책 엔진과 Calico를 동시에 실행하면 충돌합니다. Pod IP annotation과 patch 권한 등 공식 전제도 필요합니다. 전체 Calico CNI는 별도 새 클러스터 설계이며 기존 VPC CNI 위에 겹치는 방식이 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../networking/calico/01-introduction.md) | [다음 퀴즈: 아키텍처](02-architecture-quiz.md)
