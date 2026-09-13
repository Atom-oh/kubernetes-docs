# Kubernetes 네트워킹 개요 퀴즈

2026년 9월 11일 검토. 버전·플랫폼 조건은 [네트워킹 개요](../../networking/README.md)와 공식 근거를 함께 확인합니다.

## 퀴즈 문제

### 1. Kubernetes 네트워킹 모델이 보장하지 않는 것은?

- A. 일반 Pod는 의도적인 분리를 고려하면서 Pod 네트워크로 직접 연결 가능
- B. 노드 에이전트는 자기 노드의 Pod에 접근 가능
- C. 일반 Pod 안의 컨테이너는 네트워크 네임스페이스 공유
- D. 재생성된 Pod가 항상 같은 IP 유지

<details>
<summary>정답 및 설명</summary>

**정답: D. 재생성된 Pod가 항상 같은 IP 유지**

대체 Pod는 다른 IP를 받을 수 있으며, 같은 Pod 내부 컨테이너의 재시작이 네트워크 sandbox 재생성을 반드시 뜻하지는 않습니다. Service는 바뀌는 엔드포인트에 안정적인 검색 수단을 제공합니다. 실제 연결 성공 여부는 정책과 라우팅에도 달려 있습니다.

</details>

### 2. 현재 Kubernetes에서 CNI의 주된 역할은?

- A. API 서버를 통해 Pod 스케줄링
- B. 컨테이너 네트워킹·주소 설정을 위한 런타임 인터페이스 제공
- C. 모든 Service 로드 밸런싱 구현 대체
- D. 컨테이너 이미지 다운로드

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨테이너 네트워킹·주소 설정을 위한 런타임 인터페이스 제공**

kubelet은 CRI로 sandbox 작업을 요청하고 컨테이너 런타임이 CNI 플러그인을 관리·호출합니다. 플러그인은 네트워크 작업을 수행하며 IPAM을 위임하거나 공급자별 에이전트를 사용할 수 있습니다. veth pair는 흔한 구현이지 모든 CNI의 필수 조건은 아닙니다.

</details>

### 3. Overlay와 native routing을 구분하는 설명은?

- A. Overlay가 항상 더 빠름
- B. Overlay는 다른 네트워크 위에서 트래픽을 캡슐화하고 native routing은 해당 캡슐화 없이 하부 경로 사용
- C. Native routing에는 항상 VXLAN 필요
- D. Overlay는 AWS에서만 사용 가능

<details>
<summary>정답 및 설명</summary>

**정답: B. Overlay는 다른 네트워크 위에서 트래픽을 캡슐화하고 native routing은 해당 캡슐화 없이 하부 경로 사용**

VXLAN/IPIP는 캡슐화 예입니다. Native routing에는 적절한 경로 설계가 필요하고 BGP를 사용할 수 있지만 항상 필수는 아닙니다. 성능을 판단하기 전에 MTU, 암호화, 정책, 트래픽, 하드웨어를 비교합니다.

</details>

### 4. 기본적으로 클러스터 내부 가상 IP를 제공하는 Service 유형은?

- A. NodePort
- B. LoadBalancer
- C. ClusterIP
- D. ExternalName

<details>
<summary>정답 및 설명</summary>

**정답: C. ClusterIP**

ClusterIP가 기본 유형입니다. 일반적인 내부 노출 방식은 보안 경계나 도달성 보장과 다릅니다. NodePort는 설정된 노드 주소·포트를 사용하고 LoadBalancer에는 실제 구현이 필요하며 내부용일 수도 있습니다. ExternalName은 DNS 별칭을 제공하고 headless Service는 가상 IP를 생략합니다.

</details>

### 5. eBPF 기반 네트워킹 데이터 플레인과 Hubble을 함께 제공하는 프로젝트는?

- A. Flannel
- B. 원래 Weave Net 프로젝트
- C. Cilium
- D. AWS VPC CNI

<details>
<summary>정답 및 설명</summary>

**정답: C. Cilium**

Cilium은 eBPF와 Hubble 관측을 제공하고 해당 L7 기능에는 Envoy를 사용합니다. Calico 데이터 플레인 옵션과 AWS 정책 에이전트 등 다른 프로젝트도 eBPF를 사용합니다. 기술 이름만으로 보편적인 성능 순위가 정해지지는 않습니다.

</details>

### 6. 공식 EKS VPC-CNI/Auto Mode 정책 기능에 대한 설명으로 부정확한 것은?

