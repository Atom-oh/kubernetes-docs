# Cilium 고급 퀴즈

> **검토 기준**: Cilium 1.20.1; Cilium CLI 0.20.0; Hubble CLI 1.19.4.
> **최종 검토**: 2026년 9월 12일.

[본문으로 돌아가기](../../../networking/cilium/07-advanced-topics.md)

## eBPF 기술

1. **이 과정의 Linux eBPF 데이터 경로 프로그램은 어디서 실행되나요?**

   - A) 브라우저에서만
   - B) Linux 커널의 지원 훅에서
   - C) Envoy 내부에서만
   - D) Kubernetes API 서버에서

   <details>
   <summary>정답 보기</summary>

   **정답: B) Linux 커널의 지원 훅에서**

   Cilium은 eBPF 프로그램을 커널 훅에 연결하고 사용자 공간 구성 요소가 이를 로드·관리합니다.

   </details>

2. **커널이 eBPF 프로그램을 수락하기 전에 검사하는 수단은 무엇인가요?**

   - A) 암호화
   - B) 컨테이너 스케줄링
   - C) 검증기(verifier)
   - D) DNS

   <details>
   <summary>정답 보기</summary>

   **정답: C) 검증기(verifier)**

   검증기는 메모리 접근과 유한 실행 같은 속성을 검사합니다. 구현 취약점이나 모든 커널 장애가 없다는 절대 보장은 아닙니다.

   </details>

3. **Cilium의 소프트웨어 eBPF 데이터 경로에 일반적으로 필수적이지 않은 것은 무엇인가요?**

   - A) 지원 커널 기능
   - B) 적절한 권한
   - C) 호환되는 네트워크 구성
   - D) 전용 하드웨어 오프로딩

   <details>
   <summary>정답 보기</summary>

   **정답: D) 전용 하드웨어 오프로딩**

   하드웨어 오프로딩은 필수가 아닙니다. 성능은 실제 경로, 워크로드, 커널과 하드웨어에 따라 달라집니다.

   </details>

## 네트워킹 모델

4. **이 과정에서 설명한 Cilium native/tunnel 선택에 해당하지 않는 것은 무엇인가요?**

   - A) VXLAN
   - B) Geneve
   - C) Native 라우팅
   - D) MPLS 데이터 경로 모드

   <details>
   <summary>정답 보기</summary>

   **정답: D) MPLS 데이터 경로 모드**

   Cilium의 구성 선택에 관한 설명이며 MPLS 기반 외부 underlay 사용을 금지한다는 뜻은 아닙니다.

   </details>

5. **Cilium의 kube-proxy 대체는 무엇으로 구현되나요?**

   - A) iptables 체인만
   - B) IPVS 규칙만
   - C) eBPF 서비스 처리와 선택적 XDP 가속
   - D) 필수 외부 하드웨어 스위치

   <details>
   <summary>정답 보기</summary>

   **정답: C) eBPF 서비스 처리와 선택적 XDP 가속**

   소켓·패킷 경로 eBPF가 서비스를 처리합니다. XDP는 조건에 맞는 외부 전달 경로를 가속하며 모든 Service의 필수 조건이 아닙니다.

   </details>

6. **Kubernetes 메타데이터가 포함된 흐름 기록을 제공하는 Cilium 관측 구성 요소는 무엇인가요?**

   - A) Helm
   - B) Hubble
   - C) kube-scheduler
   - D) etcdctl

   <details>
   <summary>정답 보기</summary>

   **정답: B) Hubble**

   Hubble은 유한한 관측 데이터를 제공하며 모든 패킷의 무손실 캡처가 아닙니다. 다른 패킷 분석 도구의 역할과 구분합니다.

   </details>

## IPAM 및 네트워크 정책

7. **EC2 ENI를 사용해 VPC 주소를 할당하는 Cilium IPAM 모드는 무엇인가요?**

   - A) Cluster pool
   - B) Kubernetes host scope
   - C) ENI
   - D) 일반 CRD 기반

   <details>
   <summary>정답 보기</summary>

   **정답: C) ENI**

   ENI 모드는 AWS 네트워크 인터페이스와 주소 할당을 사용합니다. 모든 EKS 컴퓨팅 모드가 대체 CNI를 지원한다는 뜻은 아니므로 플랫폼 조건을 확인합니다.

   </details>

8. **toFQDNs는 무엇을 사용해 외부 연결을 허용하나요?**

   - A) 검증된 JWT
   - B) 고정 Service 포트만
   - C) 일치하는 DNS 이름에서 학습한 목적지 IP
   - D) 자동 TLS 복호화

   <details>
   <summary>정답 보기</summary>

   **정답: C) 일치하는 DNS 이름에서 학습한 목적지 IP**

   DNS 질의 허용·프록시 관측과 이후 IP 연결은 별개이며 원격 애플리케이션을 인증하지 않습니다.

   </details>

