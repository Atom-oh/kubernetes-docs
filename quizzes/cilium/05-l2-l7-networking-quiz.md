# Cilium L2-L7 네트워킹 및 로드 밸런싱 퀴즈

이 퀴즈는 Cilium의 L2-L7 네트워킹 기능, 로드 밸런싱 아키텍처, 마스커레이딩, 서비스 메시 통합 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. OSI 모델에서 HTTP, gRPC, DNS 등의 프로토콜이 작동하는 계층은 무엇인가요?
   - A) L3 (네트워크 계층)
   - B) L4 (전송 계층)
   - C) L5 (세션 계층)
   - D) L7 (응용 계층)

<details>

<summary>정답 보기</summary>

**정답: D) L7 (응용 계층)**

**설명:**
OSI 모델에서 L7(응용 계층)은 사용자와 가장 가까운 계층으로, HTTP, HTTPS, gRPC, DNS, FTP, Kafka 등의 애플리케이션 프로토콜이 작동합니다. Cilium은 L7 계층에서 API 인식 필터링을 제공하여, HTTP 메서드/경로/헤더, gRPC 메서드, Kafka 주제 등을 기반으로 세밀한 네트워크 정책을 적용할 수 있습니다. 이는 마이크로서비스 아키텍처에서 서비스 간 통신을 세밀하게 제어하는 데 필수적입니다.
</details>

2. Cilium의 DSR(Direct Server Return) 모드의 주요 장점은 무엇인가요?
   - A) 클라이언트 IP를 숨길 수 있다
   - B) 응답 트래픽이 로드 밸런서를 거치지 않아 성능이 향상된다
   - C) 모든 트래픽을 암호화한다
   - D) L7 정책을 자동으로 적용한다

<details>

<summary>정답 보기</summary>

**정답: B) 응답 트래픽이 로드 밸런서를 거치지 않아 성능이 향상된다**

**설명:**
DSR(Direct Server Return) 모드에서는 클라이언트의 요청만 로드 밸런서를 통과하고, 서버의 응답은 로드 밸런서를 우회하여 직접 클라이언트로 전송됩니다. 이로 인해 로드 밸런서의 병목 현상이 제거되고, 네트워크 대역폭이 절약되며, 응답 지연 시간이 단축됩니다. 특히 대용량 응답(파일 다운로드, 스트리밍 등)을 처리할 때 효과적입니다. DSR 모드는 외부 로드 밸런서 뒤에서도 클라이언트 IP를 보존합니다.
</details>

3. Cilium에서 L7 프록시 기능을 제공하는 구성 요소는 무엇인가요?
   - A) kube-proxy
   - B) Hubble
   - C) Envoy
   - D) CoreDNS

<details>

<summary>정답 보기</summary>

**정답: C) Envoy**

**설명:**
Cilium은 L7 프록시 기능을 위해 Envoy 프록시를 통합하고 있습니다. CiliumNetworkPolicy에 L7 규칙(HTTP, gRPC, Kafka, DNS 등)을 정의하면 Cilium은 자동으로 Envoy 프록시를 사이드카 없이 투명하게 배치합니다. Envoy는 HTTP/gRPC 트래픽 처리, 고급 로드 밸런싱, 트래픽 분할, 메트릭 수집 등의 기능을 제공합니다. 이 방식은 별도의 사이드카 프록시를 배포하지 않아도 되므로 리소스 오버헤드가 줄어듭니다.
</details>

4. Cilium에서 지원하는 로드 밸런싱 알고리즘이 아닌 것은 무엇인가요?
   - A) Round Robin
   - B) Maglev Consistent Hashing
   - C) Source IP Hash
   - D) Weighted Response Time

<details>

<summary>정답 보기</summary>

**정답: D) Weighted Response Time**

**설명:**
Cilium은 Round Robin, Least Connection, Source IP Hash, Random, Maglev Consistent Hashing 등의 로드 밸런싱 알고리즘을 지원합니다. Maglev는 Google에서 개발한 일관된 해싱 알고리즘으로, 백엔드 서버가 추가/제거되어도 연결의 일관성을 유지합니다. Weighted Response Time(가중 응답 시간)은 Cilium에서 직접 지원하지 않는 알고리즘입니다. 그러나 Envoy 프록시를 통해 더 고급 로드 밸런싱 전략을 구현할 수 있습니다.
</details>

5. Cilium의 마스커레이딩(Masquerading)에서 eBPF 기반 구현의 장점이 아닌 것은 무엇인가요?
   - A) iptables보다 빠른 처리 속도
   - B) 더 나은 확장성
   - C) 모든 Linux 커널 버전에서 지원
   - D) 커널 공간에서 직접 처리

