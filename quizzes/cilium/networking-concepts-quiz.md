# Cilium 네트워킹 개념 퀴즈

> **지원 버전**: Cilium 1.17  
> **마지막 업데이트**: 2025년 7월 21일

## OSI 모델 및 기본 개념

1. **OSI 모델에서 Cilium이 주로 작동하는 계층은?**
   - A) L2 (데이터 링크 계층)
   - B) L3/L4 (네트워크/전송 계층)
   - C) L7 (애플리케이션 계층)
   - D) L3부터 L7까지 모두
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) L3부터 L7까지 모두</p>
   <p><strong>설명</strong>: Cilium은 L3/L4(IP 주소, 포트) 뿐만 아니라 L7(HTTP, gRPC, Kafka 등) 계층까지 네트워킹 및 보안 기능을 제공합니다.</p>
   </details>

2. **다음 중 L2(데이터 링크 계층) 주소는 무엇인가요?**
   - A) IP 주소
   - B) MAC 주소
   - C) 포트 번호
   - D) URL
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) MAC 주소</p>
   <p><strong>설명</strong>: MAC(Media Access Control) 주소는 네트워크 인터페이스 카드의 고유 식별자로, L2 계층에서 사용됩니다.</p>
   </details>

3. **다음 중 L3(네트워크 계층) 프로토콜은 무엇인가요?**
   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) IP</p>
   <p><strong>설명</strong>: IP(Internet Protocol)는 네트워크 계층(L3)에서 패킷 라우팅을 담당하는 프로토콜입니다.</p>
   </details>

## 컨테이너 네트워킹

4. **Cilium의 기본 네트워크 모델은 무엇인가요?**
   - A) 브리지 모드
   - B) 오버레이 네트워크
   - C) 언더레이 네트워크
   - D) 호스트 네트워크
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 오버레이 네트워크</p>
   <p><strong>설명</strong>: Cilium은 기본적으로 VXLAN 또는 Geneve를 사용한 오버레이 네트워크 모델을 사용합니다.</p>
   </details>

5. **Cilium에서 사용하는 기본 오버레이 프로토콜은 무엇인가요?**
   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) VXLAN</p>
   <p><strong>설명</strong>: Cilium은 기본적으로 VXLAN(Virtual Extensible LAN) 프로토콜을 사용하여 오버레이 네트워크를 구성합니다.</p>
   </details>

6. **Cilium의 Direct Routing 모드의 주요 이점은 무엇인가요?**
   - A) 더 높은 보안성
   - B) 더 나은 호환성
   - C) 더 낮은 지연 시간과 더 높은 처리량
   - D) 더 쉬운 설정
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) 더 낮은 지연 시간과 더 높은 처리량</p>
   <p><strong>설명</strong>: Direct Routing 모드는 오버레이 캡슐화를 사용하지 않기 때문에 더 낮은 지연 시간과 더 높은 처리량을 제공합니다.</p>
   </details>

## IP 주소 관리 (IPAM)

7. **Cilium의 기본 IPAM 모드는 무엇인가요?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Cluster Scope</p>
   <p><strong>설명</strong>: Cilium의 기본 IPAM 모드는 Cluster Scope로, 클러스터 전체에서 중앙 집중식으로 IP 주소를 할당합니다.</p>
   </details>

8. **AWS EKS에서 Cilium을 사용할 때 권장되는 IPAM 모드는 무엇인가요?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) AWS ENI</p>
   <p><strong>설명</strong>: AWS EKS에서는 AWS ENI IPAM 모드를 사용하여 VPC의 IP 주소를 Pod에 직접 할당하는 것이 권장됩니다.</p>
   </details>

9. **Cilium의 IPAM에서 'PodCIDR' 모드는 어떤 Kubernetes 기능을 활용하나요?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>설명</strong>: Cilium의 PodCIDR IPAM 모드는 Kubernetes가 각 노드에 할당한 NodeSpec.PodCIDR 필드를 활용합니다.</p>
   </details>

## 서비스 및 로드 밸런싱

10. **Cilium의 kube-proxy 대체 모드에서 제공하지 않는 기능은?**
    - A) ClusterIP 서비스 지원
    - B) NodePort 서비스 지원
    - C) LoadBalancer 서비스 지원
    - D) 서비스 메시 기능
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 서비스 메시 기능</p>
    <p><strong>설명</strong>: Cilium의 kube-proxy 대체 모드는 기본적인 Kubernetes 서비스 유형을 지원하지만, 서비스 메시 기능은 별도의 Cilium Service Mesh 기능을 통해 제공됩니다.</p>
    </details>

