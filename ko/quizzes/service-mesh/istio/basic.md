# Basic 퀴즈

> **검토 버전**: Istio 1.31.0 **EKS 버전**: 1.34–1.36 **마지막 업데이트**: 2026년 9월 11일

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
* C (O): VirtualService, DestinationRule 등으로 트래픽을 제어하고, 메트릭을 노출합니다. 로그·추적에는 설정과 애플리케이션의 추적 컨텍스트 전파가 필요합니다
* D (O): mTLS, Authorization Policy 등으로 네트워크 레벨에서 보안 정책을 적용합니다

**참고 자료:**

* [Istio 핵심 개념](../../../service-mesh/istio/02-basic-concepts.md)
* [서비스 메시란?](../../../service-mesh/istio/README.md)

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
* [아키텍처 개요](../../../service-mesh/istio/README.md)

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

Kubernetes API Server가 리소스를 저장하고 스키마를 검증하며 istiod는 admission webhook으로 Istio 구성을 검증합니다. Envoy가 Kubernetes CRD를 저장하지는 않습니다.

**해설:**

* A (O): Envoy는 VirtualService 규칙에 따라 트래픽을 라우팅하고 로드 밸런싱합니다
* B (O): Envoy는 서비스 간 통신을 자동으로 mTLS로 암호화하고 인증서를 검증합니다
* C (X): CRD 검증 및 저장은 Kubernetes API Server와 Istiod의 역할입니다
* D (O): Envoy는 메트릭을 노출하고 설정한 로깅 및 샘플링에 따라 액세스 로그와 추적 span을 생성합니다

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

**정답: A**

이 가이드의 Sidecar 설치는 `default`를 프로덕션 시작 프로필로 사용합니다. 기본 제공 `production` 프로필은 없습니다. Replica, 리소스 요청, 배치, PDB, 보안 정책은 명시적으로 구성해야 하며 `default`만 선택해도 고가용성이 보장되지는 않습니다.

| 프로필 | 용도 |
| --- | --- |
| default | 프로덕션 시작 설정; 워크로드에 맞게 조정 |
| demo | 데모용; 상세 텔레메트리로 성능 테스트에는 부적합 |
| minimal | Control Plane만 설치 |
| production | 기본 제공 프로필이 아님 |

```bash
istioctl install --set profile=default
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
apiVersion: networking.istio.io/v1
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
apiVersion: security.istio.io/v1
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
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
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

아래 값은 산술 연습용 가정이며 측정한 Istio 요구량이나 용량 권장값이 아닙니다. MB/GB는 10진 단위로 계산합니다. CPU도 사이드카당 0.1 vCPU, ztunnel당 0.1 vCPU, waypoint 0.5 vCPU로 가정합니다.

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

**해석:**

가정한 값의 프록시 합계만 비교하면 메모리 98.6%, CPU 98.5% 감소입니다. 이것이 AWS 비용 96% 절감이나 10노드·1,000파드 클러스터의 인스턴스 1개 운영을 뜻하지는 않습니다. 애플리케이션 리소스, 파드/IP 제한, HA, replica, 처리량, waypoint 용량이 빠져 있습니다. 용량과 비용은 실제 토폴로지를 벤치마크해 산정하세요. Ambient 핵심 기능은 Istio 1.24부터 GA입니다.

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

* 파드 시작 시 Istio 에이전트가 개인 키/CSR을 만들고 워크로드 자격 증명으로 istiod에 인증합니다. Envoy는 로컬 에이전트의 SDS로 인증서/키를 받습니다
* Istiod는 Service Account를 검증하고 X.509 인증서 발급
* 인증서에는 Service Account ID가 포함됨 (예: `cluster.local/ns/default/sa/service-a`)
* 인증서 유효기간: 기본 24시간 (자동 갱신)

**2단계: 서비스 간 통신 (mTLS 핸드셰이크)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**상세 과정:**

```text
1. 출발 앱의 HTTP 요청은 설정된 리다이렉션으로 Envoy A에 전달됩니다.
2. 자동 mTLS/DestinationRule이 아웃바운드 TLS를 결정하고,
   목적지 PeerAuthentication이 Envoy B의 인바운드 mTLS 요구를 결정합니다.