<details>

<summary>정답 보기</summary>

**정답: C) 모든 Linux 커널 버전에서 지원**

**설명:**
eBPF 기반 마스커레이딩은 iptables보다 빠르고 확장성이 뛰어나며, 커널 공간에서 직접 처리되어 효율적입니다. 그러나 eBPF 기반 마스커레이딩은 최신 Linux 커널(4.19 이상)에서만 완전히 지원됩니다. 구형 커널에서는 iptables 기반 마스커레이딩으로 폴백해야 합니다. Cilium 설정에서 `enable-bpf-masquerade: true` 옵션으로 eBPF 기반 마스커레이딩을 활성화할 수 있습니다.
</details>

6. Cilium에서 Kubernetes 서비스를 위해 kube-proxy를 완전히 대체하는 모드는 무엇인가요?
   - A) kube-proxy-replacement: partial
   - B) kube-proxy-replacement: strict
   - C) kube-proxy-replacement: hybrid
   - D) kube-proxy-replacement: disabled

<details>

<summary>정답 보기</summary>

**정답: B) kube-proxy-replacement: strict**

**설명:**
`kube-proxy-replacement: strict` 설정은 Cilium이 kube-proxy의 모든 기능을 완전히 대체하도록 합니다. 이 모드에서 Cilium은 ClusterIP, NodePort, LoadBalancer, ExternalIP 서비스를 모두 처리합니다. strict 모드에서는 kube-proxy를 반드시 제거하거나 비활성화해야 합니다. `partial` 모드는 일부 기능만 대체하고, `disabled`는 kube-proxy 대체를 비활성화합니다. strict 모드는 DSR, Maglev 해싱, 소켓 수준 로드 밸런싱 등의 고급 기능을 사용할 때 필요합니다.
</details>

7. Cilium L7 정책에서 HTTP 요청을 필터링할 때 사용할 수 있는 조건이 아닌 것은 무엇인가요?
   - A) HTTP 메서드 (GET, POST 등)
   - B) URL 경로
   - C) HTTP 헤더
   - D) 요청 본문 (Request Body)

<details>

<summary>정답 보기</summary>

**정답: D) 요청 본문 (Request Body)**

**설명:**
Cilium L7 HTTP 정책에서는 HTTP 메서드(GET, POST, PUT, DELETE 등), URL 경로(정규식 지원), HTTP 헤더(정규식 지원)를 기반으로 필터링할 수 있습니다. 그러나 요청 본문(Request Body)을 검사하는 것은 성능 오버헤드가 크고 복잡하기 때문에 Cilium에서 직접 지원하지 않습니다. 요청 본문 검사가 필요한 경우 WAF(Web Application Firewall)나 별도의 애플리케이션 계층 보안 솔루션을 사용해야 합니다.
</details>

8. Cilium에서 Istio와 통합할 때의 주요 이점은 무엇인가요?
   - A) Istio의 모든 기능을 완전히 대체한다
   - B) eBPF 기반 데이터 플레인으로 사이드카 오버헤드를 줄인다
   - C) mTLS를 자동으로 비활성화한다
   - D) Istio 없이 서비스 메시를 구현한다

<details>

<summary>정답 보기</summary>

**정답: B) eBPF 기반 데이터 플레인으로 사이드카 오버헤드를 줄인다**

**설명:**
Cilium과 Istio를 통합하면 eBPF 기반 데이터 플레인을 통해 일부 Envoy 사이드카 기능을 대체하여 리소스 오버헤드를 줄일 수 있습니다. Cilium은 L3/L4 트래픽 처리와 네트워크 정책을 eBPF로 처리하고, 필요한 경우에만 L7 트래픽을 Envoy로 전달합니다. 이를 통해 성능이 향상되고 지연 시간이 줄어듭니다. 그러나 Cilium이 Istio의 모든 기능을 대체하는 것은 아니며, mTLS 등 Istio의 고급 기능은 여전히 Istio에서 처리됩니다.
</details>

9. Cilium에서 소켓 수준 로드 밸런싱(Socket-level LB)의 이점은 무엇인가요?
   - A) 패킷 처리 전에 커널에서 서비스 IP를 백엔드 IP로 변환한다
   - B) L7 정책을 자동으로 적용한다
   - C) 암호화된 트래픽만 처리한다
   - D) 외부 로드 밸런서가 필요하다

<details>

