# 네트워크 기초 Part 4 퀴즈 — 요청의 여정과 클라우드

> **마지막 업데이트**: 2026년 9월 11일

한 요청의 전체 여정과 클라우드·쿠버네티스 매핑에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 캐시와 기존 연결을 제외한 새로운 HTTPS 연결의 개념적 의존 순서로 옳은 것은 무엇인가요?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) 서버 주소 확인 → 링크·IP 연결 사용 → TCP+TLS 또는 QUIC 핸드셰이크 → HTTP 요청
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP 연결 → DNS 조회 → TLS → 라우팅 → HTTP

<details>
<summary>정답 보기</summary>

**정답: B) 서버 주소 확인 → 링크·IP 연결 사용 → TCP+TLS 또는 QUIC 핸드셰이크 → HTTP 요청**

**설명:**
실제 패킷 추적이 아닌 의존 관계 요약입니다. DNS 메시지도 링크·IP 연결을 사용하며 DNS 통신 중이나 이후에 ARP·IPv6 Neighbor Discovery가 수행될 수 있습니다. NAT는 선택 사항이고 라우팅은 각 관련 패킷에 적용됩니다. HTTP/3은 TLS1.3이 통합된 QUIC을 사용하며 HTTP/1.1·HTTP/2의 HTTPS는 보통 TCP에 별도 TLS 핸드셰이크를 사용합니다.

</details>

2. kube-proxy를 사용하는 클러스터에서 일반적인 ClusterIP Service 전달을 설명하는 짝은 무엇인가요?
   - A) CoreDNS — DHCP
   - B) kube-proxy — NAT + L4 분산
   - C) CNI 플러그인 — TLS 종료
   - D) NetworkPolicy — BGP 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) kube-proxy — NAT + L4 분산**

**설명:**
Linux kube-proxy는 iptables·nftables를 설정하며 IPVS 모드는 Kubernetes1.35부터 deprecated입니다. eBPF 기반 Service 구현은 kube-proxy를 대체할 수 있지만 kube-proxy의 eBPF 모드는 아닙니다. Service·EndpointSlice 상태가 적합한 엔드포인트를 제공합니다. Headless Service에는 ClusterIP가 없고 NetworkPolicy에는 지원 구현이 필요합니다.

</details>

3. 엔드포인트 의존성과 총비용을 확인한 뒤 지원되는 AWS 서비스 트래픽의 NAT Gateway 처리를 줄일 수 있는 방법은 무엇인가요?
   - A) NAT Gateway를 리전마다 하나로 통합한다
   - B) 지원 서비스에 적절한 VPC 엔드포인트를 사용하고 필요한 DNS·경로·접근 정책을 구성한다
   - C) 모든 파드에 공인 IP를 부여한다
   - D) IPv6를 비활성화한다

<details>
<summary>정답 보기</summary>

**정답: B) 지원 서비스에 적절한 VPC 엔드포인트를 사용하고 필요한 DNS·경로·접근 정책을 구성한다**

**설명:**
엔드포인트는 해당 서비스 트래픽을 NAT 경로에서 제외할 수 있지만 인터페이스 엔드포인트에는 시간·데이터 요금이 있으며 구성에 따라 비용이 달라집니다. S3·DynamoDB 게이트웨이 엔드포인트는 추가 엔드포인트 요금이 없습니다. 사설 ECR 이미지 다운로드에는 보통 ecr.api·ecr.dkr 인터페이스 엔드포인트, S3 경로, 사설 DNS와 적절한 접근 권한이 필요합니다. 풀스루 캐시의 첫 다운로드나 외부 Windows 레이어에는 인터넷 접근이 남을 수 있습니다. 총비용과 필요한 송신 경로를 검토해야 하며 비용 절감이나 포트 고갈 제거가 항상 보장되지는 않습니다.

</details>

---

[학습 자료로 돌아가기](../../basics/06-network-fundamentals-part4.md) | [다음 퀴즈: 클러스터 아키텍처](../core/01-cluster-architecture-quiz.md)
