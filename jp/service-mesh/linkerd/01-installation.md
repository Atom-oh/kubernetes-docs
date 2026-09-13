# Linkerdのインストールと設定

> **最終更新**: September 11, 2026 · 公開CLI: edge-26.9.1 · 対応チャート: 2026.9.1

管理されたKubernetes導入、Helm/CLI所有権、HA、任意拡張、EKS、更新、削除を扱います。上流はedge成果物を公開し、stableディストリビューションの導入/サポートはベンダーごとです。2.20という節目は上流stable-2.20.0ダウンロードではありません。

PowerShell表記以外はBashを使います。意図したkubeconfig/contextと所有者を使用します。CLIとHelmは**代替手順**で、Helm所有リリースへCLI生成リソースを適用しないでください。オフライン確認では本番サイズ、ストレージ、ネットワーク適用、アプリ互換性は成立しません。

## 前提条件

### KubernetesとGateway API

| 系列/版 | Kubernetesの根拠 | Gateway APIの根拠 |
|---|---|---|
| Linkerd 2.20の節目/ディストリビューション | 公表表1.31–1.35。ベンダー対応を確認 | 公表表1.2.1–1.5.1 |
| ここでの公開edge-26.9.1 | CLI最小1.31.0。edge-26.8.2でテスト最大1.36へ引き上げ | 1.5.1対応をリリース。このガイドはStandardバンドル |
| 過去の2.16 | 公表表1.22–1.29 | 現在の導入推奨ではない |
| 過去の2.15 / 2.14 | 公表範囲1.22–1.29 / 1.21–1.28 | 対応リリースを確認。「以降すべてのKubernetes」対応と推測しない |

CLIの最小版チェックは最大対応チェックではありません。check --pre成功は新Kubernetes/Gateway API互換性の証明ではありません。EKSでは提供版とサポート期間も確認します。監査のHelm検証はKubernetes 1.35 capabilityを使いました。

### 容量とプラットフォーム

一律100m CPU/200Miという主張で制御全体をサイジングしないでください。controller、policy container、proxy、init、拡張のレンダリング済みrequests/limitsを確認し、実通信/接続負荷を測ります。HAは必須node anti-affinityのため最低3適格ノードと更新中の余裕が必要です。ゾーン分散は希望で、異なる3ゾーン保証ではありません。

説明はLinux Kubernetesノードが対象です。Windows CLIダウンロードはWindowsワークロード対応の証明ではありません。選択版のworkload/platform対応は別確認です。Cilium kube-proxy置換ではsocketLB.hostNamespaceOnly、Linkerd CNIチェイニングでは他プラグインを許すcni.exclusiveを確認します。

### ネットワーク経路と事前確認

全場所に開くポート一覧でなく、送信元/宛先経路を検証します。

| 経路 | 固定レンダリングのデフォルト例 |
|---|---|
| API server → admission | Service 443 → injector/SP-validator 8443、policy-validator 9443 |
| Proxy → control plane | Identity 8080、destination 8086、policy 8090 |
| メッシュアプリ通信 | Proxy inbound 4143と実アプリ/Service経路 |
| Viz（導入時） | Tap API server 8089、tap gRPC 8088、metrics API 8085、Prometheus 9090 |
| 診断 | Proxy metrics 4191、web UI 8084、別web admin/readiness 9994 |

コンポーネントのポートで、無制限SGルール群ではありません。DNS、Kubernetes API、選択CNI/NetworkPolicy動作も含めます。実Service targetPortsとWebhook設定を確認します。

```bash
LINKERD_CHART_VERSION=2026.9.1
CNI_ENABLED=false  # Set true only after installing/verifying Linkerd CNI.
kubectl config current-context
kubectl version
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,topology.kubernetes.io/zone
kubectl get crd httproutes.gateway.networking.k8s.io \
  -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
# For a new lab without a conflicting installed bundle, after ownership review:
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
linkerd check --pre --linkerd-cni-enabled="$CNI_ENABLED"
```

既存CRD所有権と全利用controller確認後、必要な場合だけGateway APIバンドルを適用します。Linkerd CNI選択時は制御前に導入/確認し、後述CNI対応チェックを使います。実出力と終了コードを読みます。旧例の長い「全部緑」出力はあなたのクラスター結果ではありません。

## Linkerd CLIのインストール

