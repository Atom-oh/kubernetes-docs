# 서비스와 네트워킹 퀴즈

이 퀴즈는 Kubernetes의 서비스 유형, 인그레스, 네트워크 정책, 서비스 디스커버리 등 네트워킹 개념에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 기본 서비스 유형은 무엇인가요?
   - A) NodePort
   - B) LoadBalancer
   - C) ClusterIP
   - D) ExternalName
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) ClusterIP**
   
   **설명:**
   ClusterIP는 Kubernetes의 기본 서비스 유형으로, 클러스터 내부에서만 접근 가능한 IP 주소를 제공합니다. 이 서비스는 클러스터 내의 다른 애플리케이션이 서비스에 접근할 수 있게 하지만, 클러스터 외부에서는 접근할 수 없습니다.
   </details>

2. 다음 중 클러스터 외부에서 클러스터 내부 서비스로의 HTTP 및 HTTPS 경로를 노출하는 API 객체는 무엇인가요?
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) Ingress**
   
   **설명:**
   Ingress는 클러스터 외부에서 클러스터 내부 서비스로의 HTTP 및 HTTPS 경로를 노출하는 API 객체입니다. Ingress는 로드 밸런싱, SSL 종료, 이름 기반 가상 호스팅을 제공합니다.
   </details>

3. 다음 중 Kubernetes에서 서비스 디스커버리를 위해 제공하는 방법이 아닌 것은 무엇인가요?
   - A) 환경 변수
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: D) ConfigMap**
   
   **설명:**
   Kubernetes는 두 가지 주요 서비스 디스커버리 방법을 제공합니다: 환경 변수와 DNS. ConfigMap은 구성 데이터를 저장하는 데 사용되며 서비스 디스커버리 메커니즘이 아닙니다.
   </details>

4. Kubernetes에서 모든 노드의 특정 포트를 통해 서비스에 접근할 수 있게 하는 서비스 유형은 무엇인가요?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) NodePort**
   
   **설명:**
   NodePort 서비스는 모든 노드의 특정 포트를 통해 서비스에 접근할 수 있게 합니다. 이 서비스 유형은 각 노드의 IP 주소와 NodePort 값(기본적으로 30000-32767 범위에서 할당)을 통해 서비스에 접근할 수 있게 합니다.
   </details>

5. 다음 중 클러스터 IP가 없는 서비스로, 각 포드에 대한 DNS 레코드를 생성하는 서비스는 무엇인가요?
   - A) NodePort 서비스
   - B) LoadBalancer 서비스
   - C) 헤드리스 서비스
   - D) ExternalName 서비스
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) 헤드리스 서비스**
   
   **설명:**
   헤드리스 서비스는 `clusterIP: None`으로 설정된 서비스로, 클러스터 IP를 할당하지 않고 각 포드에 대한 DNS 레코드를 생성합니다. 이는 클라이언트가 서비스 뒤의 특정 포드에 직접 접근해야 하는 경우에 유용합니다.
   </details>

6. Kubernetes에서 포드 간의 통신을 제어하는 방법을 제공하는 리소스는 무엇인가요?
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) NetworkPolicy**
   
   **설명:**
   NetworkPolicy는 포드 간의 통신을 제어하는 방법을 제공합니다. 네트워크 정책을 사용하면 포드 간의 인그레스 및 이그레스 트래픽을 제한할 수 있습니다.
   </details>

7. Kubernetes 클러스터의 DNS 서버로 사용되는 것은 무엇인가요?
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) CoreDNS**
   
   **설명:**
   CoreDNS는 Kubernetes 클러스터의 DNS 서버로 사용되는 유연하고 확장 가능한 DNS 서버입니다. Kubernetes 1.11부터 CoreDNS가 기본 DNS 서버로 사용되고 있습니다.
   </details>

8. 다음 중 Cilium이 활용하는 Linux 커널 기술은 무엇인가요?
   - A) iptables
   - B) netfilter
   - C) eBPF
   - D) nftables
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) eBPF**
   
   **설명:**
   Cilium은 Linux 커널의 eBPF(extended Berkeley Packet Filter) 기술을 활용하여 컨테이너화된 애플리케이션 간의 네트워크 연결, 보안, 관찰 가능성을 제공합니다.
   </details>

9. 다음 중 서비스 메시의 주요 기능이 아닌 것은 무엇인가요?
   - A) 서비스 디스커버리
   - B) 로드 밸런싱
   - C) 영구 스토리지 제공
   - D) 암호화된 통신
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) 영구 스토리지 제공**
   
   **설명:**
   서비스 메시는 마이크로서비스 간의 통신을 관리하는 인프라 계층으로, 서비스 디스커버리, 로드 밸런싱, 암호화, 인증, 권한 부여, 관찰 가능성 등의 기능을 제공합니다. 영구 스토리지 제공은 서비스 메시의 주요 기능이 아닙니다.
   </details>

10. 다음 중 Kubernetes에서 외부 서비스에 대한 별칭을 제공하는 서비스 유형은 무엇인가요?
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
    <details>
    <summary>정답 보기</summary>
    
    **정답: D) ExternalName**
    
    **설명:**
    ExternalName 서비스는 외부 서비스에 대한 별칭을 제공합니다. 이 서비스 유형은 DNS 이름을 외부 서비스의 DNS 이름으로 매핑합니다.
    </details>

