# 설치 및 초기 설정

이 문서에서는 Amazon EKS 클러스터에 Istio를 설치하고 초기 설정하는 방법을 다룹니다.

## 목차

1. [사전 요구 사항](01-installation.md#사전-요구-사항)
2. [설치 방법 선택](01-installation.md#설치-방법-선택)
3. [istioctl을 사용한 설치](01-installation.md#istioctl을-사용한-설치)
4. [Helm을 사용한 설치](01-installation.md#helm을-사용한-설치)
5. [Istio Operator를 사용한 설치](01-installation.md#istio-operator를-사용한-설치)
6. [설치 프로필](01-installation.md#설치-프로필)
7. [설치 검증](01-installation.md#설치-검증)
8. [샘플 애플리케이션 배포](01-installation.md#샘플-애플리케이션-배포)
9. [Istio 제거](01-installation.md#istio-제거)
10. [문제 해결](01-installation.md#문제-해결)

## 사전 요구 사항

Istio를 설치하기 전에 다음 요구 사항을 충족해야 합니다:

### 1. Amazon EKS 클러스터

* **Kubernetes 버전**: 1.28 이상 (권장: 1.34)
* **노드 유형**: 최소 2개의 워커 노드 (권장: 3개 이상)
* **노드 크기**: 최소 2 vCPU, 4GB RAM (권장: t3.medium 이상)

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
* **Helm**: 3.x 이상 (Helm 설치 방법을 사용하는 경우)

### 4. 클러스터 리소스

최소 리소스 요구 사항:

* **Control Plane**: 1 vCPU, 1.5GB RAM
* **Sidecar (per pod)**: 0.1 vCPU, 128MB RAM

## 설치 방법 선택

Istio는 세 가지 주요 설치 방법을 제공합니다:

| 방법                 | 장점                   | 단점          | 권장 사용 사례             |
| ------------------ | -------------------- | ----------- | -------------------- |
| **istioctl**       | 간단하고 빠름, 검증 기능 제공    | 자동화 어려움     | 개발 및 테스트 환경          |
| **Helm**           | GitOps 친화적, 버전 관리 용이 | 구성 복잡할 수 있음 | 프로덕션 환경, CI/CD 파이프라인 |
| **Istio Operator** | 선언적 관리, 자동 업그레이드     | 추가 리소스 필요   | 대규모 프로덕션 환경          |

## istioctl을 사용한 설치

istioctl은 Istio의 공식 CLI 도구로, 가장 간단한 설치 방법입니다.

### 1. istioctl 설치

```bash
# istioctl 다운로드 (최신 버전)
curl -L https://istio.io/downloadIstio | sh -

# 또는 특정 버전 다운로드
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -

# istioctl을 PATH에 추가
cd istio-1.28.0
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

Helm은 Kubernetes 패키지 매니저로, GitOps 워크플로우에 적합합니다.

### 1. Helm 저장소 추가

```bash
# Istio Helm 저장소 추가
helm repo add istio https://istio-release.storage.googleapis.com/charts
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
  --version 1.28.0
```

### 3. istiod 설치

istiod는 Istio Control Plane입니다.

```bash
# istiod 차트 설치
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  --wait
```

### 4. Istio Ingress Gateway 설치 (선택 사항)

```bash
# istio-ingress 네임스페이스 생성
kubectl create namespace istio-ingress

# Istio Ingress Gateway 설치
helm install istio-ingress istio/gateway \
  -n istio-ingress \
  --version 1.28.0 \
  --wait
```

### 5. values.yaml을 사용한 커스텀 설치

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.28.0

pilot:
  autoscaleEnabled: true
  autoscaleMin: 2
  autoscaleMax: 5
  resources:
    requests:
      cpu: 500m
      memory: 2048Mi

# AWS EKS 특정 설정
meshConfig:
  accessLogFile: /dev/stdout
  enableTracing: true
  defaultConfig:
    tracing:
      sampling: 100.0
```

```bash
# values.yaml 파일을 사용하여 설치
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  -f values.yaml \
  --wait
```

## Istio Operator를 사용한 설치

Istio Operator는 선언적 방식으로 Istio를 관리합니다.

### 1. Istio Operator 설치

```bash
# Operator 설치
istioctl operator init

# Operator 설치 확인
kubectl get pods -n istio-operator
```

### 2. IstioOperator 리소스 생성

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

### 3. Operator를 통한 Istio 설치

```bash
# IstioOperator 리소스 적용
kubectl create ns istio-system
kubectl apply -f istio-operator.yaml

# 설치 진행 상황 확인
kubectl get istiooperator -n istio-system
```

## 설치 프로필

Istio는 다양한 사용 사례에 맞는 여러 프로필을 제공합니다.

### 사용 가능한 프로필

| 프로필         | 설명                        | 구성 요소                                              | 권장 사용            |
| ----------- | ------------------------- | -------------------------------------------------- | ---------------- |
| **default** | 프로덕션 배포용 기본 설정            | istiod, ingress gateway                            | 대부분의 프로덕션 환경     |
| **demo**    | 모든 기능 활성화, 학습용            | istiod, ingress gateway, egress gateway, 높은 추적 샘플링 | 개발 및 데모          |
| **minimal** | 최소한의 구성 요소만 설치            | istiod only                                        | 리소스 제약 환경        |
| **remote**  | Multi-cluster 환경의 원격 클러스터 | -                                                  | Multi-cluster 설정 |
| **empty**   | 기본 구성 없음                  | -                                                  | 완전한 커스텀 설정       |
| **preview** | 실험적 기능 포함                 | 다양한 실험적 기능                                         | 테스트 환경           |

### 프로필 확인

```bash
# 사용 가능한 프로필 목록 확인
istioctl profile list

# 특정 프로필의 구성 확인
istioctl profile dump default

# 두 프로필 비교
istioctl profile diff default demo
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
  --set values.pilot.resources.requests.memory=2Gi \
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
istioctl verify-install

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

### 1. 네임스페이스에 Sidecar 자동 주입 활성화

```bash
# default 네임스페이스에 레이블 추가
kubectl label namespace default istio-injection=enabled

# 레이블 확인
kubectl get namespace -L istio-injection
```

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
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Gateway 확인
kubectl get gateway

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

### istioctl을 사용한 제거

```bash
# 샘플 애플리케이션 제거
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f samples/bookinfo/networking/bookinfo-gateway.yaml

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
helm delete istio-ingress -n istio-ingress

# istiod 제거
helm delete istiod -n istio-system

# istio-base 제거
helm delete istio-base -n istio-system

# 네임스페이스 제거
kubectl delete namespace istio-system
kubectl delete namespace istio-ingress
```

### Istio Operator를 사용한 제거

```bash
# IstioOperator 리소스 제거
kubectl delete istiooperator istio-control-plane -n istio-system

# Operator 제거
istioctl operator remove

# 네임스페이스 제거
kubectl delete namespace istio-system
kubectl delete namespace istio-operator
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
kubectl label namespace default istio-injection=enabled

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

1. [**기본 개념**](/broken/pages/ducaju4XiXAIssAYkJ8h): Istio의 핵심 개념과 아키텍처 이해
2. [**Traffic Management**](/broken/pages/KbABk4V1immX9KTfw6H7): Gateway, VirtualService, DestinationRule 학습
3. [**Security**](/broken/pages/3c3ksbHxkXoGxJXLSp3m): mTLS, 인증, 권한 부여 설정

## 참고 자료

* [Istio 공식 설치 가이드](https://istio.io/latest/docs/setup/install/)
* [Istio 프로필 문서](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [AWS EKS 워크숍 - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
* [Istio 문제 해결 가이드](https://istio.io/latest/docs/ops/diagnostic-tools/)
