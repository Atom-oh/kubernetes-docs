# Linkerd 설치 및 설정

> **지원 버전**: Linkerd 2.16+
> **마지막 업데이트**: 2026년 2월 22일

## 개요

이 문서에서는 Linkerd를 Kubernetes 클러스터에 설치하는 다양한 방법을 다룹니다. CLI 도구 설치부터 컨트롤 플레인 설치, 고가용성(HA) 구성, 그리고 Viz, Jaeger, Multicluster 등 확장 기능 설치까지 포괄적으로 설명합니다.

## 사전 요구사항

### Kubernetes 버전

| Linkerd 버전 | 최소 Kubernetes 버전 | 권장 Kubernetes 버전 |
|-------------|---------------------|---------------------|
| 2.16.x | 1.25+ | 1.28+ |
| 2.15.x | 1.24+ | 1.27+ |
| 2.14.x | 1.22+ | 1.26+ |

### 클러스터 요구사항

```yaml
# 최소 요구사항
CPU: 100m (컨트롤 플레인 전체)
Memory: 200Mi (컨트롤 플레인 전체)
Nodes: 1+ (프로덕션은 3+ 권장)

# 권장 요구사항 (프로덕션)
CPU: 500m - 1000m
Memory: 500Mi - 1Gi
Nodes: 3+ (HA 구성)
```

### 네트워크 요구사항

- TCP 포트 443: Webhook 통신
- TCP 포트 8443: Proxy injector
- TCP 포트 8089: Tap API
- 클러스터 내 DNS 해결 가능

### 사전 검증

```bash
# Linkerd CLI가 설치되어 있다면 사전 검증 실행
linkerd check --pre

# 예상 출력:
# kubernetes-api
# --------------
# √ can initialize the client
# √ can query the Kubernetes API
#
# kubernetes-version
# ------------------
# √ is running the minimum Kubernetes API version
#
# pre-kubernetes-setup
# --------------------
# √ control plane namespace does not already exist
# √ can create non-namespaced resources
# √ can create ServiceAccounts
# √ can create Services
# √ can create Deployments
# √ can create CronJobs
# √ can create ConfigMaps
# √ can create Secrets
# √ can read Secrets
# √ can read extension-apiserver-authentication configmap
# √ no clock skew detected
#
# Status check results are √
```

## Linkerd CLI 설치

### Linux/macOS (curl)

```bash
# 최신 안정 버전 설치
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# PATH에 추가
export PATH=$HOME/.linkerd2/bin:$PATH

# 영구적으로 PATH 추가 (bash)
echo 'export PATH=$HOME/.linkerd2/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# 영구적으로 PATH 추가 (zsh)
echo 'export PATH=$HOME/.linkerd2/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

### 특정 버전 설치

```bash
# 특정 버전 설치 (예: 2.16.0)
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh -s -- --version stable-2.16.0

# Edge 버전 설치
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install-edge | sh
```

### macOS (Homebrew)

```bash
# Homebrew를 통한 설치
brew install linkerd

# 업그레이드
brew upgrade linkerd
```

### Windows (Chocolatey)

```powershell
# Chocolatey를 통한 설치
choco install linkerd2

# 업그레이드
choco upgrade linkerd2
```

### Windows (수동 설치)

```powershell
# PowerShell에서 다운로드
$version = "stable-2.16.0"
$arch = "windows-amd64"
$url = "https://github.com/linkerd/linkerd2/releases/download/$version/linkerd2-cli-$version-$arch.exe"

Invoke-WebRequest -Uri $url -OutFile linkerd.exe

# PATH에 추가하거나 원하는 위치로 이동
Move-Item linkerd.exe C:\tools\linkerd.exe
```

### 설치 확인

```bash
# 버전 확인
linkerd version

# 출력 예시:
# Client version: stable-2.16.0
# Server version: unavailable (서버 미설치 시)
```

## 컨트롤 플레인 설치

### 기본 설치 (CLI)

```bash
# 1단계: CRD 설치
linkerd install --crds | kubectl apply -f -

# 2단계: 컨트롤 플레인 설치
linkerd install | kubectl apply -f -