3. ClientHello/ServerHello로 TLS 매개변수와 키 교환을 협상합니다.
   인증서는 Hello가 아닌 Certificate 메시지에 포함됩니다.
   서버가 클라이언트 인증서를 요청하고 양쪽은 구성된 신뢰 체인에 따라
   상대 인증서와 개인 키 소유 증명을 검증합니다.
4. Envoy B가 인가 정책을 적용하고 복호화한 요청을 Service B로 전달합니다.
5. 응답은 수립한 TLS 연결로 반환됩니다.
```

**각 컴포넌트의 역할:**

**Istiod:**

* CA 역할 (외부 루트 아래의 중간 CA일 수 있음)
* Service Account 기반 인증서 발급
* 만료 전 갱신 요청에 서명; 인증서 수명은 설정 가능
* PeerAuthentication 정책 배포

**Envoy Sidecar:**

* Istio 에이전트의 SDS에서 인증서 수신
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
apiVersion: security.istio.io/v1
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
# Inspect certificate validity/status; private keys are not shown as plaintext
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config secret <pod-name> -n <namespace> -o json
```

**보안 이점:**

1. **기밀성**: 모든 통신 암호화
2. **무결성**: 데이터 변조 방지
3. **인증**: 양방향 신원 확인
4. **자동화**: 코드 변경 없이 적용

**참고 자료:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [인증서 관리](../../../service-mesh/istio/03-architecture.md#3-certificate-management-citadel-기능)

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
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}{" "}{.spec.initContainers[*].name}'
# 예상 출력: myapp istio-proxy

# Sidecar 주입 여부 상세 확인
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Pod 로그 확인
kubectl logs <pod-name> -n <namespace> -c myapp        # 애플리케이션 로그
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy 로그
```

**문제 진단:**

* containers와 native sidecar initContainers에서 istio-proxy 확인; Ambient 워크로드는 주입된 사이드카가 없음
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
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service-name>

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
kubectl get gateways.networking.istio.io -n <namespace>

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
# Referenced gateway not found: missing-gateway
```

***

**4단계: mTLS 및 보안 정책 확인**

```bash
# PeerAuthentication 정책 확인
kubectl get peerauthentication -A

# 특정 Pod의 mTLS 모드 확인
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
istioctl x authz check <pod-name> -n <namespace>

# AuthorizationPolicy 확인
kubectl get authorizationpolicy -n <namespace>
```

**문제 진단:**

* STRICT 목적지에 평문 클라이언트 접근, 만료 인증서, 신뢰 체인 불일치
* AuthorizationPolicy가 트래픽 차단

**해결:**

유효 정책, 워크로드 ID, 인증서와 Envoy 거부 로그를 확인하세요. STRICT와 PERMISSIVE 서버 모두 메시 mTLS 클라이언트를 받을 수 있습니다. 정책 변경은 격리된 테스트 네임스페이스에서 재현하며 운영 인가 삭제나 mTLS 완화를 기본 디버깅 단계로 사용하지 않습니다.



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

# Pod IP 라우팅 비교; 이 요청도 사이드카 가로채기를 우회하지 않음
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# DNS 해석 확인
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Envoy Admin API로 통계 확인
istioctl dashboard envoy <pod-name> -n <namespace>
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

텔레메트리 애드온은 별도 설치가 필요합니다. 각 port-forward는 별도 터미널에서 실행하며 실제 수집기의 서비스/네임스페이스를 사용하세요.

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
   ├─ NO → ID·인증서·거부 로그 확인
   └─ YES → 5단계

5. Envoy 구성 정상?
   ├─ NO → xDS 상태와 istiod 로그 확인
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

호환되는 EKS 클러스터에서 Istio 1.30.4를 1.31.0으로 Canary Upgrade하는 방법을 설명하세요. 워크로드 이전, 게이트웨이 처리, 검증, 롤백 조건을 포함하세요.

<details>
<summary>예시 답안</summary>

모든 워크로드와 게이트웨이 이전 및 롤백 기간 종료 전까지 기존 Control Plane을 유지합니다. 아래는 istioctl 관리 Sidecar 예제이며 Helm과 Ambient 설치는 별도 업그레이드 절차를 사용합니다. Revision 이름은 실제 설치와 일치하도록 바꾸세요.

**1. 사전 준비 및 백업**

Istio/EKS 지원 매트릭스와 업그레이드 노트를 확인합니다. 모범 사례 장에 따라 기존 설치 파일, 해당하는 차트 버전, 메시 리소스, CA/TLS Secret을 보존하세요. 대상 istioctl을 다운로드하고 사전 검증합니다:

