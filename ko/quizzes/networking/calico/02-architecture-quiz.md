# Calico 아키텍처 퀴즈

> **관련 문서**: [Calico 아키텍처](../../../networking/calico/02-architecture.md)
> **마지막 업데이트**: 2026년 2월 22일

## 퀴즈

1. Felix의 주요 역할로 올바르지 않은 것은?
   - A) 인터페이스 관리 (Pod veth pair 생성)
   - B) 라우팅 테이블 프로그래밍
   - C) BGP 피어 연결 관리
   - D) Network Policy 적용

<details>
<summary>정답 보기</summary>

**정답: C) BGP 피어 연결 관리**

**설명:**
BGP 피어 연결 관리는 BIRD의 역할입니다. Felix는 인터페이스 관리, 라우팅 테이블 프로그래밍, iptables/eBPF 규칙 관리, Network Policy 적용을 담당합니다.

</details>

2. BIRD (BIRD Internet Routing Daemon)의 주요 역할은 무엇입니까?
   - A) Network Policy 적용
   - B) Pod IP 할당
   - C) BGP 라우팅 및 라우트 교환
   - D) 데이터스토어 연결 집계

<details>
<summary>정답 보기</summary>

**정답: C) BGP 라우팅 및 라우트 교환**

**설명:**
BIRD는 BGP 피어 연결 관리, 라우트 교환 및 전파, Route Reflector 기능을 담당하는 BGP 라우팅 데몬입니다.

</details>

3. confd의 주요 역할은 무엇입니까?
   - A) Pod 간 트래픽 암호화
   - B) BIRD 설정 파일 동적 생성
   - C) Network Policy 평가
   - D) Kubernetes API 캐싱

<details>
<summary>정답 보기</summary>

**정답: B) BIRD 설정 파일 동적 생성**

**설명:**
confd는 BGP 설정 템플릿을 처리하고, 노드/피어 변경을 감지하여 BIRD 설정을 자동으로 업데이트하는 역할을 합니다.

</details>

4. Typha가 필요한 클러스터 크기는 일반적으로 몇 노드 이상입니까?
   - A) 10+ 노드
   - B) 25+ 노드
   - C) 50+ 노드
   - D) 100+ 노드

<details>
<summary>정답 보기</summary>

**정답: C) 50+ 노드**

**설명:**
Typha는 대규모 클러스터(50+ 노드)에서 필수적인 컴포넌트입니다. 데이터스토어 연결을 집계하여 API 서버 부하를 줄이고 Felix에게 캐시된 데이터를 제공합니다.

</details>

5. Typha를 사용하지 않을 때 발생할 수 있는 문제는 무엇입니까?
   - A) Network Policy가 작동하지 않음
   - B) BGP 피어링 실패
   - C) API 서버에 과도한 부하
   - D) Pod IP 할당 실패

<details>
<summary>정답 보기</summary>

**정답: C) API 서버에 과도한 부하**

**설명:**
Typha 없이는 각 노드의 Felix가 직접 데이터스토어(Kubernetes API)에 연결합니다. 대규모 클러스터에서는 이로 인해 API 서버에 과도한 부하가 발생할 수 있습니다. Typha는 연결을 집계하여 이 문제를 해결합니다.

</details>

6. kube-controllers에 포함된 컨트롤러가 아닌 것은?
   - A) Policy Controller
   - B) Node Controller
   - C) BGP Controller
   - D) WorkloadEndpoint Controller

<details>
<summary>정답 보기</summary>

**정답: C) BGP Controller**

**설명:**
kube-controllers에는 Policy Controller, Namespace Controller, ServiceAccount Controller, WorkloadEndpoint Controller, Node Controller가 포함됩니다. BGP 관련 기능은 BIRD와 confd가 담당합니다.

</details>

7. Calico가 지원하는 데이터스토어 옵션은 무엇입니까?
   - A) etcd만
   - B) Kubernetes API만
   - C) etcd와 Kubernetes API 모두
   - D) MySQL과 PostgreSQL

<details>
<summary>정답 보기</summary>

**정답: C) etcd와 Kubernetes API 모두**

**설명:**
Calico는 독립 etcd 클러스터 또는 Kubernetes API (CRD 사용)를 데이터스토어로 사용할 수 있습니다. Kubernetes API를 사용하면 별도의 etcd 관리가 필요 없어 운영이 간편합니다.

</details>

8. Felix와 Typha 간의 관계를 올바르게 설명한 것은?
   - A) Felix가 Typha를 관리한다
   - B) Typha가 Felix에게 캐시된 데이터를 제공한다
   - C) Felix와 Typha는 독립적으로 동작한다
   - D) Typha가 Felix의 Network Policy를 평가한다

<details>
<summary>정답 보기</summary>

**정답: B) Typha가 Felix에게 캐시된 데이터를 제공한다**

**설명:**
Typha는 데이터스토어에서 데이터를 읽어 캐시하고, 여러 Felix 인스턴스에게 이 데이터를 제공합니다. 이를 통해 데이터스토어(API 서버) 부하를 줄입니다.

</details>

9. Calico CNI 플러그인의 역할은 무엇입니까?
   - A) BGP 라우팅 설정
   - B) Pod 생성 시 네트워크 인터페이스 설정
   - C) Network Policy 적용
   - D) 데이터스토어 동기화

<details>
<summary>정답 보기</summary>

**정답: B) Pod 생성 시 네트워크 인터페이스 설정**

**설명:**
Calico CNI 플러그인은 kubelet이 호출하며, Pod 생성 시 veth pair를 생성하고 IP를 할당하는 등 네트워크 인터페이스 설정을 담당합니다.

</details>

10. FelixConfiguration에서 설정할 수 있는 항목이 아닌 것은?
    - A) bpfEnabled (eBPF 모드 활성화)
    - B) logSeverityScreen (로깅 설정)
    - C) bgpAsNumber (BGP AS 번호)
    - D) healthEnabled (헬스체크)

<details>
<summary>정답 보기</summary>

**정답: C) bgpAsNumber (BGP AS 번호)**

**설명:**
BGP AS 번호는 BGPConfiguration 리소스에서 설정합니다. FelixConfiguration에서는 eBPF 모드, 로깅, IP 자동 감지, 플로우 로그, 헬스체크, 성능 튜닝 등을 설정합니다.

</details>

11. Typha 레플리카 수의 권장 공식은 무엇입니까?
    - A) 노드 수 / 50, 최소 1
    - B) 노드 수 / 100, 최소 2
    - C) 노드 수 / 200, 최소 3
    - D) 노드 수 / 500, 최소 5

<details>
<summary>정답 보기</summary>

**정답: C) 노드 수 / 200, 최소 3**

**설명:**
Typha 레플리카 수는 일반적으로 노드 수 / 200으로 계산하며, 최소 3개를 권장합니다. 이는 고가용성과 부하 분산을 위한 것입니다.

</details>

12. 다음 중 Calico 노드에서 실행되지 않는 컴포넌트는?
    - A) Felix
    - B) BIRD
    - C) confd
    - D) kube-controllers

<details>
<summary>정답 보기</summary>

**정답: D) kube-controllers**

**설명:**
kube-controllers는 별도의 Deployment로 실행되며, 각 노드에서 실행되지 않습니다. Felix, BIRD, confd는 calico-node DaemonSet의 일부로 각 노드에서 실행됩니다.

</details>
