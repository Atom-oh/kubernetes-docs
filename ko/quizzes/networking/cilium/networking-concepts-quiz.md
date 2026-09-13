# Cilium 네트워킹 개념 퀴즈

> **검토 기준**: Cilium 1.20.1.
> **최종 검토**: 2026년 9월 12일.

[본문으로 돌아가기](../../../networking/cilium/networking-concepts.md)

## OSI 및 기본 개념

1. **Cilium 정책 기능의 올바른 설명은 무엇인가요?**

   - A) 일반 MAC 주소 방화벽만 제공
   - B) 프록시 연동 없는 L3/L4만 제공
   - C) HTTP 정책만 제공
   - D) L3/L4 제어와 구성된 지원 L7 규칙 제공

   <details>
   <summary>정답 보기</summary>

   **정답: D) L3/L4 제어와 구성된 지원 L7 규칙 제공**

   Cilium은 L3/L4 집행과 지원 HTTP/gRPC·DNS 프록시 기능을 결합합니다. 모든 OSI 계층이나 제거된 Kafka L7 API를 구현한다는 뜻은 아닙니다.

   </details>

2. **링크 계층 주소는 무엇인가요?**

   - A) IP 주소
   - B) MAC 주소
   - C) 포트 번호
   - D) URL

   <details>
   <summary>정답 보기</summary>

   **정답: B) MAC 주소**

   MAC 주소는 링크 계층 인터페이스 주소입니다. 로컬 할당·변경이 가능하므로 전역 고유성과 진위가 보장되지는 않습니다.

   </details>

3. **네트워크 계층 IP 주소 지정을 제공하는 프로토콜은 무엇인가요?**

   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>정답 보기</summary>

   **정답: C) IP**

   IP는 논리 주소와 네트워크 계층 패킷 전달을 제공하며 TCP와 UDP의 전송 의미는 서로 다릅니다.

   </details>

## 컨테이너 네트워킹

4. **플랫폼 재정의가 없을 때 일반 Cilium Helm 라우팅 기본값은 무엇인가요?**

   - A) Docker 브리지
   - B) 터널·오버레이 모드
   - C) 필수 BGP native 모드
   - D) 모든 워크로드의 호스트 네트워킹

   <details>
   <summary>정답 보기</summary>

   **정답: B) 터널·오버레이 모드**

   일반 기본값은 터널 모드입니다. 플랫폼별 설치 프로필은 다른 모드를 선택할 수 있으므로 모든 EKS·클라우드의 불변 조건은 아닙니다.

   </details>

5. **일반 Cilium 터널 프로필의 기본 프로토콜은 무엇인가요?**

   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>정답 보기</summary>

   **정답: A) VXLAN**

   기본 터널 프로토콜은 VXLAN이며 Cilium 기본 포트는 UDP 8472입니다. 표준 VXLAN에 할당된 UDP 포트는 4789입니다.

   </details>

6. **Native 라우팅의 구체적인 특성은 무엇인가요?**

   - A) 자동 암호화
   - B) 반환 라우트 불필요
   - C) 해당 경로의 오버레이 캡슐화 없음
   - D) 최고 처리량 보장

   <details>
   <summary>정답 보기</summary>

   **정답: C) 해당 경로의 오버레이 캡슐화 없음**

   Native 라우팅은 오버레이 헤더를 사용하지 않지만 유효한 Pod 연결성과 반환 라우트가 필요합니다. 성능은 워크로드·구현에 따라 달라집니다.

   </details>

## IPAM

7. **플랫폼 재정의가 없는 일반 Helm IPAM 기본값은 무엇인가요?**

   - A) kubernetes
   - B) cluster-pool
   - C) PodCIDR라는 모드
   - D) eni

   <details>
   <summary>정답 보기</summary>

   **정답: B) cluster-pool**

   Cluster-pool에서 operator는 노드 CIDR을, 에이전트는 로컬 Pod IP를 할당합니다. 모호한 Cluster Scope 표현 대신 실제 모드 이름을 사용합니다.

   </details>

