# 설치 및 초기 설정

이 문서에서는 Amazon EKS 클러스터에 Istio를 설치하고 초기 설정하는 방법을 다룹니다.

## 목차

1. [사전 요구 사항](01-installation.md#사전-요구-사항)
2. [설치 방법 선택](01-installation.md#설치-방법-선택)
3. [istioctl을 사용한 설치](01-installation.md#istioctl을-사용한-설치)
4. [Helm을 사용한 설치](01-installation.md#helm을-사용한-설치)
5. [istioctl 선언적 설치](01-installation.md#istioctl-선언적-설치)
6. [설치 프로필](01-installation.md#설치-프로필)
7. [설치 검증](01-installation.md#설치-검증)
8. [샘플 애플리케이션 배포](01-installation.md#샘플-애플리케이션-배포)
9. [Istio 제거](01-installation.md#istio-제거)
10. [문제 해결](01-installation.md#문제-해결)

## 사전 요구 사항

Istio를 설치하기 전에 다음 요구 사항을 충족해야 합니다:

### 1. Amazon EKS 클러스터

* **Kubernetes 버전**: Istio 1.31.0 예제는 EKS 1.34–1.36 사용 (2026-09-11 검토). Istio 1.31은 1.32–1.36을 지원하며 EKS 1.32/1.33은 연장 지원 상태입니다. [Istio 매트릭스](https://istio.io/latest/docs/releases/supported-releases/)와 [EKS 수명 주기](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)를 함께 확인하세요.
* **노드 유형**: 최소 2개의 워커 노드 (권장: 3개 이상)
* **노드 크기**: 최소 2 vCPU, 4GB RAM (권장: t3.medium 이상)

이 예제는 Linux EC2 워커 노드를 대상으로 합니다. Fargate는 이 Istio 설치 방식에 필요한 DaemonSet/특권 네트워킹을 실행할 수 없습니다. EKS Auto Mode는 네트워킹과 로드 밸런서 관리 방식이 다르므로 별도 사전 검증이 필요합니다.

### 2. kubectl 설치 및 구성

```bash
# kubectl 설치 확인
kubectl version --client

# EKS 클러스터 연결 확인
kubectl get nodes
```

### 3. 필요한 도구

* **AWS CLI**: 2.x 이상
* **eksctl**: (선택 사항) 클러스터 관리를 위해
* **Helm**: 현재 지원되는 Helm 3 또는 Helm 4 (최소 3.6; 공식 설치 가이드 참조)

### 4. 클러스터 리소스

계획용 리소스 요청 예시이며 공통 최소 요구량이 아닙니다. 실제 부하를 측정해 조정하세요:

* **Control Plane**: 1 vCPU, 1.5GB RAM
* **Sidecar (per pod)**: 0.1 vCPU, 128MB RAM

## 설치 방법 선택

지원되는 설치 방식 중 하나를 선택하세요. 같은 Control Plane에 istioctl과 Helm 설치를 중복 실행하지 마세요:

| 방법                 | 장점                   | 단점          | 권장 사용 사례             |
| ------------------ | -------------------- | ----------- | -------------------- |
| **istioctl**       | 간단하고 빠름, 검증 기능 제공    | 자동화 시 명시적 재적용 필요     | 개발 및 프로덕션 환경          |
| **Helm**           | GitOps 친화적, 버전 관리 용이 | 구성 복잡할 수 있음 | 프로덕션 환경, CI/CD 파이프라인 |

## istioctl을 사용한 설치

istioctl은 Istio의 공식 CLI 도구로, 가장 간단한 설치 방법입니다.

### 1. istioctl 설치

```bash
# 검토한 릴리스 다운로드
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -

# istioctl을 PATH에 추가
cd istio-1.31.0
export PATH=$PWD/bin:$PATH

# 설치 확인
istioctl version
```

### 2. 설치 전 클러스터 검증

```bash
# 클러스터가 Istio 설치 요구 사항을 충족하는지 확인
istioctl x precheck
```

### 3. Istio 설치

```bash
# default 프로필로 설치
istioctl install --set profile=default -y

# 설치 진행 상황 확인
kubectl get pods -n istio-system
```

### 4. 설치 확인

```bash
# Istio 구성 요소 확인
kubectl get all -n istio-system

# istiod 로그 확인
kubectl logs -n istio-system -l app=istiod
```

## Helm을 사용한 설치

이번 검토에서 고정한 1.31.0 릴리스 차트를 렌더링했습니다. 현재 개요 문서의 목록과 달리 해당 차트에는 `eks` 플랫폼 프로필이 없습니다. 따라서 예제는 `global.platform=eks`를 생략하며 EKS 사전 요구사항과 로드 밸런서 설정을 명시적으로 적용합니다.

Helm은 Kubernetes 패키지 매니저로, GitOps 워크플로우에 적합합니다.

### 1. Helm 저장소 추가

```bash
# Istio Helm 저장소 추가
helm repo add istio https://blob.istio.io/istio-release/charts
helm repo update
```

### 2. istio-base 설치

istio-base는 Istio의 CRD(Custom Resource Definitions)를 설치합니다.

```bash
# istio-system 네임스페이스 생성
kubectl create namespace istio-system

# istio-base 차트 설치
helm install istio-base istio/base \
  -n istio-system \
  --set defaultRevision=default \
  --version 1.31.0
```

### 3. istiod 설치

istiod는 Istio Control Plane입니다.

```bash
# istiod 차트 설치
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.0 \
  --wait
```

### 4. Istio Ingress Gateway 설치 (선택 사항)

```bash
# 게이트웨이 네임스페이스 확인
kubectl get namespace istio-system

# Istio Ingress Gateway 설치
helm install istio-ingressgateway istio/gateway \
  -n istio-system \
  --set labels.istio=ingressgateway \
  --set labels.app=istio-ingressgateway \
  --version 1.31.0 \
  --wait
```

### 5. values.yaml을 사용한 커스텀 설치

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.0

autoscaleEnabled: true
autoscaleMin: 2
autoscaleMax: 5
resources:
  requests:
    cpu: 500m
    memory: 2048Mi

meshConfig:
  accessLogFile: /dev/stdout
```

```bash
# values.yaml 파일을 사용하여 설치
helm upgrade --install istiod istio/istiod \
  -n istio-system \
  --version 1.31.0 \
  -f values.yaml \
  --wait
```

## istioctl 선언적 설치

업스트림 in-cluster operator는 1.23에서 사용 중단되고 1.24에서 제거되었습니다. `istioctl operator init/remove`와 IstioOperator 리소스의 클러스터 직접 적용은 현재 설치 방식이 아닙니다. [IstioOperator 파일 형식은 istioctl 입력으로 계속 지원됩니다](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/).

```yaml
# istio-operator.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  profile: default
  meshConfig:
    accessLogFile: /dev/stdout
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
```

```bash
istioctl install -f istio-operator.yaml
kubectl rollout status deployment/istiod -n istio-system
```

## 설치 프로필

Istio는 다양한 사용 사례에 맞는 여러 프로필을 제공합니다.

### 사용 가능한 프로필

| 프로필         | 설명                        | 구성 요소                                              | 권장 사용            |
| ----------- | ------------------------- | -------------------------------------------------- | ---------------- |
| **default** | 프로덕션 배포용 기본 설정            | istiod, ingress gateway                            | 대부분의 프로덕션 환경     |
| **demo**    | 데모용 설정 (모든 기능 활성화가 아님)            | istiod, ingress gateway, egress gateway, 높은 추적 샘플링 | 개발 및 데모          |
| **minimal** | 최소한의 구성 요소만 설치            | istiod only                                        | 리소스 제약 환경        |
| **remote**  | Multi-cluster 환경의 원격 클러스터 | -                                                  | Multi-cluster 설정 |
| **empty**   | 기본 구성 없음                  | -                                                  | 완전한 커스텀 설정       |
| **preview** | 실험적 기능 포함                 | 다양한 실험적 기능                                         | 테스트 환경           |
| **ambient** | 사이드카 없는 L4 메시 | istiod, CNI, ztunnel; L7 waypoint는 별도 구성 | Ambient 배포 |

위 구성 요소 목록은 istioctl 기준입니다. Helm에서는 프로필을 선택해도 다른 차트가 자동 설치되지 않으므로 각 차트를 따로 설치해야 합니다.

### 프로필 확인

```bash
helm show values istio/istiod --version 1.31.0
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
```

### 프로필별 설치

```bash
# demo 프로필로 설치
istioctl install --set profile=demo -y

# minimal 프로필로 설치
istioctl install --set profile=minimal -y
```

### 프로필 커스터마이징

```bash
# 프로필을 기반으로 특정 설정 변경
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set components.pilot.k8s.resources.requests.memory=2Gi \
  -y
```

## 설치 검증

### 1. Control Plane 확인

```bash
# istio-system 네임스페이스의 모든 리소스 확인
kubectl get all -n istio-system

# istiod 상태 확인
kubectl get deployment istiod -n istio-system

# istiod 로그 확인
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. Istio 버전 확인

```bash
# Control Plane 버전
istioctl version

# 또는
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. Istio 구성 검증

```bash
# Istio 설치 상태 확인
kubectl rollout status deployment/istiod -n istio-system
istioctl proxy-status

# Istio 구성 분석
istioctl analyze -A
```

### 4. Webhook 확인

```bash
# MutatingWebhookConfiguration 확인
kubectl get mutatingwebhookconfiguration

# ValidatingWebhookConfiguration 확인
kubectl get validatingwebhookconfiguration
```

## 샘플 애플리케이션 배포

Istio에는 Bookinfo라는 샘플 애플리케이션이 포함되어 있습니다.

압축을 푼 `istio-1.31.0` 디렉터리에서 기본 네임스페이스를 선택한 후 실행하세요 (`kubectl config set-context --current --namespace=default`). Helm 경로는 위의 선택적 게이트웨이 설치를 먼저 완료하세요. 뒤의 대시보드 명령은 별도로 설치한 텔레메트리 애드온이 필요합니다.

### 1. 네임스페이스에 Sidecar 자동 주입 활성화

```bash
# default 네임스페이스에 레이블 추가
kubectl label namespace default istio-injection=enabled --overwrite

# 레이블 확인
kubectl get namespace -L istio-injection
```

주입 레이블 변경은 기존 파드에 소급 적용되지 않으므로 파드를 재생성해야 합니다. 충돌하는 `istio.io/rev` 또는 Ambient 레이블이 없는 네임스페이스를 사용하세요.

### 2. Bookinfo 애플리케이션 배포

```bash
# Bookinfo 애플리케이션 배포
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# 파드 확인 (각 파드에 2개의 컨테이너가 있어야 함)
kubectl get pods

# 서비스 확인
kubectl get services
```

### 3. 애플리케이션 접근 확인

```bash
# productpage 서비스 테스트
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. Ingress Gateway 구성

```bash
# Bookinfo Gateway 생성
cat <<'EOF' > bookinfo-gateway.yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: default
spec:
  hosts:
  - "*"
  gateways:
  - bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage
        port:
          number: 9080
EOF
kubectl apply -f bookinfo-gateway.yaml

# Gateway 확인
kubectl get gateway.networking.istio.io

# VirtualService 확인
kubectl get virtualservice
```

### 5. 외부 접근 설정

```bash
# Ingress Gateway의 External IP 확인
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')

export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# 애플리케이션 접근
echo "http://$GATEWAY_URL/productpage"

# 브라우저에서 접근하거나 curl로 확인
curl -s "http://$GATEWAY_URL/productpage" | grep -o "<title>.*</title>"
```

## Istio 제거

아래 정리는 폐기 가능한 실습 환경용입니다. Purge는 공유 메시 리소스를 삭제합니다. 운영 메시 제거 전에 주입된 워크로드를 제거하거나 주입 없이 재시작하세요. Helm 제거는 CRD를 남깁니다.

### istioctl을 사용한 제거

```bash
# 샘플 애플리케이션 제거
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f bookinfo-gateway.yaml

# Istio 제거
istioctl uninstall --purge -y

# istio-system 네임스페이스 제거
kubectl delete namespace istio-system

# Istio 레이블 제거
kubectl label namespace default istio-injection-
```

### Helm을 사용한 제거

```bash
# Ingress Gateway 제거
helm delete istio-ingressgateway -n istio-system

# istiod 제거
helm delete istiod -n istio-system

# istio-base 제거
helm delete istio-base -n istio-system

# 네임스페이스 제거
kubectl delete namespace istio-system
```

## 문제 해결

### 일반적인 문제

#### 1. Sidecar 자동 주입 실패

**증상**: 파드에 Envoy sidecar가 주입되지 않음

**해결 방법**:

```bash
# 네임스페이스 레이블 확인
kubectl get namespace -L istio-injection

# 레이블이 없으면 추가
kubectl label namespace default istio-injection=enabled --overwrite

# Webhook 확인
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod 파드가 시작되지 않음

**증상**: istiod 파드가 Pending 또는 CrashLoopBackOff 상태

**해결 방법**:

```bash
# 파드 상태 확인
kubectl get pods -n istio-system

# 파드 이벤트 확인
kubectl describe pod -n istio-system -l app=istiod

# 로그 확인
kubectl logs -n istio-system -l app=istiod

# 리소스 확인
kubectl top nodes
kubectl describe nodes
```

#### 3. Ingress Gateway가 External IP를 받지 못함

**증상**: LoadBalancer 타입 서비스가 Pending 상태

**해결 방법**:

```bash
# 서비스 상태 확인
kubectl get svc -n istio-system istio-ingressgateway

# AWS Load Balancer Controller 확인
kubectl get deployment -n kube-system aws-load-balancer-controller

# 이벤트 확인
kubectl describe svc -n istio-system istio-ingressgateway
```

### 디버깅 도구

#### istioctl analyze

```bash
# 전체 클러스터 분석
istioctl analyze -A

# 특정 네임스페이스 분석
istioctl analyze -n default
```

#### istioctl proxy-status

```bash
# 모든 프록시 상태 확인
istioctl proxy-status

# 특정 파드의 프록시 상태 확인
istioctl proxy-status <POD_NAME>.<NAMESPACE>
```

#### istioctl dashboard

```bash
# Kiali 대시보드 실행
istioctl dashboard kiali

# Grafana 대시보드 실행
istioctl dashboard grafana

# Prometheus 대시보드 실행
istioctl dashboard prometheus

# Envoy 관리 인터페이스
istioctl dashboard envoy <POD_NAME>.<NAMESPACE>
```

### 로그 수집

```bash
# Control Plane 로그
kubectl logs -n istio-system -l app=istiod

# Ingress Gateway 로그
kubectl logs -n istio-system -l app=istio-ingressgateway

# 특정 파드의 Envoy 로그
kubectl logs <POD_NAME> -c istio-proxy

# 모든 Istio 관련 로그를 파일로 저장
istioctl bug-report
```

## 다음 단계

Istio 설치가 완료되었습니다! 이제 다음 문서를 참고하여 Istio를 활용해보세요:

1. [**기본 개념**](02-basic-concepts.md): Istio의 핵심 개념과 아키텍처 이해
2. [**Traffic Management**](traffic-management/README.md): Gateway, VirtualService, DestinationRule 학습
3. [**Security**](security/README.md): mTLS, 인증, 권한 부여 설정

## 참고 자료

* [Istio 공식 설치 가이드](https://istio.io/latest/docs/setup/install/)
* [Istio 프로필 문서](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Istio EKS 플랫폼 가이드](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Istio 문제 해결 가이드](https://istio.io/latest/docs/ops/diagnostic-tools/)

* [EKS Fargate 제약](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
* [Istio 1.31 릴리스 및 아티팩트 이전](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
