# Cilium 고급 퀴즈

> **지원 버전**: Cilium 1.17  
> **마지막 업데이트**: 2026년 2월 22일

## eBPF 기술

1. **eBPF 프로그램이 실행되는 위치는 어디인가요?**
   - A) 사용자 공간(User Space)
   - B) 커널 공간(Kernel Space)
   - C) 컨테이너 내부
   - D) 가상 머신 내부
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 커널 공간(Kernel Space)</p>
   <p><strong>설명</strong>: eBPF 프로그램은 Linux 커널 내부에서 안전하게 실행되며, 커널 기능을 확장하고 수정할 수 있습니다.</p>
   </details>

2. **eBPF 프로그램의 안전성을 보장하는 메커니즘은 무엇인가요?**
   - A) 가상화
   - B) 컨테이너화
   - C) 정적 검증기(Verifier)
   - D) 암호화
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) 정적 검증기(Verifier)</p>
   <p><strong>설명</strong>: eBPF 검증기는 프로그램이 로드되기 전에 안전성을 검사하여 무한 루프나 커널 충돌을 방지합니다.</p>
   </details>

3. **Cilium에서 eBPF를 사용하는 주요 이점이 아닌 것은?**
   - A) 커널 모듈 없이 네트워킹 기능 구현
   - B) 높은 성능과 낮은 오버헤드
   - C) 세분화된 네트워크 정책 적용
   - D) 하드웨어 가속화 필수
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) 하드웨어 가속화 필수</p>
   <p><strong>설명</strong>: eBPF는 하드웨어 가속화 없이도 소프트웨어 기반으로 높은 성능을 제공할 수 있습니다.</p>
   </details>

## 네트워킹 모델

4. **Cilium에서 지원하는 데이터 경로 모드가 아닌 것은?**
   - A) VXLAN
   - B) Geneve
   - C) Direct Routing
   - D) MPLS
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) MPLS</p>
   <p><strong>설명</strong>: Cilium은 VXLAN, Geneve, Direct Routing을 지원하지만 MPLS는 지원하지 않습니다.</p>
   </details>

5. **Cilium의 kube-proxy 대체 모드에서 사용하는 기술은 무엇인가요?**
   - A) iptables
   - B) IPVS
   - C) eBPF 기반 XDP
   - D) netfilter
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) eBPF 기반 XDP</p>
   <p><strong>설명</strong>: Cilium은 eBPF와 XDP(eXpress Data Path)를 사용하여 kube-proxy를 대체하고 더 높은 성능을 제공합니다.</p>
   </details>

6. **Cilium의 네트워크 모델에서 Pod 간 통신 시 패킷 경로를 추적하는 기능은 무엇인가요?**
   - A) tcpdump
   - B) Hubble Flow Monitoring
   - C) Wireshark
   - D) Prometheus
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Hubble Flow Monitoring</p>
   <p><strong>설명</strong>: Hubble은 Cilium의 네트워크 흐름 모니터링 도구로, Pod 간 통신을 실시간으로 추적하고 시각화할 수 있습니다.</p>
   </details>

## IPAM 및 네트워크 정책

7. **Cilium에서 지원하는 IPAM(IP 주소 관리) 모드 중 AWS EKS와 통합되는 모드는?**
   - A) Cluster Pool
   - B) Kubernetes Host Scope
   - C) AWS ENI
   - D) CRD-based
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) AWS ENI</p>
   <p><strong>설명</strong>: Cilium은 AWS ENI(Elastic Network Interface) 모드를 통해 EKS와 통합되어 VPC IP 주소를 Pod에 직접 할당할 수 있습니다.</p>
   </details>

8. **Cilium 네트워크 정책에서 'toFQDNs' 규칙은 무엇을 허용하나요?**
   - A) 특정 IP 주소로의 트래픽
   - B) 특정 포트로의 트래픽
   - C) 특정 도메인 이름으로의 트래픽
   - D) 특정 프로토콜의 트래픽
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) 특정 도메인 이름으로의 트래픽</p>
   <p><strong>설명</strong>: toFQDNs 규칙은 특정 도메인 이름(FQDN)으로의 트래픽을 허용하며, Cilium이 DNS 조회를 모니터링하여 해당 도메인의 IP 주소를 동적으로 허용합니다.</p>
   </details>

