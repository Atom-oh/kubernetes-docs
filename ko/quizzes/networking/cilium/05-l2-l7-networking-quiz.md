# Cilium L2–L7 네트워킹 및 로드 밸런싱 퀴즈

> **Cilium 1.20.1 · CLI 0.20.0 · 2026-09-12**

## 객관식 문제

1. **HTTP·DNS·gRPC 애플리케이션 동작은 개념적인 OSI 어느 계층에 해당하나요?**
   - A) L1
   - B) L2
   - C) L3
   - D) L7

   <details>
   <summary>정답 보기</summary>

   **정답: D) L7**

   애플리케이션 프로토콜은 개념적으로 L7에 해당합니다. 모든 프로토콜에 Cilium 내장 정책 parser가 있다는 뜻은 아니며 Kafka L7 규칙은 제거되었습니다.

   </details>

2. **DSR의 직접 반환 특성은 무엇인가요?**
   - A) 모든 응답 암호화
   - B) 원격 backend가 진입 LB 노드로 돌아가지 않고 응답 가능
   - C) Client IP 인증
   - D) 앞단 proxy가 바꾼 client IP 복원

   <details>
   <summary>정답 보기</summary>

   **정답: B) 원격 backend가 진입 LB 노드로 돌아가지 않고 응답 가능**

   비대칭 반환 경로를 네트워크가 지원해야 합니다. 응답 경로 hop을 줄일 수 있지만 성능·client IP 보존은 실제 topology에 따릅니다.

   </details>

3. **지원되는 Cilium HTTP/gRPC 정책을 담당하는 구성 요소는 무엇인가요?**
   - A) kube-proxy
   - B) Hubble Relay
   - C) Envoy
   - D) CoreDNS

   <details>
   <summary>정답 보기</summary>

   **정답: C) Envoy**

   Envoy 배포는 설치 값에 따릅니다. DNS는 Cilium DNS proxy를 사용하며 지원하지 않는 Kafka 규칙을 선언한다고 parser가 설치되지 않습니다.

   </details>

4. **문서화된 Cilium BPF Service backend 선택 알고리즘 쌍은 무엇인가요?**
   - A) Round Robin과 Least Connection
   - B) Random과 Maglev
   - C) Source-IP Hash와 Weighted Response Time
   - D) 모든 Envoy 알고리즘

   <details>
   <summary>정답 보기</summary>

   **정답: B) Random과 Maglev**

   BPF 선택과 Envoy L7 LB는 다른 구성 요소입니다. Maglev는 지정된 외부 경로에 적용되며 일반 socket-LB E–W 트래픽은 대상이 아닙니다.

   </details>

5. **마스커레이딩 구현 설명으로 맞는 것은 무엇인가요?**
   - A) BPF가 모든 workload에서 항상 빠름
   - B) 모든 Linux kernel이 현재 Cilium 지원
   - C) 두 구현 모두 커널에서 동작하며 설정·플랫폼 조건이 있음
   - D) BPF를 선택하면 routing 조건이 없어짐

   <details>
   <summary>정답 보기</summary>

   **정답: C) 두 구현 모두 커널에서 동작하며 설정·플랫폼 조건이 있음**

   제품 이름이나 커널 실행만으로 성능 결과가 결정되지 않습니다. 이 릴리스의 BPF masquerading에는 기능·장치 의존성이 있으며 IPv6는 beta입니다.

   </details>

6. **현재 kube-proxy 대체를 활성화하는 값은 무엇인가요?**
   - A) kubeProxyReplacement: partial
   - B) kubeProxyReplacement: true
   - C) kubeProxyReplacement: strict
   - D) kubeProxyReplacement: hybrid

   <details>
   <summary>정답 보기</summary>

   **정답: B) kubeProxyReplacement: true**

   현재 true 값과 API 연결 등 전체 대체 조건을 사용합니다. 이전 strict/partial 표현은 현재 설정 계약이 아닙니다.

   </details>

7. **Cilium 내장 HTTP 정책 조건이 아닌 것은 무엇인가요?**
   - A) Method
   - B) Path
   - C) 지원 header 조건
   - D) 임의 요청 본문 내용

   <details>
   <summary>정답 보기</summary>

   **정답: D) 임의 요청 본문 내용**

   Method·path와 지원 header 조건은 다릅니다. 값이 있는 headers 문자열은 일반 정규식이 아닌 리터럴입니다. Payload 검사는 별도로 설계한 애플리케이션·proxy 기능이 필요합니다.

   </details>