<summary>정답 보기</summary>

**정답: A) 패킷 처리 전에 커널에서 서비스 IP를 백엔드 IP로 변환한다**

**설명:**
소켓 수준 로드 밸런싱은 패킷이 전송되기 전에 connect() 시스템 호출 시점에서 서비스 IP를 백엔드 포드 IP로 변환합니다. 이는 기존 패킷 기반 NAT(Network Address Translation)보다 훨씬 효율적입니다. 장점으로는 conntrack(연결 추적) 오버헤드 감소, 소스 IP 보존, 낮은 지연 시간, 더 나은 확장성 등이 있습니다. 소켓 수준 LB는 애플리케이션 관점에서 투명하게 작동하며, 애플리케이션은 백엔드 포드와 직접 통신하는 것처럼 보입니다.
</details>

10. IPv4 프래그먼트 처리와 관련하여 Cilium에서 권장하는 모범 사례는 무엇인가요?
    - A) 프래그먼트 추적을 항상 비활성화한다
    - B) MTU를 일관되게 구성하여 프래그먼테이션을 방지한다
    - C) 모든 프래그먼트를 차단한다
    - D) 프래그먼트 크기를 최대로 설정한다

<details>

<summary>정답 보기</summary>

**정답: B) MTU를 일관되게 구성하여 프래그먼테이션을 방지한다**

**설명:**
IPv4 프래그먼테이션은 성능 저하와 보안 문제를 일으킬 수 있으므로, 가능한 한 방지하는 것이 좋습니다. 이를 위해 네트워크 전체에서 MTU(Maximum Transmission Unit)를 일관되게 구성하고, 오버레이 네트워크(VXLAN 등)를 사용할 경우 캡슐화 오버헤드(약 50바이트)를 고려하여 MTU를 조정해야 합니다. Path MTU Discovery(PMTUD)를 활성화하면 자동으로 최적의 MTU를 감지할 수 있습니다. 프래그먼트 추적(`enable-ipv4-fragment-tracking`)을 활성화하면 프래그먼트 기반 공격을 방지할 수 있습니다.
</details>

## 단답형 문제

11. Cilium에서 L7 네트워크 정책을 적용할 때 지원하는 프로토콜 4가지를 나열하세요.

<details>

<summary>정답 보기</summary>

**정답:** HTTP, gRPC, Kafka, DNS

**설명:**
Cilium L7 정책에서 지원하는 주요 프로토콜은 다음과 같습니다:
- **HTTP/HTTPS**: REST API 및 웹 트래픽, 메서드/경로/헤더 기반 필터링 지원
- **gRPC**: 마이크로서비스 간 RPC 통신, 서비스/메서드 기반 필터링 지원
- **Kafka**: 메시지 큐 프로토콜, 주제/클라이언트ID/API 키 기반 필터링 지원
- **DNS**: DNS 쿼리 및 응답 필터링, FQDN 기반 정책 지원
또한 Envoy 필터를 통해 사용자 정의 프로토콜도 지원할 수 있습니다.
</details>

12. Cilium 로드 밸런서에서 백엔드 서버의 상태를 확인하는 메커니즘의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Health Check (상태 확인 또는 헬스 체크)

**설명:**
Cilium 로드 밸런서는 여러 가지 상태 확인(Health Check) 메커니즘을 지원합니다:
- **TCP 상태 확인**: 포트 연결 가능성 확인
- **HTTP 상태 확인**: HTTP 응답 코드 확인 (200 OK 등)
- **Kubernetes Readiness/Liveness Probe 통합**: 포드의 상태 프로브 결과 활용
비정상 백엔드는 자동으로 로드 밸런싱 풀에서 제외되며, 복구되면 다시 포함됩니다. 이를 통해 서비스의 고가용성을 보장합니다.
</details>

13. Cilium에서 클러스터 외부 트래픽의 소스 IP를 내부 IP로 변환하는 기능의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Masquerading (마스커레이딩) 또는 SNAT (Source NAT)

**설명:**
마스커레이딩(Masquerading)은 클러스터 내부 포드에서 외부로 나가는 트래픽의 소스 IP를 노드의 IP로 변환하는 기능입니다. 이는 SNAT(Source Network Address Translation)의 한 형태입니다. 마스커레이딩의 목적은 클러스터 내부 IP를 외부 네트워크에 숨기고, 클러스터 외부 서비스에 대한 접근을 가능하게 하는 것입니다. Cilium은 iptables 기반과 eBPF 기반 마스커레이딩을 모두 지원하며, eBPF 기반이 더 높은 성능을 제공합니다.
</details>