# 설치 확인
linkerd check

# 예상 출력:
# kubernetes-api
# --------------
# √ can initialize the client
# √ can query the Kubernetes API
#
# linkerd-existence
# -----------------
# √ 'linkerd-config' config map exists
# √ heartbeat ServiceAccount exist
# √ control plane replica sets are ready
# √ no unschedulable pods
# √ control plane pods are ready
# √ cluster networks contains all pods
# √ cluster networks contains all services
#
# linkerd-config
# --------------
# √ control plane Namespace exists
# √ control plane ClusterRoles exist
# √ control plane ClusterRoleBindings exist
# √ control plane ServiceAccounts exist
# √ control plane CustomResourceDefinitions exist
# √ control plane MutatingWebhookConfigurations exist
# √ control plane ValidatingWebhookConfigurations exist
# √ proxy-init container runs as root user if docker container runtime is used
#
# linkerd-identity
# ----------------
# √ certificate config is valid
# √ trust anchors are using supported crypto algorithm
# √ trust anchors are within their validity period
# √ trust anchors are valid for at least 60 days
# √ issuer cert is using supported crypto algorithm
# √ issuer cert is within its validity period
# √ issuer cert is valid for at least 60 days
# √ issuer cert is issued by the trust anchor
#
# linkerd-webhooks-and-apisvc-tls
# -------------------------------
# √ proxy-injector webhook has valid cert
# √ proxy-injector cert is valid for at least 60 days
# √ sp-validator webhook has valid cert
# √ sp-validator cert is valid for at least 60 days
# √ policy-validator webhook has valid cert
# √ policy-validator cert is valid for at least 60 days
#
# linkerd-version
# ---------------
# √ can determine the latest version
# √ cli is up-to-date
#
# control-plane-version
# ---------------------
# √ can retrieve the control plane version
# √ control plane is up-to-date
# √ control plane and cli versions match
#
# Status check results are √
```

### 설치 매니페스트 미리 보기

```bash
# 설치될 리소스 미리 보기
linkerd install --crds > linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml

# 검토 후 적용
kubectl apply -f linkerd-crds.yaml
kubectl apply -f linkerd-control-plane.yaml
```

### Helm을 사용한 설치

Helm을 사용하면 더 세밀한 설정이 가능합니다.

#### Helm 저장소 추가

```bash
# Linkerd Helm 저장소 추가
helm repo add linkerd https://helm.linkerd.io/stable
helm repo update

# Edge 버전용 저장소
helm repo add linkerd-edge https://helm.linkerd.io/edge
```

#### 인증서 생성

Helm 설치 시 인증서를 직접 제공해야 합니다.

```bash
# step CLI 설치 (인증서 생성용)
# macOS
brew install step

# Linux
wget https://dl.step.sm/gh-release/cli/docs-cli-install/v0.25.0/step-cli_0.25.0_amd64.deb
sudo dpkg -i step-cli_0.25.0_amd64.deb

# Trust Anchor (Root CA) 생성
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h  # 10년

# Issuer 인증서 생성
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca \
  --not-after=8760h \  # 1년
  --no-password \
  --insecure \
  --ca ca.crt \
  --ca-key ca.key
```

#### Helm으로 CRD 설치

```bash
# CRD 설치
helm install linkerd-crds linkerd/linkerd-crds \
  -n linkerd \
  --create-namespace \
  --wait
```

#### Helm으로 컨트롤 플레인 설치

```bash
# 컨트롤 플레인 설치
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

#### Helm Values 파일 사용

```yaml
# values.yaml
# 프록시 리소스 설정
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi

# 프록시 로그 레벨
proxyLogLevel: warn,linkerd=info

# 프록시 로그 형식
proxyLogFormat: plain

# Identity 설정
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s

# 컨트롤 플레인 리소스
controllerResources: &controller_resources
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi

destinationResources: *controller_resources
identityResources: *controller_resources
proxyInjectorResources: *controller_resources

# Pod 안티-어피니티 설정
enablePodAntiAffinity: false

# 네임스페이스 메타데이터
namespace:
  labels:
    linkerd.io/control-plane-ns: linkerd
```