9. **다음 중 Cilium CiliumNetworkPolicy에서 지원하지 않는 선택자는?**
   - A) endpointSelector
   - B) nodeSelector
   - C) namespaceSelector
   - D) serviceSelector
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) serviceSelector</p>
   <p><strong>설명</strong>: Cilium은 endpointSelector, nodeSelector, namespaceSelector를 지원하지만 serviceSelector는 직접 지원하지 않습니다.</p>
   </details>

## L2-L7 네트워킹

10. **Cilium의 L7 정책이 HTTP 요청에 대해 필터링할 수 있는 속성이 아닌 것은?**
    - A) 경로(Path)
    - B) 메서드(Method)
    - C) 헤더(Headers)
    - D) 응답 시간(Response Time)
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 응답 시간(Response Time)</p>
    <p><strong>설명</strong>: Cilium의 L7 정책은 경로, 메서드, 헤더와 같은 HTTP 요청 속성을 필터링할 수 있지만 응답 시간은 필터링 대상이 아닙니다.</p>
    </details>

11. **Cilium의 Service Mesh 기능에서 제공하는 것이 아닌 것은?**
    - A) 상호 TLS(mTLS)
    - B) 트래픽 분할(Traffic Splitting)
    - C) 서비스 디스커버리
    - D) 사용자 인증(Authentication)
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 사용자 인증(Authentication)</p>
    <p><strong>설명</strong>: Cilium Service Mesh는 상호 TLS, 트래픽 분할, 서비스 디스커버리 등을 제공하지만, 사용자 인증은 일반적으로 별도의 인증 시스템에서 처리합니다.</p>
    </details>

12. **Cilium의 Envoy 통합은 어떤 기능을 제공하나요?**
    - A) L7 로드 밸런싱
    - B) L7 가시성
    - C) L7 정책 적용
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium은 Envoy 프록시와 통합하여 L7 로드 밸런싱, 가시성, 정책 적용을 모두 제공합니다.</p>
    </details>

## 보안 및 가시성

13. **Hubble UI에서 제공하지 않는 기능은?**
    - A) 서비스 의존성 맵
    - B) 네트워크 흐름 시각화
    - C) 정책 위반 알림
    - D) 코드 배포 관리
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 코드 배포 관리</p>
    <p><strong>설명</strong>: Hubble UI는 서비스 의존성 맵, 네트워크 흐름 시각화, 정책 위반 알림 등을 제공하지만 코드 배포 관리는 제공하지 않습니다.</p>
    </details>

14. **Cilium에서 네트워크 트래픽 암호화에 사용할 수 있는 프로토콜은?**
    - A) IPsec와 WireGuard
    - B) TLS와 SSH
    - C) SSL과 HTTPS
    - D) DTLS와 QUIC
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) IPsec와 WireGuard</p>
    <p><strong>설명</strong>: Cilium은 IPsec와 WireGuard 프로토콜을 사용하여 노드 간 네트워크 트래픽을 암호화할 수 있습니다.</p>
    </details>

15. **Cilium의 보안 기능 중 다음 설명에 해당하는 것은? "특정 애플리케이션 계층 프로토콜의 특정 필드나 패턴을 기반으로 트래픽을 필터링"**
    - A) 네트워크 정책
    - B) L7 정책
    - C) 암호화
    - D) 침입 탐지
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) L7 정책</p>
    <p><strong>설명</strong>: L7(애플리케이션 계층) 정책은 HTTP, gRPC, Kafka 등의 프로토콜에서 특정 필드나 패턴을 기반으로 트래픽을 필터링할 수 있습니다.</p>
    </details>

## 고급 주제 및 실제 사례

16. **Cilium Cluster Mesh의 주요 기능이 아닌 것은?**
    - A) 클러스터 간 서비스 검색
    - B) 클러스터 간 네트워크 정책
    - C) 클러스터 간 로드 밸런싱
    - D) 클러스터 간 스토리지 공유
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 클러스터 간 스토리지 공유</p>
    <p><strong>설명</strong>: Cilium Cluster Mesh는 클러스터 간 서비스 검색, 네트워크 정책, 로드 밸런싱을 제공하지만 스토리지 공유는 제공하지 않습니다.</p>
    </details>

17. **Cilium의 Bandwidth Manager 기능은 무엇을 제공하나요?**
    - A) 네트워크 대역폭 모니터링
    - B) 네트워크 대역폭 제한 및 QoS
    - C) 네트워크 대역폭 최적화
    - D) 네트워크 대역폭 예측
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 네트워크 대역폭 제한 및 QoS</p>
    <p><strong>설명</strong>: Cilium의 Bandwidth Manager는 eBPF를 사용하여 Pod별 네트워크 대역폭 제한 및 QoS(Quality of Service)를 제공합니다.</p>
    </details>

