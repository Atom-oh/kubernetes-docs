# Cilium Service Mesh 아키텍처 퀴즈

Cilium 1.20.1 기준으로 검토했습니다. 설정, 적용 조건과 공식 근거는 [아키텍처 본문](../../../service-mesh/cilium-service-mesh/01-architecture.md)을 참고하세요.

### 1. Cilium 아키텍처의 특징은 무엇인가요?

- **A.** Kubernetes API 서버를 대체함
- **B.** eBPF L3/L4 처리와 해당되는 L7 트래픽의 Envoy 처리를 결합함
- **C.** 모든 패킷을 Pod별 Envoy로 전달함
- **D.** Kubernetes 리소스를 사용할 수 없음

<details>
<summary>정답 및 설명</summary>

**정답: B. eBPF L3/L4 처리와 해당되는 L7 트래픽의 Envoy 처리를 결합함**

Cilium은 eBPF로 네트워킹과 L3/L4 정책을 구현합니다. 해당 L7 기능에는 Agent 관리 또는 별도 DaemonSet의 Envoy를 사용합니다. 이는 구성 요소 배치 설명이며 보편적인 성능 결과를 의미하지 않습니다.

</details>

### 2. Cilium 데이터패스를 설명하는 커널 부착 메커니즘이 아닌 것은?

- **A.** TC/TCX
- **B.** cgroup 소켓 훅
- **C.** 애플리케이션의 HTTP 핸들러
- **D.** XDP

<details>
<summary>정답 및 설명</summary>

**정답: C. 애플리케이션의 HTTP 핸들러**

HTTP 핸들러는 애플리케이션 코드이며 커널 훅이 아닙니다. Cilium은 TC/TCX와 cgroup 훅을 사용할 수 있고, XDP 가속에는 적절한 설정·장치가 필요합니다. eBPF를 사용한다고 모든 패킷이 모든 훅을 거치는 것은 아닙니다.

</details>

### 3. 노드 범위에서 Envoy 프로세스를 공유한다는 사실로 알 수 있는 것은?

- **A.** 노드당 메모리가 정확히 100MB임
- **B.** 요청 지연이 반드시 0.1ms임
- **C.** 워크로드에 맞춰 용량을 정해야 하는 공유 프록시 수명 주기·리소스·장애 범위가 생김
- **D.** 암호화에 설정이 필요하지 않음

<details>
<summary>정답 및 설명</summary>

**정답: C. 워크로드에 맞춰 용량을 정해야 하는 공유 프록시 수명 주기·리소스·장애 범위가 생김**

Pod별 사이드카보다 프록시 수를 줄일 수 있지만, 전체 리소스에는 Agent, 맵, 제어 평면과 선택 구성 요소도 포함됩니다. 노드 수, 트래픽, 정책과 기능이 실제 비용을 결정합니다. 기존의 고정 5GB 대 500MB 비교는 측정 결과가 아니었습니다.

</details>

### 4. CiliumEnvoyConfig가 정의하는 것은?

- **A.** Pod 스케줄링만 정의함
- **B.** 네임스페이스 범위의 저수준 Envoy 리소스와 Service 리다이렉션·백엔드 동기화
- **C.** 모든 CiliumEndpoint를 대체함
- **D.** kubectl apply 성공만으로 유효성이 보장되는 범용 설정

<details>
<summary>정답 및 설명</summary>

**정답: B. 네임스페이스 범위의 저수준 Envoy 리소스와 Service 리다이렉션·백엔드 동기화**

CEC는 Kubernetes Service를 Envoy Listener, Route, Cluster와 연결합니다. Cilium은 생략된 Listener 주소를 할당하고 xDS 소스를 보완할 수 있습니다. Kubernetes가 내장 Envoy 필드를 모두 검증하지 않으므로 설정 수락과 실제 동작을 확인해야 합니다. CCEC는 클러스터 범위지만 '*'가 Service 와일드카드가 되지는 않습니다.