### 固定Linux/macOSバイナリ

正確な公開assetを選び、公式release metadataのSHA256と比較します。PATH変更は現在のシェルだけです。

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.9.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=094e1de06215fbe76fc011cf62c96214f8dae0cd5a58135fb40307be88b6b176 ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=f92eddc52dc1f3089b65fd16014cdb1bc6b07c3fd177091c365cf3d8c0ea1a8b ;;
  Darwin/x86_64) suffix=darwin; expected=acff9471f26552dd0ebb9560925a98d5ca1213a13dfc81464a2b815c9201664d ;;
  Darwin/arm64) suffix=darwin-arm64; expected=5050da9d974e0c2f548a2e9f145540ec035582cfd67f47c58c37411ae3008913 ;;
  *) echo "No verified asset for this OS/architecture in this example" >&2; exit 1 ;;
esac
CLI_DIR="$PWD/linkerd-cli/$LINKERD_VERSION"
mkdir -p "$CLI_DIR"
curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/linkerd/linkerd2/releases/download/$LINKERD_VERSION/linkerd2-cli-$LINKERD_VERSION-$suffix" \
  -o "$CLI_DIR/linkerd.download"
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$CLI_DIR/linkerd.download" | awk '{print $1}')
else
  actual=$(shasum -a 256 "$CLI_DIR/linkerd.download" | awk '{print $1}')
fi
test "$actual" = "$expected"
chmod 755 "$CLI_DIR/linkerd.download"
mv "$CLI_DIR/linkerd.download" "$CLI_DIR/linkerd"
export PATH="$CLI_DIR:$PATH"
linkerd version --client
```

列挙assetはLinux amd64/arm64、macOS Intel/Apple Siliconです。installerの汎用ARM分岐から32ビットARM公開を推測しないでください。監査ではネイティブLinux arm64 CLIを実行し、他platformは公式metadataで確認しました。

### 公式installerという代替

旧run.linkerd.io/installは非推奨で、stableでなくedgeを導入します。現installerは環境変数LINKERD2_VERSIONを受け取ります。旧sh --version stable-2.16.0は対応上流stableを選択しません。

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.9.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

互換表からGateway APIバンドルを選びます。installer完了メッセージには独自例の版がありますが、本ガイドは選択release確認後1.5.1に固定します。パッケージ管理/ベンダー版は別版を選び得ます。Homebrew/Chocolateyだからここの固定版と考えず、出所と版を検証します。シェルprofile編集は不要です。

### Windowsバイナリ

release asset名はwindows-amd64.exeでなくwindows.exeです。

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.9.1"
$ExpectedSha256 = "d50119c635a0052bfcc7e0b96dcc985676b237ebc87464380677c413344d99a9"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

残りのBash例には設定済みWSLなど適切なシェルか、ネイティブPowerShellへの変換が必要です。監査ではPowerShell実行やWindows workloadテストはしていません。

## コントロールプレーンのインストール

### CLIによる導入

新しいCLI所有導入では、制御の生成/導入前にLinkerd CRDを適用します。

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

コマンドはマニフェストを生成し、kubectlが導入します。CLI生成のデフォルトtrust anchor/issuer認証情報は有限の寿命を持ち、rotation計画が必要です。共有信頼multiclusterでは各clusterで別rootを生成せず、意図的に供給した認証情報が必要です。

### Helmによる導入

Helmは反復可能なrelease/values手順を提供します。チャート版はCLIタグと別に固定します。

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

対応公開チャートはlinkerd-crds、linkerd-control-plane、linkerd-viz、linkerd-multicluster、linkerd2-cniの2026.9.1です。現core appVersionはedge-26.9.1です。未固定の古いstableリポジトリチャートを入れ、CLIに合うと想定しないでください。

#### Trust anchorとissuer

Helmにはtrust anchor証明書とissuer証明書/秘密鍵、または意図的に設定した対応外部issuer-secret統合が必要です。root CA秘密鍵のアップロードは不要です。

導入済み[Smallstep CLI](https://smallstep.com/docs/step-cli/installation/)と公開certificate-createインターフェースを使います。このECDSA P-256例は元のデモ寿命を保持し、--not-after後の壊れた継続を修正します。

```bash
umask 077
mkdir linkerd-pki
(
  cd linkerd-pki
  # Demonstration lifetimes, not a universal certificate policy.
  step certificate create root.linkerd.cluster.local ca.crt ca.key \
    --profile root-ca --kty EC --curve P-256 \
    --not-after 87600h --no-password --insecure
  step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
    --profile intermediate-ca --kty EC --curve P-256 \
    --not-after 8760h --no-password --insecure \
    --ca ca.crt --ca-key ca.key
  openssl verify -CAfile ca.crt issuer.crt
  openssl x509 -in issuer.crt -noout -text
)
```

導入前にchain、algorithm、期限を確認します。root秘密鍵はKubernetes外に置き、以下には公開trust anchorとissuer署名認証情報だけを渡します。--no-password/--insecureは暗号化なしローカル鍵を作るため、例は制限directory/umaskを使います。本番PKIには承認済み鍵保存/rotation処理が必要です。監査は公式文書でフラグを確認し、Smallstep証明書生成は実行していません。

#### カスタムvalues

linkerd-values.yamlとして保存します。サイジング例で、workload保証ではありません。

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
  logLevel: warn,linkerd=info
  logFormat: plain
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s
controllerResources: &id001
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi
destinationResources: *id001
identityResources: *id001
proxyInjectorResources: *id001
```

