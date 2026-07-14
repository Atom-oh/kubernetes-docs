# Istio のインストールと初期設定

このドキュメントでは、Amazon EKS クラスターに Istio をインストールし、初期設定を行う方法を説明します。

## 目次

1. [前提条件](#prerequisites)
2. [インストール方法の選択](#choosing-an-installation-method)
3. [istioctl を使用したインストール](#installation-using-istioctl)
4. [Helm を使用したインストール](#installation-using-helm)
5. [Istio Operator を使用したインストール](#installation-using-istio-operator)
6. [インストールプロファイル](#installation-profiles)
7. [インストールの検証](#installation-verification)
8. [サンプルアプリケーションのデプロイ](#sample-application-deployment)
9. [Istio の削除](#istio-removal)
10. [トラブルシューティング](#troubleshooting)

## 前提条件

Istio をインストールする前に、以下の要件を満たす必要があります。

### 1. Amazon EKS クラスター

- **Kubernetes バージョン**: 1.28 以上（推奨: 1.34）
- **Node タイプ**: 最低 2 台の worker node（推奨: 3 台以上）
- **Node サイズ**: 最低 2 vCPU、4GB RAM（推奨: t3.medium 以上）

### 2. kubectl のインストールと設定

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. 必要なツール

- **AWS CLI**: 2.x 以上
- **eksctl**: （任意）クラスター管理用
- **Helm**: 3.x 以上（Helm インストール方法を使用する場合）

### 4. クラスターリソース

最小リソース要件:
- **Control Plane**: 1 vCPU、1.5GB RAM
- **Sidecar（Pod ごと）**: 0.1 vCPU、128MB RAM

## インストール方法の選択

Istio には主に 3 つのインストール方法があります。

| 方法 | 利点 | 欠点 | 推奨ユースケース |
|------|------|------|---------------|
| **istioctl** | シンプルかつ高速で、検証機能を提供 | 自動化が困難 | 開発・テスト環境 |
| **Helm** | GitOps に適し、バージョン管理が容易 | 設定が複雑になる場合がある | 本番環境、CI/CD パイプライン |
| **Istio Operator** | 宣言的な管理、自動アップグレード | 追加リソースが必要 | 大規模な本番環境 |

## istioctl を使用したインストール

istioctl は Istio の公式 CLI ツールであり、最も簡単なインストール方法です。

### 1. istioctl のインストール

```bash
# Download istioctl (latest version)
curl -L https://istio.io/downloadIstio | sh -

# Or download a specific version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -

# Add istioctl to PATH
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Verify installation
istioctl version
```

### 2. インストール前のクラスター検証

```bash
# Verify cluster meets Istio installation requirements
istioctl x precheck
```

### 3. Istio のインストール

```bash
# Install with default profile
istioctl install --set profile=default -y

# Check installation progress
kubectl get pods -n istio-system
```

### 4. インストールの検証

```bash
# Check Istio components
kubectl get all -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod
```

## Helm を使用したインストール

Helm は GitOps ワークフローに適した Kubernetes パッケージマネージャーです。

### 1. Helm リポジトリの追加

```bash
# Add Istio Helm repository
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update
```

### 2. istio-base のインストール

istio-base は Istio の CRD（Custom Resource Definitions）をインストールします。

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --version 1.28.0
```

### 3. istiod のインストール

istiod は Istio Control Plane です。

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  --wait
```

### 4. Istio Ingress Gateway のインストール（任意）

```bash
# Create istio-ingress namespace
kubectl create namespace istio-ingress

# Install Istio Ingress Gateway
helm install istio-ingress istio/gateway \
  -n istio-ingress \
  --version 1.28.0 \
  --wait
```

### 5. values.yaml を使用したカスタムインストール

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

# AWS EKS specific settings
meshConfig:
  accessLogFile: /dev/stdout
  enableTracing: true
  defaultConfig:
    tracing:
      sampling: 100.0
```

```bash
# Install using values.yaml file
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  -f values.yaml \
  --wait
```

## Istio Operator を使用したインストール

Istio Operator は Istio を宣言的に管理します。

### 1. Istio Operator のインストール

```bash
# Install Operator
istioctl operator init

# Verify Operator installation
kubectl get pods -n istio-operator
```

### 2. IstioOperator リソースの作成

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

### 3. Operator 経由での Istio のインストール

```bash
# Apply IstioOperator resource
kubectl create ns istio-system
kubectl apply -f istio-operator.yaml

# Check installation progress
kubectl get istiooperator -n istio-system
```

## インストールプロファイル

Istio はさまざまなユースケース向けに複数のプロファイルを提供します。

### 利用可能なプロファイル

| プロファイル | 説明 | コンポーネント | 推奨用途 |
|-------|------|----------|----------|
| **default** | 本番デプロイ用のデフォルト設定 | istiod、ingress gateway | ほとんどの本番環境 |
| **demo** | すべての機能を有効化、学習用 | istiod、ingress gateway、egress gateway、高い trace sampling | 開発・デモ |
| **minimal** | 最小限のコンポーネントのみをインストール | istiod のみ | リソース制約のある環境 |
| **remote** | マルチクラスター環境のリモートクラスター用 | - | マルチクラスター構成 |
| **empty** | デフォルト設定なし | - | 完全なカスタム構成 |
| **preview** | 実験的機能を含む | 各種の実験的機能 | テスト環境 |

### プロファイルの確認

```bash
# List available profiles
istioctl profile list

# Check specific profile configuration
istioctl profile dump default

# Compare two profiles
istioctl profile diff default demo
```

### プロファイルによるインストール

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### プロファイルのカスタマイズ

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set values.pilot.resources.requests.memory=2Gi \
  -y
```

## インストールの検証

### 1. Control Plane の確認

```bash
# Check all resources in istio-system namespace
kubectl get all -n istio-system

# Check istiod status
kubectl get deployment istiod -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. Istio バージョンの確認

```bash
# Control Plane version
istioctl version

# Or
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. Istio 設定の検証

```bash
# Check Istio installation status
istioctl verify-install

# Analyze Istio configuration
istioctl analyze -A
```

### 4. Webhook の確認

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## サンプルアプリケーションのデプロイ

Istio には Bookinfo というサンプルアプリケーションが含まれています。

### 1. Namespace の自動 Sidecar injection を有効化

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled

# Verify label
kubectl get namespace -L istio-injection
```

### 2. Bookinfo アプリケーションのデプロイ

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. アプリケーションアクセスの検証

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. Ingress Gateway の設定

```bash
# Create Bookinfo Gateway
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway

# Check VirtualService
kubectl get virtualservice
```

### 5. 外部アクセスの設定

```bash
# Get Ingress Gateway External IP
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')

export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# Access application
echo "http://$GATEWAY_URL/productpage"

# Access in browser or verify with curl
curl -s "http://$GATEWAY_URL/productpage" | grep -o "<title>.*</title>"
```

## Istio の削除

### istioctl を使用した削除

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Remove Istio
istioctl uninstall --purge -y

# Remove istio-system namespace
kubectl delete namespace istio-system

# Remove Istio label
kubectl label namespace default istio-injection-
```

### Helm を使用した削除

```bash
# Remove Ingress Gateway
helm delete istio-ingress -n istio-ingress

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-ingress
```

### Istio Operator を使用した削除

```bash
# Remove IstioOperator resource
kubectl delete istiooperator istio-control-plane -n istio-system

# Remove Operator
istioctl operator remove

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-operator
```

## トラブルシューティング

### よくある問題

#### 1. Sidecar 自動 injection の失敗

**症状**: Envoy sidecar が Pod に injection されない

**解決策**:
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod Pod が起動しない

**症状**: istiod Pod が Pending または CrashLoopBackOff 状態である

**解決策**:
```bash
# Check pod status
kubectl get pods -n istio-system

# Check pod events
kubectl describe pod -n istio-system -l app=istiod

# Check logs
kubectl logs -n istio-system -l app=istiod

# Check resources
kubectl top nodes
kubectl describe nodes
```

#### 3. Ingress Gateway が External IP を受信しない

**症状**: LoadBalancer タイプの Service が Pending 状態である

**解決策**:
```bash
# Check service status
kubectl get svc -n istio-system istio-ingressgateway

# Check AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check events
kubectl describe svc -n istio-system istio-ingressgateway
```

### デバッグツール

#### istioctl analyze

```bash
# Analyze entire cluster
istioctl analyze -A

# Analyze specific namespace
istioctl analyze -n default
```

#### istioctl proxy-status

```bash
# Check all proxy status
istioctl proxy-status

# Check specific pod proxy status
istioctl proxy-status <POD_NAME>.<NAMESPACE>
```

#### istioctl dashboard

```bash
# Launch Kiali dashboard
istioctl dashboard kiali

# Launch Grafana dashboard
istioctl dashboard grafana

# Launch Prometheus dashboard
istioctl dashboard prometheus

# Envoy admin interface
istioctl dashboard envoy <POD_NAME>.<NAMESPACE>
```

### ログ収集

```bash
# Control Plane logs
kubectl logs -n istio-system -l app=istiod

# Ingress Gateway logs
kubectl logs -n istio-system -l app=istio-ingressgateway

# Envoy logs for specific pod
kubectl logs <POD_NAME> -c istio-proxy

# Save all Istio-related logs to file
istioctl bug-report
```

## 次のステップ

Istio のインストールは完了です。次に、以下のドキュメントを参照して Istio の使用を開始してください。

1. **[基本概念](02-basic-concepts.md)**: Istio の中核概念とアーキテクチャを理解する
2. **[Traffic Management](traffic-management/README.md)**: Gateway、VirtualService、DestinationRule を学ぶ
3. **[Security](security/README.md)**: mTLS、認証、認可を設定する

## 参考資料

- [Istio 公式インストールガイド](https://istio.io/latest/docs/setup/install/)
- [Istio プロファイルドキュメント](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
- [Istio トラブルシューティングガイド](https://istio.io/latest/docs/ops/diagnostic-tools/)
