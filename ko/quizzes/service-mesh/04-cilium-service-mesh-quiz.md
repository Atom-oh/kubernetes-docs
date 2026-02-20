# Cilium Service Mesh 퀴즈

이 퀴즈는 Cilium Service Mesh에 대한 이해도를 테스트합니다. 각 질문에 대해 가장 적절한 답을 선택하세요.

---

## eBPF 아키텍처

1. Cilium Service Mesh가 기존 서비스 메시와 다른 핵심적인 아키텍처 차이점은?
   - A) 더 많은 사이드카 프록시 사용
   - B) eBPF를 사용한 커널 레벨 처리
   - C) Java 기반 프록시
   - D) 별도의 컨트롤 플레인 클러스터 필요

<details>
<summary>정답 보기</summary>

**정답: B) eBPF를 사용한 커널 레벨 처리**

**설명:**
Cilium Service Mesh는 eBPF(extended Berkeley Packet Filter)를 사용하여 네트워크 트래픽을 커널 레벨에서 직접 처리합니다. 이를 통해 사이드카 프록시 없이도 서비스 메시 기능을 제공할 수 있습니다.

</details>

---

2. eBPF 프로그램이 실행되는 위치는 어디입니까?
   - A) 사용자 공간 (User Space)
   - B) 컨테이너 내부
   - C) 커널 공간 (Kernel Space)
   - D) 별도의 가상 머신

<details>
<summary>정답 보기</summary>

**정답: C) 커널 공간 (Kernel Space)**

**설명:**
eBPF 프로그램은 Linux 커널 내에서 실행됩니다. 이를 통해 시스템 콜, 네트워크 패킷, 커널 함수 등에 대한 고성능 처리가 가능합니다. 커널에서 직접 실행되므로 컨텍스트 스위칭 오버헤드가 최소화됩니다.

</details>

---

3. Cilium에서 eBPF 기반 로드 밸런싱의 장점이 아닌 것은?
   - A) kube-proxy 대체 가능
   - B) 더 낮은 지연 시간
   - C) 더 적은 메모리 사용
   - D) 모든 애플리케이션 프로토콜 자동 인식

<details>
<summary>정답 보기</summary>

**정답: D) 모든 애플리케이션 프로토콜 자동 인식**

**설명:**
eBPF 기반 로드 밸런싱은 L3/L4 레벨에서 동작하며, L7 프로토콜 인식에는 Envoy 프록시가 필요합니다. eBPF의 장점은 kube-proxy 대체, 낮은 지연 시간, 적은 메모리 사용입니다.

</details>

---

4. Cilium에서 사용하는 eBPF Map의 주요 용도는?
   - A) 로그 저장
   - B) 커널과 사용자 공간 간 데이터 공유
   - C) 컨테이너 이미지 캐싱
   - D) DNS 레코드 저장

<details>
<summary>정답 보기</summary>

**정답: B) 커널과 사용자 공간 간 데이터 공유**

**설명:**
eBPF Map은 eBPF 프로그램(커널)과 사용자 공간 프로세스(Cilium Agent) 간에 데이터를 공유하는 키-값 저장소입니다. 엔드포인트 정보, 정책, 연결 상태 등을 저장합니다.

</details>

---

## Per-Node Proxy 아키텍처

5. Cilium Service Mesh의 per-node proxy 모델에서 Envoy 프록시는 어디에 배포됩니까?
   - A) 각 파드 내 사이드카
   - B) 각 노드당 하나
   - C) 중앙 집중식 클러스터
   - D) 외부 서버

<details>
<summary>정답 보기</summary>

**정답: B) 각 노드당 하나**

**설명:**
Cilium의 per-node proxy 아키텍처에서는 각 노드에 하나의 Envoy 인스턴스만 배포됩니다. 이 모델은 사이드카 방식보다 리소스 사용량이 적고 관리가 단순합니다.

</details>

---

6. Per-node proxy 아키텍처의 장점이 아닌 것은?
   - A) 리소스 사용량 감소
   - B) 관리 복잡도 감소
   - C) 파드별 완전한 격리
   - D) 운영 오버헤드 감소