## 단답형 문제

1. Kubernetes에서 서비스가 가리키는 포드의 IP 주소와 포트를 저장하는 리소스의 이름은 무엇인가요?

   <details>
   <summary>정답 보기</summary>
   
   **정답: Endpoints**
   
   **설명:**
   Endpoints는 서비스가 가리키는 포드의 IP 주소와 포트를 저장하는 리소스입니다. 서비스의 셀렉터와 일치하는 포드가 있으면 Kubernetes는 자동으로 엔드포인트 객체를 생성하고 관리합니다.
   </details>

2. AWS EKS에서 Application Load Balancer를 프로비저닝하기 위해 사용하는 인그레스 컨트롤러의 이름은 무엇인가요?

   <details>
   <summary>정답 보기</summary>
   
   **정답: AWS ALB Ingress Controller**
   
   **설명:**
   AWS ALB Ingress Controller는 AWS EKS에서 Application Load Balancer를 프로비저닝하기 위해 사용되는 인그레스 컨트롤러입니다. 이 컨트롤러는 Kubernetes 인그레스 리소스를 AWS ALB로 변환합니다.
   </details>

3. Kubernetes에서 포드의 DNS 정책 중, 포드가 실행 중인 노드의 DNS 설정을 상속받는 정책의 이름은 무엇인가요?

   <details>
   <summary>정답 보기</summary>
   
   **정답: Default**
   
   **설명:**
   `Default` DNS 정책은 포드가 실행 중인 노드의 DNS 설정을 상속받습니다. 이는 노드의 `/etc/resolv.conf` 파일을 포드에 그대로 사용하는 것을 의미합니다.
   </details>

4. Cilium의 관찰 가능성 계층으로, eBPF를 활용하여 네트워크 흐름을 모니터링하고 문제를 해결하는 도구의 이름은 무엇인가요?

   <details>
   <summary>정답 보기</summary>
   
   **정답: Hubble**
   
   **설명:**
   Hubble은 Cilium의 관찰 가능성 계층으로, eBPF를 활용하여 네트워크 흐름을 모니터링하고 문제를 해결하는 도구입니다. Hubble은 네트워크 흐름 모니터링, 서비스 의존성 매핑, 보안 관찰, 성능 분석, 문제 해결 등의 기능을 제공합니다.
   </details>

5. Kubernetes에서 엔드포인트의 확장 가능한 대안으로, 대규모 클러스터에서 더 나은 성능을 제공하는 리소스의 이름은 무엇인가요?

   <details>
   <summary>정답 보기</summary>
   
   **정답: EndpointSlice**
   
   **설명:**
   EndpointSlice는 엔드포인트의 확장 가능한 대안으로, 대규모 클러스터에서 더 나은 성능을 제공합니다. EndpointSlice는 엔드포인트를 여러 조각으로 나누어 관리하여 대규모 서비스의 성능을 향상시킵니다.
   </details>

## 심화 문제

1. Kubernetes에서 서비스 메시(예: Istio)를 사용하여 마이크로서비스 간의 통신을 관리하는 방법과 그 이점을 설명하세요.

   <details>
   <summary>정답 보기</summary>
   
   **정답:**
   
   서비스 메시는 마이크로서비스 간의 통신을 관리하는 인프라 계층으로, 다음과 같은 방법으로 구현됩니다:
   
   1. **사이드카 패턴**: 각 포드에 프록시 컨테이너(예: Envoy)를 주입하여 모든 네트워크 트래픽을 가로채고 제어합니다.
   
   2. **컨트롤 플레인**: 중앙 집중식 관리 구성 요소(예: Istio의 istiod)가 모든 사이드카 프록시를 구성하고 관리합니다.
   
   3. **트래픽 관리**:
      ```yaml
      apiVersion: networking.istio.io/v1alpha3
      kind: VirtualService
      metadata:
        name: reviews
      spec:
        hosts:
        - reviews
        http:
        - match:
          - headers:
              end-user:
                exact: jason
          route:
          - destination:
              host: reviews
              subset: v2
        - route:
          - destination:
              host: reviews
              subset: v1
      ```
   
   4. **보안 정책**:
      ```yaml
      apiVersion: security.istio.io/v1beta1
      kind: AuthorizationPolicy
      metadata:
        name: httpbin
        namespace: foo
      spec:
        selector:
          matchLabels:
            app: httpbin
        action: ALLOW
        rules:
        - from:
          - source:
              principals: ["cluster.local/ns/default/sa/sleep"]
          to:
          - operation:
              methods: ["GET"]
              paths: ["/info*"]
      ```
   
   **이점**:
   
   1. **트래픽 관리**: 고급 라우팅, 로드 밸런싱, 트래픽 분할, 카나리 배포 등을 지원합니다.
   
   2. **보안**: 서비스 간 상호 TLS(mTLS) 암호화, 인증, 권한 부여를 제공합니다.
   
   3. **관찰 가능성**: 분산 추적, 메트릭 수집, 로깅을 통해 서비스 간 통신을 모니터링합니다.
   
   4. **복원력**: 서킷 브레이커, 재시도, 타임아웃, 장애 주입 등을 통해 시스템 복원력을 향상시킵니다.
   
   5. **정책 시행**: 속도 제한, 할당량, 액세스 제어 등의 정책을 적용할 수 있습니다.
   
   6. **플랫폼 독립성**: 애플리케이션 코드를 변경하지 않고도 이러한 기능을 추가할 수 있습니다.
   
   서비스 메시는 복잡한 마이크로서비스 아키텍처에서 서비스 간 통신의 복잡성을 추상화하고, 개발자가 비즈니스 로직에 집중할 수 있게 해줍니다.
   </details>

