# Kubernetes 네트워킹 개요 퀴즈

이 퀴즈는 Kubernetes 네트워킹의 기본 개념, CNI(Container Network Interface), 그리고 다양한 CNI 솔루션에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes 네트워킹 모델의 핵심 요구사항이 아닌 것은?

A. 모든 Pod는 NAT 없이 다른 모든 Pod와 통신할 수 있어야 함
B. 모든 노드는 NAT 없이 모든 Pod와 통신할 수 있어야 함
C. Pod가 자신을 보는 IP와 다른 Pod가 그 Pod를 보는 IP가 동일해야 함
D. 모든 Pod는 고정 IP 주소를 가져야 하며 재시작 후에도 유지되어야 함

<details>
<summary>정답 및 설명</summary>

**정답: D. 모든 Pod는 고정 IP 주소를 가져야 하며 재시작 후에도 유지되어야 함**

**설명:**
Kubernetes 네트워킹 모델의 핵심 요구사항은 다음 세 가지입니다:
1. 모든 Pod는 NAT 없이 다른 모든 Pod와 통신 가능
2. 모든 노드는 NAT 없이 모든 Pod와 통신 가능
3. Pod가 보는 자신의 IP와 다른 Pod가 보는 IP가 동일

Pod의 IP 주소는 일시적이며, Pod가 재시작되면 새로운 IP가 할당됩니다. 이것이 바로 Service가 필요한 이유입니다.

</details>

### 2. CNI(Container Network Interface)의 주요 역할로 올바른 것은?

A. Kubernetes API 서버와 통신하여 Pod 스케줄링 결정
B. 컨테이너의 네트워크 인터페이스 생성 및 IP 주소 할당
C. Kubernetes Service의 로드밸런싱 구현
D. 컨테이너 이미지 다운로드 및 캐싱

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨테이너의 네트워크 인터페이스 생성 및 IP 주소 할당**

**설명:**
CNI는 컨테이너 네트워크 연결을 위한 표준 인터페이스입니다. 주요 역할은:
- 컨테이너 생성 시 네트워크 인터페이스 생성 (veth pair)
- IP 주소 할당 (IPAM)
- 라우팅 규칙 설정
- 컨테이너 삭제 시 네트워크 리소스 정리

Kubelet이 CNI 플러그인을 호출하여 Pod의 네트워크를 설정합니다.

</details>

### 3. Overlay 네트워크와 Underlay(Native Routing) 네트워크의 차이점으로 올바른 것은?

A. Overlay는 더 높은 성능을 제공하고, Underlay는 더 많은 오버헤드를 발생시킨다
B. Overlay는 기존 네트워크 위에 가상 네트워크를 구성하고, Underlay는 물리 네트워크에 직접 라우팅한다
C. Overlay는 BGP를 사용하고, Underlay는 VXLAN을 사용한다
D. Overlay는 AWS에서만 사용 가능하고, Underlay는 온프레미스에서만 사용 가능하다

<details>
<summary>정답 및 설명</summary>

**정답: B. Overlay는 기존 네트워크 위에 가상 네트워크를 구성하고, Underlay는 물리 네트워크에 직접 라우팅한다**

**설명:**
- **Overlay 네트워크**: VXLAN, IPIP 등의 캡슐화를 사용하여 기존 네트워크 위에 가상 네트워크를 구성합니다. 설정이 간단하지만 캡슐화 오버헤드가 있습니다.
- **Underlay(Native Routing)**: 물리 네트워크에 직접 라우팅하여 더 높은 성능을 제공합니다. BGP 등을 사용하며, 네트워크 인프라와의 통합이 필요합니다.

</details>

### 4. Kubernetes Service 유형 중 클러스터 내부에서만 접근 가능한 것은?

A. NodePort
B. LoadBalancer
C. ClusterIP
D. ExternalName

<details>
<summary>정답 및 설명</summary>

**정답: C. ClusterIP**

**설명:**
Kubernetes Service 유형별 특징:
- **ClusterIP**: 클러스터 내부에서만 접근 가능한 가상 IP 할당 (기본값)
- **NodePort**: 모든 노드의 특정 포트(30000-32767)로 외부 접근 가능
- **LoadBalancer**: 클라우드 로드밸런서를 프로비저닝하여 외부 접근 가능
- **ExternalName**: 외부 DNS 이름에 대한 CNAME 레코드 생성

</details>

### 5. 다음 CNI 중 eBPF 기술을 핵심으로 사용하는 것은?

A. Flannel
B. Weave Net
C. Cilium
D. AWS VPC CNI

<details>
<summary>정답 및 설명</summary>

**정답: C. Cilium**

**설명:**
Cilium은 eBPF(extended Berkeley Packet Filter)를 핵심 기술로 사용하는 CNI입니다. eBPF의 장점:
- 커널 수준에서 네트워크 처리로 높은 성능
- iptables 대비 더 효율적인 패킷 처리
- L7 수준의 가시성 및 정책 적용
- kube-proxy 대체 가능

Calico도 eBPF 모드를 지원하지만, Cilium은 처음부터 eBPF를 중심으로 설계되었습니다.

</details>

### 6. AWS VPC CNI의 특징으로 올바르지 않은 것은?