<details>
<summary>정답 보기</summary>

**정답: C) 파드별 완전한 격리**

**설명:**
per-node proxy 모델에서는 노드의 모든 파드가 동일한 Envoy 인스턴스를 공유하므로 파드별 완전한 격리는 제공하지 않습니다. 완전한 격리가 필요한 경우 사이드카 모드를 사용해야 합니다.

</details>

---

7. Cilium에서 트래픽이 Envoy 프록시를 거치도록 하는 설정은?
   - A) CiliumNetworkPolicy
   - B) CiliumEnvoyConfig
   - C) CiliumEndpoint
   - D) CiliumClusterwideNetworkPolicy

<details>
<summary>정답 보기</summary>

**정답: B) CiliumEnvoyConfig**

**설명:**
CiliumEnvoyConfig(CEC)는 특정 서비스의 트래픽을 Envoy 프록시로 리다이렉트하고 L7 정책을 적용하는 데 사용됩니다. 이 리소스를 통해 HTTP 라우팅, 부하 분산 등을 구성합니다.

</details>

---

8. Cilium의 sidecar-less 서비스 메시에서 L4 트래픽은 어떻게 처리됩니까?
   - A) 항상 Envoy를 통과
   - B) eBPF가 직접 처리
   - C) kube-proxy가 처리
   - D) 처리되지 않음

<details>
<summary>정답 보기</summary>

**정답: B) eBPF가 직접 처리**

**설명:**
Cilium에서 L4(TCP/UDP) 트래픽은 eBPF 프로그램이 커널 레벨에서 직접 처리합니다. L7 정책이 필요한 경우에만 트래픽이 Envoy 프록시로 전달됩니다. 이를 통해 불필요한 프록시 홉을 줄입니다.

</details>

---

## CiliumEnvoyConfig

9. CiliumEnvoyConfig에서 지원하는 Envoy 리소스가 아닌 것은?
   - A) Listener
   - B) Cluster
   - C) Route
   - D) VirtualMachine

<details>
<summary>정답 보기</summary>

**정답: D) VirtualMachine**

**설명:**
CiliumEnvoyConfig는 Envoy의 표준 리소스인 Listener, Cluster, Route, Endpoint 등을 지원합니다. VirtualMachine은 Envoy 리소스가 아닙니다.

</details>

---

10. 다음 CiliumEnvoyConfig에서 정의하는 기능은?
    ```yaml
    spec:
      services:
      - name: my-service
        namespace: default
      backendServices:
      - name: my-service
        namespace: default
      resources:
      - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    ```
    - A) DNS 캐싱
    - B) L7 프록시 정책
    - C) 네트워크 격리
    - D) 로그 수집

<details>
<summary>정답 보기</summary>

**정답: B) L7 프록시 정책**

**설명:**
CiliumEnvoyConfig는 특정 서비스(my-service)에 대한 L7 프록시 정책을 정의합니다. services는 프론트엔드 서비스를, backendServices는 백엔드 서비스를, resources는 Envoy 구성을 지정합니다.

</details>

---

11. CiliumEnvoyConfig에서 HTTP 라우팅 규칙을 정의하는 Envoy 리소스 타입은?
    - A) type.googleapis.com/envoy.config.listener.v3.Listener
    - B) type.googleapis.com/envoy.config.cluster.v3.Cluster
    - C) type.googleapis.com/envoy.config.route.v3.RouteConfiguration
    - D) type.googleapis.com/envoy.config.endpoint.v3.Endpoint

<details>
<summary>정답 보기</summary>

**정답: C) type.googleapis.com/envoy.config.route.v3.RouteConfiguration**

**설명:**
RouteConfiguration은 HTTP 요청의 라우팅 규칙을 정의합니다. 경로 기반 라우팅, 헤더 매칭, 가중치 기반 트래픽 분할 등을 구성할 수 있습니다.

</details>

---

## Hubble