</details>

### 5. Maglev에 대한 올바른 설명은?

- **A.** HTTP 쿠키 파서임
- **B.** Kubernetes ClientIP 세션 어피니티를 대체함
- **C.** 해당 외부 트래픽에서 일관된 백엔드 선택을 제공하며 세션 어피니티와는 별도임
- **D.** 제거된 백엔드가 기존 연결을 계속 서비스하도록 보장함

<details>
<summary>정답 및 설명</summary>

**정답: C. 해당 외부 트래픽에서 일관된 백엔드 선택을 제공하며 세션 어피니티와는 별도임**

Maglev는 해당 north–south 로드 밸런싱에서 흐름을 백엔드에 일관되게 매핑합니다. 문서화된 소켓 수준 east–west 경로에는 적용되지 않습니다. ClientIP 어피니티와 연결 추적은 별도 기능이며, Maglev가 사용할 수 없는 백엔드를 유지해 주지는 않습니다.

</details>

### 6. Cilium 워크로드 보안 Identity는 어떻게 할당되나요?

- **A.** 항상 Pod IP와 같음
- **B.** Cilium이 Identity 관련 레이블 집합에 숫자 ID를 할당하며 여러 Pod가 공유할 수 있음
- **C.** 사용자가 레이블 해시를 계산해 임의의 CiliumIdentity를 생성함
- **D.** 모든 Pod에 전역 영구 숫자 ID가 있음

<details>
<summary>정답 및 설명</summary>

**정답: B. Cilium이 Identity 관련 레이블 집합에 숫자 ID를 할당하며 여러 Pod가 공유할 수 있음**

Identity 관련 레이블에는 네임스페이스, ServiceAccount와 선택한 워크로드 레이블이 포함될 수 있습니다. 할당기가 집합을 ID로 해석하며, 사용자 계산 해시나 반드시 Pod별로 고유한 값이 아닙니다. CiliumEndpoint/CiliumIdentity와 Agent의 cilium-dbg identity list로 조회하세요.

</details>

### 7. 어떤 트래픽이 Envoy를 사용할 수 있나요?

- **A.** 모든 설정의 모든 패킷
- **B.** HTTP L7 정책 트래픽과 지원되는 Service·Ingress·Gateway 설정으로 리다이렉트된 트래픽
- **C.** CiliumNetworkPolicy HTTP 규칙이 있는 흐름만 가능하고 Gateway 트래픽은 불가능
- **D.** 모든 Pod에 Envoy 사이드카가 없으면 어떤 트래픽도 사용 불가

<details>
<summary>정답 및 설명</summary>

**정답: B. HTTP L7 정책 트래픽과 지원되는 Service·Ingress·Gateway 설정으로 리다이렉트된 트래픽**

HTTP 정책은 해당 ingress 또는 egress 트래픽을 Envoy로 보냅니다. CEC Service 로드 밸런싱과 Gateway/Ingress도 Envoy를 요구할 수 있습니다. 프록시를 거친 요청의 응답은 기존 프록시 연결을 사용하며, 응답마다 독립적으로 선택하는 리다이렉트가 아닙니다.

</details>

### 8. Cilium BPF 연결 추적의 용도는?

- **A.** Kubernetes API 대체
- **B.** 흐름 상태 유지와 응답 인식을 수행하며 정책 검사와 함께 동작
- **C.** 첫 허용 결정을 모든 이후 패킷에 영구 캐시
- **D.** HTTP 애플리케이션 자격 증명 저장

<details>
<summary>정답 및 설명</summary>

**정답: B. 흐름 상태 유지와 응답 인식을 수행하며 정책 검사와 함께 동작**

CT 맵은 흐름 상태, 수명과 변환·프록시 정보를 추적합니다. 릴리스된 엔드포인트 데이터패스는 명시적 예외를 제외하고 연결을 시작한 방향의 신규·기존 트래픽에 정책을 검사하고, 인식된 응답을 상태 기반으로 처리합니다. CT 캐시는 정책 적용을 전면 면제하는 기능이 아닙니다.

