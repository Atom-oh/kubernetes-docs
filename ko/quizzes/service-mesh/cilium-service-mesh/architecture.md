# Cilium Service Mesh 아키텍처 퀴즈

이 퀴즈는 Cilium Service Mesh의 아키텍처, eBPF 데이터패스, 노드 Envoy 프록시, CRD 모델에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Cilium Service Mesh가 전통적인 사이드카 기반 서비스 메시와 다른 주요 특징은 무엇인가요?

A. Kubernetes 네이티브가 아님
B. eBPF를 사용하여 커널 레벨에서 L3/L4 트래픽 처리
C. 모든 트래픽을 사용자 공간에서 처리
D. Pod당 여러 개의 프록시 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. eBPF를 사용하여 커널 레벨에서 L3/L4 트래픽 처리**

**설명:**
Cilium Service Mesh는 eBPF(extended Berkeley Packet Filter)를 사용하여 Linux 커널 내에서 직접 L3/L4 트래픽을 처리합니다. 이는 사용자 공간의 사이드카 프록시를 통해 모든 트래픽을 처리하는 전통적인 서비스 메시와 근본적으로 다릅니다. L7 처리가 필요한 경우에만 노드당 하나의 공유 Envoy 프록시로 트래픽을 전달합니다.

</details>

### 2. Cilium에서 eBPF 프로그램이 실행될 수 있는 훅 포인트가 아닌 것은?

A. XDP (eXpress Data Path)
B. TC (Traffic Control)
C. Application Layer
D. cgroup

<details>
<summary>정답 및 설명</summary>

**정답: C. Application Layer**

**설명:**
eBPF 프로그램은 커널 레벨에서 실행되며, 주요 훅 포인트는 XDP(NIC 드라이버), TC(네트워크 스택 진입점), Socket Operations(소켓 레벨), cgroup(프로세스 그룹)입니다. Application Layer는 사용자 공간에 있으므로 eBPF 훅 포인트가 아닙니다.

</details>

### 3. Cilium의 노드당 Envoy 프록시 모델의 장점은 무엇인가요?

A. 더 복잡한 설정 가능
B. Pod당 메모리 사용량 증가
C. 리소스 효율성과 낮은 지연 시간
D. 모든 트래픽의 암호화 불가능

<details>
<summary>정답 및 설명</summary>

**정답: C. 리소스 효율성과 낮은 지연 시간**

**설명:**
노드당 하나의 Envoy 프록시를 사용하면 Pod당 사이드카를 배포하는 것보다 훨씬 적은 메모리를 사용합니다. 100개 Pod 클러스터에서 Istio는 약 5GB(Pod당 50MB)를 사용하지만, Cilium은 약 500MB(노드당 100MB)만 사용합니다. 또한 L3/L4 트래픽은 eBPF에서 직접 처리되어 지연 시간이 크게 줄어듭니다.

</details>

### 4. CiliumEnvoyConfig CRD의 주요 용도는 무엇인가요?

A. Kubernetes 네트워크 정책 정의
B. 특정 서비스에 대한 Envoy 프록시 설정 정의
C. Pod 스케줄링 규칙 정의
D. 스토리지 클래스 정의

<details>
<summary>정답 및 설명</summary>

**정답: B. 특정 서비스에 대한 Envoy 프록시 설정 정의**

**설명:**
CiliumEnvoyConfig는 네임스페이스 범위의 CRD로, 특정 서비스에 대한 Envoy 프록시 설정(리스너, 라우트, 클러스터 등)을 정의합니다. 이를 통해 HTTP 라우팅, 헤더 조작, 로드 밸런싱 등의 L7 기능을 구성할 수 있습니다.

</details>

### 5. Cilium이 kube-proxy를 대체할 때 사용하는 로드 밸런싱 알고리즘 중 일관된 해싱을 제공하는 것은?

A. Random
B. Round Robin
C. Maglev
D. Least Connection

<details>
<summary>정답 및 설명</summary>

**정답: C. Maglev**

**설명:**
Maglev는 Google이 개발한 일관된 해싱 알고리즘으로, Cilium의 eBPF 기반 로드 밸런서에서 사용됩니다. 이 알고리즘은 백엔드 변경 시에도 기존 연결의 대부분을 유지하는 세션 어피니티를 제공합니다. O(1) 룩업 시간으로 높은 성능을 제공합니다.

</details>

### 6. Cilium Identity에 대한 설명으로 올바른 것은?

A. IP 주소를 기반으로 워크로드를 식별
B. Pod 레이블을 해시하여 숫자 ID를 생성
C. MAC 주소를 사용하여 식별
D. 사용자가 수동으로 할당해야 함

<details>
<summary>정답 및 설명</summary>

**정답: B. Pod 레이블을 해시하여 숫자 ID를 생성**