12. Hubble의 주요 기능이 아닌 것은?
    - A) 네트워크 흐름 관찰
    - B) 서비스 맵 시각화
    - C) DNS 쿼리 모니터링
    - D) 컨테이너 이미지 스캔

<details>
<summary>정답 보기</summary>

**정답: D) 컨테이너 이미지 스캔**

**설명:**
Hubble은 네트워크 흐름 관찰, 서비스 맵 시각화, DNS 쿼리 모니터링, HTTP 요청 추적 등을 제공합니다. 컨테이너 이미지 스캔은 Hubble의 기능이 아니며, Trivy나 ECR 스캔 등을 사용합니다.

</details>

---

13. Hubble에서 실시간 네트워크 흐름을 관찰하는 명령어는?
    - A) hubble status
    - B) hubble observe
    - C) hubble flows
    - D) hubble watch

<details>
<summary>정답 보기</summary>

**정답: B) hubble observe**

**설명:**
`hubble observe` 명령어는 실시간 네트워크 흐름을 모니터링합니다. 소스/목적지 파드, 프로토콜, 포트, verdict(FORWARDED/DROPPED) 등의 정보를 확인할 수 있습니다.

</details>

---

14. Hubble UI에서 제공하는 Service Map의 주요 정보가 아닌 것은?
    - A) 서비스 간 의존성
    - B) 트래픽 흐름
    - C) 응답 시간
    - D) 소스 코드 변경 이력

<details>
<summary>정답 보기</summary>

**정답: D) 소스 코드 변경 이력**

**설명:**
Hubble Service Map은 서비스 간 의존성, 트래픽 흐름, 응답 시간, 성공/실패율 등을 시각화합니다. 소스 코드 변경 이력은 Git이나 CI/CD 도구에서 관리합니다.

</details>

---

15. Hubble Relay의 역할은?
    - A) 각 노드의 Hubble 데이터를 수집하고 집계
    - B) DNS 캐싱
    - C) 인증서 관리
    - D) Envoy 구성 배포

<details>
<summary>정답 보기</summary>

**정답: A) 각 노드의 Hubble 데이터를 수집하고 집계**

**설명:**
Hubble Relay는 클러스터 내 모든 노드의 Hubble Agent로부터 네트워크 흐름 데이터를 수집하고 집계합니다. 이를 통해 클러스터 전체의 트래픽을 중앙에서 관찰할 수 있습니다.

</details>

---

## Gateway API

16. Cilium이 지원하는 Gateway API 리소스가 아닌 것은?
    - A) Gateway
    - B) HTTPRoute
    - C) GRPCRoute
    - D) TCPRoute

<details>
<summary>정답 보기</summary>

**정답: D) TCPRoute**

**설명:**
Cilium은 Gateway API의 Gateway, HTTPRoute, GRPCRoute, TLSRoute를 지원합니다. TCPRoute는 아직 완전히 지원되지 않으며, TCP 트래픽은 Service와 CiliumNetworkPolicy를 통해 관리합니다.

</details>

---

17. Gateway API에서 HTTPRoute의 parentRefs가 참조하는 것은?
    - A) Service
    - B) Gateway
    - C) Pod
    - D) Namespace

<details>
<summary>정답 보기</summary>

**정답: B) Gateway**

**설명:**
HTTPRoute의 parentRefs는 트래픽을 수신할 Gateway를 참조합니다. 하나의 HTTPRoute가 여러 Gateway에 연결될 수 있으며, 이를 통해 트래픽 라우팅 규칙을 정의합니다.

</details>

---

18. 다음 HTTPRoute 설정의 동작은?
    ```yaml
    spec:
      rules:
      - matches:
        - path:
            type: PathPrefix
            value: /api
        backendRefs:
        - name: api-service
          weight: 80
        - name: api-canary
          weight: 20
    ```
    - A) /api 경로를 api-service로만 전달
    - B) /api 경로를 80:20 비율로 두 서비스에 분할
    - C) 모든 트래픽을 차단
    - D) DNS 기반 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) /api 경로를 80:20 비율로 두 서비스에 분할**