9. **CiliumClusterwideNetworkPolicy의 노드 호스트 정책에 사용하는 선택자는 무엇인가요?**

   - A) 모든 노드용 endpointSelector
   - B) nodeSelector
   - C) 최상위 serviceSelector
   - D) 최상위 namespaceSelector

   <details>
   <summary>정답 보기</summary>

   **정답: B) nodeSelector**

   nodeSelector는 클러스터 범위 호스트 정책 필드입니다. Kubernetes의 모든 선택자를 CiliumNetworkPolicy 최상위에서 교환 가능한 필드로 설명하면 안 됩니다.

   </details>

## L2–L7 네트워킹

10. **Cilium HTTP 정책의 요청 일치 필드가 아닌 것은 무엇인가요?**

   - A) 경로
   - B) 메서드
   - C) 헤더
   - D) 응답 지연

   <details>
   <summary>정답 보기</summary>

   **정답: D) 응답 지연**

   HTTP가 보이는 경로에서 지원 요청 필드를 검사합니다. 지연 측정이 지연 기반 허용 규칙 필드를 생성하지는 않습니다.

   </details>

11. **ID 기반 네트워크 정책만으로 제공되지 않는 것은 무엇인가요?**

   - A) 엔드포인트 선택
   - B) 네트워크 접근 제한
   - C) 방향별 규칙
   - D) 최종 사용자 토큰 인증

   <details>
   <summary>정답 보기</summary>

   **정답: D) 최종 사용자 토큰 인증**

   사용자 인증에는 애플리케이션·게이트웨이 로직이 필요합니다. SPIRE 상호 인증과 Beta ztunnel 워크로드 mTLS는 별도 구성과 제약을 가집니다.

   </details>

12. **적절한 경로에 구성된 Cilium Envoy 연동은 무엇을 제공할 수 있나요?**

   - A) HTTP 로드 밸런싱
   - B) HTTP 가시성
   - C) HTTP 정책 집행
   - D) 위의 모든 것

   <details>
   <summary>정답 보기</summary>

   **정답: D) 위의 모든 것**

   선택한 프록시 경로와 구성에 따라 제공되며 무관한 네트워크 기능을 켠다고 모든 L7 기능이 활성화되지는 않습니다.

   </details>

## 보안 및 가시성

13. **Hubble UI의 기능은 무엇인가요?**

   - A) Slack 장애 티켓 자동 생성
   - B) 서비스 의존성 맵과 흐름 탐색
   - C) 소스 코드 배포 관리
   - D) JWT 서명 키 교체

   <details>
   <summary>정답 보기</summary>

   **정답: B) 서비스 의존성 맵과 흐름 탐색**

   알림·자동 대응에는 별도 연동이 필요합니다. UI는 관측된 네트워크 흐름을 시각화합니다.

   </details>

14. **Cilium 노드 전송 암호화의 대안 모드는 무엇인가요?**

   - A) IPsec와 WireGuard
   - B) HTTP와 DNS
   - C) Relay와 Prometheus
   - D) TCP와 UDP

   <details>
   <summary>정답 보기</summary>

   **정답: A) IPsec와 WireGuard**

   적용 범위와 전제 조건을 확인해야 합니다. 동일 노드 트래픽은 노드 터널로 암호화되지 않으며 워크로드 mTLS는 별도 기능입니다.

   </details>

15. **HTTP 메서드와 경로를 검사하는 정책 계층은 무엇인가요?**

   - A) L2 주소 검사만
   - B) L7 정책
   - C) L3 CIDR 검사만
   - D) 전송 암호화

   <details>
   <summary>정답 보기</summary>

   **정답: B) L7 정책**

   현재 Cilium HTTP 정책은 이러한 필드를 검사하며 Kafka 토픽 규칙은 제거되었습니다. 헤더 일치는 토큰 인증이 아닙니다.

   </details>

## 고급 주제 및 사용 사례

16. **ClusterMesh의 기능이 아닌 것은 무엇인가요?**

   - A) 클러스터 간 서비스 검색
   - B) 정책에서 원격 엔드포인트 ID 사용
   - C) 클러스터 간 서비스 로드 밸런싱
   - D) 공유 영구 스토리지

   <details>
   <summary>정답 보기</summary>

   **정답: D) 공유 영구 스토리지**

   ClusterMesh는 네트워크 메타데이터·연결성을 다루며 공유 스토리지나 모든 정책 리소스의 자동 복제를 제공하지 않습니다.

   </details>

17. **Bandwidth Manager의 올바른 설명은 무엇인가요?**

   - A) 대역폭 그래프만 그립니다
   - B) 구성된 Pod별 대역폭 한계를 집행합니다
   - C) Pod마다 물리 링크 예약을 보장합니다
   - D) 머신 러닝으로 미래 트래픽을 예측합니다

   <details>
   <summary>정답 보기</summary>

   **정답: B) 구성된 Pod별 대역폭 한계를 집행합니다**

   Egress는 EDT, ingress는 eBPF 토큰 버킷을 사용합니다. Pod별 제한이며 egress L7·kind 제약이 있고 용량 예약을 보장하지는 않습니다.

   </details>

