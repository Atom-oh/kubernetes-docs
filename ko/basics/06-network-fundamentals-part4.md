# 네트워크 기초 Part 4 — 요청의 여정과 클라우드 매핑

> **마지막 업데이트**: 2026년 9월 11일

::: tip 4부작 시리즈입니다
[Part 1: 계층 모델과 링크·라우팅](./06-network-fundamentals-part1.md) ·
[Part 2: 전송 계층과 TLS](./06-network-fundamentals-part2.md) ·
[Part 3: 애플리케이션 프로토콜](./06-network-fundamentals-part3.md) ·
**Part 4: 요청의 여정과 클라우드** *(현재 문서)*
:::

이 시리즈의 프로토콜·메커니즘 25개를 예시 요청으로 연결하고 AWS·쿠버네티스의 관련 역할과 비교합니다. 기능상 대응 관계이며 일대일 대체 관계는 아닙니다.

![주소 설정·DNS, 로컬 전달·라우팅, 선택적인 NAT를 거쳐 TCP+TLS의 HTTP/1.1·HTTP/2 또는 TLS가 통합된 QUIC의 HTTP/3으로 이어지는 예시 요청 경로. 캐시와 망 구성에 따라 생략되는 단계가 있다.](../.gitbook/assets/ko-basics-06-network-fundamentals-part4-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-06-network-fundamentals-part4-0.html)

---

## 6. 하나의 요청을 끝까지 따라가기

`https://example.com`에 새로 연결할 때의 개념적 의존 관계입니다. 실제 패킷 추적 결과는 아닙니다. DNS 질의와 핸드셰이크 패킷 자체도 링크·라우팅 계층을 사용하고, 캐시나 기존 연결이 있으면 일부 작업을 생략합니다.

1. **주소 설정** — 호스트는 DHCP, 정적 설정, IPv6 SLAAC·Router Advertisement 또는 관리형 방식으로 주소·경로·리졸버 설정을 이미 갖추고 있습니다.
2. **DNS (또는 DoH)** — 필요할 때 목적지를 조회합니다. 재귀 리졸버는 캐시·위임 조회·전달을 사용할 수 있고 애플리케이션이 루트에 직접 물을 필요는 없습니다. HTTPS 레코드로 연결 매개변수를 알 수도 있습니다.
3. **이웃 해석** — Ethernet의 IPv4에서는 선택한 다음 홉의 MAC이 캐시에 없으면 ARP로 조회합니다. IPv6는 Neighbor Discovery를 사용합니다. 다음 홉은 로컬 목적지 또는 라우터일 수 있습니다.
4. **Ethernet / Wi-Fi** — 해당 다음 홉으로 프레임을 전송합니다. 선택한 경로가 요구할 때만 기본 게이트웨이를 사용합니다.
5. **IP 라우팅** — 라우터는 포워딩 테이블로 패킷을 전달합니다. 경로는 정적·직접 연결·BGP·OSPF 또는 다른 제어 방식으로 구성될 수 있습니다. 요청마다 라우팅 프로토콜을 새로 협상하지는 않습니다.
6. **선택적인 NAT** — IPv4 인터넷 송신 경로에서 사설 주소를 공인 주소로 변환할 수 있습니다. 여러 내부·IPv6 경로는 NAT를 사용하지 않고 사설 주소 간 NAT도 존재합니다.
7. **TCP 또는 QUIC** — 전송 연결을 수립하거나 재사용합니다. HTTP/1.1·HTTP/2는 일반적으로 TCP를, HTTP/3은 UDP 위의 QUIC을 사용합니다.
8. **TLS** — 핸드셰이크 모드에 따라 상대를 인증하고 트래픽 키를 설정합니다. QUIC에서는 TLS 1.3이 7번과 통합됩니다. 재개는 새 인증서 기반 핸드셰이크와 다릅니다.
9. **HTTP** — 협상한 버전으로 요청·응답을 교환합니다. HTTP/3은 QUIC 경로가 필요하며 TCP 경로에서 동작하지 않습니다.
10. **선택적인 애플리케이션 기능** — WebSocket, 브라우저 호환 gRPC, WebRTC는 구현에 따라 추가 연결을 만들거나 기존 전송을 재사용·다중화할 수 있습니다.