**설명:**
이 HTTPRoute는 /api 경로 prefix와 일치하는 트래픽을 api-service(80%)와 api-canary(20%)로 분할합니다. 이는 카나리 배포에 활용됩니다.

</details>

---

## mTLS

19. Cilium에서 mTLS를 활성화하는 방법은?
    - A) CiliumNetworkPolicy에서 mtls: true 설정
    - B) Cilium Agent 구성에서 encryption.enabled=true
    - C) CiliumEnvoyConfig에서 TLS 구성
    - D) B와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D) B와 C 모두**

**설명:**
Cilium에서 mTLS는 두 가지 방법으로 구성됩니다. Cilium Agent의 encryption 설정(WireGuard 또는 IPsec)을 통한 노드 간 암호화와, CiliumEnvoyConfig를 통한 L7 레벨 mTLS 설정이 있습니다.

</details>

---

20. Cilium의 WireGuard 기반 암호화의 장점은?
    - A) 인증서 관리 불필요
    - B) L7 프로토콜 검사
    - C) 커널 레벨에서 고성능 암호화
    - D) A와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D) A와 C 모두**

**설명:**
WireGuard는 키 교환이 자동화되어 인증서 관리가 불필요하며, 커널에서 직접 암호화를 수행하여 높은 성능을 제공합니다. 단, L7 검사는 불가능하며 이를 위해서는 Envoy를 사용해야 합니다.

</details>

---

21. Cilium에서 SPIFFE ID 기반 인증을 사용하려면 어떤 컴포넌트가 필요합니까?
    - A) SPIRE
    - B) Istio
    - C) Linkerd
    - D) cert-manager

<details>
<summary>정답 보기</summary>

**정답: A) SPIRE**

**설명:**
Cilium은 SPIRE(SPIFFE Runtime Environment)와 통합하여 SPIFFE ID 기반 워크로드 인증을 지원합니다. SPIRE는 워크로드에 SVID(SPIFFE Verifiable Identity Document)를 발급합니다.

</details>

---

## EKS 배포

22. Amazon EKS에서 Cilium을 CNI로 사용할 때 비활성화해야 하는 것은?
    - A) CoreDNS
    - B) kube-proxy
    - C) AWS VPC CNI
    - D) B와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D) B와 C 모두**

**설명:**
Cilium을 EKS의 주 CNI로 사용할 때는 AWS VPC CNI를 제거하고 kube-proxy도 비활성화합니다. Cilium은 자체적으로 네트워킹과 kube-proxy 기능을 제공합니다.

</details>

---

23. EKS에서 Cilium Service Mesh를 설치할 때 권장되는 Helm 값은?
    - A) kubeProxyReplacement=strict
    - B) kubeProxyReplacement=disabled
    - C) kubeProxyReplacement=partial
    - D) kubeProxyReplacement=probe

<details>
<summary>정답 보기</summary>

**정답: A) kubeProxyReplacement=strict**

**설명:**
`kubeProxyReplacement=strict`는 Cilium이 kube-proxy를 완전히 대체하도록 합니다. 이 모드에서 kube-proxy가 없으면 Cilium이 서비스 로드 밸런싱을 전담합니다.

</details>

---

24. Cilium CLI로 클러스터 연결성을 테스트하는 명령어는?
    - A) cilium status
    - B) cilium connectivity test
    - C) cilium validate
    - D) cilium check

<details>
<summary>정답 보기</summary>

**정답: B) cilium connectivity test**

**설명:**
`cilium connectivity test` 명령어는 클러스터 내 네트워크 연결성을 종합적으로 테스트합니다. 파드 간 통신, 서비스 접근, 네트워크 정책 적용 등을 검증합니다.

</details>

---

## 고급 기능

25. Cilium에서 L7 정책을 적용하지 않고 L4만 사용하는 경우의 장점은?
    - A) 더 많은 기능 사용 가능
    - B) 더 낮은 지연 시간과 리소스 사용
    - C) 더 상세한 로깅
    - D) HTTP 헤더 기반 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) 더 낮은 지연 시간과 리소스 사용**