11. **Cilium의 서비스 로드 밸런싱에서 사용하는 알고리즘은 무엇인가요?**
    - A) 라운드 로빈
    - B) 최소 연결
    - C) IP 해시
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium은 라운드 로빈, 최소 연결, IP 해시 등 다양한 로드 밸런싱 알고리즘을 지원합니다.</p>
    </details>

12. **Cilium의 Global Service 기능은 무엇을 가능하게 하나요?**
    - A) 전 세계적으로 분산된 서비스 접근
    - B) 여러 클러스터에 걸친 서비스 로드 밸런싱
    - C) 글로벌 IP 주소 할당
    - D) 글로벌 네트워크 정책 적용
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 여러 클러스터에 걸친 서비스 로드 밸런싱</p>
    <p><strong>설명</strong>: Cilium의 Global Service 기능은 Cluster Mesh를 통해 여러 클러스터에 걸쳐 동일한 서비스에 대한 로드 밸런싱을 가능하게 합니다.</p>
    </details>

## 네트워크 정책

13. **Cilium 네트워크 정책의 'toCIDR' 규칙은 무엇을 허용하나요?**
    - A) 특정 IP 주소 범위로의 트래픽
    - B) 특정 도메인 이름으로의 트래픽
    - C) 특정 서비스로의 트래픽
    - D) 특정 포트로의 트래픽
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) 특정 IP 주소 범위로의 트래픽</p>
    <p><strong>설명</strong>: toCIDR 규칙은 특정 IP 주소 범위(CIDR 표기법)로의 트래픽을 허용하는 데 사용됩니다.</p>
    </details>

14. **Cilium 네트워크 정책에서 'toEntities' 규칙의 'world' 엔티티는 무엇을 의미하나요?**
    - A) 모든 내부 클러스터 엔드포인트
    - B) 모든 외부 네트워크
    - C) 모든 노드
    - D) 모든 네임스페이스
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 모든 외부 네트워크</p>
    <p><strong>설명</strong>: 'world' 엔티티는 클러스터 외부의 모든 네트워크를 의미합니다.</p>
    </details>

15. **Cilium의 L7 정책에서 지원하는 프로토콜이 아닌 것은?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) SMTP</p>
    <p><strong>설명</strong>: Cilium은 HTTP, gRPC, Kafka 등의 L7 프로토콜을 지원하지만, SMTP는 기본적으로 지원하지 않습니다.</p>
    </details>

## 고급 네트워킹 개념

16. **Cilium의 Transparent Encryption 기능에서 사용할 수 있는 프로토콜은?**
    - A) IPsec
    - B) WireGuard
    - C) A와 B 모두
    - D) TLS
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) A와 B 모두</p>
    <p><strong>설명</strong>: Cilium은 IPsec과 WireGuard 모두를 사용하여 노드 간 트래픽을 암호화할 수 있습니다.</p>
    </details>

17. **Cilium의 Multi-cluster 기능에서 사용하는 기술은?**
    - A) Cluster Federation
    - B) Cluster Mesh
    - C) Multi-cluster Networking
    - D) Global Cluster
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) Cluster Mesh</p>
    <p><strong>설명</strong>: Cilium은 Cluster Mesh 기술을 사용하여 여러 Kubernetes 클러스터 간의 연결을 제공합니다.</p>
    </details>

18. **Cilium의 BGP 지원을 통해 가능한 것은?**
    - A) 외부 라우터와의 경로 교환
    - B) LoadBalancer 서비스의 외부 IP 광고
    - C) 클러스터 간 직접 라우팅
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium의 BGP 지원은 외부 라우터와의 경로 교환, LoadBalancer 서비스의 외부 IP 광고, 클러스터 간 직접 라우팅을 모두 가능하게 합니다.</p>
    </details>

19. **Cilium의 Egress Gateway 기능의 주요 목적은?**
    - A) 외부 트래픽의 소스 IP 주소 보존
    - B) 외부 트래픽의 대상 IP 주소 변경
    - C) 외부 트래픽의 암호화
    - D) 외부 트래픽의 차단
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) 외부 트래픽의 소스 IP 주소 보존</p>
    <p><strong>설명</strong>: Egress Gateway는 Pod에서 클러스터 외부로 나가는 트래픽의 소스 IP 주소를 특정 IP로 SNAT하여 일관된 소스 IP를 제공합니다.</p>
    </details>

20. **Cilium의 Host Routing 기능에 대한 설명으로 옳은 것은?**
    - A) 호스트 네트워크와 Pod 네트워크 간의 라우팅
    - B) 호스트 간 직접 라우팅
    - C) 호스트 네트워크 인터페이스 보호
    - D) 호스트 기반 로드 밸런싱
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 호스트 간 직접 라우팅</p>
    <p><strong>설명</strong>: Cilium의 Host Routing은 오버레이 네트워크 없이 호스트 간에 직접 라우팅을 제공합니다.</p>
    </details>