8. **가이드에서 의도한 Cilium/Istio 통합 모델은 무엇인가요?**
   - A) Istio sidecar 자동 우회
   - B) Istio 경로를 보존하고 Cilium 네트워크 제어와 Istio L7·mTLS 책임을 조합
   - C) mTLS 자동 비활성화
   - D) 모든 Cilium HTTP 규칙으로 암호화된 Istio 트래픽 검사

   <details>
   <summary>정답 보기</summary>

   **정답: B) Istio 경로를 보존하고 Cilium 네트워크 제어와 Istio L7·mTLS 책임을 조합**

   CNI·socket-LB 호환성을 구성하고 topology를 검증합니다. 예제는 Istio mTLS를 유지하고 암호문에 평문 HTTP 검사를 적용하는 대신 Cilium L3/L4 정책을 사용합니다.

   </details>

9. **Socket-level LB가 할 수 있는 것은 무엇인가요?**
   - A) 지원 socket hook에서 패킷 생성 전 backend 선택
   - B) HTTP header 자동 인증
   - C) 모든 트래픽 해독
   - D) 외부 LB 생성

   <details>
   <summary>정답 보기</summary>

   **정답: A) 지원 socket hook에서 패킷 생성 전 backend 선택**

   TCP connect와 지원 UDP socket 경로에서 Service를 backend로 먼저 변환할 수 있습니다. 보편적인 지연 보장이 아니며 sidecar interception과 함께 쓰면 별도 설정이 필요할 수 있습니다.

   </details>

10. **적절한 fragment 처리 원칙은 무엇인가요?**
    - A) Tracking이 모든 fragment 공격 차단 보장
    - B) 유효 path MTU를 계획하고 필요한 오류 신호를 확인
    - C) 모든 fragment를 항상 폐기
    - D) Cilium MTU는 항상 최종 Pod payload 크기

    <details>
    <summary>정답 보기</summary>

    **정답: B) 유효 path MTU를 계획하고 필요한 오류 신호를 확인**

    Cilium MTU는 기반 네트워크 값의 override입니다. Fragment tracking은 L4 문맥을 보존하며 재조립·공격 차단 보장이 아닙니다. PMTUD도 필요한 신호·경로가 깨지면 실패할 수 있습니다.

    </details>

## 단답형 문제

11. **현재 내장 L7 정책 그룹과 gRPC의 관계를 설명하세요.**

<details>
<summary>정답 보기</summary>

HTTP와 DNS입니다. 지원 gRPC 제약은 Envoy의 HTTP/2 path·header 매칭을 사용합니다. DNS는 Cilium DNS proxy이고 Kafka L7 규칙은 제거되었습니다. TLS 가시성은 가정하지 말고 구성해야 합니다.

</details>

12. **Service backend readiness와 일반 active health-check 엔진을 구분하세요.**

<details>
<summary>정답 보기</summary>

Kubernetes endpoint·readiness 상태가 Service·종료 의미와 전파 지연에 따라 backend 선택에 영향을 줍니다. 모든 BPF Service가 별도 TCP/HTTP probe를 수행한다는 뜻은 아닙니다. Cilium 연결 건강 상태, 애플리케이션 probe, proxy health check는 다른 메커니즘입니다.

</details>

13. **외부 경로에서 Pod의 outbound source 주소를 바꾸는 동작은 무엇인가요?**

<details>
<summary>정답 보기</summary>

Source NAT/masquerading입니다. Service backend로의 목적지 변환과 구분합니다. 선택 인터페이스, 제외 CIDR, 노드 예외와 후단 cloud NAT가 관측 source에 영향을 주며 외부 HTTP 성공만으로 구현이 증명되지 않습니다.

</details>

14. **Maglev와 sessionAffinity: ClientIP가 서로 대체되지 않는 이유를 설명하세요.**

<details>
<summary>정답 보기</summary>

Maglev는 지원 경로에서 호환 table·상태·seed로 일관된 backend 선택을 제공합니다. ClientIP affinity는 IP 또는 해당 socket-LB namespace cookie에 따른 별도 client별 Service affinity와 timeout입니다. 실패·제거된 backend의 session을 보존하는 보장은 아닙니다.

</details>

15. **L4와 TCP·UDP의 신뢰성 차이를 설명하세요.**

<details>
<summary>정답 보기</summary>

L4는 전송 계층입니다. TCP는 신뢰할 수 있는 순서 있는 byte stream, UDP는 전달·순서 보장이 없는 datagram입니다. 모든 애플리케이션에서 UDP가 더 빠른 것은 아니며 port·protocol 정책이 애플리케이션 인증을 제공하지 않습니다.