A. 각 Pod에 VPC의 실제 IP 주소를 할당한다
B. EC2 인스턴스의 ENI(Elastic Network Interface)를 활용한다
C. Pod당 할당 가능한 IP 수는 인스턴스 유형에 따라 제한된다
D. 기본적으로 L7 Network Policy를 지원한다

<details>
<summary>정답 및 설명</summary>

**정답: D. 기본적으로 L7 Network Policy를 지원한다**

**설명:**
AWS VPC CNI의 특징:
- VPC의 실제 IP 주소를 Pod에 할당 (VPC 네이티브)
- EC2 ENI의 Secondary IP를 활용
- 인스턴스 유형에 따라 최대 Pod 수 제한 (ENI 수 × ENI당 IP 수)
- 기본적으로 L3-L4 Network Policy만 지원 (L7은 Calico나 Cilium과 함께 사용)

L7 Network Policy를 사용하려면 Cilium 같은 별도의 솔루션이 필요합니다.

</details>

### 7. 다음 중 BGP(Border Gateway Protocol)를 지원하는 CNI 조합으로 올바른 것은?

A. Flannel, Weave Net
B. Calico, Cilium
C. AWS VPC CNI, Flannel
D. Weave Net, AWS VPC CNI

<details>
<summary>정답 및 설명</summary>

**정답: B. Calico, Cilium**

**설명:**
BGP를 지원하는 주요 CNI:
- **Calico**: BGP가 핵심 기능, ToR 스위치와의 피어링, Route Reflector 지원
- **Cilium**: BGP 지원 (v1.10+), 멀티클러스터 환경에서 활용

지원하지 않는 CNI:
- **Flannel**: 단순한 오버레이 네트워크, BGP 미지원
- **Weave Net**: 자체 라우팅 프로토콜 사용, BGP 미지원
- **AWS VPC CNI**: VPC 네이티브 라우팅 사용, BGP 미지원

</details>

### 8. Kubernetes Network Policy가 적용되지 않는 트래픽 유형은?

A. Pod에서 다른 Pod로의 트래픽
B. Pod에서 외부 인터넷으로의 트래픽
C. 같은 Pod 내 컨테이너 간의 localhost 트래픽
D. 외부에서 Pod로 들어오는 트래픽

<details>
<summary>정답 및 설명</summary>

**정답: C. 같은 Pod 내 컨테이너 간의 localhost 트래픽**

**설명:**
Network Policy는 Pod 간 트래픽을 제어합니다. 같은 Pod 내의 컨테이너들은:
- 동일한 네트워크 네임스페이스를 공유
- localhost(127.0.0.1)를 통해 통신
- Network Policy의 적용 대상이 아님

Network Policy가 적용되는 트래픽:
- Pod 간 Ingress/Egress 트래픽
- Pod에서 외부로의 Egress 트래픽
- 외부에서 Pod로의 Ingress 트래픽

</details>

### 9. 대규모 Kubernetes 클러스터(500+ 노드)에서 CNI 선택 시 가장 중요하게 고려해야 할 사항은?

A. UI 대시보드 제공 여부
B. 컨트롤 플레인 확장성 및 데이터 동기화 효율성
C. 로고 디자인 및 문서 품질
D. 최신 버전 출시 빈도

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨트롤 플레인 확장성 및 데이터 동기화 효율성**

**설명:**
대규모 클러스터에서 CNI 선택 시 고려사항:

1. **컨트롤 플레인 확장성**:
   - Calico: Typha 컴포넌트로 API 서버 부하 감소
   - Cilium: Operator 모드로 효율적인 동기화

2. **데이터 동기화**:
   - 노드당 에이전트의 리소스 사용량
   - 정책 업데이트 전파 시간

3. **성능**:
   - eBPF 기반 솔루션이 iptables 기반보다 확장성 우수
   - 규칙 수 증가에 따른 성능 저하 정도

</details>

### 10. 다음 중 Ingress와 Service의 차이점으로 올바른 것은?

A. Ingress는 L4에서 동작하고, Service는 L7에서 동작한다
B. Ingress는 HTTP/HTTPS 라우팅 규칙을 정의하고, Service는 Pod 집합에 대한 네트워크 엔드포인트를 제공한다
C. Ingress는 클러스터 내부 통신만 지원하고, Service는 외부 통신만 지원한다
D. Ingress는 TCP만 지원하고, Service는 UDP만 지원한다

<details>
<summary>정답 및 설명</summary>

**정답: B. Ingress는 HTTP/HTTPS 라우팅 규칙을 정의하고, Service는 Pod 집합에 대한 네트워크 엔드포인트를 제공한다**

**설명:**
- **Service**: Pod 집합에 대한 안정적인 네트워크 엔드포인트 제공 (L4)
  - ClusterIP, NodePort, LoadBalancer 유형
  - TCP/UDP 프로토콜 지원

- **Ingress**: HTTP/HTTPS 트래픽 라우팅 규칙 정의 (L7)
  - 호스트 기반 라우팅
  - 경로 기반 라우팅
  - TLS 종료
  - Ingress Controller가 실제 구현

Ingress는 결국 백엔드 Service로 트래픽을 전달합니다.

</details>

---

## 추가 학습 자료

- [Kubernetes 네트워킹 모델](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [CNI 명세](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Network Policy 가이드](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