**설명:**
L4만 사용하면 트래픽이 Envoy 프록시를 거치지 않고 eBPF에서 직접 처리되므로 지연 시간이 줄고 리소스 사용이 감소합니다. L7 기능이 필요 없는 경우 L4만 사용하는 것이 효율적입니다.

</details>

---

26. Cilium의 Local Redirect Policy(LRP)의 용도는?
    - A) 외부로 나가는 트래픽 차단
    - B) 특정 트래픽을 로컬 파드로 리다이렉트
    - C) DNS 쿼리 캐싱
    - D) mTLS 인증서 갱신

<details>
<summary>정답 보기</summary>

**정답: B) 특정 트래픽을 로컬 파드로 리다이렉트**

**설명:**
Local Redirect Policy는 특정 목적지(예: kube-dns)로 향하는 트래픽을 로컬 노드의 파드로 리다이렉트합니다. 이를 통해 node-local DNS 캐시나 사이드카 프록시로 트래픽을 전달할 수 있습니다.

</details>

---

27. Cilium에서 Cluster Mesh의 주요 기능은?
    - A) 단일 클러스터 내 네트워크 정책
    - B) 멀티클러스터 서비스 검색 및 연결
    - C) 컨테이너 이미지 동기화
    - D) Git 저장소 미러링

<details>
<summary>정답 보기</summary>

**정답: B) 멀티클러스터 서비스 검색 및 연결**

**설명:**
Cilium Cluster Mesh는 여러 Kubernetes 클러스터를 연결하여 서비스 검색과 파드 간 직접 통신을 가능하게 합니다. 각 클러스터의 파드가 다른 클러스터의 서비스에 직접 접근할 수 있습니다.

</details>

---

28. Cilium의 Bandwidth Manager 기능은 무엇을 제어합니까?
    - A) CPU 사용량
    - B) 메모리 사용량
    - C) 네트워크 대역폭 제한
    - D) 디스크 I/O

<details>
<summary>정답 보기</summary>

**정답: C) 네트워크 대역폭 제한**

**설명:**
Bandwidth Manager는 파드의 네트워크 대역폭을 제한하는 기능입니다. kubernetes.io/egress-bandwidth 어노테이션을 사용하여 파드별 egress 대역폭을 설정할 수 있습니다.

</details>

---

29. Cilium에서 Host Firewall의 역할은?
    - A) 파드 간 통신만 제어
    - B) 노드(호스트) 레벨 네트워크 보안
    - C) 외부 방화벽 연동
    - D) DNS 필터링

<details>
<summary>정답 보기</summary>

**정답: B) 노드(호스트) 레벨 네트워크 보안**

**설명:**
Host Firewall은 노드 자체의 네트워크 트래픽을 제어합니다. 노드로 들어오는 SSH, kubelet API 등의 접근을 CiliumClusterwideNetworkPolicy로 제어할 수 있습니다.

</details>

---

30. Cilium Service Mesh를 선택하는 주요 이유가 아닌 것은?
    - A) 사이드카 없는 서비스 메시
    - B) eBPF 기반 고성능
    - C) Istio와 100% 호환
    - D) CNI와 서비스 메시 통합

<details>
<summary>정답 보기</summary>

**정답: C) Istio와 100% 호환**

**설명:**
Cilium Service Mesh는 Istio와 별개의 서비스 메시 솔루션입니다. Istio API와 직접 호환되지 않으며, 자체 CiliumEnvoyConfig와 Gateway API를 사용합니다. 장점은 사이드카 없는 아키텍처, eBPF 기반 성능, CNI 통합입니다.

</details>

---

## 정리

이 퀴즈를 통해 다음 내용을 학습했습니다:
- Cilium Service Mesh의 eBPF 기반 아키텍처
- Per-node proxy vs 사이드카 모델
- CiliumEnvoyConfig를 통한 L7 정책 구성
- Hubble을 사용한 네트워크 관측성
- Gateway API 지원
- mTLS 및 보안 기능
- EKS에서의 Cilium 배포
- Cluster Mesh와 고급 기능