</details>

## 실습 문제

16. **l7-exercise의 TCP8080 API에 frontend GET /api/v1/users를 허용하고 POST /api/v1/data는 X-Auth-Token 존재 시에만 허용하는 정책을 작성하세요.**

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-http
  namespace: l7-exercise
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: l7-exercise
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/users$
        - method: ^POST$
          path: ^/api/v1/data$
          headerMatches:
          - name: x-auth-token
```

해당 workload label·namespace·listener가 전제입니다. 이름만 있는 headerMatches는 존재를 확인하며 토큰을 검증하지 않습니다. 이전 `X-Auth-Token: .*`는 모든 값이 아니라 리터럴 값 매칭입니다. 다른 적용 정책과 실현 proxy 상태를 확인합니다.

</details>

17. **준비된 새 kube-proxy-free IPv4 테스트 클러스터에 문서화된 DSR/Maglev 프로필을 설치하세요.**

<details>
<summary>정답 보기</summary>

**lb-values.yaml**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```

```bash
: "${API_SERVER_HOST:?Set the real reachable API server host}"
: "${API_SERVER_PORT:?Set its actual port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.1 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

Geneve overlay와 Geneve DSR dispatch를 사용합니다. API endpoint, 반환 경로, 보존한 공통 Maglev seed가 준비되어야 합니다. 65521은 허용 크기이지 보편적 필수값이 아닙니다. 임의 설치 후 kube-proxy를 삭제하거나 기능 테스트 편의상 실행 중 전달 모드를 바꾸지 않습니다.

</details>

18. **order-service의 orders produce, payment-processor의 payments consume이 요구사항입니다. 현재 Cilium과 broker가 각각 집행할 부분은 무엇인가요?**

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: broker-connectivity
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: order-service
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: payment-processor
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

두 source workload를 가정한 TCP9092 broker listener에 연결하도록 허용할 뿐입니다. 실제 설정 port로 바꿔야 하며 topic 작업을 집행하지 않습니다. Broker principal을 구분해 인증하고 Kafka에서 produce·consume·consumer-group 인가를 구성합니다. rules.kafka가 제거되었으므로 이전 YAML을 완성된 인가로 제시하면 안 됩니다.

</details>

19. **실제로 라우팅 가능한 10.0.0.0/8 목적지를 제외하는 BPF masquerading 설정 조각을 작성하세요.**

<details>
<summary>정답 보기</summary>

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

준비한 설정에 병합합니다. BPF NodePort·장치 조건과 반환 경로가 필요합니다. ipv4NativeRoutingCIDR은 해당 masquerade 제외를 제어하며 route 생성이나 routingMode 전환이 아닙니다. 선택 노드의 cilium-dbg status --verbose, cilium-dbg bpf nat list와 통제된 외부 관측을 함께 확인합니다.

</details>

20. **L7 정책의 예상과 다른 동작을 중단 없이 조사하는 순서를 작성하세요.**

<details>
<summary>정답 보기</summary>

```bash
cilium status --verbose
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system get pods -l k8s-app=cilium-envoy -o wide
kubectl -n cilium-l2l7-demo get pods -o wide
export APP_POD=REPLACE-WITH-APP1-POD
export CILIUM_POD=REPLACE-WITH-AGENT-ON-APP-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "pod-name:cilium-l2l7-demo:$APP_POD"
kubectl -n cilium-l2l7-demo get cnp -o yaml
kubectl get ccnp -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
```

명시적으로 활성화한 Envoy DaemonSet을 사용하는 경우:

```bash
export ENVOY_POD=REPLACE-WITH-ENVOY-POD-ON-APP-NODE
kubectl -n kube-system logs "$ENVOY_POD" --all-containers=true --tail=100
```

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

임의 DaemonSet Pod가 아닌 workload 노드의 agent·Envoy를 선택합니다. Envoy DaemonSet이면 해당 Pod의 제한된 로그, embedded 방식이면 설정된 agent 로그를 확인합니다. Relay forward는 별도 터미널에 유지합니다. 의도·실현 규칙, 평문·TLS 가시성, 앱 응답·플로우를 비교합니다. HTTP403은 packet drop과 다르며 관측 누락도 필터·유실 때문일 수 있습니다. 제거된 policy trace나 강제 endpoint 재생성이 첫 단계일 필요는 없습니다.

</details>

---

[학습 자료로 돌아가기](../../../networking/cilium/05-l2-l7-networking.md) | [다음 퀴즈: 보안 및 가시성](./06-security-visibility-quiz.md)
