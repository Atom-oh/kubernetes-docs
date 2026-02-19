# Linkerd 퀴즈

이 퀴즈는 Linkerd 서비스 메시에 대한 이해도를 테스트합니다. 각 질문에 대해 가장 적절한 답을 선택하세요.

---

## 기본 개념

1. Linkerd의 아키텍처에서 Data Plane의 핵심 구성 요소는 무엇입니까?
   - A) Envoy 프록시
   - B) linkerd2-proxy (Rust 기반)
   - C) NGINX
   - D) HAProxy

<details>
<summary>정답 보기</summary>

**정답: B) linkerd2-proxy (Rust 기반)**

**설명:**
Linkerd는 Envoy 대신 자체 개발한 Rust 기반의 경량 프록시인 linkerd2-proxy를 사용합니다. 이 프록시는 메모리 사용량이 적고 빠른 시작 시간을 제공하여 서비스 메시의 오버헤드를 최소화합니다.

</details>

---

2. Linkerd Control Plane의 핵심 컴포넌트가 아닌 것은?
   - A) destination
   - B) identity
   - C) proxy-injector
   - D) pilot

<details>
<summary>정답 보기</summary>

**정답: D) pilot**

**설명:**
pilot은 Istio의 컴포넌트입니다. Linkerd Control Plane은 destination(서비스 검색 및 라우팅), identity(인증서 발급), proxy-injector(사이드카 주입)로 구성됩니다.

</details>

---

3. Linkerd에서 mTLS 인증서의 기본 유효 기간은 얼마입니까?
   - A) 1시간
   - B) 24시간
   - C) 7일
   - D) 30일

<details>
<summary>정답 보기</summary>

**정답: B) 24시간**

**설명:**
Linkerd의 프록시 인증서는 기본적으로 24시간 유효하며, identity 컴포넌트에 의해 자동으로 갱신됩니다. 짧은 유효 기간은 인증서 탈취 시 피해를 최소화합니다.

</details>

---

4. Linkerd 설치 시 `linkerd check --pre` 명령어의 목적은 무엇입니까?
   - A) 설치 후 상태 검증
   - B) 클러스터 사전 요구 사항 확인
   - C) 프록시 버전 확인
   - D) 네트워크 정책 테스트

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 사전 요구 사항 확인**

**설명:**
`linkerd check --pre` 명령어는 Linkerd 설치 전에 클러스터가 필요한 요구 사항을 충족하는지 확인합니다. Kubernetes 버전, RBAC 권한, 네임스페이스 상태 등을 점검합니다.

</details>

---

## 트래픽 관리

5. Linkerd에서 트래픽 분할(Traffic Split)을 구현할 때 사용하는 리소스는?
   - A) VirtualService
   - B) TrafficSplit
   - C) DestinationRule
   - D) HTTPRoute

<details>
<summary>정답 보기</summary>

**정답: B) TrafficSplit**

**설명:**
Linkerd는 SMI(Service Mesh Interface) 표준의 TrafficSplit 리소스를 사용하여 서비스 간 트래픽을 분할합니다. 이는 카나리 배포나 A/B 테스트에 활용됩니다.

</details>

---

6. 다음 TrafficSplit 설정에서 stable 버전이 받는 트래픽 비율은?
   ```yaml
   spec:
     backends:
     - service: web-stable
       weight: 900
     - service: web-canary
       weight: 100
   ```
   - A) 100%
   - B) 90%
   - C) 10%
   - D) 9%

<details>
<summary>정답 보기</summary>

**정답: B) 90%**

**설명:**
TrafficSplit의 weight는 상대적 가중치입니다. 전체 가중치(900 + 100 = 1000)에서 stable의 비율은 900/1000 = 90%입니다.

</details>

---

7. Linkerd에서 ServiceProfile의 주요 기능이 아닌 것은?
   - A) 라우트별 메트릭 수집
   - B) 재시도 정책 설정
   - C) 타임아웃 설정
   - D) Circuit Breaker 구성