**ICMP**는 목적지 도달 불가나 경로에 비해 큰 패킷 등 일부 IP 계층 오류를 알릴 수 있습니다. 모든 오류를 보고하지는 않습니다. 패킷이나 ICMP 오류가 차단될 수 있고 TLS·애플리케이션 오류는 별도 방식으로 처리합니다. 필요한 ICMP 허용과 전송·애플리케이션 로그 및 측정을 함께 사용하세요. ICMP 오류가 없다고 성공이 증명되지는 않습니다.

---

## 7. 클라우드에서 이 개념들은 어디로 가는가

클라우드에도 주소·라우팅·필터링·전송 역할이 있지만 전통적인 장비와 책임 경계가 다릅니다. AWS에서는 다음과 같이 비교할 수 있습니다.

| 전통적 개념 | AWS에서의 대응 |
|---|---|
| 분리와 필터링 | VPC·서브넷은 논리적 망 경계, 보안 그룹·NACL은 필터링이며 VLAN과 동일하지 않음 |
| 라우팅 테이블 | VPC 라우트 테이블, Transit Gateway |
| BGP 피어링 | Direct Connect 가상 인터페이스, 동적 라우팅 Site-to-Site VPN; 정적 VPN 라우팅도 가능 |
| NAT / 사설 서비스 접근 | NAT Gateway는 주소 변환, VPC 엔드포인트는 지원 서비스의 사설 접근 경로 제공 |
| DNS 서버 | Route 53, Resolver 엔드포인트 |
| DHCP | VPC DHCP 옵션 세트 |
| TLS 종료 / 인증서 | ALB HTTPS 리스너·NLB TLS 리스너·CloudFront; ACM은 트래픽 전달이 아닌 지원 인증서 관리 |
| L7 로드밸런싱 | ALB, 별도로 관리하는 서비스 메시의 Istio·Envoy 같은 애플리케이션 프록시 |
| SSH 접속 | Systems Manager Session Manager |
| 내부 구간 암호화 | 애플리케이션·프록시의 TLS/mTLS; 네트워크 계층 암호화는 별도의 설계 선택 |

AWS App Mesh는 기존 설계의 예이며 신규 설계 기본값으로 제시하지 않습니다. AWS가 발표한 지원 종료일은 **2026년 9월 30일**입니다. 기존 배포는 마이그레이션을 계획해야 합니다.

**설계 시 먼저 결정해야 하는 항목 세 가지**를 꼽자면 이렇습니다.

1. **IP 주소 계획** — 온프레미스·Pod·Service 범위를 포함해 연결해야 하는 망의 CIDR을 계획하세요. 중복되면 주소 변환이나 재설계가 필요할 수 있습니다. 주소 변경에는 운영 비용이 있지만 언제나 가장 비싸다는 순위를 단정할 수는 없습니다.
2. **아웃바운드 경로** — 목적지별로 인터넷 또는 사설 서비스 경로를 정하세요. NAT의 시간·데이터 요금, 인터페이스 엔드포인트의 시간·데이터 요금, AZ 간 전송과 가용성 요구를 비교해야 합니다. S3·DynamoDB 게이트웨이 엔드포인트는 추가 엔드포인트 요금이 없지만 모든 인터넷 목적지를 대체하지는 않습니다.
3. **암호화 종료 지점** — 로드밸런서 이후 백엔드 연결을 포함해 구간별 암호화·인증을 명시하세요. 워크로드 요구와 적용 정책을 확인해야 하며 TLS 종료만으로 다음 구간이 보호되지는 않습니다.

---

## 8. 쿠버네티스에서는 누가 이 일을 하는가

클러스터 안에서도 같은 개념이 컴포넌트 이름만 바꿔 반복됩니다. 이 표가 이 시리즈와 이후 심화 문서들을 잇는 다리입니다.