- A. VPC CNI는 VPC 주소와 EC2 ENI/prefix 사용
- B. 노드별 Pod 용량은 인스턴스 한계·할당 모드·kubelet 상한에 영향받음
- C. 지원되는 EKS 구성은 표준·Admin 네트워크 정책 제공
- D. DNS 기반 ApplicationNetworkPolicy라는 이름이 현재 HTTP 메서드·본문 검사를 의미함

<details>
<summary>정답 및 설명</summary>

**정답: D. DNS 기반 ApplicationNetworkPolicy라는 이름이 현재 HTTP 메서드·본문 검사를 의미함**

AWS는 Auto Mode의 DNS/FQDN ApplicationNetworkPolicy와 Auto Mode·지원 EC2/VPC-CNI 구성의 Admin ClusterNetworkPolicy를 문서화합니다. DNS 기반 네트워크 계층 제어는 HTTP 검사와 다릅니다. Linux EC2, Windows, Fargate의 지원 조건도 다르며 표준 EC2 add-on이 Auto Mode 구현과 같지는 않습니다.

</details>

### 7. BGP 제어 평면 옵션을 제공하는 조합은?

- A. Flannel과 원래 Weave Net
- B. Calico와 Cilium
- C. AWS VPC CNI와 Flannel
- D. 원래 Weave Net과 AWS VPC CNI

<details>
<summary>정답 및 설명</summary>

**정답: B. Calico와 Cilium**

Calico와 Cilium은 적절한 peer에 경로를 광고할 수 있습니다. BGP만으로 애플리케이션 서비스 검색, 워크로드 인증, 암호화가 제공되지는 않습니다. 경로 소유 관계와 선택한 CNI의 현재 BGP API·토폴로지 전제를 확인합니다.

</details>

### 8. 일반적인 Pod 간 Kubernetes NetworkPolicy 격리 범위 밖인 트래픽은?

- A. 다른 Pod 사이의 트래픽
- B. Pod에서 외부 엔드포인트로의 egress
- C. 한 Pod 네트워크 네임스페이스를 공유하는 컨테이너 간 localhost 통신
- D. 외부에서 Pod로 진입하는 트래픽

<details>
<summary>정답 및 설명</summary>

**정답: C. 한 Pod 네트워크 네임스페이스를 공유하는 컨테이너 간 localhost 통신**

Pod 네트워크 네임스페이스를 공유하는 컨테이너는 localhost로 통신할 수 있습니다. NetworkPolicy에는 강제 구현이 필요하고 정의된 예외·구현별 차이가 있습니다. 모든 host·주소 변환·터널 흐름이 같은 방식으로 제어된다고 추정하지 않습니다.

</details>

### 9. 큰 클러스터를 평가할 때 유용한 확장성 기준은?

- A. 대시보드 제공 여부만
- B. 컨트롤러/API 부하, 상태 전파, 노드별 리소스, 실제 변경 부하에서의 동작
- C. 로고 모양
- D. 릴리스 빈도만

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨트롤러/API 부하, 상태 전파, 노드별 리소스, 실제 변경 부하에서의 동작**

정책·엔드포인트 cardinality, 변경 전파, 연결 변경, 장애 복구, 실제 데이터 플레인 부하를 시험합니다. 노드 수 기준이나 eBPF 표시만으로 적합성이 입증되지 않습니다. 제품 구성 요소와 확장 메커니즘이 선택한 설치 모드에 맞아야 합니다.

</details>

### 10. Ingress와 Service의 올바른 관계는?

- A. Ingress는 L4 전용이고 Service는 L7 전용
- B. Ingress는 HTTP/HTTPS 라우팅을, Service는 네트워크 엔드포인트·검색을 정의
- C. Service는 항상 외부용
- D. Ingress는 UDP 전용

<details>
<summary>정답 및 설명</summary>

**정답: B. Ingress는 HTTP/HTTPS 라우팅을, Service는 네트워크 엔드포인트·검색을 정의**

Ingress에는 컨트롤러·데이터 플레인이 필요하고 보통 Service 백엔드를 참조합니다. 데이터 플레인이 Pod IP나 NodePort에 직접 연결할 수 있어 Service 가상 IP가 반드시 추가 패킷 홉은 아닙니다. 실제 구현의 Service 프로토콜·로드 밸런서 지원도 확인합니다.

</details>
