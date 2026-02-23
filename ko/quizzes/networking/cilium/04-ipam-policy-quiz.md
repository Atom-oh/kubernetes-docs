# Cilium IPAM 및 네트워크 정책 퀴즈

> **지원 버전**: Cilium 1.17  
> **마지막 업데이트**: 2026년 2월 22일

## IPAM (IP 주소 관리)

1. **Cilium의 기본 IPAM 모드는 무엇인가요?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Cluster Scope</p>
   <p><strong>설명</strong>: Cilium의 기본 IPAM 모드는 Cluster Scope로, 클러스터 전체에서 중앙 집중식으로 IP 주소를 할당합니다.</p>
   </details>

2. **Cilium의 IPAM 모드 중 각 노드가 자체 CIDR 범위에서 IP를 할당하는 모드는?**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD-based
   - D) AWS ENI
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Kubernetes Host Scope</p>
   <p><strong>설명</strong>: Kubernetes Host Scope IPAM 모드에서는 각 노드가 자체 CIDR 범위에서 IP 주소를 할당합니다.</p>
   </details>

3. **AWS EKS에서 Cilium을 사용할 때 권장되는 IPAM 모드는 무엇인가요?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) AWS ENI</p>
   <p><strong>설명</strong>: AWS EKS에서는 AWS ENI IPAM 모드를 사용하여 VPC의 IP 주소를 Pod에 직접 할당하는 것이 권장됩니다.</p>
   </details>

4. **Cilium의 IPAM에서 'PodCIDR' 모드는 어떤 Kubernetes 기능을 활용하나요?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>설명</strong>: Cilium의 PodCIDR IPAM 모드는 Kubernetes가 각 노드에 할당한 NodeSpec.PodCIDR 필드를 활용합니다.</p>
   </details>

