# 네트워크 기초 Part 4 퀴즈 — 요청의 여정과 클라우드

> **마지막 업데이트**: 2026년 8월 28일

한 요청의 전체 여정과 클라우드·쿠버네티스 매핑에 대한 이해도를 테스트합니다.

## 객관식 문제

1. `https://example.com` 접속 시 프로토콜이 동작하는 순서로 올바른 것은 무엇인가요?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) DNS 조회 → 게이트웨이 ARP → IP 라우팅/NAT → TCP/QUIC+TLS 연결 → HTTP 요청
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP 연결 → DNS 조회 → TLS → 라우팅 → HTTP

<details>
<summary>정답 보기</summary>

**정답: B) DNS 조회 → 게이트웨이 ARP → IP 라우팅/NAT → TCP/QUIC+TLS 연결 → HTTP 요청**

**설명:**
목적지 IP를 알아야 패킷을 만들 수 있고(DNS), 게이트웨이 MAC을 알아야 프레임을 보낼 수 있으며(ARP), 라우팅과 NAT를 거쳐 상대에 도달한 뒤에야 전송 연결과 암호화(TCP/QUIC+TLS)가 성립하고, 그 위에서 HTTP 요청이 오갑니다. 하위 계층이 먼저 동작해야 상위 계층이 성립하는 구조입니다.

</details>

2. 쿠버네티스에서 Service의 ClusterIP를 실제 파드 IP로 변환하는 컴포넌트와, 그것이 대응되는 전통적 네트워크 개념의 짝으로 올바른 것은 무엇인가요?
   - A) CoreDNS — DHCP
   - B) kube-proxy — NAT + L4 분산
   - C) CNI 플러그인 — TLS 종료
   - D) NetworkPolicy — BGP 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) kube-proxy — NAT + L4 분산**

**설명:**
kube-proxy는 iptables/IPVS(또는 CNI에 따라 eBPF) 규칙으로 ClusterIP라는 가상 IP를 실제 파드 IP로 변환하고 여러 파드에 분산합니다 — 전통적 개념으로는 NAT와 L4 로드밸런싱의 조합입니다. CoreDNS는 DNS, CNI의 IPAM은 DHCP/IP 할당, NetworkPolicy는 방화벽 규칙에 대응합니다.

</details>

3. 아웃바운드 트래픽이 매우 많은 EKS 워크로드에서 NAT Gateway 비용을 줄이는 대표적인 설계는 무엇인가요?
   - A) NAT Gateway를 리전마다 하나로 통합한다
   - B) S3·ECR 등 AWS 서비스 트래픽을 VPC 엔드포인트로 우회시켜 NAT Gateway를 거치지 않게 한다
   - C) 모든 파드에 공인 IP를 부여한다
   - D) IPv6를 비활성화한다

<details>
<summary>정답 보기</summary>

**정답: B) S3·ECR 등 AWS 서비스 트래픽을 VPC 엔드포인트로 우회시켜 NAT Gateway를 거치지 않게 한다**

**설명:**
NAT Gateway는 처리 데이터량 기준으로 과금되므로, S3·ECR처럼 트래픽이 큰 AWS 서비스 경로를 VPC 엔드포인트(게이트웨이/인터페이스)로 돌리면 비용이 크게 줄고 포트 고갈 위험도 낮아집니다. IP 주소 계획, 아웃바운드 경로, 암호화 종료 지점은 설계 초기에 결정할 3대 항목입니다.

</details>

---

[학습 자료로 돌아가기](../../basics/06-network-fundamentals-part4.md) | [다음 퀴즈: 클러스터 아키텍처](../core/01-cluster-architecture-quiz.md)
