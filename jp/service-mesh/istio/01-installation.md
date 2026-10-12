# Istio のインストールと初期設定

> **最終更新**: October 12, 2026 · Install pin: Istio 1.31.1

2026 年 10 月 12 日時点で、Istio 1.31.1 は現在の 1.31 パッチであり、`BackendTLSPolicy` の平文フォールバックを修正しています。以下の Helm コマンド例は 1.31.0 から更新されています。この以前のチャートレンダリングはすべての 1.31.1 値の検証ではないため、適用前に選択したチャートをレンダリングして確認してください。

このドキュメントでは、Amazon EKS クラスターに Istio をインストールし、初期設定する方法を説明します。

## 目次

1. [前提条件](#prerequisites)
2. [インストール方法の選択](#choosing-an-installation-method)
3. [istioctl を使用したインストール](#installation-using-istioctl)
4. [Helm を使用したインストール](#installation-using-helm)
5. [istioctl を使用した宣言的インストール](#declarative-installation-with-istioctl)
6. [インストールプロファイル](#installation-profiles)
7. [インストールの検証](#installation-verification)
8. [サンプルアプリケーションのデプロイ](#sample-application-deployment)
9. [Istio の削除](#istio-removal)
10. [トラブルシューティング](#troubleshooting)

## 前提条件

Istio をインストールする前に、以下の要件を満たす必要があります。

### 1. Amazon EKS クラスター

- **Kubernetes バージョン**: この Istio 1.31.1 の例では EKS 1.34～1.37（2026 年 10 月 12 日レビュー）。Istio 1.31 は 1.32～1.37 をサポートします。EKS 1.31～1.33 は延長サポート、1.34～1.37 は標準サポートです。[Istio マトリックス](https://istio.io/latest/docs/releases/supported-releases/)と [EKS ライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)の両方を確認してください。
- **Node タイプ**: 最低 2 台の worker node（推奨: 3 台以上）
- **Node サイズ**: 最低 2 vCPU、4GB RAM（推奨: t3.medium 以上）

これらの例は Linux EC2 worker node を対象としています。Fargate では、これらの Istio インストールパスで必要な DaemonSet/特権ネットワークを実行できません。EKS Auto Mode は異なるマネージドネットワーキング/ロードバランシングモデルを使用するため、前提条件を個別に検証してください。

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
- **Helm**: 現在サポートされている Helm 3 または Helm 4 リリース（最低 3.6。公式インストールガイドを参照）

### 4. クラスターリソース

以下は普遍的な最小値ではなく、計画例です。測定した負荷に基づいてサイズを決めてください。
- **Control Plane**: 1 vCPU、1.5GB RAM
- **Sidecar（Pod ごと）**: 0.1 vCPU、128MB RAM

## インストール方法の選択

サポート対象のインストールパスを 1 つ選択してください。同じ Control Plane で istioctl と Helm のインストールを併用しないでください。

| 方法 | 利点 | 欠点 | 推奨ユースケース |
|------|------|------|---------------|
| **istioctl** | シンプルで高速、検証機能を提供 | 自動化では明示的なリコンシリエーションが必要 | 開発および本番環境 |
| **Helm** | GitOps に適しており、バージョン管理が容易 | 設定が複雑になる場合がある | 本番環境、CI/CD パイプライン |

## istioctl を使用したインストール

istioctl は Istio の公式 CLI ツールであり、最も簡単なインストール方法です。

### 1. istioctl をインストールする

```bash
# Download the current 1.31 patch
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.1 sh -

# Add istioctl to PATH
cd istio-1.31.1
export PATH=$PWD/bin:$PATH

# Verify installation
istioctl version
```

### 2. インストール前のクラスター検証

```bash
# Verify cluster meets Istio installation requirements
istioctl x precheck
```

### 3. Istio をインストールする

```bash
# Install with default profile
istioctl install --set profile=default -y

# Check installation progress
kubectl get pods -n istio-system
```

### 4. インストールを検証する

```bash
# Check Istio components
kubectl get all -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod
```

## Helm を使用したインストール

前回のレビューでレンダリングされた 1.31.0 チャートには、`eks` プラットフォームプロファイルが含まれていませんでした。以下のチャート例は現在 1.31.1 に固定されていますが、このレビューではそのパッチのチャートをレンダリングしていません。インストール前に選択したチャートを確認してください。これらの例では、プロファイルが存在すると仮定するのではなく `global.platform=eks` を省略し、明示的な EKS 前提条件とロードバランサー設定を使用しています。

Helm は GitOps ワークフローに適した Kubernetes パッケージマネージャーです。

### 1. Helm リポジトリを追加する

```bash
# Add Istio Helm repository
helm repo add istio https://blob.istio.io/istio-release/charts
helm repo update
```

### 2. istio-base をインストールする

istio-base は Istio の CRD（Custom Resource Definition）をインストールします。

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --set defaultRevision=default \
  --version 1.31.1
```

### 3. istiod をインストールする

istiod は Istio Control Plane です。

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.1 \
  --wait
```

### 4. Istio Ingress Gateway をインストールする（任意）

```bash
# Verify the gateway namespace
kubectl get namespace istio-system

# Install Istio Ingress Gateway
helm install istio-ingressgateway istio/gateway \
  -n istio-system \
  --set labels.istio=ingressgateway \
  --set labels.app=istio-ingressgateway \
  --version 1.31.1 \
  --wait
```

### 5. values.yaml を使用したカスタムインストール

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.1

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
# Install using values.yaml file
helm upgrade --install istiod istio/istiod \
  -n istio-system \
  --version 1.31.1 \
  -f values.yaml \
  --wait
```

## istioctl を使用した宣言的インストール

アップストリームのクラスター内 operator は 1.23 で非推奨となり、1.24 で削除されました。`istioctl operator init/remove` および IstioOperator オブジェクトをクラスターに適用する方法は、現在のインストール方法ではありません。[IstioOperator ファイル形式は、istioctl への入力として引き続きサポートされています](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/)。

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

## インストールプロファイル

Istio は用途に応じたさまざまなプロファイルを提供します。

### 利用可能なプロファイル

| プロファイル | 説明 | コンポーネント | 推奨用途 |
|-------|------|----------|----------|
| **default** | 本番デプロイ用のデフォルト設定 | istiod、ingress gateway | ほとんどの本番環境 |
| **demo** | デモ用設定、すべての機能を含むわけではない | istiod、ingress gateway、egress gateway、高い trace サンプリング | 開発およびデモ |
| **minimal** | 最小限のコンポーネントのみをインストール | istiod のみ | リソースに制約のある環境 |
| **remote** | マルチクラスター環境のリモートクラスター用 | - | マルチクラスターのセットアップ |
| **empty** | デフォルト設定なし | - | 完全なカスタムセットアップ |
| **preview** | 実験的機能を含む | さまざまな実験的機能 | テスト環境 |
| **ambient** | Sidecar を使用しない L4 メッシュ | istiod、CNI、ztunnel、L7 waypoint は別途設定 | Ambient デプロイ |

コンポーネントリストは istioctl に適用されます。Helm では各チャートを個別にインストールする必要があります。プロファイルによって他のチャートがインストールされるわけではありません。

### プロファイルを確認する

```bash
helm show values istio/istiod --version 1.31.1
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
```

### プロファイル別のインストール

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
  --set components.pilot.k8s.resources.requests.memory=2Gi \
  -y
```

## インストールの検証

### 1. Control Plane を確認する

```bash
# Check all resources in istio-system namespace
kubectl get all -n istio-system

# Check istiod status
kubectl get deployment istiod -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. Istio バージョンを確認する

```bash
# Control Plane version
istioctl version

# Or
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. Istio 設定を検証する

```bash
# Check Istio installation status
kubectl rollout status deployment/istiod -n istio-system
istioctl proxy-status

# Analyze Istio configuration
istioctl analyze -A
```

### 4. Webhook を確認する

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## サンプルアプリケーションのデプロイ

Istio には Bookinfo というサンプルアプリケーションが含まれています。

デフォルト namespace を選択した状態で、展開した `istio-1.31.1` ディレクトリからこれらのコマンドを実行してください（`kubectl config set-context --current --namespace=default`）。Helm の場合は、最初に上記の任意の gateway をインストールしてください。後述の dashboard コマンドでは、別途インストールした telemetry addon が必要です。

### 1. Namespace の自動 Sidecar Injection を有効にする

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled --overwrite

# Verify label
kubectl get namespace -L istio-injection
```

injection label を変更した後、既存の Pod は再作成する必要があります。競合する `istio.io/rev` または ambient label がない namespace を使用してください。

### 2. Bookinfo アプリケーションをデプロイする

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. アプリケーションアクセスを検証する

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. Ingress Gateway を設定する

```bash
# Create Bookinfo Gateway
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

# Check Gateway
kubectl get gateway.networking.istio.io

# Check VirtualService
kubectl get virtualservice
```

### 5. 外部アクセスを設定する

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

これらのクリーンアップコマンドは使い捨てのラボ向けです。purge は共有メッシュリソースを削除します。本番稼働中のメッシュをアンインストールする前に、injection された workload を削除するか、injection なしで再起動してください。Helm のアンインストールでは CRD は保持されます。

### istioctl を使用した削除

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f bookinfo-gateway.yaml

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
helm delete istio-ingressgateway -n istio-system

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
```

## トラブルシューティング

### よくある問題

#### 1. Sidecar 自動 Injection の失敗

**症状**: Envoy Sidecar が Pod に injection されない

**解決策**:
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled --overwrite

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

#### 3. Ingress Gateway が外部 IP を受信しない

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

### ログの収集

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

1. **[基本概念](02-basic-concepts.md)**: Istio のコア概念とアーキテクチャを理解する
2. **[トラフィック管理](traffic-management/README.md)**: Gateway、VirtualService、DestinationRule を学ぶ
3. **[セキュリティ](security/README.md)**: mTLS、認証、認可を設定する

## 参考資料

- [Istio 公式インストールガイド](https://istio.io/latest/docs/setup/install/)
- [Istio プロファイルドキュメント](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [Istio EKS プラットフォームガイダンス](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Istio トラブルシューティングガイド](https://istio.io/latest/docs/ops/diagnostic-tools/)

- [EKS Fargate の制限](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Istio 1.31 リリースおよびアーティファクト移行](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