</details>

### 9. CiliumClusterwideNetworkPolicy와 CiliumNetworkPolicy의 차이는?

- **A.** Kubernetes 리소스 범위가 같음
- **B.** CCNP는 클러스터 범위, CNP는 네임스페이스 범위이며 실제 대상은 selector로 결정
- **C.** CNP만 L7 규칙을 표현할 수 있음
- **D.** 모든 CCNP는 반드시 모든 네임스페이스를 거부함

<details>
<summary>정답 및 설명</summary>

**정답: B. CCNP는 클러스터 범위, CNP는 네임스페이스 범위이며 실제 대상은 selector로 결정**

두 리소스 모두 해당되는 L7 규칙을 지원합니다. 리소스 범위와 엔드포인트 선택은 별개이므로 클러스터 범위라는 이유만으로 모든 워크로드를 선택하거나 거부하지 않습니다. 다른 적용 정책의 허용 규칙도 고려해야 합니다.

</details>

### 10. Cilium 베타 out-of-band 상호 인증의 기본 SPIFFE ID 형식은?

- **A.** urn:spiffe:cluster/namespace/pod
- **B.** `spiffe://spiffe.cilium/identity/<numeric-security-identity>`
- **C.** 모든 Cilium 설치에서 `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`
- **D.** `https://spiffe.io/id/<pod-name>`

<details>
<summary>정답 및 설명</summary>

**정답: B. `spiffe://spiffe.cilium/identity/<numeric-security-identity>`**

Cilium의 SPIRE provider는 설정한 trust domain 아래에 `/identity/<numeric-id>` 경로를 구성하며 기본 domain은 spiffe.cilium입니다. Agent가 Cilium 보안 Identity를 대신합니다. 인증 교환은 데이터 경로 밖에서 수행하고, 애플리케이션 암호화에는 별도 WireGuard/IPsec 설정이 필요합니다. Out-of-band 기능은 여전히 베타·미완성 상태입니다. 별도의 ztunnel 암호화 베타는 다른 워크로드 Identity 모델을 사용하므로 이 정답이 해당 인증서 경로를 설명하지는 않습니다.

</details>

### 11. Cilium Agent의 역할이 아닌 것은?

- **A.** 로컬 eBPF 프로그램·맵 관리
- **B.** 로컬 정책과 Envoy 설정 관리
- **C.** Kubernetes API 서버 역할
- **D.** 로컬 엔드포인트와 Identity 관련 관리

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubernetes API 서버 역할**

Agent는 노드에서 실행하고 Kubernetes API 서버는 별도 제어 평면 구성 요소로 남습니다. Cilium Operator도 별도 Deployment로서 Identity 가비지 컬렉션과 해당 IPAM 작업 등의 클러스터 전체 기능을 담당합니다.

</details>

### 12. 동일 노드의 Pod 트래픽에 대한 올바른 설명은?

- **A.** 항상 노드 밖으로 나가야 함
- **B.** 적절한 BPF host-routing 경로는 호스트 상위 네트워크 계층을 우회할 수 있지만 실제 경로는 설정에 따라 달라짐
- **C.** 모든 Linux·Pod 네트워크 스택을 항상 우회함
- **D.** 지연이 반드시 0.1ms임

<details>
<summary>정답 및 설명</summary>

**정답: B. 적절한 BPF host-routing 경로는 호스트 상위 네트워크 계층을 우회할 수 있지만 실제 경로는 설정에 따라 달라짐**

BPF host routing은 요건을 충족하면 호스트 상위 스택과 netfilter를 우회할 수 있습니다. Pod 프로토콜 스택은 남습니다. Legacy routing, 엔드포인트 장치 모드, L7 정책과 통합 구성에 따라 경로가 바뀌며, 지연은 측정해야 합니다.

</details>
