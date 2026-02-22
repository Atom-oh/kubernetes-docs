# Calico 고급 주제 퀴즈

> **관련 문서**: [Calico 고급 주제](../../../networking/calico/07-advanced-topics.md)
> **마지막 업데이트**: 2025년 2월 22일

## 퀴즈

1. Calico Block-based IPAM의 기본 블록 크기는 얼마입니까?
   - A) /24 (256 IPs)
   - B) /26 (64 IPs)
   - C) /28 (16 IPs)
   - D) /30 (4 IPs)

<details>
<summary>정답 보기</summary>

**정답: B) /26 (64 IPs)**

**설명:**
Calico IPAM은 기본적으로 /26 크기의 블록(64개 IP 주소)을 각 노드에 할당합니다. 이 블록 기반 접근 방식은 라우팅 테이블 크기를 줄이고 IP 할당 효율성을 높입니다. 블록 크기는 IPPool 설정에서 `blockSize` 파라미터로 조정할 수 있습니다.

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
블록 어피니티는 IP 블록을 특정 노드에 연결하여 해당 노드에서 생성되는 Pod에 해당 블록의 IP를 할당합니다. 이를 통해 노드별로 연속된 IP 범위를 사용하게 되어 라우팅이 단순해지고 효율적인 BGP 광고가 가능합니다.

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
FelixConfiguration에서 `wireguardEnabled: true`를 설정하면 노드 간 Pod 트래픽이 WireGuard로 암호화됩니다. WireGuard는 현대적인 암호화 프로토콜로, 설정이 간단하고 성능이 우수합니다. 추가로 `wireguardInterfaceName`으로 인터페이스 이름을 지정할 수 있습니다.

</details>

4. WireGuard와 IPsec 비교에서 WireGuard의 장점이 아닌 것은?
   - A) 더 간단한 설정
   - B) 더 나은 성능
   - C) 더 오래된 검증된 기술
   - D) 더 작은 코드베이스

<details>
<summary>정답 보기</summary>

**정답: C) 더 오래된 검증된 기술**

**설명:**
IPsec이 더 오래되고 검증된 기술입니다. WireGuard는 비교적 새로운 프로토콜로, 간단한 설정, 더 나은 성능, 더 작은 코드베이스(약 4,000줄)가 장점입니다. IPsec은 복잡하지만 오랜 기간 검증되었고 FIPS 준수가 필요한 환경에서 선호됩니다.

</details>

5. Calico Egress Gateway의 주요 사용 사례는 무엇입니까?
   - A) 클러스터로 들어오는 트래픽 로드밸런싱
   - B) 특정 Pod의 외부 통신을 고정 IP로 SNAT하여 방화벽 규칙 단순화
   - C) DNS 쿼리 캐싱
   - D) TLS 인증서 관리

<details>
<summary>정답 보기</summary>

**정답: B) 특정 Pod의 외부 통신을 고정 IP로 SNAT하여 방화벽 규칙 단순화**

**설명:**
Egress Gateway는 특정 워크로드의 외부 트래픽이 지정된 게이트웨이 노드를 통해 나가도록 하여 고정된 소스 IP를 사용하게 합니다. 이를 통해 외부 방화벽에서 클러스터 트래픽을 쉽게 식별하고 제어할 수 있으며, 규정 준수 요구사항을 충족할 수 있습니다.

</details>

6. 멀티클러스터 Federation에서 Calico가 지원하는 기능이 아닌 것은?
   - A) 클러스터 간 Pod IP 라우팅
   - B) 클러스터 간 Network Policy 적용
   - C) 자동 데이터베이스 복제
   - D) 클러스터 간 Service 연결

<details>
<summary>정답 보기</summary>

**정답: C) 자동 데이터베이스 복제**

**설명:**
Calico Federation은 여러 클러스터 간 네트워크 연결과 정책 관리를 지원합니다. Pod IP 라우팅, 클러스터 간 Network Policy 적용, Service 연결이 가능하지만, 데이터베이스 복제와 같은 애플리케이션 레벨 기능은 Calico의 범위가 아닙니다.

</details>