8. **EC2 ENI와 VPC 주소를 사용하는 Cilium IPAM 모드는 무엇인가요?**

   - A) Kubernetes host-scope
   - B) Cluster-pool
   - C) ENI
   - D) 일반 CRD 기반

   <details>
   <summary>정답 보기</summary>

   **정답: C) ENI**

   ENI 모드는 AWS 전제 조건을 가지며 모든 EKS 컴퓨팅 모드나 CNI 체이닝 구성의 보편적인 권장은 아닙니다.

   </details>

9. **ipam.mode: kubernetes가 사용하는 Node 필드는 무엇인가요?**

   - A) spec.podCIDR / spec.podCIDRs
   - B) spec.CIDR
   - C) spec.Subnet
   - D) spec.IPRange

   <details>
   <summary>정답 보기</summary>

   **정답: A) spec.podCIDR / spec.podCIDRs**

   Kubernetes가 노드 Pod CIDR을 할당하며 Cilium의 Kubernetes host-scope IPAM이 이를 사용합니다. PodCIDR는 실제 IPAM 모드 이름이 아닙니다.

   </details>

## 서비스 및 로드 밸런싱

10. **kube-proxy 대체만으로 활성화되지 않는 기능은 무엇인가요?**

   - A) ClusterIP 전달
   - B) NodePort 전달
   - C) 지원 LoadBalancer Service 전달
   - D) 워크로드 mTLS

   <details>
   <summary>정답 보기</summary>

   **정답: D) 워크로드 mTLS**

   서비스 전달과 워크로드 인증·암호화는 별개이며 외부 로드 밸런서 생성에도 해당 컨트롤러·제공자가 필요합니다.

   </details>

11. **Cilium BPF Service의 로드 밸런싱 알고리즘은 무엇인가요?**

   - A) Random과 Maglev
   - B) 라운드 로빈만
   - C) 기본 최소 연결
   - D) 주기적 Maglev 타임아웃 순환

   <details>
   <summary>정답 보기</summary>

   **정답: A) Random과 Maglev**

   기본값은 random이며 지원 경로에서 Maglev를 선택할 수 있습니다. Envoy 알고리즘, ClientIP 어피니티와 어피니티 시간 제한은 별개입니다.

   </details>

12. **구성된 Global Service는 무엇을 가능하게 하나요?**

   - A) 전 세계 공인 IP 자동 할당
   - B) 연결된 클러스터 간 서비스 로드 밸런싱
   - C) 모든 정책 자동 복제
   - D) 공유 영구 스토리지

   <details>
   <summary>정답 보기</summary>

   **정답: B) 연결된 클러스터 간 서비스 로드 밸런싱**

   ClusterMesh와 일치하는 Service 이름·네임스페이스가 필요하며 엔드포인트·캐시 동작과 장애 처리는 검증해야 합니다.

   </details>

## 네트워크 정책

13. **toCIDR는 무엇을 선택하나요?**

   - A) 목적지 주소 범위
   - B) 인증된 DNS 호스트 이름
   - C) 이름 있는 Service만
   - D) TCP 포트만

   <details>
   <summary>정답 보기</summary>

   **정답: A) 목적지 주소 범위**

   CIDR 선택자는 엔드포인트 분류 규칙을 따릅니다. 기본적으로 클러스터 내부 관리 Pod·노드는 제외되며 이 버전에는 명시적 Beta 선택 기능이 있습니다. 인증 수단은 아닙니다.

   </details>

