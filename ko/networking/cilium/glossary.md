# 용어 및 약어

> **검토 기준**: Cilium 1.20.1.
> **최종 검토**: 2026년 9월 12일.

Cilium, eBPF, Kubernetes와 네트워킹 용어를 알파벳순으로 정리합니다. 반복된 정의는 하나로 합쳤습니다.

## A

**API(Application Programming Interface)** ⚪

- 애플리케이션 간의 통신을 가능하게 하는 인터페이스 정의 집합

**ARP(Address Resolution Protocol)** 🟣

- 로컬 링크에서 IPv4 주소를 링크 계층 주소(보통 Ethernet MAC 주소)로 해석합니다.
- 원격 목적지에는 다음 홉의 주소를 해석합니다. IPv6는 ARP 대신 Neighbor Discovery를 사용합니다.

**AWS ENI(Elastic Network Interface)** 🟣

- Amazon Web Services에서 제공하는 가상 네트워크 인터페이스
- Cilium의 AWS ENI IPAM 모드에서 사용됨

## B

**BGP(Border Gateway Protocol)** 🟣

- 피어 간 연결성을 광고하는 도메인 간 라우팅 프로토콜입니다.
- Cilium BGP Control Plane은 선택한 접두사를 광고하며, native 라우팅 모드 자체이거나 로컬 데이터 경로 라우트를 설치하는 기능은 아닙니다.

**BPF(Berkeley Packet Filter)** 🟠

- 패킷 필터링을 위한 기술, eBPF의 전신
- 원래 네트워크 패킷 캡처를 위해 개발됨

**BPF 맵(BPF Maps)** 🟠

- BPF 프로그램과 사용자 공간이 상태·이벤트를 공유하는 커널 관리 자료 구조입니다.
- 여러 유형이 키와 값을 사용하지만 ring buffer·queue·stack의 연산은 다릅니다. BPF ring buffer는 map lookup/update/delete를 지원하지 않습니다.

## C

**CGroup(Control Group)** 🟢

- Linux control group은 프로세스를 묶고 CPU·메모리 등의 자원을 집계·제어합니다.
- 컨테이너 런타임이 사용하지만 cgroup 자체가 프로세스·네트워크 네임스페이스 격리를 제공하지는 않습니다.

**CIDR(Classless Inter-Domain Routing)** 🟣

- IP 주소 할당 및 라우팅 집계 방법
- 예: 192.168.1.0/24는 192.168.1.0부터 192.168.1.255까지의 IP 주소 범위를 나타냄

**Cilium** 🔵

- eBPF를 기반으로 하는 오픈 소스 네트워킹, 보안 및 관찰성 솔루션
- Kubernetes CNI 구현체로 사용됨

**Cilium Agent** - Cilium

- 엔드포인트, BPF 프로그램과 정책·데이터 경로 상태를 관리하는 노드 로컬 구성 요소입니다. Cilium이 관리하는 적격 노드에서 실행됩니다.

**Cilium Operator** - Cilium

- CRD 등록, 모드별 IPAM/LB IPAM, 가비지 컬렉션과 활성화한 Ingress/Gateway 컨트롤러 등을 담당하는 클러스터 수준 컨트롤러입니다.
- 복제본 수는 구성할 수 있습니다. 선택적 ID 관리와 ClusterMesh 동기화는 활성 기능에 따라 다르며 노드의 패킷 전달 구성 요소는 아닙니다.

**ClusterMesh** - Cilium

- 서비스 검색, 로드 밸런싱과 원격 ID 정책을 위한 Cilium 멀티 클러스터 네트워크 메타데이터·연결 기능입니다.
- 호환 주소, 신뢰와 연결 경로가 필요하며 공유 스토리지나 모든 정책 리소스의 자동 복제를 제공하지 않습니다.

**CNI(Container Network Interface)** 🟢

- Container Network Interface: 컨테이너 네트워크 연결을 구성하는 명세와 플러그인입니다.
- 현재 Kubernetes에서는 CRI 컨테이너 런타임이 CNI 플러그인을 로드·호출합니다. kubelet의 이전 직접 CNI 관리 플래그는 Kubernetes 1.24에서 제거되었습니다.

**CoreDNS** 🟢

- Kubernetes 클러스터에서 일반적으로 사용되는 DNS 서버
- 서비스 디스커버리에 중요한 역할을 함

**CRD(Custom Resource Definition)** 🟢

- Kubernetes API를 확장하여 사용자 정의 리소스를 정의하는 방법
- Cilium은 CRD를 사용하여 네트워크 정책 등을 정의함

## D

**DaemonSet**

- 스케줄링 제약에 따라 선택된 적격 노드에 데몬 Pod를 실행하는 Kubernetes 컨트롤러입니다. 모든 노드를 반드시 포함하지는 않습니다.

**DNAT(Destination Network Address Translation)** 🟣

- 패킷의 목적지 IP 주소를 수정하는 NAT 유형
- 로드 밸런싱 및 포트 포워딩에 사용됨

**DNS(Domain Name System)** 🟣