```bash
# values 파일로 설치
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

## 고가용성(HA) 설치

프로덕션 환경에서는 고가용성 구성을 권장합니다.

### CLI를 사용한 HA 설치

```bash
# HA 프로필로 설치
linkerd install --crds | kubectl apply -f -
linkerd install --ha | kubectl apply -f -
```

### Helm을 사용한 HA 설치

```yaml
# ha-values.yaml
# HA 기본 설정
enablePodAntiAffinity: true

# 컨트롤 플레인 복제본
controllerReplicas: 3

# Destination 컨트롤러 설정
destination:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# Identity 컨트롤러 설정
identity:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 10Mi
      limit: 250Mi

# Proxy Injector 설정
proxyInjector:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# PodDisruptionBudget 설정
podDisruptionBudget:
  maxUnavailable: 1

# 프록시 리소스 (HA용 증가)
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi

# Pod 안티-어피니티
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchLabels:
          linkerd.io/control-plane-component: destination
      topologyKey: kubernetes.io/hostname

# 토폴로지 분산 제약
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        linkerd.io/control-plane-ns: linkerd
```

```bash
# HA values로 설치
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f ha-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

### HA 구성 확인

```bash
# 컨트롤 플레인 Pod 배포 확인
kubectl get pods -n linkerd -o wide

# PodDisruptionBudget 확인
kubectl get pdb -n linkerd

# 안티-어피니티 적용 확인 (각기 다른 노드에 배포)
kubectl get pods -n linkerd -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
```

## 확장 기능 설치

### Viz 확장 (대시보드 및 메트릭)

Viz 확장은 Linkerd의 관찰성 기능을 제공합니다.

#### CLI로 설치

```bash
# Viz 확장 설치
linkerd viz install | kubectl apply -f -

# 설치 확인
linkerd viz check

# 대시보드 열기
linkerd viz dashboard &
```

#### Helm으로 설치

```bash
# Viz 확장 Helm 설치
helm install linkerd-viz linkerd/linkerd-viz \
  -n linkerd-viz \
  --create-namespace \
  --wait
```

#### Viz Values 커스터마이징

```yaml
# viz-values.yaml
# Prometheus 설정
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    enabled: true
    storageClass: gp3
    size: 10Gi

# Grafana 비활성화 (외부 Grafana 사용 시)
grafana:
  enabled: false

# 대시보드 설정
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
  # 인증 비활성화 (개발 환경용)
  # enforcedHostRegexp: ""

# Tap 설정
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# 메트릭 API 설정
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
# 커스텀 values로 설치
helm install linkerd-viz linkerd/linkerd-viz \
  -n linkerd-viz \
  --create-namespace \
  -f viz-values.yaml \
  --wait
```

### Jaeger 확장 (분산 추적)

#### CLI로 설치

```bash
# Jaeger 확장 설치
linkerd jaeger install | kubectl apply -f -

# 설치 확인
linkerd jaeger check
```

#### Helm으로 설치

```bash
# Jaeger 확장 Helm 설치
helm install linkerd-jaeger linkerd/linkerd-jaeger \
  -n linkerd-jaeger \
  --create-namespace \
  --wait
```

#### Jaeger Values 커스터마이징

```yaml
# jaeger-values.yaml
# Collector 설정
collector:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi

# Jaeger UI/Query 설정
jaeger:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi

# 샘플링 설정
webhook:
  collectorSvcAddr: collector.linkerd-jaeger:55678
  collectorSvcAccount: collector
```

### Multicluster 확장 (다중 클러스터)

#### CLI로 설치

```bash
# Multicluster 확장 설치
linkerd multicluster install | kubectl apply -f -

# 설치 확인
linkerd multicluster check
```

#### Helm으로 설치

```bash
# Multicluster 확장 Helm 설치
helm install linkerd-multicluster linkerd/linkerd-multicluster \
  -n linkerd-multicluster \
  --create-namespace \
  --wait
```

#### Multicluster Values

```yaml
# multicluster-values.yaml
# Gateway 설정
gateway:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
  # LoadBalancer 설정 (EKS용)
  serviceType: LoadBalancer
  loadBalancerIP: ""
  # NLB 사용 시
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

# Service Account 설정
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access
```

