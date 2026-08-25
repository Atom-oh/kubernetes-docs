# Basic 퀴즈

> **지원 버전**: Istio 1.28.0 **EKS 버전**: 1.34 (Kubernetes 1.28+) **마지막 업데이트**: 2026년 2월 23일

이 퀴즈는 Istio의 기본 개념과 아키텍처에 대한 이해도를 테스트합니다.

## 객관식 문제 (1-5번)

### 문제 1: 서비스 메시의 정의

서비스 메시(Service Mesh)에 대한 설명으로 **가장 적절하지 않은** 것은?

A. 마이크로서비스 간 통신을 처리하는 인프라 계층이다\
B. 애플리케이션 코드를 수정해야만 사용할 수 있다.\
C. 서비스 간 트래픽 제어와 관찰성을 제공한다.\
D. 네트워크 레벨에서 보안과 정책을 적용한다.

<details>

<summary>정답 및 해설</summary>

**정답: B**

서비스 메시의 핵심 장점 중 하나는 **애플리케이션 코드를 변경하지 않고도** 서비스 간 통신을 제어하고 관찰할 수 있다는 것입니다.

**해설:**

* A (O): 서비스 메시는 마이크로서비스 아키텍처에서 서비스 간 통신을 담당하는 전용 인프라 계층입니다
* B (X): 애플리케이션 코드 변경 없이 사이드카 프록시나 Ambient Mode로 투명하게 적용됩니다
* C (O): VirtualService, DestinationRule 등으로 트래픽을 제어하고, 메트릭/로그/트레이스를 자동 수집합니다
* D (O): mTLS, Authorization Policy 등으로 네트워크 레벨에서 보안 정책을 적용합니다

**참고 자료:**