- A/AAAA 주소, CNAME 별칭, SRV 서비스 정보 등의 레코드를 제공하는 분산 이름 시스템입니다.
- Cilium DNS 정책과 학습한 IP를 사용하는 FQDN 정책은 관련되지만 서로 다른 제어입니다.

## E

**eBPF(extended Berkeley Packet Filter)** 🟠

- Extended Berkeley Packet Filter: Cilium이 사용하는 프로그래밍 가능한 커널 훅과 관련 기반 기능입니다.
- 검증기가 프로그램 수락 전에 속성을 검사하지만 커널·검증기 구현의 취약점 부재를 보장하지는 않습니다.

**Endpoint** 🔵

- 로컬 데이터 경로·정책 상태를 가진 Cilium 관리 네트워크 엔드포인트이며 보통 Pod에 해당합니다.
- 엔드포인트 ID는 에이전트에 로컬이며 여러 엔드포인트가 공유할 수 있는 보안 ID와 다릅니다.

**Envoy** 🔵

- Cilium이 구성된 HTTP/gRPC 정책, L7 가시성, 프록시 기반 서비스 라우팅에 사용하는 오픈 소스 프록시입니다.
- DNS 정책은 Cilium DNS 프록시를 사용합니다. Kafka L7 정책은 제거되었으며 모든 L7 규칙이 Envoy 인스턴스를 자동 배포하는 것은 아닙니다.

## F

**FQDN(Fully Qualified Domain Name)**

- Fully Qualified Domain Name: DNS 트리에서 전체 위치를 나타내는 절대 이름이며 `www.example.com.`처럼 마지막 루트 점을 쓰기도 합니다.
- Cilium `toFQDNs`는 학습한 목적지 IP를 허용합니다. 자체적으로 HTTPS 서버를 인증하거나 공유 IP의 모든 HTTP Host 값을 제한하지는 않습니다.

## G

**GENEVE(Generic Network Virtualization Encapsulation)**

- 네트워크 가상화를 위한 캡슐화 프로토콜

**gRPC(gRPC Remote Procedure Call)**

- Google에서 개발한 고성능 RPC(원격 프로시저 호출) 프레임워크

## H

**Hubble** 🔵

- 흐름 이벤트, 지원 프로토콜 메타데이터, 메트릭과 질의 인터페이스를 제공하는 Cilium 네트워크 관측 계층입니다.
- 이력은 유한하며 관측 데이터가 손실·필터링될 수 있습니다. 알림·영구 저장·자동 대응에는 구성된 연동이 필요합니다.

## I

**Identity** - Cilium

- 보안 관련 레이블에서 도출한 숫자 보안 식별자입니다. 해당 할당 범위 안에서 여러 엔드포인트가 공유할 수 있습니다.
- CRD 할당 모드에서 CiliumIdentity의 `security-labels`가 원본 필드입니다. 예약 ID와 노드 로컬 ID가 모두 이러한 클러스터 범위 객체로 표현되는 것은 아닙니다.

**IPAM(IP Address Management)** 🟣

- IP Address Management: 주소 할당, 추적과 회수입니다.
- Cilium의 cluster-pool, multi-pool, Kubernetes host-scope, 클라우드별 모드는 할당 주체와 데이터 원본이 다릅니다. 플랫폼 이름이 반드시 별도 `ipam.mode` 값인 것은 아닙니다.

**IPsec** 🟣

- Internet Protocol Security: IP 계층 인증·무결성과 적절한 구성의 기밀성을 제공하는 프로토콜 모음입니다.
- Cilium은 지원되는 노드 간 트래픽 암호화에 IPsec을 사용하며 키 관리와 경로별 제약을 확인해야 합니다.

**Istio**

- 서비스 메시를 구현하는 오픈 소스 플랫폼

## K

**Kafka**

- 분산 이벤트 스트리밍 플랫폼입니다. 워크로드로 사용할 수 있지만 현재 Cilium에는 이전 Kafka 토픽 L7 정책 API가 없습니다.

**kube-proxy** 🟢

- 지원되는 노드 네트워크 방식으로 Service 가상 IP·포트 전달을 구현하는 Kubernetes 구성 요소입니다.
- Cilium은 eBPF로 이 기능을 대체할 수 있습니다. XDP 가속은 선택 사항이며 플랫폼이 선택한 구성을 지원해야 합니다.

**Kubernetes**

- 컨테이너화된 애플리케이션의 배포, 확장 및 관리를 자동화하는 오픈 소스 플랫폼

## L

**L2(Layer 2)**

- OSI 모델의 데이터 링크 계층

**L3(Layer 3)**

- OSI 모델의 네트워크 계층

**L4(Layer 4)**

- OSI 모델의 전송 계층

**L7(Layer 7)**

- OSI 모델의 애플리케이션 계층

**LoadBalancer**

- 트래픽 분산 기능입니다. Kubernetes `type: LoadBalancer`는 컨트롤러·제공자에 구현을 요청하며 해당 구현 없이 외부 로드 밸런서가 보장되지는 않습니다.

## M

**MAC(Media Access Control) 주소**