<details>
<summary>정답 보기</summary>

**정답: D) Circuit Breaker 구성**

**설명:**
Linkerd의 ServiceProfile은 라우트별 메트릭, 재시도, 타임아웃을 지원합니다. Circuit Breaker는 현재 Linkerd에서 직접 지원하지 않으며, 재시도 예산(retry budget)으로 유사한 효과를 얻을 수 있습니다.

</details>

---

8. Linkerd에서 재시도(retry)를 설정할 때 "idempotent" 라우트의 의미는?
   - A) 중요한 라우트
   - B) 재시도해도 부작용이 없는 라우트
   - C) 인증이 필요한 라우트
   - D) 캐시 가능한 라우트

<details>
<summary>정답 보기</summary>

**정답: B) 재시도해도 부작용이 없는 라우트**

**설명:**
idempotent(멱등) 라우트는 여러 번 실행해도 동일한 결과를 반환하는 라우트입니다. GET 요청이 대표적인 예이며, 이런 라우트는 안전하게 재시도할 수 있습니다.

</details>

---

## 보안

9. Linkerd에서 mTLS 모드 중 "permissive"의 의미는?
   - A) mTLS만 허용
   - B) 평문만 허용
   - C) mTLS와 평문 모두 허용
   - D) 모든 트래픽 차단

<details>
<summary>정답 보기</summary>

**정답: C) mTLS와 평문 모두 허용**

**설명:**
permissive 모드에서는 메시 내부(mTLS)와 외부(평문) 트래픽을 모두 수락합니다. 이는 점진적 마이그레이션 시 유용하며, 완전한 mTLS 적용 전 전환 단계에서 사용됩니다.

</details>

---

10. Linkerd의 Identity 컴포넌트가 사용하는 인증서 발급 표준은?
    - A) SPIFFE
    - B) X.509
    - C) JWT
    - D) OAuth 2.0

<details>
<summary>정답 보기</summary>

**정답: A) SPIFFE**

**설명:**
Linkerd는 SPIFFE(Secure Production Identity Framework For Everyone) 표준을 사용하여 워크로드 ID를 발급합니다. SPIFFE ID는 `spiffe://trust-domain/ns/namespace/sa/service-account` 형식입니다.

</details>

---

11. Linkerd에서 Authorization Policy를 사용하여 특정 서비스로의 접근을 제한할 때, 기본 동작은?
    - A) 모든 트래픽 허용
    - B) 모든 트래픽 거부
    - C) 인증된 트래픽만 허용
    - D) 메시 내부 트래픽만 허용

<details>
<summary>정답 보기</summary>

**정답: A) 모든 트래픽 허용**

**설명:**
Linkerd의 기본 동작은 모든 트래픽을 허용합니다. AuthorizationPolicy를 적용하면 명시적으로 허용된 트래픽만 통과할 수 있습니다. 정책이 없으면 "fail-open" 방식으로 동작합니다.

</details>

---

## 관측성 (Viz)

12. Linkerd Viz 확장에서 제공하는 대시보드의 기본 포트는?
    - A) 8080
    - B) 8084
    - C) 9990
    - D) 50750

<details>
<summary>정답 보기</summary>

**정답: B) 8084**

**설명:**
Linkerd Viz 대시보드는 기본적으로 포트 8084에서 실행됩니다. `linkerd viz dashboard` 명령어로 브라우저에서 접속할 수 있습니다.

</details>

---

13. Linkerd에서 Golden Metrics에 포함되지 않는 것은?
    - A) Success Rate
    - B) Request Rate
    - C) Latency
    - D) Memory Usage

<details>
<summary>정답 보기</summary>

**정답: D) Memory Usage**

**설명:**
Linkerd의 Golden Metrics는 Success Rate(성공률), Request Rate(요청률), Latency(지연 시간) 세 가지입니다. 이 메트릭들은 서비스 상태를 한눈에 파악하는 데 핵심적입니다.