18. **Cilium Host Firewall의 범위는 무엇인가요?**

   - A) 컨테이너 간 HTTP만
   - B) 스토리지 암호화만
   - C) 호스트의 네트워크 트래픽
   - D) 외부 SaaS 인가

   <details>
   <summary>정답 보기</summary>

   **정답: C) 호스트의 네트워크 트래픽**

   호스트 방화벽은 노드·호스트 네트워크 정책이며 일반적인 런타임 시스템 호출 제어 시스템이 아닙니다.

   </details>

19. **Egress Gateway는 일치하는 외부 전송 트래픽에 무엇을 수행하나요?**

   - A) 선택한 예측 가능한 게이트웨이 IP로 SNAT
   - B) 항상 원래 Pod 출발지 IP 보존
   - C) 모든 외부 연결 자동 암호화
   - D) 전제 조건 없이 모든 클라우드에 공인 IP 생성

   <details>
   <summary>정답 보기</summary>

   **정답: A) 선택한 예측 가능한 게이트웨이 IP로 SNAT**

   게이트웨이 IP·인터페이스·라우팅을 준비해야 합니다. 새 Pod는 정책 적용 전에 트래픽을 보낼 수 있으며 ClusterMesh·CiliumEndpointSlice 비호환도 확인합니다.

   </details>

20. **Cilium BGP Control Plane이 수행하는 동작은 무엇인가요?**

   - A) 학습한 모든 라우트를 로컬 Linux 데이터 경로에 설치
   - B) 선택한 Pod 또는 Service 접두사를 피어에 광고
   - C) 모든 Service의 DNS 레코드 생성
   - D) 외부 라우터 인터페이스 할당

   <details>
   <summary>정답 보기</summary>

   **정답: B) 선택한 Pod 또는 Service 접두사를 피어에 광고**

   BGP 광고와 로컬 데이터 경로 라우팅·주소 할당·DNS는 별개입니다. 외부 라우터와 실제 왕복 경로를 검증합니다.

   </details>

## 성능 및 문제 해결

21. **지원되는 외부 서비스 전달을 native 드라이버 훅에서 처리할 수 있는 수단은 무엇인가요?**

   - A) Grafana 대시보드
   - B) XDP 가속
   - C) DNS 검색 접미사
   - D) 더 큰 애플리케이션 로그 파일

   <details>
   <summary>정답 보기</summary>

   **정답: B) XDP 가속**

   XDP에는 지원 NIC·드라이버와 경로가 필요합니다. 임의 워크로드에 고정 지연·처리량 개선을 가정할 수 없습니다.

   </details>

22. **연결 시나리오를 시험하도록 워크로드를 실제 생성하는 독립 Cilium CLI 명령은 무엇인가요?**

   - A) `cilium status`
   - B) `cilium connectivity test`
   - C) `hubble status`
   - D) `kubectl get nodes`

   <details>
   <summary>정답 보기</summary>

   **정답: B) `cilium connectivity test`**

   리소스 생성과 트래픽을 수반하는 실제 시험이며 읽기 전용 상태 조회가 아닙니다. 격리된 시험 범위와 정리를 확인합니다.

   </details>

23. **담당 Cilium 에이전트 안에서 특정 엔드포인트의 상세 정보를 확인하는 명령은 무엇인가요?**

   - A) `cilium endpoint list`
   - B) `cilium policy get`
   - C) `cilium-dbg endpoint get ENDPOINT_ID`
   - D) `cilium status --all-endpoints`

   <details>
   <summary>정답 보기</summary>

   **정답: C) `cilium-dbg endpoint get ENDPOINT_ID`**

   해당 에이전트의 목록에서 노드 로컬 엔드포인트 ID를 얻습니다. 다른 에이전트의 ID가 같은 워크로드를 뜻하지는 않습니다.

   </details>

24. **에이전트 맵 관리자가 아는 열린 BPF 맵을 나열하는 로컬 명령은 무엇인가요?**

   - A) `cilium-dbg map list`
   - B) `cilium bpf maps`
   - C) `cilium status --maps`
   - D) `cilium bpf map list`

   <details>
   <summary>정답 보기</summary>

   **정답: A) `cilium-dbg map list`**

   모든 커널 BPF 맵의 목록은 아닙니다. 이전 답변의 cilium bpf maps는 유효한 명령이 아니었습니다.

   </details>

25. **Cilium BPF 프로그램이 발생시킨 로컬 이벤트를 표시하는 명령은 무엇인가요?**

   - A) `cilium tcpdump`
   - B) `cilium capture`
   - C) `cilium-dbg monitor`
   - D) `cilium packet-capture`

   <details>
   <summary>정답 보기</summary>

   **정답: C) `cilium-dbg monitor`**

   지원 이벤트·추적 유형을 표시합니다. 집계, 억제와 버퍼가 가시성에 영향을 주며 모든 패킷의 캡처를 보장하지 않습니다.

   </details>