5. **Cilium의 IPAM 구성을 확인하는 명령어는?**
   - A) `cilium status --ipam`
   - B) `cilium ipam`
   - C) `cilium config get ipam`
   - D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`</p>
   <p><strong>설명</strong>: Cilium의 IPAM 구성은 cilium-config ConfigMap에 저장되어 있으며, 이 명령어로 확인할 수 있습니다.</p>
   </details>

## 네트워크 정책 기본

6. **Cilium NetworkPolicy의 API 버전은 무엇인가요?**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) cilium.io/v2</p>
   <p><strong>설명</strong>: Cilium NetworkPolicy는 cilium.io/v2 API 버전을 사용합니다.</p>
   </details>

7. **Cilium NetworkPolicy에서 'endpointSelector'의 역할은 무엇인가요?**
   - A) 정책이 적용될 대상 Pod 선택
   - B) 정책이 적용될 대상 노드 선택
   - C) 정책이 적용될 대상 네임스페이스 선택
   - D) 정책이 적용될 대상 서비스 선택
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 정책이 적용될 대상 Pod 선택</p>
   <p><strong>설명</strong>: endpointSelector는 정책이 적용될 대상 Pod(엔드포인트)를 선택하는 데 사용됩니다.</p>
   </details>

8. **Cilium NetworkPolicy에서 'ingress' 규칙은 무엇을 제어하나요?**
   - A) 선택된 Pod로 들어오는 트래픽
   - B) 선택된 Pod에서 나가는 트래픽
   - C) 선택된 Pod 내부의 트래픽
   - D) 클러스터 외부로의 트래픽
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 선택된 Pod로 들어오는 트래픽</p>
   <p><strong>설명</strong>: ingress 규칙은 선택된 Pod로 들어오는 트래픽을 제어합니다.</p>
   </details>

9. **Cilium NetworkPolicy에서 'egress' 규칙은 무엇을 제어하나요?**
   - A) 선택된 Pod로 들어오는 트래픽
   - B) 선택된 Pod에서 나가는 트래픽
   - C) 선택된 Pod 내부의 트래픽
   - D) 클러스터 외부에서의 트래픽
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 선택된 Pod에서 나가는 트래픽</p>
   <p><strong>설명</strong>: egress 규칙은 선택된 Pod에서 나가는 트래픽을 제어합니다.</p>
   </details>

10. **Cilium NetworkPolicy에서 'labels' 필드의 역할은 무엇인가요?**
    - A) 정책이 적용될 Pod 선택
    - B) 정책 자체의 식별자
    - C) 정책이 적용될 네임스페이스 선택
    - D) 정책이 적용될 노드 선택
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 정책 자체의 식별자</p>
    <p><strong>설명</strong>: labels 필드는 정책 자체의 식별자로 사용되며, 다른 정책에서 이 정책을 참조할 때 사용됩니다.</p>
    </details>

## 고급 네트워크 정책

11. **Cilium NetworkPolicy의 'toCIDR' 규칙은 무엇을 허용하나요?**
    - A) 특정 IP 주소 범위로의 트래픽
    - B) 특정 도메인 이름으로의 트래픽
    - C) 특정 서비스로의 트래픽
    - D) 특정 포트로의 트래픽
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) 특정 IP 주소 범위로의 트래픽</p>
    <p><strong>설명</strong>: toCIDR 규칙은 특정 IP 주소 범위(CIDR 표기법)로의 트래픽을 허용하는 데 사용됩니다.</p>
    </details>

12. **Cilium NetworkPolicy의 'toFQDNs' 규칙은 무엇을 허용하나요?**
    - A) 특정 IP 주소로의 트래픽
    - B) 특정 포트로의 트래픽
    - C) 특정 도메인 이름으로의 트래픽
    - D) 특정 프로토콜의 트래픽
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) 특정 도메인 이름으로의 트래픽</p>
    <p><strong>설명</strong>: toFQDNs 규칙은 특정 도메인 이름(FQDN)으로의 트래픽을 허용하며, Cilium이 DNS 조회를 모니터링하여 해당 도메인의 IP 주소를 동적으로 허용합니다.</p>
    </details>

13. **Cilium NetworkPolicy의 'toEntities' 규칙에서 'world' 엔티티는 무엇을 의미하나요?**
    - A) 모든 내부 클러스터 엔드포인트
    - B) 모든 외부 네트워크
    - C) 모든 노드
    - D) 모든 네임스페이스
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 모든 외부 네트워크</p>
    <p><strong>설명</strong>: 'world' 엔티티는 클러스터 외부의 모든 네트워크를 의미합니다.</p>
    </details>

14. **Cilium NetworkPolicy의 'toServices' 규칙은 무엇을 허용하나요?**
    - A) 특정 Kubernetes 서비스로의 트래픽
    - B) 특정 외부 서비스로의 트래픽
    - C) 특정 포트로의 트래픽
    - D) 특정 프로토콜의 트래픽
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) 특정 Kubernetes 서비스로의 트래픽</p>
    <p><strong>설명</strong>: toServices 규칙은 특정 Kubernetes 서비스로의 트래픽을 허용하는 데 사용됩니다.</p>
    </details>

15. **Cilium NetworkPolicy에서 'nodeSelector'의 역할은 무엇인가요?**
    - A) 정책이 적용될 대상 Pod 선택
    - B) 정책이 적용될 대상 노드 선택
    - C) 정책이 적용될 대상 네임스페이스 선택
    - D) 정책이 적용될 대상 서비스 선택
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 정책이 적용될 대상 노드 선택</p>
    <p><strong>설명</strong>: nodeSelector는 정책이 적용될 대상 노드를 선택하는 데 사용됩니다.</p>
    </details>

## L7 정책

16. **Cilium의 L7 HTTP 정책에서 필터링할 수 있는 속성은?**
    - A) 경로(Path)
    - B) 메서드(Method)
    - C) 헤더(Headers)
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium의 L7 HTTP 정책은 경로, 메서드, 헤더 등 다양한 HTTP 요청 속성을 필터링할 수 있습니다.</p>
    </details>

17. **Cilium의 L7 Kafka 정책에서 필터링할 수 있는 속성은?**
    - A) 토픽(Topic)
    - B) API 키(API Key)
    - C) 클라이언트 ID(Client ID)
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium의 L7 Kafka 정책은 토픽, API 키, 클라이언트 ID 등 다양한 Kafka 요청 속성을 필터링할 수 있습니다.</p>
    </details>

18. **Cilium의 L7 DNS 정책에서 'matchPattern' 규칙은 무엇을 허용하나요?**
    - A) 정확한 도메인 이름 일치
    - B) 와일드카드를 포함한 도메인 이름 패턴 일치
    - C) IP 주소 일치
    - D) 포트 번호 일치
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 와일드카드를 포함한 도메인 이름 패턴 일치</p>
    <p><strong>설명</strong>: matchPattern 규칙은 와일드카드(*)를 포함한 도메인 이름 패턴을 일치시킬 수 있습니다. 예: *.example.com</p>
    </details>

19. **Cilium의 L7 gRPC 정책에서 필터링할 수 있는 속성은?**
    - A) 메서드 이름
    - B) 서비스 이름
    - C) 메타데이터
    - D) 위의 모든 것
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 위의 모든 것</p>
    <p><strong>설명</strong>: Cilium의 L7 gRPC 정책은 메서드 이름, 서비스 이름, 메타데이터 등 다양한 gRPC 요청 속성을 필터링할 수 있습니다.</p>
    </details>

20. **Cilium의 L7 정책을 적용하기 위해 필요한 구성 요소는?**
    - A) kube-proxy
    - B) Envoy 프록시
    - C) NGINX 인그레스 컨트롤러
    - D) HAProxy
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) Envoy 프록시</p>
    <p><strong>설명</strong>: Cilium은 L7 정책을 적용하기 위해 Envoy 프록시를 사용합니다.</p>
    </details>