```bash
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"
istioctl version
istioctl x precheck
```

**2. Canary Control Plane 설치**

기존 설정에서 `canary-install.yaml`을 준비해 메시 ID·신뢰·리소스 설정을 보존하세요. Revision은 `1-31-0`, Control Plane만 설치하는 프로필은 `minimal`로 설정하고 게이트웨이 구성 요소는 활성화하지 않습니다. 렌더링 결과를 검토한 후 설치합니다:

```bash
istioctl manifest generate -f canary-install.yaml > canary-rendered.yaml
istioctl install -f canary-install.yaml
kubectl rollout status deployment/istiod-1-31-0 -n istio-system
```

`production` 프로필은 없습니다. Revision 레이블은 바이너리 버전을 선택하지 않으며 대상 istioctl과 설정이 버전을 결정합니다.

**3. 테스트 네임스페이스 검증**

```bash
kubectl create namespace istio-upgrade-test
kubectl label namespace istio-upgrade-test istio.io/rev=1-31-0
kubectl apply -n istio-upgrade-test -f samples/curl/curl.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n istio-upgrade-test
kubectl rollout status deployment/httpbin -n istio-upgrade-test
kubectl exec -n istio-upgrade-test deploy/curl -c curl -- curl -fsS http://httpbin:8000/headers
istioctl proxy-status
istioctl analyze -n istio-upgrade-test
```

실제 프록시 이미지 버전, 동기화 상태, mTLS/인가 동작, 오류율, 지연 시간을 검증한 뒤 진행합니다.

**4. 스테이징 후 프로덕션 네임스페이스를 하나씩 이전**

Revision보다 우선하는 `istio-injection` 레이블을 제거합니다. 컨트롤러를 재시작해 새 프록시가 있는 파드를 만들고 해당하는 StatefulSet·DaemonSet·향후 Job도 확인하세요.

```bash
kubectl label namespace staging istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n staging
kubectl rollout status deployment -n staging
istioctl proxy-status
```

애플리케이션 smoke test 통과와 워크로드에 맞는 관찰 기간 후에만 다음 네임스페이스로 진행합니다. 고정 sleep 시간은 정상 동작 검증을 대신하지 않습니다.

**5. 이전 Control Plane 제거 전에 게이트웨이 이전**

게이트웨이의 관리 도구인 istioctl/Helm으로 프록시 이미지, revision, 외부 로드 밸런서 설정을 함께 업데이트하세요. 이전 이미지가 명시된 Deployment는 레이블만 바꿔도 업그레이드되지 않습니다. 롤아웃, 외부 요청, proxy-status를 확인합니다. istioctl default 프로필은 공유 게이트웨이를 in-place 업그레이드할 수 있으므로 명시적으로 계획하세요.

**6. 완료 또는 롤백**

게이트웨이와 Deployment 외 워크로드를 포함한 모든 프록시가 이전 revision을 떠난 것을 확인한 후 설치 도구로 제거합니다. 공유 검증 webhook을 직접 삭제하지 마세요:

```bash
istioctl proxy-status
istioctl uninstall --revision=1-30-4
```

제거 전 롤백은 네임스페이스를 아직 실행 중인 이전 revision으로 되돌리고 워크로드를 재시작하며 업그레이드한 게이트웨이도 이전 릴리스 설정으로 복구한 뒤 트래픽을 검증하는 것입니다. 새 revision에 의존하는 프록시가 없을 때만 새 revision을 제거하세요. 이전 revision을 이미 제거했다면 워크로드 레이블 변경 전에 재설치·검증해야 합니다.

**참고 자료:**

- [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
- [백업 및 운영 가이드](../../../service-mesh/istio/best-practices.md)

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

* [Installation Configuration Profiles](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Installing the Sidecar](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
* [Security](https://istio.io/latest/docs/concepts/security/)
* [Internet Engineering Task Force (IETF)                       E. Rescorla](https://www.rfc-editor.org/rfc/rfc8446.html)
* [Canary Upgrades](https://istio.io/latest/docs/setup/upgrade/canary/)
* [istioctl](https://istio.io/latest/docs/reference/commands/istioctl/)
* [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Announcing Istio 1.24.0](https://istio.io/latest/news/releases/1.24.x/announcing-1.24/)
* [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