実際のネストキーはproxy.logLevelとproxy.logFormatです。destinationResources、identityResources、proxyInjectorResourcesは基本valuesにすべて載らなくても対応しており、同梱HAとtemplateが使います。旧namespace.labels mapと最上位proxyLogLevel/proxyLogFormatは消費されませんでした。チャートはデフォルトで設定proxy log selectorにヘッダー/要求ログ抑制規則を追加します。最終環境値を確認します。

```bash
helm install linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --create-namespace --wait

helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  > linkerd-rendered.yaml
# Review the render, then install through Helm (do not apply the render as another owner).
helm install linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  --wait --timeout 10m
linkerd check
```

生成マニフェストとHelm valuesバックアップにはissuer秘密鍵が含まれ得ます。制限して保存し、診断レポートへ貼らないでください。後の更新も同じrelease/認証情報所有者を維持します。

## 高可用性（HA）インストール

固定チャート同梱のvalues-ha.yamlを使います。

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

Helmではrenderとinstallの両方でカスタムvaluesの**前に**HAファイルを使います。後の上書きが必要HAを無効にしないか確認します。

同梱profileは主要コンポーネント3レプリカ、必須node分離、希望zone分離、PDB、Fail admission-webhookを有効にします。冗長な提供インスタンスで、3メンバー合意クォーラムではありません。可用性はAPI server/ネットワーク、認証情報、容量、アプリにも依存します。

旧手書きdestination.replicas/identity.resources/proxyInjector.resourcesでは対象containerを設定できませんでした。root podDisruptionBudget mapではPDBが作られず、root topologySpreadConstraintsも消費されません。旧例のオフラインrenderは3レプリカでしたがcontroller resource不足、PDBなしでした。実同梱profileを使い結果を確認します。

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

適格ノード3未満なら必須anti-affinityでPendingになる場合があります。HAに依存する前にadmission Fail動作と中断を確認します。汎用可用性修正としてWebhookポリシーを弱めないでください。


## 拡張のインストール

### Viz: ダッシュボードとメトリクス

CLI所有拡張では次を使います。

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Helmではviz-values.yamlとして保存し、renderされたPVC、Deployment、resource設定を確認します。

```yaml
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
    storageClass: gp3
    size: 10Gi
    accessMode: ReadWriteOnce
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi
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
helm install linkerd-viz linkerd-edge/linkerd-viz \
  --version "$LINKERD_CHART_VERSION" -n linkerd-viz --create-namespace \
  -f viz-values.yaml --wait --timeout 10m
linkerd viz check
```

選択チャートはpersistenceの**mapが存在する**と永続化をサポートします。persistence.enabledはスイッチではありません。PVC templateはaccessMode必須で、旧例は省略してnullをrenderしていました。map省略はemptyDirです。gp3 StorageClassは前提例でVizが作るものではありません。EKSではEBS CSI、権限、volume topologyを確認します。

同梱Prometheusは1レプリカで、永続化はRecreate戦略を選びます。PVCは適切なPod置換をまたいで保存しますが、保存HAや無停止保証にはなりません。2026.9.1はPrometheus v2.55.1と6時間保持がデフォルトです。保守、保持、可用性要件を明示選択します。