| 전통적 개념 | 쿠버네티스에서의 대응 |
|---|---|
| Pod IP 할당 | CNI/IPAM 통합(VPC CNI, Cilium 등); 반드시 Pod마다 DHCP를 수행하는 것은 아님 |
| 로컬 전달 / 포워딩 | 호스트 인터페이스·이웃 처리·CNI 데이터패스; veth·경로·터널·eBPF 등 구현별 상이 |
| DNS | 보통 CoreDNS를 사용하는 클러스터 DNS; `서비스명.네임스페이스.svc.<클러스터 도메인>`에서 `cluster.local`은 흔한 설정값 |
| Service 가상 IP / L4 분산 | Linux kube-proxy의 iptables·nftables; IPVS는 1.35부터 deprecated. eBPF 구현은 kube-proxy를 대체할 수 있지만 kube-proxy 모드는 아님 |
| Pod 트래픽 정책 | NetworkPolicy를 지원하는 네트워킹 컨트롤러·플러그인이 집행 |
| L7 라우팅 / TLS 종료 | Ingress·Gateway API 리소스와 이를 구현하는 컨트롤러·데이터플레인 |
| 서비스 간 mTLS | 애플리케이션 TLS 또는 설정된 Istio·Linkerd 등 메시; 임의의 CNI 설치만으로 활성화되지 않음 |
| BGP 라우팅 / 광고 | 예: Calico BGP 경로, MetalLB의 Service 주소 BGP 광고; 역할은 서로 다름 |

Pod를 백엔드로 갖는 일반적인 ClusterIP Service는 클러스터 DNS가 Service IP를 반환하고 kube-proxy 또는 대체 구현이 Service·EndpointSlice 상태로 적합한 엔드포인트를 선택합니다. 데이터패스는 같은 노드나 다른 노드의 해당 엔드포인트로 전달합니다. Headless Service는 DNS로 엔드포인트 주소를 노출하고 ExternalName Service는 CNAME을 반환합니다. mTLS는 해당 피어와 정책을 설정했을 때 적용됩니다. 이런 차이 때문에 “모든 계층이 항상 실행된다”는 패킷 흐름 가정은 성립하지 않습니다.

---

## 마무리

프로토콜·메커니즘 25개를 살펴본 뒤에는 각 선택의 절충과 보장 범위를 확인해야 합니다.

TCP는 복구·순서 유지 비용으로 신뢰성 있는 순차 전달을 제공합니다. UDP는 이를 상위 계층에 맡깁니다. QUIC은 UDP 위에 신뢰성 있는 스트림과 통합 보안을 제공합니다. NAT는 공인 IPv4 주소를 절약하지만 외부에서 시작하는 연결을 복잡하게 만들며 ICE·STUN·TURN이 이를 다루는 데 도움을 줍니다. DoH는 리졸버까지의 구간을 보호하며 조직의 가시성은 리졸버·단말 정책에 따라 달라집니다.

장애 조사에서는 각 계층의 실제 보장과 관찰 증거로 원인 범위를 좁히세요. 그럴듯한 프로토콜 설명도 로그·추적·측정으로 다른 가능성과 구분하기 전까지는 가설입니다.

---

## 다음 문서

이 기초 위에서 클러스터 네트워킹으로 넘어갑니다.

- [eBPF 기초](./05-ebpf-fundamentals.md) — 커널에서 패킷을 처리하는 방식
- [Cilium 네트워킹](../networking/cilium/03-networking.md) — eBPF 기반 CNI
- [Calico BGP 심화](../networking/calico/04-bgp-deep-dive.md) — 클러스터 내 BGP 라우팅
- [Amazon VPC CNI](../networking/01-vpc-cni.md) — VPC CNI와 IP 할당

## 참고

프로토콜 목록 구성은 ByteByteGo의 "What Keeps the Internet Running?" 인포그래픽을
출발점으로 삼았으며, 설명과 실무 관점은 별도로 작성했습니다.

공식 참고 자료: [Kubernetes Service proxy modes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [Service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [NAT Gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html), [ECR VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html), [App Mesh lifecycle](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