## Amazon EKS 특화 설정

### EKS 클러스터 준비

```bash
# EKS 클러스터 생성 (eksctl 사용)
eksctl create cluster \
  --name linkerd-cluster \
  --version 1.28 \
  --region ap-northeast-2 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# kubeconfig 업데이트
aws eks update-kubeconfig --name linkerd-cluster --region ap-northeast-2
```

### EKS CNI 호환성

Linkerd는 대부분의 CNI와 호환됩니다.

```bash
# Amazon VPC CNI 버전 확인
kubectl describe daemonset aws-node -n kube-system | grep Image

# Linkerd CNI 플러그인 설치 (선택적, Amazon VPC CNI와 함께 사용)
linkerd install-cni | kubectl apply -f -
```

### EKS IAM 설정

```yaml
# linkerd-service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: linkerd-destination
  namespace: linkerd
  annotations:
    # IRSA 사용 시 (필요한 경우)
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/LinkerdDestinationRole
```

### EKS용 Ingress 설정 (AWS Load Balancer Controller)

```yaml
# linkerd-viz-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: linkerd-viz
  namespace: linkerd-viz
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:ACCOUNT_ID:certificate/CERT_ID
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/healthcheck-path: /ready
spec:
  rules:
  - host: linkerd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web
            port:
              number: 8084
```

### EKS용 NLB Gateway 설정 (Multicluster)

```yaml
# multicluster-gateway-nlb.yaml
# Helm values
gateway:
  serviceType: LoadBalancer
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
```

### EKS 보안 그룹 설정

```bash
# 클러스터 보안 그룹에 필요한 포트 허용
# - TCP 4143: Linkerd 프록시
# - TCP 4191: Linkerd 프록시 메트릭
# - TCP 8443: Proxy injector webhook
# - TCP 8089: Tap API

# eksctl로 보안 그룹 규칙 추가 (예시)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 4143 \
  --source-group sg-xxxxxxxxx
```

## 설치 확인 및 검증

### 전체 상태 확인

```bash
# 포괄적인 상태 확인
linkerd check

# 확장 포함 상태 확인
linkerd check --proxy

# Viz 확장 상태 확인
linkerd viz check

# Multicluster 확장 상태 확인
linkerd multicluster check

# Jaeger 확장 상태 확인
linkerd jaeger check
```

### 컴포넌트 상태 확인

```bash
# 컨트롤 플레인 Pod 상태
kubectl get pods -n linkerd

# 확장 Pod 상태
kubectl get pods -n linkerd-viz
kubectl get pods -n linkerd-jaeger
kubectl get pods -n linkerd-multicluster

# 서비스 상태
kubectl get svc -n linkerd
kubectl get svc -n linkerd-viz

# CRD 확인
kubectl get crds | grep linkerd
```

### 샘플 애플리케이션으로 테스트

```bash
# emojivoto 샘플 앱 설치
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -

# 프록시 주입
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -

# 배포 확인
kubectl get pods -n emojivoto

# 통계 확인
linkerd viz stat deploy -n emojivoto

# 실시간 트래픽 확인
linkerd viz top deploy -n emojivoto
```

## Linkerd 업그레이드

### Stable 채널 업그레이드

```bash
# CLI 업그레이드
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# 새 버전 확인
linkerd version

# 업그레이드 전 확인
linkerd check --pre

# CRD 업그레이드
linkerd upgrade --crds | kubectl apply -f -

# 컨트롤 플레인 업그레이드
linkerd upgrade | kubectl apply -f -

# 업그레이드 확인
linkerd check

# 확장 업그레이드
linkerd viz upgrade | kubectl apply -f -
linkerd viz check
```

### Helm 업그레이드

```bash
# Helm 저장소 업데이트
helm repo update

# 현재 values 백업
helm get values linkerd-control-plane -n linkerd > current-values.yaml

# CRD 업그레이드
helm upgrade linkerd-crds linkerd/linkerd-crds -n linkerd --wait

# 컨트롤 플레인 업그레이드
helm upgrade linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f current-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait

# Viz 확장 업그레이드
helm upgrade linkerd-viz linkerd/linkerd-viz -n linkerd-viz --wait
```