* [Istio 핵심 개념](../../../service-mesh/istio/02-basic-concepts.md)
* [서비스 메시란?](https://github.com/Atom-oh/kubernetes-docs/blob/main/ko/service-mesh/02-istio.md#%EC%86%8C%EA%B0%9C)

</details>

***

### 문제 2: Istio 아키텍처 구성 요소

Istio의 Control Plane에서 **중앙 집중식 컴포넌트**로 서비스 검색, 구성 관리, 인증서 관리를 담당하는 것은?

A. Envoy\
B. Istiod\
C. Pilot\
D. Citadel

<details>

<summary>정답 및 해설</summary>

**정답: B**

**Istiod**는 Istio 1.5부터 도입된 단일 바이너리로, 이전의 Pilot, Citadel, Galley를 통합한 컴포넌트입니다.

**해설:**

* A (X): Envoy는 Data Plane의 프록시로, 각 파드의 사이드카로 실행됩니다
* B (O): Istiod는 Control Plane의 핵심으로 다음을 담당합니다:
  * 서비스 검색 (Service Discovery)
  * 구성 관리 (Configuration Management)
  * 인증서 관리 (Certificate Management)
* C (X): Pilot은 Istio 1.5 이전 버전의 컴포넌트로, 현재는 Istiod에 통합되었습니다
* D (X): Citadel도 Istio 1.5 이전 버전의 컴포넌트로, 현재는 Istiod에 통합되었습니다

**Istiod의 주요 역할:**

```yaml
# Istiod가 관리하는 구성
1. 서비스 검색: Kubernetes Service → Envoy Cluster
2. 구성 배포: VirtualService, DestinationRule → Envoy Config
3. 인증서 발급: Service Account → mTLS Certificate
```

**참고 자료:**

* [Istio 구성 요소](../../../service-mesh/istio/03-architecture.md)
* [아키텍처 개요](https://github.com/Atom-oh/kubernetes-docs/blob/main/ko/service-mesh/02-istio.md#%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-%EA%B0%9C%EC%9A%94)

</details>

***

### 문제 3: Envoy 프록시의 역할

Data Plane의 Envoy 프록시가 수행하는 작업이 **아닌** 것은?

A. 트래픽 라우팅 및 로드 밸런싱\
B. mTLS 암호화 및 인증\
C. Kubernetes CRD 검증 및 저장\
D. 메트릭, 로그, 트레이스 수집

<details>

<summary>정답 및 해설</summary>

**정답: C**

Kubernetes CRD 검증 및 저장은 Control Plane(Istiod)의 역할입니다.

**해설:**

* A (O): Envoy는 VirtualService 규칙에 따라 트래픽을 라우팅하고 로드 밸런싱합니다
* B (O): Envoy는 서비스 간 통신을 자동으로 mTLS로 암호화하고 인증서를 검증합니다
* C (X): CRD 검증 및 저장은 Kubernetes API Server와 Istiod의 역할입니다
* D (O): Envoy는 모든 요청에 대한 메트릭(Prometheus), 로그(Access Log), 트레이스(Jaeger)를 수집합니다

**참고 자료:**

* [Data Plane 구조](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### 문제 4: Istio 설치 프로파일

Amazon EKS 프로덕션 환경에서 Istio를 설치할 때 **권장되는 프로파일**은?

A. default\
B. demo\
C. minimal\
D. production

<details>

<summary>정답 및 해설</summary>

**정답: D**

프로덕션 환경에서는 **production** 프로파일을 사용해야 합니다.

**해설:**

**Istio 설치 프로파일 비교:**

| 프로파일           | 용도     | 특징                   |
| -------------- | ------ | -------------------- |
| **default**    | 개발/테스트 | 기본 구성, 중간 리소스        |
| **demo**       | 데모/학습  | 모든 기능 활성화, 높은 리소스 사용 |
| **minimal**    | 최소 구성  | Control Plane만 설치    |
| **production** | 프로덕션   | HA 구성, 높은 가용성        |

**Production 프로파일 특징:**

```bash
# Production 프로파일 설치
istioctl install --set profile=production -y

# 주요 특징:
# - Istiod replica: 3개 (HA)
# - PodDisruptionBudget 설정
# - 리소스 제한 적절히 설정
# - Ingress/Egress Gateway 포함
```

**프로덕션 체크리스트:**

* ✅ Control Plane HA (replica ≥ 3)
* ✅ mTLS STRICT 모드
* ✅ PodDisruptionBudget 설정
* ✅ 리소스 제한 및 HPA 구성
* ✅ 모니터링 스택 준비

**참고 자료:**

* [설치 가이드](../../../service-mesh/istio/01-installation.md)
* [모범 사례](../../../service-mesh/istio/best-practices.md#프로덕션-체크리스트)

</details>

***

### 문제 5: Istio CRD (Custom Resource Definition)

다음 중 Istio의 **트래픽 관리**를 위한 CRD가 **아닌** 것은?

A. VirtualService\
B. DestinationRule\
C. PeerAuthentication\
D. Gateway

<details>

<summary>정답 및 해설</summary>

**정답: C**

**PeerAuthentication**은 보안(Security) 관련 CRD입니다.

**해설:**

**Istio CRD 분류:**

**1. 트래픽 관리 (Traffic Management):**

* VirtualService: 라우팅 규칙 정의
* DestinationRule: 로드 밸런싱, 서브셋 정의
* Gateway: 외부 트래픽 진입점
* ServiceEntry: 외부 서비스 정의
* Sidecar: Envoy 구성 범위 제한

**2. 보안 (Security):**

* PeerAuthentication: 서비스 간 인증 (mTLS)
* RequestAuthentication: 최종 사용자 인증 (JWT)
* AuthorizationPolicy: 액세스 제어

**3. 관찰성 (Observability):**

* Telemetry: 메트릭, 로그, 트레이스 구성

**예제:**

```yaml
# 트래픽 관리
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1

---
# 보안
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**참고 자료:**

* [트래픽 관리](../../../service-mesh/istio/traffic-management/README.md)
* [보안](../../../service-mesh/istio/security/README.md)

</details>

***

## 주관식 문제 (6-10번)

### 문제 6: Sidecar 주입 메커니즘

Istio에서 Pod에 Envoy Sidecar를 자동으로 주입하는 방법 2가지를 설명하고, 각각의 장단점을 비교하세요.

<details>

<summary>예시 답안</summary>

**답변:**

Istio는 두 가지 방법으로 Sidecar를 자동 주입합니다:

**1. Namespace 레벨 자동 주입:**

```bash
# Namespace에 레이블 추가
kubectl label namespace default istio-injection=enabled

# 이후 배포되는 모든 Pod에 자동 주입
kubectl apply -f deployment.yaml
```

**장점:**

* Namespace 전체에 일괄 적용 가능
* 관리가 간편함
* 실수로 누락될 가능성 낮음

**단점:**

* Namespace 내 모든 Pod에 적용됨 (선택적 제외 필요)
* 기존 Pod는 재시작 필요

**2. Pod 레벨 선택적 주입:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "true"  # 또는 "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**장점:**

* 특정 Pod만 선택적으로 주입 가능
* 세밀한 제어 가능
* Namespace 레이블 설정 불필요

**단점:**

* 각 Deployment마다 설정 필요
* 관리 포인트 증가
* 실수로 누락될 가능성 있음

**비교표:**

| 항목     | Namespace 레벨  | Pod 레벨 |
| ------ | ------------- | ------ |
| 적용 범위  | Namespace 전체  | 개별 Pod |
| 관리 복잡도 | 낮음            | 높음     |
| 선택성    | 낮음 (제외 설정 필요) | 높음     |
| 권장 사용  | 프로덕션 환경       | 혼합 환경  |

**프로덕션 권장 사항:**

* 기본적으로 Namespace 레벨 사용
* 제외가 필요한 Pod만 `sidecar.istio.io/inject: "false"` 설정

**참고 자료:**

* [Sidecar Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### 문제 7: Istio 리소스 사용량 최적화

1000개의 Pod가 있는 대규모 Kubernetes 클러스터에서 Istio를 사용할 때, Sidecar Mode와 Ambient Mode의 **예상 리소스 사용량**을 계산하고 비교하세요. (ztunnel이 10개 노드에 배포되고, waypoint가 1개라고 가정)

<details>
<summary>정답 및 해설</summary>

**답변:**

**가정:**

* Pod 수: 1000개
* Node 수: 10개
* Sidecar 메모리: 50MB/Pod
* ztunnel 메모리: 50MB/Node
* waypoint 메모리: 200MB

**1. Sidecar Mode 리소스 사용량:**

```
메모리 사용량 = Pod 수 × Sidecar 메모리
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU 사용량 = Pod 수 × Sidecar CPU
           = 1000 × 0.1 vCPU
           = 100 vCPU
```

**2. Ambient Mode 리소스 사용량:**

```
메모리 사용량 = (Node 수 × ztunnel 메모리) + waypoint 메모리
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU 사용량 = (Node 수 × ztunnel CPU) + waypoint CPU
           = (10 × 0.1 vCPU) + 0.5 vCPU
           = 1.5 vCPU
```

**3. 비교 및 절감량:**

| 항목      | Sidecar Mode | Ambient Mode | 절감량       | 절감률       |
| ------- | ------------ | ------------ | --------- | --------- |
| **메모리** | 50GB         | 0.7GB        | 49.3GB    | **98.6%** |
| **CPU** | 100 vCPU     | 1.5 vCPU     | 98.5 vCPU | **98.5%** |

**비용 계산 (AWS EKS 기준):**

```
# r5.xlarge: 4 vCPU, 32GB RAM, $0.252/시간

Sidecar Mode:
- CPU: 100 vCPU → 25개 인스턴스 필요
- 메모리: 50GB → 2개 인스턴스 필요
- 필요 인스턴스: max(25, 2) = 25개
- 월간 비용: 25 × $0.252 × 24 × 30 = $4,536

Ambient Mode:
- CPU: 1.5 vCPU → 1개 인스턴스면 충분
- 메모리: 0.7GB → 1개 인스턴스면 충분
- 필요 인스턴스: 1개
- 월간 비용: 1 × $0.252 × 24 × 30 = $181

월간 비용 절감: $4,536 - $181 = $4,355 (96%)
```

**결론:**

* Ambient Mode는 대규모 클러스터에서 **96% 이상의 비용 절감** 효과
* 1000개 Pod 규모에서 월간 약 **$4,300 절감**
* 리소스 사용량이 **98% 이상 감소**

**주의사항:**

* L7 기능이 필요한 경우 waypoint 추가 필요
* Ambient Mode는 Istio 1.28+ 베타 기능

**참고 자료:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#리소스-사용량-비교)
* [비용 최적화](../../../service-mesh/istio/best-practices.md#비용-최적화)

</details>

***

### 문제 8: mTLS 작동 원리

Istio에서 두 서비스(service-a와 service-b) 간 통신 시 mTLS가 작동하는 과정을 단계별로 설명하세요. Istiod, Envoy, Certificate의 역할을 포함해야 합니다.

<details>

<summary>예시 답안</summary>

**답변:**

**mTLS (Mutual TLS) 작동 과정:**

**1단계: 인증서 발급 (부트스트랩)**

* Pod 시작 시 Envoy는 자신의 Service Account를 사용하여 Istiod에 인증서 요청(CSR)
* Istiod는 Service Account를 검증하고 X.509 인증서 발급
* 인증서에는 Service Account ID가 포함됨 (예: `cluster.local/ns/default/sa/service-a`)
* 인증서 유효기간: 기본 24시간 (자동 갱신)

**2단계: 서비스 간 통신 (mTLS 핸드셰이크)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**상세 과정:**

```yaml
# Service A가 Service B 호출
1. Service A → Envoy A (localhost:outbound)
   - 애플리케이션은 평문 HTTP 요청

2. Envoy A: Outbound 처리
   - Istiod로부터 받은 구성 확인
   - PeerAuthentication 정책 확인 (STRICT mTLS)
   - Service B의 Envoy B로 연결 시작

3. TLS 핸드셰이크 (Envoy A ↔ Envoy B)
   a. Envoy A → Envoy B: ClientHello
      - 자신의 인증서 제시
      - 지원하는 암호화 알고리즘 제시

   b. Envoy B → Envoy A: ServerHello
      - 자신의 인증서 제시
      - 선택된 암호화 알고리즘

   c. 상호 인증서 검증
      - Envoy A: Service B의 인증서 검증
      - Envoy B: Service A의 인증서 검증
      - Istiod의 Root CA로 서명 검증

   d. 암호화 세션 키 생성
      - TLS 1.3 암호화 채널 생성

4. Envoy B → Service B (localhost:inbound)
   - 복호화된 평문 HTTP 요청 전달

5. Service B → Envoy B → [mTLS] → Envoy A → Service A
   - 응답도 같은 암호화 채널 사용
```

**각 컴포넌트의 역할:**

**Istiod:**

* Root CA 역할 (인증서 서명)
* Service Account 기반 인증서 발급
* 인증서 자동 갱신 (24시간마다)
* PeerAuthentication 정책 배포

**Envoy Sidecar:**

* 인증서 요청 및 갱신
* TLS 핸드셰이크 수행
* 트래픽 암호화/복호화
* 인증서 검증

**Certificate:**

* X.509 인증서 형식
* Subject Alternative Name (SAN): Service Account URI
* 유효기간: 24시간 (기본값)
* 자동 갱신

**설정 예시:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # 모든 통신을 mTLS로 강제
```

**인증서 확인:**

```bash
# Pod의 인증서 확인
istioctl proxy-config secret <pod-name> -o json

# 출력 예시:
{
  "name": "default",
  "tlsCertificate": {
    "certificateChain": "...",
    "privateKey": "...",
    "subjectAltNames": [
      "spiffe://cluster.local/ns/default/sa/service-a"
    ]
  }
}
```

**보안 이점:**

1. **기밀성**: 모든 통신 암호화
2. **무결성**: 데이터 변조 방지
3. **인증**: 양방향 신원 확인
4. **자동화**: 코드 변경 없이 적용

**참고 자료:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [인증서 관리](../../../service-mesh/istio/03-architecture.md#인증서-관리)

</details>

***

### 문제 9: Istio 디버깅

새로 배포한 서비스가 Istio 메시에서 통신이 되지 않을 때, 문제를 진단하는 단계별 디버깅 방법을 작성하세요. (최소 5단계 이상)

<details>

<summary>예시 답안</summary>

**답변:**

**Istio 서비스 통신 디버깅 체크리스트:**

**1단계: Pod 및 Sidecar 상태 확인**

```bash
# Pod가 정상 실행 중인지 확인
kubectl get pods -n <namespace>

# Sidecar가 주입되었는지 확인 (컨테이너가 2개여야 함)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# 예상 출력: myapp istio-proxy

# Sidecar 주입 여부 상세 확인
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Pod 로그 확인
kubectl logs <pod-name> -n <namespace> -c myapp        # 애플리케이션 로그
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy 로그
```

**문제 진단:**

* 컨테이너가 1개만 있으면 → Sidecar 미주입
* Pod가 CrashLoopBackOff → 애플리케이션 또는 Sidecar 초기화 실패

**해결:**

```bash
# Namespace에 injection 레이블 확인
kubectl get namespace <namespace> --show-labels

# 레이블이 없으면 추가
kubectl label namespace <namespace> istio-injection=enabled

# Pod 재시작
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**2단계: Service 및 Endpoint 확인**

```bash
# Service 존재 확인
kubectl get svc <service-name> -n <namespace>

# Service Endpoint 확인 (Pod IP가 등록되어 있는지)
kubectl get endpoints <service-name> -n <namespace>

# Service 상세 정보
kubectl describe svc <service-name> -n <namespace>
```

**문제 진단:**

* Endpoint가 비어있으면 → Service Selector와 Pod Label 불일치
* Service 포트와 Pod 포트 불일치

**해결:**

```bash
# Pod 레이블 확인
kubectl get pods <pod-name> -n <namespace> --show-labels

# Service Selector 확인
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**3단계: Istio 구성 확인**

```bash
# VirtualService 확인
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# DestinationRule 확인
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Gateway 확인 (외부 접근 시)
kubectl get gateway -n <namespace>

# Istio 구성 검증
istioctl analyze -n <namespace>
```

**문제 진단:**

* `istioctl analyze` 오류 메시지 확인
* VirtualService의 host가 Service 이름과 일치하는지
* DestinationRule의 subset 레이블이 Pod 레이블과 일치하는지

**해결:**

```bash
# 구성 오류 자동 감지
istioctl analyze -n <namespace>

# 출력 예시:
# Error [IST0101] (VirtualService reviews.default)
# Referenced host not found: reviews
```

***

**4단계: mTLS 및 보안 정책 확인**

```bash
# PeerAuthentication 정책 확인
kubectl get peerauthentication -A

# 특정 Pod의 mTLS 모드 확인
istioctl authn tls-check <pod-name>.<namespace> <service-name>.<namespace>.svc.cluster.local

# AuthorizationPolicy 확인
kubectl get authorizationpolicy -n <namespace>
```

**문제 진단:**

* mTLS 모드 불일치 (STRICT vs PERMISSIVE)
* AuthorizationPolicy가 트래픽 차단

**해결:**

```bash
# PERMISSIVE 모드로 임시 변경 (디버깅용)
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: <namespace>
spec:
  mtls:
    mode: PERMISSIVE
EOF

# AuthorizationPolicy 임시 삭제
kubectl delete authorizationpolicy <policy-name> -n <namespace>
```

***

**5단계: Envoy 구성 확인**

```bash
# Envoy 클러스터 구성 확인 (서비스 검색)
istioctl proxy-config clusters <pod-name> -n <namespace>

# Envoy 리스너 구성 확인 (인바운드/아웃바운드)
istioctl proxy-config listeners <pod-name> -n <namespace>

# Envoy 라우트 구성 확인
istioctl proxy-config routes <pod-name> -n <namespace>

# Envoy 엔드포인트 확인
istioctl proxy-config endpoints <pod-name> -n <namespace>
```

**문제 진단:**

* 클러스터에 타겟 서비스가 없으면 → Istiod가 서비스를 인식 못함
* 리스너가 없으면 → 포트 구성 오류
* 엔드포인트가 UNHEALTHY → Pod가 준비되지 않음

***

**6단계: 네트워크 연결 테스트**

```bash
# Pod 내에서 직접 테스트
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Envoy를 거치지 않고 직접 테스트 (Pod IP로)
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# DNS 해석 확인
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Envoy Admin API로 통계 확인
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- curl localhost:15000/stats | grep <service-name>
```

***

**7단계: Istiod 로그 확인**

```bash
# Istiod 로그 확인 (구성 푸시 오류)
kubectl logs -n istio-system -l app=istiod --tail=100

# xDS 구성 푸시 상태 확인
istioctl proxy-status

# 특정 Pod의 동기화 상태
istioctl proxy-status <pod-name>.<namespace>
```

***

**8단계: 메트릭 및 트레이싱 확인**

```bash
# Prometheus에서 메트릭 확인
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Jaeger에서 트레이스 확인
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Kiali에서 토폴로지 확인
istioctl dashboard kiali
```

***

**문제 해결 순서도:**

```
1. Pod/Sidecar 정상?
   ├─ NO → Sidecar 주입 확인
   └─ YES → 2단계

2. Service/Endpoint 정상?
   ├─ NO → Selector 확인
   └─ YES → 3단계

3. Istio 구성 정상?
   ├─ NO → istioctl analyze 실행
   └─ YES → 4단계

4. mTLS/정책 정상?
   ├─ NO → PERMISSIVE 모드 테스트
   └─ YES → 5단계

5. Envoy 구성 정상?
   ├─ NO → Istiod 재시작
   └─ YES → 6단계

6. 네트워크 연결 정상?
   ├─ NO → NetworkPolicy 확인
   └─ YES → 로그/메트릭 분석
```

**참고 자료:**

* [Istio 디버깅 가이드](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### 문제 10: Istio 업그레이드 전략

프로덕션 환경에서 Istio를 1.27.0에서 1.28.0으로 업그레이드하는 **Canary Upgrade** 전략을 설명하세요. 단계별 명령어와 검증 방법을 포함해야 합니다.

<details>

<summary>예시 답안</summary>

**답변:**

**Istio Canary Upgrade 전략:**

Canary Upgrade는 새 버전과 이전 버전의 Control Plane을 동시에 실행하고, 점진적으로 워크로드를 이전하는 안전한 업그레이드 방식입니다.

***

**사전 준비:**

```bash
# 1. 현재 버전 확인
istioctl version

# 2. 백업 생성
kubectl get istiooperator -A -o yaml > istio-1.27-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 3. 새 버전 다운로드
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 4. 호환성 확인
istioctl x precheck
```

***

**1단계: 새 Control Plane 설치 (revision 사용)**

```bash
# Revision을 사용하여 새 버전 Control Plane 설치
istioctl install --set revision=1-28-0 --set profile=production -y

# 설치 확인
kubectl get pods -n istio-system -l app=istiod
# 출력 예시:
# istiod-1-27-0-xxxx  (기존 버전)
# istiod-1-28-0-xxxx  (새 버전)

# Revision 확인
kubectl get mutatingwebhookconfigurations | grep istio
# 출력:
# istio-sidecar-injector-1-27-0
# istio-sidecar-injector-1-28-0
```

**중요:** 이 시점에서 **두 개의 Control Plane**이 동시에 실행됩니다.

***

**2단계: 테스트 Namespace로 Canary 검증**

```bash
# 테스트 네임스페이스 생성
kubectl create namespace istio-upgrade-test

# 새 버전으로 레이블 지정
kubectl label namespace istio-upgrade-test istio.io/rev=1-28-0

# 테스트 애플리케이션 배포
kubectl apply -n istio-upgrade-test -f samples/sleep/sleep.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml

# Sidecar 버전 확인 (1.28.0이어야 함)
kubectl get pods -n istio-upgrade-test -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'

# 통신 테스트
kubectl exec -n istio-upgrade-test deploy/sleep -- curl http://httpbin:8000/headers

# Envoy 구성 확인
istioctl proxy-config clusters deploy/sleep.istio-upgrade-test
```

**검증 체크리스트:**

* ✅ Sidecar가 1.28.0 버전으로 주입되었는가?
* ✅ 서비스 간 통신이 정상인가?
* ✅ mTLS가 정상 작동하는가?
* ✅ 메트릭이 수집되는가?

***

**3단계: 스테이징 Namespace 이전**

```bash
# 스테이징 네임스페이스를 새 버전으로 전환
kubectl label namespace staging istio.io/rev=1-28-0 --overwrite

# 기존 레이블 제거 (있는 경우)
kubectl label namespace staging istio-injection-

# Pod 재시작 (새 버전 Sidecar 주입)
kubectl rollout restart deployment -n staging

# 재시작 상태 모니터링
kubectl rollout status deployment -n staging

# 버전 확인
kubectl get pods -n staging -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

**검증:**

```bash
# 메트릭 확인
kubectl exec -n staging <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_build

# 통신 테스트
kubectl exec -n staging <pod-name> -- curl http://<service-name>

# Kiali로 시각화 확인
istioctl dashboard kiali
```

**24-48시간 모니터링:**

* Prometheus 메트릭 확인
* 에러율, 지연시간 비교
* Istiod 리소스 사용량 확인

***

**4단계: 프로덕션 Namespace 단계적 이전**

```bash
# 프로덕션 Namespace 목록
PROD_NAMESPACES="prod-api prod-web prod-worker"

# 하나씩 단계적으로 이전
for ns in $PROD_NAMESPACES; do
  echo "Upgrading namespace: $ns"

  # 레이블 업데이트
  kubectl label namespace $ns istio.io/rev=1-28-0 --overwrite

  # Pod 재시작
  kubectl rollout restart deployment -n $ns

  # 완료 대기
  kubectl rollout status deployment -n $ns

  # 검증
  echo "Verifying namespace: $ns"
  kubectl exec -n $ns <pod-name> -- curl http://<service-name>

  # 다음 Namespace 이전 전 대기 (관찰)
  echo "Waiting 1 hour before next namespace..."
  sleep 3600
done
```

**단계별 검증:**

```bash
# 각 Namespace 이전 후 확인
# 1. Golden Signals
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Prometheus에서 쿼리:
# - istio_requests_total
# - istio_request_duration_milliseconds
# - istio_request_bytes

# 2. Control Plane 상태
istioctl proxy-status | grep $ns

# 3. 에러 로그
kubectl logs -n istio-system -l app=istiod,istio.io/rev=1-28-0 --tail=100
```

***

**5단계: 이전 버전 제거**

```bash
# 모든 Namespace가 새 버전으로 이전되었는지 확인
kubectl get namespace -L istio.io/rev

# 이전 버전을 사용하는 Pod가 없는지 확인
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}' | grep 1.27

# 이전 버전 Control Plane 제거
istioctl uninstall --revision=1-27-0 -y

# 제거 확인
kubectl get pods -n istio-system -l app=istiod

# 정리
kubectl delete mutatingwebhookconfigurations istio-sidecar-injector-1-27-0
kubectl delete validatingwebhookconfigurations istio-validator-1-27-0-istio-system
```

***

**6단계: Gateway 업그레이드 (선택사항)**

```bash
# Gateway도 별도로 업그레이드
kubectl patch deployment istio-ingressgateway -n istio-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"istio.io/rev":"1-28-0"}}}}}'