18. **Cilium의 Host Firewall 기능은 무엇을 보호하나요?**
    - A) 컨테이너 간 통신만
    - B) 노드 간 통신만
    - C) 호스트 자체의 네트워크 인터페이스
    - D) 외부 클라우드 서비스
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) 호스트 자체의 네트워크 인터페이스</p>
    <p><strong>설명</strong>: Cilium의 Host Firewall은 호스트 자체의 네트워크 인터페이스를 보호하여 호스트 수준의 보안을 강화합니다.</p>
    </details>

19. **Cilium의 Egress Gateway 기능의 주요 목적은 무엇인가요?**
    - A) 외부 트래픽의 소스 IP 주소 보존
    - B) 외부 트래픽의 대상 IP 주소 변경
    - C) 외부 트래픽의 암호화
    - D) 외부 트래픽의 차단
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) 외부 트래픽의 소스 IP 주소 보존</p>
    <p><strong>설명</strong>: Cilium의 Egress Gateway는 Pod에서 클러스터 외부로 나가는 트래픽의 소스 IP 주소를 특정 IP로 SNAT하여 일관된 소스 IP를 제공합니다.</p>
    </details>

20. **Cilium의 BGP 지원을 통해 가능한 것이 아닌 것은?**
    - A) 외부 라우터와의 경로 교환
    - B) LoadBalancer 서비스의 외부 IP 광고
    - C) 클러스터 간 직접 라우팅
    - D) 자동 DNS 레코드 생성
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 자동 DNS 레코드 생성</p>
    <p><strong>설명</strong>: Cilium의 BGP 지원은 외부 라우터와의 경로 교환, LoadBalancer 서비스의 외부 IP 광고, 클러스터 간 직접 라우팅을 제공하지만 자동 DNS 레코드 생성은 제공하지 않습니다.</p>
    </details>

## 성능 및 문제 해결

21. **Cilium의 성능 최적화 기능 중 패킷 처리 지연 시간을 크게 줄이는 기술은?**
    - A) TCP BBR
    - B) XDP(eXpress Data Path)
    - C) DPDK
    - D) TSO(TCP Segmentation Offload)
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) XDP(eXpress Data Path)</p>
    <p><strong>설명</strong>: XDP는 네트워크 드라이버 수준에서 패킷을 처리하여 커널 네트워킹 스택을 우회함으로써 지연 시간을 크게 줄입니다.</p>
    </details>

22. **Cilium에서 네트워크 연결 문제를 진단하는 명령어는?**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium monitor`
    - D) `cilium endpoint list`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) `cilium connectivity test`</p>
    <p><strong>설명</strong>: `cilium connectivity test` 명령어는 클러스터 내 다양한 네트워크 연결 시나리오를 테스트하여 문제를 진단합니다.</p>
    </details>

23. **Cilium에서 특정 Pod의 네트워크 정책 상태를 확인하는 명령어는?**
    - A) `cilium endpoint list`
    - B) `cilium policy get`
    - C) `cilium endpoint get <endpoint-id>`
    - D) `cilium status --all-endpoints`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) <code>cilium endpoint get &lt;endpoint-id&gt;</code></p>
    <p><strong>설명</strong>: <code>cilium endpoint get &lt;endpoint-id&gt;</code> 명령어는 특정 엔드포인트(Pod)의 상세 정보와 적용된 네트워크 정책 상태를 보여줍니다.</p>
    </details>

24. **Cilium에서 BPF 맵 상태를 확인하는 명령어는?**
    - A) `cilium map list`
    - B) `cilium bpf maps`
    - C) `cilium status --maps`
    - D) `cilium bpf map list`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) `cilium bpf maps`</p>
    <p><strong>설명</strong>: `cilium bpf maps` 명령어는 Cilium에서 사용하는 모든 BPF 맵의 목록과 상태를 보여줍니다.</p>
    </details>

25. **Cilium에서 네트워크 패킷 캡처 및 분석을 위한 명령어는?**
    - A) `cilium tcpdump`
    - B) `cilium capture`
    - C) `cilium monitor`
    - D) `cilium packet-capture`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) `cilium monitor`</p>
    <p><strong>설명</strong>: `cilium monitor` 명령어는 Cilium의 eBPF 데이터 경로를 통과하는 패킷을 실시간으로 캡처하고 분석할 수 있습니다.</p>
    </details>
