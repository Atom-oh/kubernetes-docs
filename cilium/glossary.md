# 용어 및 약어

이 문서는 Cilium과 관련된 주요 용어 및 약어에 대한 설명을 제공합니다.

## A

**API(Application Programming Interface)**
- 애플리케이션 간의 통신을 가능하게 하는 인터페이스 정의 집합

**AWS ENI(Elastic Network Interface)**
- Amazon Web Services에서 제공하는 가상 네트워크 인터페이스

**ARP(Address Resolution Protocol)**
- IP 주소를 MAC 주소로 변환하는 프로토콜

## B

**BGP(Border Gateway Protocol)**
- 인터넷에서 라우팅 정보를 교환하는 데 사용되는 표준 외부 게이트웨이 프로토콜

**BPF(Berkeley Packet Filter)**
- 패킷 필터링을 위한 기술, eBPF의 전신

**BPF 맵(BPF Maps)**
- eBPF 프로그램에서 데이터를 저장하고 검색하는 데 사용되는 키-값 저장소

## C

**CGroup(Control Group)**
- Linux 커널 기능으로 프로세스 그룹의 리소스 사용을 제한하고 격리

**CIDR(Classless Inter-Domain Routing)**
- IP 주소 할당 및 라우팅 집계 방법

**CNI(Container Network Interface)**
- 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스

**CoreDNS**
- Kubernetes 클러스터에서 일반적으로 사용되는 DNS 서버

**CRD(Custom Resource Definition)**
- Kubernetes API를 확장하여 사용자 정의 리소스를 정의하는 방법

## D

**DNAT(Destination Network Address Translation)**
- 패킷의 목적지 IP 주소를 수정하는 NAT 유형

**DNS(Domain Name System)**
- 도메인 이름을 IP 주소로 변환하는 시스템

**DaemonSet**
- 모든 노드에서 포드의 복사본을 실행하는 Kubernetes 리소스

## E

**eBPF(extended Berkeley Packet Filter)**
- Linux 커널에서 안전하게 프로그램을 실행할 수 있는 기술

**Endpoint**
- Cilium에서 네트워크 정책이 적용되는 네트워크 엔드포인트(일반적으로 포드)

**Envoy**
- L7 프록시 및 통신 버스로 사용되는 오픈 소스 엣지 및 서비스 프록시

## F

**FQDN(Fully Qualified Domain Name)**
- 호스트의 전체 도메인 이름(예: www.example.com)

## G

**GENEVE(Generic Network Virtualization Encapsulation)**
- 네트워크 가상화를 위한 캡슐화 프로토콜

**gRPC(gRPC Remote Procedure Call)**
- Google에서 개발한 고성능 RPC(원격 프로시저 호출) 프레임워크

## H

**Hubble**
- Cilium의 네트워크 가시성 및 모니터링 구성 요소

## I

**IPAM(IP Address Management)**
- IP 주소의 계획, 추적 및 관리

**IPsec(Internet Protocol Security)**
- IP 통신의 보안을 위한 프로토콜 스위트

**Istio**
- 서비스 메시를 구현하는 오픈 소스 플랫폼

## K

**Kafka**
- 분산 스트리밍 플랫폼

**kube-proxy**
- Kubernetes 서비스 추상화를 구현하는 네트워크 프록시

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
- 트래픽을 여러 서버에 분산하는 장치 또는 서비스

## M

**MAC(Media Access Control) 주소**
- 네트워크 인터페이스에 할당된 고유 식별자

**MTU(Maximum Transmission Unit)**
- 네트워크에서 전송할 수 있는 최대 패킷 크기

**mTLS(mutual TLS)**
- 클라이언트와 서버 모두 인증서로 서로를 인증하는 TLS의 확장

## N

**NAT(Network Address Translation)**
- IP 패킷의 IP 주소 정보를 수정하는 프로세스

**NodePort**
- 각 노드의 IP에서 정적 포트를 노출하는 Kubernetes 서비스 유형

## O

**OSI(Open Systems Interconnection) 모델**
- 네트워크 통신을 7개의 추상 계층으로 분류한 개념적 모델

**Overlay Network**
- 기존 네트워크 위에 구축된 가상 네트워크

## P

**Pod**
- Kubernetes에서 가장 작은 배포 가능한 컴퓨팅 단위

**Proxy**
- 클라이언트와 서버 간의 중개자 역할을 하는 서버

## R

**RBAC(Role-Based Access Control)**
- 역할에 따라 시스템 리소스에 대한 액세스를 제어하는 방법

## S

**Service**
- Kubernetes에서 포드 집합에 대한 안정적인 엔드포인트를 제공하는 추상화

**SNAT(Source Network Address Translation)**
- 패킷의 소스 IP 주소를 수정하는 NAT 유형

**Socket**
- 네트워크를 통한 프로세스 간 통신의 엔드포인트

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
- VXLAN 네트워크를 식별하는 24비트 식별자

**VTEP(VXLAN Tunnel Endpoint)**
- VXLAN 패킷의 캡슐화 및 디캡슐화를 담당하는 엔드포인트

**VXLAN(Virtual Extensible LAN)**
- 계층 2 네트워크를 계층 3 네트워크 위에 오버레이하는 네트워크 가상화 기술

## W

**WireGuard**
- 현대적이고 빠르며 안전한 VPN 터널 프로토콜

## X

**XDP(eXpress Data Path)**
- 네트워크 패킷을 매우 빠르게 처리하기 위한 eBPF 기반 기술