7. Calico의 Windows 컨테이너 지원 상태로 올바른 것은?
   - A) 지원하지 않음
   - B) 베타 지원
   - C) 완전 지원 (GA)
   - D) 실험적 기능만 지원

<details>
<summary>정답 보기</summary>

**정답: C) 완전 지원 (GA)**

**설명:**
Calico는 Windows 컨테이너를 완전히 지원합니다(GA). Windows Server 2019 이상에서 동작하며, HNS(Host Networking Service)와 통합됩니다. Linux 노드와 Windows 노드가 혼합된 클러스터에서도 Network Policy를 일관되게 적용할 수 있습니다.

</details>

8. Calico Enterprise와 OSS의 핵심 차이점이 아닌 것은?
   - A) L7 Network Policy 지원
   - B) 플로우 로그 시각화 UI
   - C) Pod 네트워킹 기능
   - D) 컴플라이언스 보고서

<details>
<summary>정답 보기</summary>

**정답: C) Pod 네트워킹 기능**

**설명:**
기본 Pod 네트워킹은 OSS와 Enterprise 모두 동일하게 제공됩니다. Enterprise 버전은 L7 Network Policy, 플로우 로그 시각화 UI, 컴플라이언스 보고서, 위협 탐지, 다중 테넌시 RBAC 등 고급 보안 및 관측성 기능을 추가로 제공합니다.

</details>

9. 1000개 이상 노드 클러스터에서 권장되는 Typha 레플리카 수 공식은?
   - A) 노드 수 / 100
   - B) 노드 수 / 200, 최소 3
   - C) 노드 수 / 50
   - D) 고정 5개

<details>
<summary>정답 보기</summary>

**정답: B) 노드 수 / 200, 최소 3**

**설명:**
Typha 레플리카 수는 일반적으로 노드 수 / 200으로 계산하며, 최소 3개를 권장합니다. 예를 들어 1000개 노드 클러스터에서는 약 5개의 Typha 인스턴스가 필요합니다. 이는 각 Typha가 약 200개의 Felix 연결을 효율적으로 처리할 수 있기 때문입니다.

</details>

10. Calico에서 IPv6 / 듀얼스택을 설정할 때 필요한 리소스는?
    - A) IPv6용 별도의 IPPool 생성
    - B) 특별한 설정 없이 자동 지원
    - C) IPv6 전용 Calico 버전 설치
    - D) Linux 커널 재컴파일

<details>
<summary>정답 보기</summary>

**정답: A) IPv6용 별도의 IPPool 생성**

**설명:**
듀얼스택을 사용하려면 IPv4와 IPv6 각각에 대한 IPPool을 생성해야 합니다. IPv6 IPPool은 `cidr` 필드에 IPv6 주소 범위를 지정합니다. Kubernetes 클러스터도 듀얼스택 모드로 구성되어 있어야 하며, FelixConfiguration에서 `ipv6Support: Enabled`를 설정합니다.

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
`calicoctl ipam show` 명령어는 IP 할당 현황을 보여주며, `--show-blocks` 옵션을 추가하면 노드별 블록 할당 상태를 확인할 수 있습니다. IP 풀의 사용률이 높으면 새로운 Pod에 IP를 할당할 수 없으므로 IP 풀 확장이나 정리가 필요합니다.

</details>

12. 대규모 클러스터에서 etcd 대신 Kubernetes datastore를 선택해야 하는 이유가 아닌 것은?
    - A) 별도의 etcd 클러스터 운영 불필요
    - B) Kubernetes API를 통한 통합 관리
    - C) 더 빠른 읽기 성능
    - D) 운영 복잡성 감소

<details>
<summary>정답 보기</summary>

**정답: C) 더 빠른 읽기 성능**

**설명:**
Kubernetes datastore는 별도 etcd 운영이 불필요하고 Kubernetes와 통합 관리되어 운영이 단순합니다. 그러나 읽기 성능 면에서는 전용 etcd가 더 빠를 수 있습니다. 대부분의 경우 Kubernetes datastore로 충분하지만, 수천 개 이상의 정책이 있는 극대규모 환경에서는 전용 etcd를 고려할 수 있습니다.

</details>