14. Cilium에서 kube-proxy를 대체할 때 세션 지속성을 유지하기 위해 사용하는 해싱 알고리즘의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Maglev (Consistent Hashing)

**설명:**
Maglev는 Google에서 개발한 일관된 해싱(Consistent Hashing) 알고리즘입니다. Cilium에서 Maglev를 사용하면 백엔드 서버가 추가되거나 제거되어도 대부분의 기존 연결이 동일한 백엔드로 유지됩니다. 이는 세션 어피니티(Session Affinity)가 필요한 애플리케이션에서 중요합니다. Maglev는 높은 부하 분산 균등성과 낮은 연결 재분배율을 제공하여, 대규모 로드 밸런싱 환경에서 효과적입니다.
</details>

15. OSI 모델에서 TCP와 UDP 프로토콜이 작동하는 계층의 이름과 번호는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** L4 (전송 계층, Transport Layer)

**설명:**
L4(전송 계층)는 OSI 모델의 4번째 계층으로, 엔드-투-엔드 연결과 신뢰성을 담당합니다. 이 계층에서 TCP(Transmission Control Protocol)와 UDP(User Datagram Protocol)가 작동합니다. TCP는 연결 지향적이고 신뢰할 수 있는 통신을 제공하며, UDP는 비연결형으로 빠르지만 신뢰성을 보장하지 않습니다. Cilium L4 정책에서는 포트 번호와 프로토콜(TCP/UDP)을 기반으로 트래픽을 필터링할 수 있습니다.
</details>

## 실습 문제

16. HTTP GET 메서드로 `/api/v1/users` 경로에 대한 요청만 허용하고, POST 메서드로 `/api/v1/data` 경로에 대한 요청은 `X-Auth-Token` 헤더가 있는 경우에만 허용하는 CiliumNetworkPolicy를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-http-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/users"
        - method: "POST"
          path: "/api/v1/data"
          headers:
          - "X-Auth-Token: .*"
```

**설명:**
이 CiliumNetworkPolicy는 L7 HTTP 규칙을 사용하여 세밀한 접근 제어를 구현합니다. `rules.http` 섹션에서 두 가지 규칙을 정의합니다: 첫 번째는 GET 메서드로 `/api/v1/users` 경로 허용, 두 번째는 POST 메서드로 `/api/v1/data` 경로에 대해 `X-Auth-Token` 헤더가 있는 경우에만 허용합니다. 헤더 값은 정규식으로 지정할 수 있어 `.*`는 어떤 값이든 허용합니다. 이 정책이 적용되면 Cilium은 자동으로 Envoy 프록시를 투명하게 배치하여 L7 트래픽을 검사합니다.
</details>

17. kube-proxy 대체 모드로 Cilium을 설치하고, DSR 모드와 Maglev 해싱을 활성화하는 Helm 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Helm repo 추가
helm repo add cilium https://helm.cilium.io/
helm repo update

# kube-proxy 대체 + DSR + Maglev 설정으로 Cilium 설치
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=6443 \
  --set loadBalancer.mode=dsr \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set bpf.masquerade=true

# 기존 kube-proxy 비활성화 (DaemonSet 삭제 또는 스케일 다운)
kubectl -n kube-system delete ds kube-proxy
# 또는 kube-proxy ConfigMap 수정하여 비활성화

# 설치 확인
cilium status --verbose
kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
```

**설명:**
`kubeProxyReplacement=true`는 Cilium이 kube-proxy 기능을 대체하도록 설정합니다. `k8sServiceHost`와 `k8sServicePort`는 API 서버 주소를 지정합니다(kube-proxy 없이 API 서버에 접근하기 위해 필요). `loadBalancer.mode=dsr`은 Direct Server Return 모드를 활성화하고, `loadBalancer.algorithm=maglev`는 Maglev 일관된 해싱을 사용합니다. `maglev.tableSize`는 해시 테이블 크기를 설정합니다(소수 권장). `bpf.masquerade=true`는 eBPF 기반 마스커레이딩을 활성화합니다.
</details>

18. Cilium에서 Kafka 트래픽에 대한 L7 정책을 적용하여, `orders` 주제에 대한 produce 작업만 허용하고 `payments` 주제는 consume만 허용하는 CiliumNetworkPolicy를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "kafka-l7-policy"
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: order-service
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "produce"
          topic: "orders"
  - fromEndpoints:
    - matchLabels:
        app: payment-processor
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "fetch"
          topic: "payments"