</details>

---

14. `linkerd viz stat` 명령어로 확인할 수 없는 정보는?
    - A) 성공률
    - B) RPS (초당 요청 수)
    - C) P99 지연 시간
    - D) CPU 사용률

<details>
<summary>정답 보기</summary>

**정답: D) CPU 사용률**

**설명:**
`linkerd viz stat` 명령어는 HTTP 트래픽 메트릭(성공률, RPS, 지연 시간)을 보여줍니다. CPU/메모리 같은 리소스 메트릭은 Prometheus/Grafana에서 별도로 수집해야 합니다.

</details>

---

15. Linkerd에서 실시간 트래픽을 관찰하려면 어떤 명령어를 사용합니까?
    - A) linkerd viz stat
    - B) linkerd viz tap
    - C) linkerd viz edges
    - D) linkerd viz routes

<details>
<summary>정답 보기</summary>

**정답: B) linkerd viz tap**

**설명:**
`linkerd viz tap` 명령어는 실시간으로 HTTP 요청/응답을 캡처하여 보여줍니다. 특정 배포나 파드의 트래픽을 디버깅할 때 유용합니다.

</details>

---

## 멀티클러스터

16. Linkerd 멀티클러스터에서 클러스터 간 통신에 사용되는 컴포넌트는?
    - A) Gateway
    - B) Proxy
    - C) Mirror
    - D) Bridge

<details>
<summary>정답 보기</summary>

**정답: A) Gateway**

**설명:**
Linkerd 멀티클러스터는 각 클러스터에 게이트웨이를 배포하여 클러스터 간 통신을 중계합니다. 게이트웨이는 원격 클러스터의 서비스로 트래픽을 전달합니다.

</details>

---

17. Linkerd 멀티클러스터에서 Service Mirror의 역할은?
    - A) 서비스 간 트래픽 암호화
    - B) 원격 클러스터 서비스를 로컬에 미러링
    - C) 로그 수집 및 전송
    - D) 인증서 동기화

<details>
<summary>정답 보기</summary>

**정답: B) 원격 클러스터 서비스를 로컬에 미러링**

**설명:**
Service Mirror는 원격 클러스터에서 내보낸(exported) 서비스를 로컬 클러스터에 미러 서비스로 생성합니다. 이를 통해 로컬 애플리케이션은 원격 서비스를 마치 로컬 서비스처럼 접근할 수 있습니다.

</details>

---

18. Linkerd 멀티클러스터에서 서비스를 다른 클러스터에 노출하려면 어떤 어노테이션을 사용합니까?
    - A) linkerd.io/exported=true
    - B) mirror.linkerd.io/exported=true
    - C) linkerd.io/inject=enabled
    - D) multicluster.linkerd.io/export=true

<details>
<summary>정답 보기</summary>

**정답: B) mirror.linkerd.io/exported=true**

**설명:**
`mirror.linkerd.io/exported=true` 어노테이션을 서비스에 추가하면 해당 서비스가 멀티클러스터 게이트웨이를 통해 다른 클러스터에 노출됩니다.

</details>

---

## EKS 배포

19. Amazon EKS에 Linkerd를 설치할 때 권장되는 방법은?
    - A) kubectl apply만 사용
    - B) Helm 차트 사용
    - C) EKS 애드온
    - D) AWS Marketplace

<details>
<summary>정답 보기</summary>

**정답: B) Helm 차트 사용**

**설명:**
EKS에서 Linkerd는 Helm 차트를 사용하여 설치하는 것이 권장됩니다. Helm을 통해 인증서 관리, 고가용성 구성, 버전 관리 등을 쉽게 설정할 수 있습니다.

</details>

---

20. Linkerd를 프로덕션 환경에서 고가용성(HA) 모드로 배포할 때 권장되는 Control Plane 레플리카 수는?
    - A) 1
    - B) 2
    - C) 3
    - D) 5

<details>
<summary>정답 보기</summary>