### Edge 채널

```bash
# Edge 버전 설치 (최신 기능, 더 자주 업데이트)
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install-edge | sh

# Edge Helm 저장소
helm repo add linkerd-edge https://helm.linkerd.io/edge
```

### 데이터 플레인 업그레이드 (프록시 롤링 재시작)

```bash
# 모든 메시 워크로드 재시작하여 새 프록시 적용
kubectl rollout restart deploy -n my-namespace

# 또는 특정 Deployment만
kubectl rollout restart deploy/my-app -n my-namespace

# 프록시 버전 확인
linkerd viz stat deploy -n my-namespace -o wide
```

## 문제 해결

### 일반적인 설치 문제

#### Webhook 연결 실패

```bash
# 증상: 프록시 주입이 동작하지 않음
# 원인: webhook 서비스 연결 불가

# 해결 방법 1: webhook 서비스 확인
kubectl get svc -n linkerd linkerd-proxy-injector

# 해결 방법 2: webhook 설정 확인
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml

# 해결 방법 3: 네트워크 정책 확인
kubectl get networkpolicy -n linkerd
```

#### 인증서 문제

```bash
# 증상: identity 관련 오류
# linkerd check 실행 시 certificate 오류

# 해결 방법: 인증서 상태 확인
linkerd check --proxy

# Trust anchor 만료 확인
kubectl get secret linkerd-identity-trust-roots -n linkerd -o json | \
  jq -r '.data["ca-bundle.crt"]' | base64 -d | \
  openssl x509 -noout -dates

# Issuer 인증서 확인
kubectl get secret linkerd-identity-issuer -n linkerd -o json | \
  jq -r '.data["crt.pem"]' | base64 -d | \
  openssl x509 -noout -dates
```

#### 리소스 부족

```bash
# 증상: Pod가 Pending 상태로 유지
# 원인: 노드 리소스 부족

# 해결 방법: 리소스 요청 확인
kubectl describe pod -n linkerd <pod-name>

# 노드 리소스 확인
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### 디버깅 명령어

```bash
# 컨트롤 플레인 로그 확인
kubectl logs -n linkerd deploy/linkerd-destination -c destination
kubectl logs -n linkerd deploy/linkerd-identity
kubectl logs -n linkerd deploy/linkerd-proxy-injector

# 프록시 로그 확인
kubectl logs <pod-name> -c linkerd-proxy

# 이벤트 확인
kubectl get events -n linkerd --sort-by='.lastTimestamp'

# 프록시 상태 확인
linkerd diagnostics proxy-metrics <pod-name>
```

## 제거

### CLI로 제거

```bash
# 확장 먼저 제거
linkerd viz uninstall | kubectl delete -f -
linkerd jaeger uninstall | kubectl delete -f -
linkerd multicluster uninstall | kubectl delete -f -

# 컨트롤 플레인 제거
linkerd uninstall | kubectl delete -f -
```

### Helm으로 제거

```bash
# 확장 제거
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-jaeger -n linkerd-jaeger
helm uninstall linkerd-multicluster -n linkerd-multicluster

# 컨트롤 플레인 제거
helm uninstall linkerd-control-plane -n linkerd

# CRD 제거
helm uninstall linkerd-crds -n linkerd

# 네임스페이스 제거
kubectl delete namespace linkerd linkerd-viz linkerd-jaeger linkerd-multicluster
```

## 다음 단계

- [아키텍처](./02-architecture.md): Linkerd 내부 구조 상세 이해
- [트래픽 관리](./03-traffic-management.md): ServiceProfile 및 트래픽 분할 설정
- [보안](./04-security.md): mTLS 및 인증 정책 설정

## 참고 자료

- [Linkerd 설치 가이드](https://linkerd.io/2/getting-started/)
- [Helm 차트 문서](https://linkerd.io/2/tasks/install-helm/)
- [HA 설치 가이드](https://linkerd.io/2/features/ha/)
- [EKS 가이드](https://linkerd.io/2/reference/cluster-configuration/)