- Media Access Control 주소: 인터페이스와 연결된 링크 계층 주소입니다.
- 로컬에서 할당하거나 변경할 수 있으므로 고유성과 진위를 무조건 가정하지 않습니다.

**mTLS(mutual TLS)**

- Mutual TLS: 양쪽 피어가 보통 상대 인증서를 검증해 서로 인증하는 TLS 사용 방식입니다.
- 피어 인증과 애플리케이션 인가는 별개입니다. Cilium의 별도 경로 상호 인증과 Beta ztunnel 워크로드 mTLS는 트래픽 보호 방식이 다른 기능입니다.

**MTU(Maximum Transmission Unit)**

- Maximum Transmission Unit: 링크·인터페이스에서 단편화 없이 운반하는 최대 네트워크 계층 패킷 크기이며 IP 헤더를 포함하고 링크 계층 헤더는 제외합니다.
- 경로 MTU는 경로의 제약을 받으며 터널·암호화 오버헤드가 내부 패킷 크기에 영향을 줍니다. TCP MSS나 애플리케이션 페이로드 크기와 다릅니다.

## N

**NAT(Network Address Translation)**

- IP 패킷의 IP 주소 정보를 수정하는 프로세스

**NodePort**

- 할당한 노드 포트를 적격 노드 주소에 사용하는 Kubernetes Service 노출 방식입니다.
- 주소 선택, 트래픽 정책, 방화벽과 플랫폼 라우팅이 연결성을 결정하며 NodePort 선언만으로 공인 접근이 보장되지는 않습니다.

## O

**OSI(Open Systems Interconnection) 모델**

- 네트워크 통신을 7개의 추상 계층으로 분류한 개념적 모델

**Overlay Network**

- 기존 네트워크 위에 구축된 가상 네트워크

## P

**Pod**

- Kubernetes에서 가장 작은 배포 가능한 컴퓨팅 단위

**Proxy**

- 피어 간 통신을 중개하는 구성 요소이며 반드시 별도 물리 서버일 필요는 없습니다.

## R

**RBAC(Role-Based Access Control)**

- 역할에 따라 시스템 리소스에 대한 액세스를 제어하는 방법

## S

**Service**

- 논리적 백엔드 집합에 접근하는 Kubernetes 추상화이며 보통 레이블로 선택한 Pod를 대상으로 합니다.
- 일반 ClusterIP Service에는 가상 IP가 있지만 headless Service에는 없습니다. ExternalName은 DNS 별칭이며 선택자 없는 Service는 수동 관리 EndpointSlice를 사용할 수 있습니다.

**SNAT(Source Network Address Translation)**

- 패킷의 소스 IP 주소를 수정하는 NAT 유형

**Socket**

- 네트워크 또는 로컬 프로세스 간 통신에 사용하는 운영체제 통신 엔드포인트입니다.

## T

**TCP(Transmission Control Protocol)**

- 연결 지향적이고 신뢰할 수 있는 바이트 스트림을 제공하는 전송 프로토콜

**TLS(Transport Layer Security)**

- 네트워크를 통한 통신을 보호하는 암호화 프로토콜

## U

**UDP(User Datagram Protocol)**

- 비연결형 전송 프로토콜

## V

**VETH(Virtual Ethernet)**

- 가상 이더넷 장치로, 일반적으로 쌍으로 생성됨

**VNI(VXLAN Network Identifier)**

- VXLAN Network Identifier: VXLAN 헤더의 24비트 필드입니다.
- Cilium은 오버레이 메타데이터로 ID 정보를 전달할 수 있으며 필드 폭이 수백만 개의 독립 테넌트 네트워크 구성을 보장하지는 않습니다.

**VTEP(VXLAN Tunnel Endpoint)**

- VXLAN 패킷의 캡슐화 및 디캡슐화를 담당하는 엔드포인트

**VXLAN(Virtual Extensible LAN)** 🟣

- 레이어 2 네트워크를 레이어 3 네트워크 위에 오버레이하는 네트워크 가상화 기술
- Cilium의 오버레이 네트워킹 모드 중 하나

## W

**WireGuard** 🟣

- Cilium이 지원되는 노드 간 트래픽에 사용하는 VPN 터널 프로토콜입니다.
- 동일 노드 Pod 트래픽은 노드 터널로 암호화되지 않으며 외부 트래픽과 선택적 노드 암호화에는 별도 제약이 있습니다. IPsec 대비 성능은 동등한 조건의 측정이 필요합니다.

## X

**XDP(eXpress Data Path)** 🟠

- eXpress Data Path: 패킷 처리 훅이며 native XDP는 지원 네트워크 드라이버의 수신 경로에서 실행됩니다.
- PASS는 네트워크 스택으로 계속 전달하며 다른 동작으로 드롭·전송·리다이렉트할 수 있습니다. Cilium XDP 가속은 선택 사항이며 보편적 처리량·DDoS 방어 보장이 아닙니다.

## 공식 근거

- [Cilium identities](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/internals/security-identities.rst)
- [CiliumIdentity schema](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/internals/cilium_operator.rst)
- [Identity management modes](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC addressing / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## 퀴즈

[주제 퀴즈](../../quizzes/networking/cilium/glossary-quiz.md)