14. **world 엔티티는 무엇을 나타내나요?**

   - A) 알려진 모든 클러스터 ID
   - B) 알려진 클러스터·ClusterMesh ID와 구분되는 외부 엔드포인트
   - C) 모든 Kubernetes 노드
   - D) 모든 네임스페이스

   <details>
   <summary>정답 보기</summary>

   **정답: B) 알려진 클러스터·ClusterMesh ID와 구분되는 외부 엔드포인트**

   world는 모든 클러스터의 모든 엔드포인트와 같은 뜻이 아닙니다. 적절한 엔티티·ID 범위와 필요한 포트를 선택합니다.

   </details>

15. **제거된 과거 Cilium L7 기능은 무엇인가요?**

   - A) HTTP 경로 검사
   - B) DNS 질의 규칙
   - C) Kafka 토픽 규칙
   - D) HTTP 메서드 검사

   <details>
   <summary>정답 보기</summary>

   **정답: C) Kafka 토픽 규칙**

   현재 정책은 HTTP/gRPC 관련 프록시 기능과 DNS 규칙을 지원하며 이전 Kafka 정책 예제를 현재 API에 복사하면 안 됩니다.

   </details>

## 고급 개념

16. **Cilium 노드 전송 암호화의 대안 모드 쌍은 무엇인가요?**

   - A) HTTP와 DNS
   - B) TCP와 UDP
   - C) IPsec와 WireGuard
   - D) Relay와 Prometheus

   <details>
   <summary>정답 보기</summary>

   **정답: C) IPsec와 WireGuard**

   적절한 노드 암호화 모드를 선택하고 범위를 검증합니다. SPIRE 상호 인증과 Beta ztunnel 워크로드 mTLS의 역할·전제 조건은 다릅니다.

   </details>

17. **Cilium의 멀티 클러스터 네트워크 기능 이름은 무엇인가요?**

   - A) Cluster Federation
   - B) ClusterMesh
   - C) Global Cluster
   - D) NodePort Mesh

   <details>
   <summary>정답 보기</summary>

   **정답: B) ClusterMesh**

   ClusterMesh는 네트워크 메타데이터를 공유하고 구성된 클러스터 간 연결을 지원하며 주소·신뢰·underlay 전제 조건이 필요합니다.

   </details>

18. **Cilium BGP Control Plane은 무엇을 하나요?**

   - A) 학습한 모든 라우트를 로컬 데이터 경로에 설치
   - B) 선택한 Pod·Service 접두사를 피어에 광고
   - C) DNS 레코드 자동 생성
   - D) 모든 클러스터 간 트래픽 보장

   <details>
   <summary>정답 보기</summary>

   **정답: B) 선택한 Pod·Service 접두사를 피어에 광고**

   광고는 주소 할당·실제 패킷 전달과 별개입니다. 피어의 라우트를 확인하고 양방향 트래픽을 시험합니다.

   </details>

19. **Egress Gateway는 일치하는 외부 전송 트래픽에 무엇을 하나요?**

   - A) 선택한 게이트웨이 IP로 SNAT
   - B) 모든 원래 Pod 출발지 IP 보존
   - C) 외부 트래픽 자동 암호화
   - D) 전제 조건 없이 게이트웨이 인터페이스 생성

   <details>
   <summary>정답 보기</summary>

   **정답: A) 선택한 게이트웨이 IP로 SNAT**

   주소 변환으로 구성된 출발지 주소를 제공합니다. 준비된 인터페이스·라우팅과 새 Pod 정책 수렴을 고려해야 합니다.

   </details>

20. **BPF 호스트 라우팅은 무엇을 최적화하나요?**

   - A) 자동 native·overlay fallback
   - B) 호스트 내부 패킷 전달과 호스트 스택 사용
   - C) 호스트 방화벽 인가
   - D) 스토리지 암호화

   <details>
   <summary>정답 보기</summary>

   **정답: B) 호스트 내부 패킷 전달과 호스트 스택 사용**

   BPF 호스트 라우팅은 전제 조건·연동 제약 아래 호스트 스택·netfilter 일부를 우회할 수 있습니다. 노드 간 native·tunnel 라우팅 모드 선택과 다릅니다.

   </details>