**정답: C) 3**

**설명:**
Linkerd HA 모드에서는 각 Control Plane 컴포넌트를 3개의 레플리카로 실행하여 고가용성을 보장합니다. Pod Disruption Budget과 Anti-affinity 규칙도 함께 적용됩니다.

</details>

---

## 고급 기능

21. Linkerd에서 TCP 트래픽(비HTTP)에 대해 자동으로 적용되는 기능은?
    - A) 라우팅
    - B) 재시도
    - C) mTLS 암호화
    - D) 로드 밸런싱만

<details>
<summary>정답 보기</summary>

**정답: C) mTLS 암호화**

**설명:**
Linkerd는 TCP 트래픽에도 mTLS를 자동으로 적용합니다. 단, 라우팅, 재시도, ServiceProfile 기반 기능은 HTTP 트래픽에만 적용됩니다. TCP의 경우 연결 수준에서 암호화와 기본 로드 밸런싱만 제공됩니다.

</details>

---

22. Linkerd의 프록시를 특정 네임스페이스에만 주입하려면 어떤 어노테이션을 사용합니까?
    - A) linkerd.io/inject=enabled
    - B) linkerd.io/inject=namespace
    - C) sidecar.linkerd.io/inject=true
    - D) injection.linkerd.io/enabled=true

<details>
<summary>정답 보기</summary>

**정답: A) linkerd.io/inject=enabled**

**설명:**
네임스페이스에 `linkerd.io/inject=enabled` 어노테이션을 추가하면 해당 네임스페이스의 모든 파드에 자동으로 프록시가 주입됩니다. 파드 단위로도 이 어노테이션을 사용할 수 있습니다.

</details>

---

23. Linkerd와 Argo Rollouts를 연동할 때 사용되는 Traffic Router 유형은?
    - A) nginx
    - B) istio
    - C) smi
    - D) linkerd

<details>
<summary>정답 보기</summary>

**정답: C) smi**

**설명:**
Argo Rollouts는 SMI(Service Mesh Interface) 표준을 통해 Linkerd와 연동됩니다. Rollout 리소스에서 `trafficRouting.smi` 설정을 사용하여 TrafficSplit을 자동으로 관리합니다.

</details>

---

24. Linkerd에서 외부 Prometheus 서버를 사용하려면 어떤 확장을 비활성화해야 합니까?
    - A) linkerd-viz의 prometheus 컴포넌트
    - B) linkerd-identity
    - C) linkerd-destination
    - D) linkerd-proxy-injector

<details>
<summary>정답 보기</summary>

**정답: A) linkerd-viz의 prometheus 컴포넌트**

**설명:**
외부 Prometheus를 사용할 때는 linkerd-viz 설치 시 내장 Prometheus를 비활성화합니다. `--set prometheus.enabled=false`와 함께 외부 Prometheus URL을 지정합니다.

</details>

---

25. Linkerd에서 Debug 컨테이너를 파드에 추가하려면 어떤 어노테이션을 사용합니까?
    - A) config.linkerd.io/debug=true
    - B) linkerd.io/debug=enabled
    - C) config.linkerd.io/enable-debug-sidecar=true
    - D) debug.linkerd.io/inject=true

<details>
<summary>정답 보기</summary>

**정답: C) config.linkerd.io/enable-debug-sidecar=true**

**설명:**
`config.linkerd.io/enable-debug-sidecar=true` 어노테이션을 파드에 추가하면 linkerd-debug 컨테이너가 주입됩니다. 이 컨테이너에는 tcpdump, tshark 등 네트워크 디버깅 도구가 포함되어 있습니다.

</details>

---

## 정리

이 퀴즈를 통해 다음 내용을 학습했습니다:
- Linkerd 아키텍처와 구성 요소
- TrafficSplit을 사용한 트래픽 분할
- mTLS 및 보안 기능
- Linkerd Viz와 관측성
- 멀티클러스터 구성
- EKS 배포 및 고급 기능