設定済み外部Prometheusには、この**代替**valuesを使います。

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

切り替え前に外部サーバーのLinkerd scrape/relabelとアクセスを設定します。HTTP-readyだけでなく実Vizクエリ/メトリクスを検証します。dashboard、tap、metricsAPI resource設定は対応しています。grafana.enabledは導入スイッチではなく、別管理Grafanaへのリンク設定を提供します。

初期手順はlocalhost dashboardを使います。dashboard.enforcedHostRegexpはHost値検証でユーザー認証ではありません。空値はチャートのデフォルトhost制限を選びます。組織Ingressには別認証/認可、承認された公開範囲、許可hostが必要です。

### 分散トレーシング

edge-26.9.1にlinkerd jaegerサブコマンドはありません。公開linkerd-jaegerチャート履歴は2025.9.4で止まり、2026.9.1対応拡張ではありません。旧install/check/upgrade/uninstallを別管理collector/backendと選択proxy tracing設定へ置き換えます。

トレースには受信コンテキスト、アプリ伝播、互換collector/exportプロトコルが必要です。Vizトポロジー/メトリクスグラフは分散トレースではありません。完全経路は[可観測性ガイド](05-observability.md)と[公式トレース文書](https://linkerd.io/docs/features/distributed-tracing/)を参照します。この監査は未テストcollector/Jaegerのend-to-end動作を主張しません。旧linkerd-jaeger releaseがあるならデータを棚卸し・移行し、元の所有者で廃止します。現CLIは削除拡張を管理できません。

### マルチクラスター

CLIで基本拡張をrenderできます。

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

適用前にネットワークに合うGateway公開を選びます。拡張だけではclusterリンク、共有信頼、remote Kubernetes APIアクセスは作られません。

**AWS Load Balancer Controller**を使うEKS例は内部NLBを選び、Linkerd GatewayまでTCPを保持します。

```yaml
gateway:
  replicas: 1
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access-default
```

multicluster-values.yamlとして保存し、Helmの代替を使います。

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClassは対象controllerを選びます。Auto Modeは別class/設定契約なので混同せず、既存Service所有権を安易に変えないでください。remote側から内部Gatewayとprobe経路へ解決/到達できる必要があります。無関係なACM listenerでLinkerd転送mTLSを終端しないでください。

gateway.resourcesは固定チャートに消費されません。proxyリソースは注入設定由来です。無視されるvaluesでlimitが変わると思わず実Podを確認します。同梱HA上書きはgateway.replicasとanti-affinityを使います。

現edgeのremote認証情報はexec auth providerを拒否します。[マルチクラスターガイド](06-multi-cluster.md)の対応フローを使い、service-mirror controller/版と最小権限APIアクセスを検証します。

## CNIとAmazon EKS設定

### 任意のLinkerd CNI

Linkerd CNIは主CNIに連結し、Amazon VPC CNIやCiliumを置き換えません。control planeとメッシュworkloadがCNI有効設定を使う**前に**対象ノードで準備完了する必要があります。

```bash
# Optional branch, before control-plane installation.
helm install linkerd-cni linkerd-edge/linkerd2-cni \
  --version "$LINKERD_CHART_VERSION" -n linkerd-cni --create-namespace --wait
kubectl -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=180s
CNI_ENABLED=true
linkerd check --pre --linkerd-cni-enabled
# Use --linkerd-cni-enabled=true for CLI control-plane installation,
# or --set cniEnabled=true for the control-plane Helm chart.
```

ノードのCNI設定/バイナリdirectoryとplugin動作を確認します。デフォルトは/etc/cni/net.dと/opt/cni/binで、普遍的パスではありません。選択control-planeチャートはcniEnabledを消費し、renderでlinkerd-initが意図どおり省略される必要があります。

Linkerd CNIなしでは通常initリダイレクトにNET_ADMINが必要で、CNIありではノードpluginへ移ります。このreleaseはnative sidecarがデフォルトなので、診断時はcontainersとinitContainers両方を調べます。Identity Deploymentは意図的に通常proxyでstartup waitを無効にしており、注入失敗と分類しないでください。native無効化はinit network/startup順序を変えます。bypass UIDは汎用セキュリティ修正ではありません。

Cilium kube-proxy置換では、文書化されたsocketLB.hostNamespaceOnly=trueによりPod通信が検出用Serviceアドレスを保持します。Linkerd CNI連結にはcni.exclusive=falseも必要です。主CNI設定を盲目的に置換せず所有者とレビューします。

### 既存EKSクラスター

対応既存clusterを使い、Linkerd系列とEKS提供状況の両方で版を確認します。旧EKS 1.28作成コマンドは現在の案内として古いものです。Linux手順は互換EC2ノードを前提とします。Fargateは示すCNI DaemonSetを実行できず、交換可能な対象ではありません。

専用kubeconfigを準備する場合:

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

変更前に対象endpoint/contextを確認します。標準Linkerd controllerはKubernetes API認証情報を使い、linkerd-destinationがServiceを検出するだけならIAMロールは不要です。AWS API権限はLB Controller、EBS CSI、telemetry collectorなど実callerに、対応IRSA/Pod Identity設定で付与します。

### EKSダッシュボードとネットワーク

旧internet-facing ALB例は認証設計なしに管理dashboardを公開していました。組織の認証付きIngressを設定・テストするまでlocalhost管理を使います。

web Serviceの8084は有効です。別admin/readinessは9994で、その/readyにprobeがあります。UI listenerに同じhealth意味を想定しないでください。ALBではtarget health、SG、host検証、証明書所有権、認証を合わせます。TLS証明書だけでは利用者認証になりません。

SGとNetworkPolicyを実送受信ロールに限定します。component port表は診断情報で、proxy metrics/Webhookを全sourceに公開する依頼ではありません。実clusterでCNI起動、DNS、admission、identity、node間経路を検証します。

## インストールの検証

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

拡張チェックは導入済みだけ実行します。check --proxyはデータプレーン確認で「全拡張を含む」意味ではありません。業務ロジックは検証しません。

サンプルアプリは固定マニフェストを確認して適用し、選択名前空間だけに注入指定して対象workloadを再作成します。変更可能なemojivoto URLと全稼働Deploymentの再適用は再現可能入力ではありません。イメージ/architecture、Serviceポート、準備、実HTTP/TCP結果を確認します。

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

my-appを実名前空間/Deploymentに置換します。metrics/tap/topは設定拡張と対応プロトコルに依存し、全通信暗号化や全業務成功を証明しません。

## Linkerdアップグレード

### 更新計画

正確なtarget CLI/chartを選び、release note、互換性、対応skew、現healthを確認します。ここのtargetは全旧2.14/2.16から直接更新できる約束ではありません。必要中間更新とベンダー案内に従います。edgeタグはsemver保証ではありません。各所有者を通じ、CLI、CRD/control plane、導入拡張、最後にdata-plane proxyを更新します。

既存導入はcheckとcheck --proxyを使います。check --preは名前空間/設定前提を含む新規事前確認で、更新計画の代わりではありません。現信頼認証情報を保持し、更新前に削除CRD版を確認します。

### CLI所有の導入

```bash
# First install/verify the selected target CLI and review the supported upgrade path.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds > linkerd-crds-upgrade.yaml
kubectl apply -f linkerd-crds-upgrade.yaml
linkerd upgrade > linkerd-upgrade.yaml
# Review retained configuration and credentials before applying.
kubectl apply -f linkerd-upgrade.yaml
linkerd check
linkerd viz install > linkerd-viz-upgrade.yaml
kubectl apply -f linkerd-viz-upgrade.yaml
linkerd viz check
# Likewise review/install the selected multicluster extension if present.
linkerd prune > linkerd-obsolete.yaml
# Review ownership and contents before any kubectl delete -f linkerd-obsolete.yaml.
```

拡張更新のrenderはinstallコマンドで、viz upgradeではありません。helpが終了0でも親コマンドhelpの場合があります。コマンド一覧と生成内容を確認します。削除前にprune出力を確認します。multicluster controller更新には対応手順での再リンクが必要な場合があります。

### Helm所有の導入

```bash
umask 077
helm get values linkerd-control-plane -n linkerd > current-values.yaml
helm get manifest linkerd-control-plane -n linkerd > current-manifest.yaml
# Migrate intentional overrides to reviewed-values.yaml; preserve current trust credentials.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --wait
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd \
  --reset-values -f reviewed-values.yaml --wait --timeout 10m
# Upgrade each installed extension with its own reviewed values and pinned chart.
linkerd check
```

レビュー済みvaluesに意図したHA/CNIと**既存**trust/issuer設定か対応外部Secret参照を含めます。それらを保持しない--reset-valuesは動作変更/失敗を起こし得て、--reuse-valuesは古い設定を残し得ます。target defaultと上書きを比較し、通常更新の一環としてCAを再生成しないでください。

### データプレーン更新

可用性方針に従い、対象workloadを1つずつ更新します。

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

statは通信統計でproxyイメージ版一覧ではありません。上では通常/native両配置を確認します。関連skew案内と再作成後の実準備/通信を確認します。

## トラブルシューティング

### Admissionとリソース

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

注入失敗はCA bundle、Webhook選択/ネットワーク、設定拒否、Pod securityが原因になり、常にService接続とは限りません。Pendingはanti-affinity、Taint、volume、quota、resourceなどを反映します。limit/security変更前に実イベントを確認します。

### 証明書

デフォルトではtrust rootは**ConfigMap**、issuer署名鍵/証明書はSecretです。

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

デフォルトissuerはcrt.pem、kubernetes.io/tls統合はtls.crtを使います。全Secretが同じと想定せずschemeを確認します。カスタムtrustは保存所有者を変え得ます。全trust証明書、時刻/期限、issuer可用性、identityエラーを調べ、計画外root置換を避けます。

### コンポーネントとプロキシのログ

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

導入版の実component/container名を使います。Pod削除/置換前に関連ログを保持します。

## アンインストール

### 先にアプリプロキシを除去

メッシュ転送ポリシー、経路、観測の喪失を計画します。所有者を通じて注入元と手動proxy設定を除去し、workloadを再作成、control plane除去前に両container配置を確認します。

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

namespaceアノテーション除去だけではPodテンプレート指定を上書きせず、手動proxyも除去しません。メッシュ離脱後のアプリ接続/セキュリティを検証します。残る注入workloadをforceで迂回しないでください。

### CLI所有の削除

```bash
# Only after applications are unmeshed and extension dependencies are removed.
linkerd viz uninstall > remove-viz.yaml
linkerd multicluster uninstall > remove-multicluster.yaml
# Inspect each manifest and remove only the extensions actually installed via CLI.
kubectl delete -f remove-viz.yaml
kubectl delete -f remove-multicluster.yaml
linkerd uninstall > remove-linkerd.yaml
# This includes namespace-scoped resources and cluster-wide CRDs.
kubectl delete -f remove-linkerd.yaml
```

導入拡張だけを除去します。生成control-plane削除はCRDも含み、削除するとCRインスタンスも消えます。保持すべきものを棚卸し・バックアップします。単なるDeployment削除ではありません。

### Helm所有の削除

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

Linkerd CNIを入れた場合は依存workloadがなくなってから別途node-plugin cleanupに従い、主CNIが無傷か確認します。名前空間は所有権と残存内容を確認後にだけ削除し、4名前空間を無条件に片付けないでください。

## 次のステップ

- [アーキテクチャ](02-architecture.md)
- [トラフィック管理](03-traffic-management.md)
- [セキュリティと証明書ライフサイクル](04-security.md)
- [可観測性](05-observability.md)
- [マルチクラスター](06-multi-cluster.md)
- [インストールクイズ](../../quizzes/service-mesh/linkerd/installation.md)

## 参考資料

- [リリースモデル](https://linkerd.io/releases/)と[edge-26.9.1成果物](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)
- [Kubernetes対応表](https://linkerd.io/docs/reference/k8s-versions/)と[Gateway API互換性](https://linkerd.io/docs/features/gateway-api/)
- [Helm導入](https://linkerd.io/docs/tasks/install-helm/)と[公式edgeチャート索引](https://helm.linkerd.io/edge/index.yaml)
- [HA動作](https://linkerd.io/docs/features/ha/)と[cluster/Cilium設定](https://linkerd.io/docs/reference/cluster-configuration/)
- [証明書生成](https://linkerd.io/docs/tasks/generate-certificates/)と[Smallstep create参照](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/)、[更新](https://linkerd.io/docs/tasks/upgrade/)、[削除](https://linkerd.io/docs/tasks/uninstall/)
- [AWS LB ControllerのService設定](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)と[EKS Fargate制約](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