kubectl rollout restart deployment istio-ingressgateway -n istio-system
kubectl rollout status deployment istio-ingressgateway -n istio-system
```

***

**롤백 계획:**

```bash
# 문제 발생 시 즉시 롤백
# 1. 이전 버전으로 Namespace 레이블 변경
kubectl label namespace <namespace> istio.io/rev=1-27-0 --overwrite

# 2. Pod 재시작
kubectl rollout restart deployment -n <namespace>

# 3. 새 버전 Control Plane 제거
istioctl uninstall --revision=1-28-0 -y
```

***

**모범 사례:**

1. **단계적 접근:**
   * Test → Staging → Prod (단계별로 진행)
   * Namespace별로 하나씩 이전
   * 각 단계마다 충분한 관찰 시간 확보
2. **모니터링:**
   * Golden Signals 모니터링 (Latency, Traffic, Errors, Saturation)
   * Istiod 리소스 사용량 확인
   * 각 단계마다 24-48시간 관찰
3. **자동화:**
   * CI/CD 파이프라인에 통합
   * Smoke Test 자동화
   * 롤백 스크립트 준비
4. **커뮤니케이션:**
   * 팀에 업그레이드 일정 공유
   * 릴리스 노트 검토
   * 변경 사항 문서화

**참고 자료:**

* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [업그레이드 전략](../../../service-mesh/istio/best-practices.md#업그레이드-전략)

</details>

***

## 점수 계산

* 객관식 1-5번: 각 10점 (총 50점)
* 주관식 6-10번: 각 10점 (총 50점)
* **총점: 100점**

**평가 기준:**

* 90-100점: 우수 (Istio 기본 개념 완벽 이해)
* 80-89점: 양호 (기본 운영 가능)
* 70-79점: 보통 (추가 학습 권장)
* 60-69점: 미흡 (기본 개념 복습 필요)
* 0-59점: 재학습 필요

## 학습 자료

* [Istio 설치 가이드](../../../service-mesh/istio/01-installation.md)
* [핵심 개념](../../../service-mesh/istio/02-basic-concepts.md)
* [구성 요소](../../../service-mesh/istio/03-architecture.md)
* [Istio 공식 문서](https://istio.io/latest/docs/)