**설명:**
Cilium Identity는 Pod의 레이블(네임스페이스, 서비스 어카운트, 사용자 정의 레이블 등)을 해시하여 고유한 숫자 ID를 생성합니다. 이 ID 기반 접근 방식은 IP 주소가 변경되어도 정책이 영향받지 않는 장점이 있습니다.

</details>

### 7. Cilium에서 L7 정책이 적용될 때 트래픽 흐름은 어떻게 되나요?

A. 모든 트래픽이 항상 Envoy를 거침
B. L7 정책이 있는 트래픽만 Envoy로 리다이렉트됨
C. Envoy를 완전히 우회함
D. 트래픽이 드롭됨

<details>
<summary>정답 및 설명</summary>

**정답: B. L7 정책이 있는 트래픽만 Envoy로 리다이렉트됨**

**설명:**
Cilium은 효율성을 위해 L7 정책이 적용된 트래픽만 노드 Envoy 프록시로 리다이렉트합니다. L3/L4 수준의 정책만 있거나 정책이 없는 트래픽은 eBPF에서 직접 처리되어 커널 내에서 빠르게 전달됩니다.

</details>

### 8. Cilium의 연결 추적(Connection Tracking)은 어디에서 수행되나요?

A. 사용자 공간의 conntrack 데몬
B. eBPF 맵
C. Envoy 프록시
D. Kubernetes API 서버

<details>
<summary>정답 및 설명</summary>

**정답: B. eBPF 맵**

**설명:**
Cilium은 eBPF 맵을 사용하여 연결 추적을 수행합니다. CT(Connection Tracking) 맵은 커널 내에서 연결 상태를 저장하고 조회하여, 기존 연결에 대한 정책 결정을 캐시하고 빠르게 적용할 수 있습니다.

</details>

### 9. CiliumClusterwideNetworkPolicy와 CiliumNetworkPolicy의 차이점은?

A. 둘 다 동일한 범위를 가짐
B. CiliumClusterwideNetworkPolicy는 클러스터 전체에 적용됨
C. CiliumNetworkPolicy는 더 많은 기능을 가짐
D. CiliumClusterwideNetworkPolicy는 L7 정책을 지원하지 않음

<details>
<summary>정답 및 설명</summary>

**정답: B. CiliumClusterwideNetworkPolicy는 클러스터 전체에 적용됨**

**설명:**
CiliumNetworkPolicy는 네임스페이스 범위이고, CiliumClusterwideNetworkPolicy는 클러스터 전체 범위입니다. 클러스터 전체 정책은 기본 거부 정책이나 모든 네임스페이스에 적용되어야 하는 보안 규칙에 유용합니다. 두 CRD 모두 L7 정책을 지원합니다.

</details>

### 10. SPIFFE ID가 Cilium Service Mesh에서 사용되는 형식은?

A. urn:spiffe:cluster/namespace/pod
B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>
C. https://spiffe.io/id/\<pod-name\>
D. spiffe:\<namespace\>:\<pod-name\>

<details>
<summary>정답 및 설명</summary>

**정답: B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>**

**설명:**
SPIFFE(Secure Production Identity Framework for Everyone) ID는 워크로드의 고유 식별자입니다. Cilium Service Mesh에서 SPIRE와 통합할 때, 각 워크로드는 `spiffe://cluster.local/ns/<namespace>/sa/<service-account>` 형식의 SPIFFE ID를 받습니다. 이 ID는 mTLS 인증에 사용됩니다.

</details>

### 11. Cilium Agent의 역할이 아닌 것은?

A. eBPF 프로그램 관리
B. Envoy 설정 생성 및 동기화
C. Kubernetes API 서버 역할
D. Identity 관리

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubernetes API 서버 역할**

**설명:**
Cilium Agent는 각 노드에서 실행되며, eBPF 프로그램 관리, 정책 컴파일, Envoy 설정 생성/동기화, Identity 관리, 엔드포인트 관리, 흐름 로깅 등을 담당합니다. Kubernetes API 서버는 Kubernetes 컨트롤 플레인의 일부로 Cilium과는 별개입니다.

</details>

### 12. 동일 노드의 Pod 간 통신에서 Cilium이 제공하는 최적화는?

A. 항상 외부 네트워크를 통해 라우팅
B. eBPF를 통한 커널 내 직접 경로로 네트워크 스택 우회
C. 모든 트래픽을 Envoy로 전달
D. 통신 불가

<details>
<summary>정답 및 설명</summary>

**정답: B. eBPF를 통한 커널 내 직접 경로로 네트워크 스택 우회**

**설명:**
Cilium은 동일 노드의 Pod 간 통신에서 eBPF를 사용하여 커널 내 직접 경로를 통해 트래픽을 전달합니다. 이는 전체 Linux 네트워크 스택을 우회하여 매우 낮은 지연 시간(~0.1ms)을 달성합니다.

</details>