```

**설명:**
이 CiliumNetworkPolicy는 Kafka L7 규칙을 사용하여 세밀한 접근 제어를 구현합니다. 첫 번째 ingress 규칙은 `order-service` 포드가 `orders` 주제에 대해 produce(`apiKey: produce`) 작업만 할 수 있도록 허용합니다. 두 번째 규칙은 `payment-processor` 포드가 `payments` 주제에 대해 consume(`apiKey: fetch`) 작업만 할 수 있도록 허용합니다. Kafka API 키는 `produce`, `fetch`, `metadata`, `offsets` 등이 있으며, `clientID`를 추가하여 특정 클라이언트만 허용할 수도 있습니다.
</details>

19. Cilium에서 eBPF 기반 마스커레이딩을 활성화하고, 특정 CIDR 범위(10.0.0.0/8)에 대해서는 마스커레이딩을 제외하는 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
# ConfigMap 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-ipv4-masquerade: "true"
  enable-bpf-masquerade: "true"
  ipv4-native-routing-cidr: "10.0.0.0/8"
  enable-ipv6-masquerade: "false"
```

```bash
# Helm을 사용한 설치/업그레이드
helm upgrade cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8 \
  --set bpf.masquerade=true \
  --set enableIPv4Masquerade=true

# 설정 확인
kubectl -n kube-system exec ds/cilium -- cilium status --verbose | grep -i masquerade

# 마스커레이딩 규칙 확인
kubectl -n kube-system exec ds/cilium -- cilium bpf nat list
```

**설명:**
`enable-bpf-masquerade: true`는 eBPF 기반 마스커레이딩을 활성화합니다. `ipv4-native-routing-cidr: 10.0.0.0/8`은 이 CIDR 범위에 대한 트래픽은 마스커레이딩 없이 네이티브 라우팅을 사용하도록 설정합니다. 이는 클러스터 내부 통신이나 VPC 내부 통신에서 소스 IP를 보존해야 할 때 유용합니다. 클러스터 포드 CIDR과 서비스 CIDR이 이 범위에 포함되면 내부 트래픽에 마스커레이딩이 적용되지 않습니다.
</details>

20. L7 정책이 예상대로 작동하지 않을 때 Cilium에서 문제를 진단하는 명령어들을 작성하세요. Envoy 프록시 상태, 정책 적용 상태, 실시간 트래픽 모니터링을 포함해야 합니다.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. Cilium 전체 상태 확인
cilium status --verbose

# 2. Envoy 프록시 상태 확인
kubectl -n kube-system exec ds/cilium -- cilium status | grep -i proxy
kubectl -n kube-system exec ds/cilium -- cilium bpf proxy list

# 3. 정책 적용 상태 확인
cilium policy get
kubectl get cnp -A -o wide
kubectl get ccnp -A -o wide

# 4. 특정 엔드포인트의 정책 상태 확인
cilium endpoint list
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# 5. 실시간 트래픽 모니터링 (L7 포함)
cilium monitor --type l7
cilium monitor --type policy-verdict
cilium monitor --type drop

# 6. Hubble을 통한 L7 흐름 관찰
hubble observe --protocol http
hubble observe --verdict DROPPED
hubble observe --pod <namespace>/<pod-name>

# 7. Envoy 로그 확인
kubectl -n kube-system logs ds/cilium | grep -i envoy
kubectl -n kube-system logs ds/cilium | grep -i proxy

# 8. 엔드포인트 재생성 (정책 재적용)
kubectl -n kube-system exec ds/cilium -- cilium endpoint regenerate <endpoint_id>

# 9. 네트워크 정책 트러블슈팅
cilium policy trace --src-identity <src_id> --dst-identity <dst_id> --dport <port>
```

**설명:**
L7 정책 문제 해결 시 단계적 접근이 필요합니다. 먼저 `cilium status`로 전체 시스템 상태를 확인하고, Envoy 프록시가 정상적으로 실행 중인지 확인합니다. `cilium policy get`으로 적용된 정책을 확인하고, `cilium endpoint get`으로 특정 포드에 정책이 올바르게 적용되었는지 확인합니다. `cilium monitor`와 `hubble observe`로 실시간 트래픽과 정책 판정을 모니터링합니다. `policy trace` 명령어는 특정 트래픽 흐름에 대한 정책 결정 과정을 시뮬레이션합니다.
</details>

---

[학습 자료로 돌아가기](../../cilium/05-l2-l7-networking.md) | [다음 퀴즈: 보안 및 가시성](./06-security-visibility-quiz.md)