2. Cilium의 eBPF 기술이 기존 네트워킹 접근 방식(예: iptables)과 비교하여 어떤 이점을 제공하는지 설명하고, AWS EKS에서 Cilium을 최적화하는 방법을 제안하세요.

   <details>
   <summary>정답 보기</summary>
   
   **정답:**
   
   **Cilium의 eBPF 기술 이점**:
   
   1. **성능**: eBPF는 커널 내에서 직접 실행되어 패킷 처리 경로를 최적화하므로, iptables보다 훨씬 높은 성능을 제공합니다. 특히 규칙이 많을 때 iptables는 선형 검색을 수행하지만, eBPF는 해시 테이블과 같은 효율적인 데이터 구조를 사용할 수 있습니다.
   
   2. **확장성**: eBPF는 대규모 클러스터에서도 일관된 성능을 유지합니다. iptables는 규칙 수가 증가함에 따라 성능이 급격히 저하됩니다.
   
   3. **프로그래밍 가능성**: eBPF는 C와 유사한 언어로 프로그래밍할 수 있어, 복잡한 네트워킹 로직을 구현할 수 있습니다. iptables는 제한된 규칙 세트만 지원합니다.
   
   4. **관찰 가능성**: eBPF는 네트워크 흐름에 대한 세부적인 메트릭을 수집할 수 있어, 문제 해결과 성능 최적화에 유용합니다.
   
   5. **L7 인식**: eBPF는 애플리케이션 계층(L7)까지 인식하여 HTTP, gRPC, Kafka 등의 프로토콜에 대한 세분화된 정책을 적용할 수 있습니다.
   
   **AWS EKS에서 Cilium 최적화 방법**:
   
   1. **AWS ENI 모드 활성화**:
      ```bash
      helm install cilium cilium/cilium \
        --namespace kube-system \
        --set eni.enabled=true \
        --set ipam.mode=eni \
        --set egressMasqueradeInterfaces=eth0 \
        --set tunnel=disabled
      ```
      이 구성은 AWS의 Elastic Network Interface(ENI)를 활용하여 포드에 VPC 네이티브 IP 주소를 할당하고, 오버레이 네트워크 없이 VPC 네이티브 네트워킹을 제공합니다.
   
   2. **노드 그룹 최적화**:
      - 충분한 ENI와 IP 주소를 제공하는 인스턴스 유형 선택(예: m5.large 이상)
      - 적절한 최대 포드 수 구성(인스턴스 유형에 따라 다름)
   
   3. **성능 최적화**:
      ```bash
      helm install cilium cilium/cilium \
        --namespace kube-system \
        --set eni.enabled=true \
        --set ipam.mode=eni \
        --set tunnel=disabled \
        --set bpf.masquerade=true \
        --set kubeProxyReplacement=strict \
        --set loadBalancer.mode=dsr \
        --set loadBalancer.acceleration=native
      ```
      이 구성은 kube-proxy를 대체하고, 직접 서버 반환(DSR) 모드와 네이티브 로드 밸런싱 가속을 활성화합니다.
   
   4. **Hubble 활성화**:
      ```bash
      helm upgrade cilium cilium/cilium \
        --namespace kube-system \
        --reuse-values \
        --set hubble.enabled=true \
        --set hubble.relay.enabled=true \
        --set hubble.ui.enabled=true
      ```
      Hubble을 활성화하여 네트워크 흐름 모니터링 및 문제 해결 기능을 제공합니다.
   
   5. **클러스터 간 연결**:
      Cilium Cluster Mesh를 구성하여 여러 EKS 클러스터 간의 원활한 네트워킹을 제공합니다.
   
   6. **모니터링 통합**:
      Prometheus와 Grafana를 설정하여 Cilium 메트릭을 수집하고 시각화합니다.
   
   이러한 최적화를 통해 AWS EKS에서 Cilium의 성능, 보안, 관찰 가능성을 극대화할 수 있습니다.
   </details>

## 결론

이 퀴즈를 통해 Kubernetes의 서비스와 네트워킹에 대한 이해도를 테스트했습니다. 서비스 유형, 인그레스, 네트워크 정책, 서비스 디스커버리, CoreDNS, Cilium 등의 개념을 다루었습니다. 이러한 개념을 이해하고 활용하면 안전하고 확장 가능한 Kubernetes 애플리케이션을 구축할 수 있습니다.
