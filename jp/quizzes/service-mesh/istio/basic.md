# 基本クイズ

> **レビュー対象バージョン**: Istio 1.31.0 **EKS バージョン**: 1.34～1.36 **最終更新**: 2026 年 9 月 11 日

このクイズでは、Istio の基本概念とアーキテクチャへの理解を確認します。

## 選択問題（1～5）

### 問題 1: Service Mesh の定義

Service Mesh に関する次の説明のうち、**正しくない**ものはどれですか？

A. マイクロサービス間の通信を処理するインフラストラクチャ層である\
B. アプリケーションコードを変更した場合にのみ使用できる\
C. Service 間のトラフィック制御と可観測性を提供する\
D. ネットワークレベルでセキュリティとポリシーを適用する

<details>

<summary>回答を表示</summary>

**回答: B**

Service Mesh の主な利点の一つは、**アプリケーションコードを変更せずに** Service 間の通信を制御し、可視化できることです。

**解説:**

* A (正): Service Mesh は、マイクロサービスアーキテクチャにおける Service 間通信を担う専用のインフラストラクチャ層です。
* B (誤): サイドカープロキシまたは Ambient Mode を使い、アプリケーションコードを変更せず透過的に適用できます。
* C (正): VirtualService や DestinationRule などでトラフィックを制御し、メトリクスを公開します。ログ／トレースには構成が必要で、アプリケーションがトレースコンテキストを伝播する必要があります。
* D (正): mTLS、Authorization Policy などによってネットワークレベルのセキュリティポリシーを適用します。

**参考:**

* [Istio のコア概念](../../../service-mesh/istio/02-basic-concepts.md)
* [Service Mesh とは](../../../service-mesh/istio/README.md)

</details>

***

### 問題 2: Istio アーキテクチャのコンポーネント

Istio の Control Plane で、サービスディスカバリー、構成管理、証明書管理を担う**集中管理コンポーネント**はどれですか？

A. Envoy\
B. Istiod\
C. Pilot\
D. Citadel

<details>

<summary>回答を表示</summary>

**回答: B**

**Istiod** は Istio 1.5 で導入された単一バイナリで、従来は分かれていた Pilot、Citadel、Galley の各コンポーネントを統合しています。

**解説:**

* A (誤): Envoy は各 Pod 内でサイドカーとして動作する Data Plane プロキシです。
* B (正): Istiod は Control Plane の中核で、次を担当します。
  * サービスディスカバリー
  * 構成管理
  * 証明書管理
* C (誤): Pilot は Istio 1.5 より前のバージョンにあったコンポーネントで、現在は Istiod に統合されています。
* D (誤): Citadel も Istio 1.5 より前のコンポーネントで、現在は Istiod に統合されています。

**Istiod の主な役割:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**参考:**

* [Istio のコンポーネント](../../../service-mesh/istio/03-architecture.md)
* [アーキテクチャの概要](../../../service-mesh/istio/README.md)

</details>

***

### 問題 3: Envoy プロキシの役割

Data Plane の Envoy プロキシが実行するタスクでは**ない**ものはどれですか？

A. トラフィックのルーティングとロードバランシング\
B. mTLS による暗号化と認証\
C. Kubernetes CRD の検証と保存\
D. メトリクス、ログ、トレースの収集

<details>

<summary>回答を表示</summary>

**回答: C**

Kubernetes API Server がリソースを保存し、スキーマを検証します。Istiod も Admission Webhook を通じて Istio 構成を検証します。Envoy が Kubernetes CRD を保存することはありません。

**解説:**

* A (正): Envoy は VirtualService のルールに従ってトラフィックをルーティングし、ロードバランシングします。
* B (正): Envoy は Service 間通信を mTLS で自動的に暗号化し、証明書を検証します。
* C (誤): CRD の検証と保存は Kubernetes API Server と Istiod の役割です。
* D (正): 構成されたログ記録やトレースサンプリングに応じて、Envoy はメトリクス（Prometheus）、ログ（Access Log）、トレース（Jaeger）を収集します。

**参考:**

* [Data Plane の構造](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### 問題 4: Istio のインストールプロファイル

Amazon EKS の本番環境で Istio をインストールするとき、推奨されるプロファイルはどれですか？

A. default\
B. demo\
C. minimal\
D. production

<details>

<summary>回答を表示</summary>

**回答: A**

このガイドにおけるサイドカーインストールでは、`default` が本番構成の出発点です。組み込みの `production` プロファイルはありません。レプリカ数、リソース要求、配置、PDB、セキュリティポリシーは明示的に設定してください。`default` を選ぶだけで高可用性になるわけではありません。

| プロファイル | 用途 |
| --- | --- |
| default | 本番構成の出発点。ワークロードに合わせて調整する |
| demo | デモ用。テレメトリが詳細で、性能試験には向かない |
| minimal | Control Plane のみ |
| production | 組み込みプロファイルではない |

```bash
istioctl install --set profile=default
```

**本番環境のチェックリスト:**

* ✅ Control Plane の高可用性（レプリカ数 3 以上）
* ✅ mTLS STRICT モード
* ✅ PodDisruptionBudget の設定
* ✅ リソース上限と HPA の設定
* ✅ 監視スタックの準備

**参考:**

* [インストールガイド](../../../service-mesh/istio/01-installation.md)
* [ベストプラクティス](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### 問題 5: Istio CRD（Custom Resource Definition）

次のうち、Istio の**トラフィック管理用 CRD ではない**ものはどれですか？

A. VirtualService\
B. DestinationRule\
C. PeerAuthentication\
D. Gateway

<details>

<summary>回答を表示</summary>

**回答: C**

**PeerAuthentication** はセキュリティ関連の CRD です。

**解説:**

**Istio CRD の分類:**

**1. トラフィック管理:**

* VirtualService: ルーティングルールを定義
* DestinationRule: ロードバランシングと Subset の定義
* Gateway: 外部トラフィックの入口
* ServiceEntry: 外部 Service の定義
* Sidecar: Envoy の構成対象範囲を制限

**2. セキュリティ:**

* PeerAuthentication: Service 間認証（mTLS）
* RequestAuthentication: エンドユーザー認証（JWT）
* AuthorizationPolicy: アクセス制御

**3. 可観測性:**

* Telemetry: メトリクス、ログ、トレースの構成

**例:**

```yaml
# Traffic Management
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
# Security
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**参考:**

* [トラフィック管理](../../../service-mesh/istio/traffic-management/README.md)
* [セキュリティ](../../../service-mesh/istio/security/README.md)

</details>

***

## 記述問題（6～10）

### 問題 6: サイドカー注入の仕組み

Istio で Envoy サイドカーを Pod に自動注入する 2 つの方法を説明し、それぞれの長所と短所を比較してください。

<details>

<summary>回答を表示</summary>

**回答:**

Istio は次の 2 つの方法でサイドカーを自動注入します。

**1. Namespace 単位の自動注入:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**長所:**

* Namespace 全体へ一度に適用できる
* 管理しやすい
* 意図しない注入漏れが起きにくい

**短所:**

* Namespace 内のすべての Pod に適用される（対象外にする Pod は個別に除外が必要）
* 既存の Pod は再起動が必要

**2. Pod 単位の選択的注入:**

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
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**長所:**

* 特定の Pod だけを選んで注入できる
* きめ細かく制御できる
* Namespace のラベル付けは不要

**短所:**

* Deployment ごとに構成が必要
* 管理箇所が増える
* 意図しない注入漏れが起きる可能性がある

**比較表:**

| 項目 | Namespace 単位 | Pod 単位 |
| --- | --- | --- |
| 対象範囲 | Namespace 全体 | 個々の Pod |
| 管理の複雑さ | 低い | 高い |
| 選択性 | 低い（除外設定が必要） | 高い |
| 推奨用途 | 本番環境 | 構成が混在する環境 |

**本番環境での推奨:**

* 既定では Namespace 単位の注入を使う
* 除外が必要な Pod にだけ `sidecar.istio.io/inject: "false"` を設定する

**参考:**

* [サイドカー注入](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### 問題 7: Istio のリソース使用量の最適化

Istio を 1,000 Pod の大規模な Kubernetes クラスターで使用する場合、Sidecar Mode と Ambient Mode の**想定リソース使用量**を計算し、比較してください。（ztunnel は 10 ノード、waypoint は 1 つとします。）

<details>

<summary>回答を表示</summary>

**回答:**

以下は算術演習のために設定した仮定値であり、Istio の実測要件やサイジング推奨値ではありません。MB/GB はすべて十進単位として計算します。サイドカー 1 個あたり 0.1 vCPU、ztunnel 1 個あたり 0.1 vCPU、waypoint 1 個あたり 0.5 vCPU と仮定します。

**前提:**

* Pod 数: 1,000
* ノード数: 10
* サイドカーのメモリ: Pod あたり 50 MB
* ztunnel のメモリ: ノードあたり 50 MB
* waypoint のメモリ: 200 MB

**1. Sidecar Mode のリソース使用量:**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Ambient Mode のリソース使用量:**

```
Memory Usage = (Number of Nodes × ztunnel Memory) + waypoint Memory
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU Usage = (Number of Nodes × ztunnel CPU) + waypoint CPU
          = (10 × 0.1 vCPU) + 0.5 vCPU
          = 1.5 vCPU
```

**3. 比較と削減量:**

| 項目 | Sidecar Mode | Ambient Mode | 削減量 | 削減率 |
| --- | --- | --- | --- | --- |
| **メモリ** | 50 GB | 0.7 GB | 49.3 GB | **98.6%** |
| **CPU** | 100 vCPU | 1.5 vCPU | 98.5 vCPU | **98.5%** |

**解釈:**

この仮定では、プロキシ合計のメモリが 98.6%、CPU が 98.5% 減少します。この数値は AWS 請求額が 96% 減ることや、1,000 Pod の 10 ノードクラスターが 1 台のインスタンスで稼働できることを意味しません。アプリケーションのリソース、Pod／IP 上限、高可用性、レプリカ数、スループット、waypoint の容量は計算に含めていません。サイジングやコスト試算の前に実際のトポロジーをベンチマークしてください。Ambient の主要機能は Istio 1.24 から GA です。

**参考:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [コスト最適化](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### 問題 8: mTLS の動作

Istio で Service A と Service B が通信するときの mTLS の仕組みを順を追って説明してください。Istiod、Envoy、証明書の役割も含めてください。

<details>

<summary>回答を表示</summary>

**回答:**

**mTLS（Mutual TLS）の処理:**

**ステップ 1: 証明書の発行（初期化）**

* Pod の起動時に Istio agent が秘密鍵と CSR を作成し、ワークロード認証情報で Istiod に認証します。Envoy はローカル agent から SDS 経由で証明書と鍵を受け取ります。
* Istiod は Service Account を検証して X.509 証明書を発行します。
* 証明書には Service Account ID（例: `cluster.local/ns/default/sa/service-a`）が含まれます。
* 証明書の有効期間は既定で 24 時間で、自動更新されます。

**ステップ 2: Service 間通信（mTLS ハンドシェイク）**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**詳細な処理:**

```text
1. The source app sends HTTP; configured redirection sends it through Envoy A.
2. Auto mTLS/DestinationRule determines outbound TLS; destination PeerAuthentication
   determines whether Envoy B requires inbound mTLS.
3. ClientHello and ServerHello negotiate TLS parameters/key exchange.
   Certificates are sent in Certificate messages, not in ClientHello/ServerHello.
   The server requests the client certificate; each peer validates the other
   certificate and proof of key possession against the configured trust chain.
4. Envoy B applies authorization and forwards the decrypted request to Service B.
5. The response travels over the established TLS connection.
```

**各コンポーネントの役割:**

**Istiod:**

* 認証局（CA）として機能します（外部ルート CA の下に中間 CA を置く場合があります）。
* Service Account に基づいて証明書を発行します。
* 証明書の期限前に更新要求へ署名します。有効期間は構成可能です。
* PeerAuthentication ポリシーを配布します。

**Envoy サイドカー:**

* SDS 経由で Istio agent から証明書を受け取ります。
* TLS ハンドシェイクを実行します。
* トラフィックを暗号化／復号します。
* 証明書を検証します。

**証明書:**

* X.509 形式
* Subject Alternative Name（SAN）: Service Account URI
* 有効期間: 既定で 24 時間
* 自動更新

**構成例:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**証明書の検証:**

```bash
# Inspect certificate validity/status; private keys are not shown as plaintext
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config secret <pod-name> -n <namespace> -o json
```

**セキュリティ上の利点:**

1. **機密性**: すべての通信を暗号化する
2. **完全性**: データ改ざんを防ぐ
3. **認証**: 双方向で ID を検証する
4. **自動化**: コードを変更せずに適用する

**参考:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [証明書管理](../../../service-mesh/istio/03-architecture.md#3-certificate-management-citadel-functionality)

</details>

***

### 問題 9: Istio のデバッグ

新しくデプロイした Service が Istio メッシュ内で通信できないときの診断手順を、少なくとも 5 つのステップで説明してください。

<details>

<summary>回答を表示</summary>

**回答:**

**Istio Service 通信のデバッグチェックリスト:**

**ステップ 1: Pod とサイドカーの状態を確認する**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}{" "}{.spec.initContainers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**診断:**

* コンテナ内の `istio-proxy`、または native sidecar の initContainers を確認します。ambient ワークロードには注入済みサイドカーがありません。
* Pod が CrashLoopBackOff の場合は、アプリケーションまたはサイドカーの初期化に失敗しています。

**対処:**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**ステップ 2: Service と Endpoint を確認する**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service-name>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**診断:**

* Endpoint が空なら Service Selector と Pod Label が一致していません。
* Service のポートと Pod のポートが一致していません。

**対処:**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**ステップ 3: Istio の構成を確認する**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateways.networking.istio.io -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**診断:**

* `istioctl analyze` のエラーメッセージを確認します。
* VirtualService の host が Service 名と一致するか確認します。
* DestinationRule の Subset ラベルが Pod ラベルと一致するか確認します。

**対処:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced gateway not found: missing-gateway
```

***

**ステップ 4: mTLS とセキュリティポリシーを確認する**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
istioctl x authz check <pod-name> -n <namespace>

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**診断:**

* STRICT 宛てに平文クライアントトラフィックが到達している、証明書が期限切れ、または信頼設定が互換でない可能性があります。
* AuthorizationPolicy がトラフィックを拒否している可能性があります。

**対処:**

有効なポリシー、ワークロード ID、証明書、Envoy の拒否ログを調べてください。STRICT と PERMISSIVE のサーバーはいずれも、メッシュの mTLS クライアントからの接続を受け入れられます。ポリシー変更は隔離したテスト Namespace で再現してください。稼働中の認可ポリシーを削除したり、mTLS を緩和したりすることを既定のデバッグ手順にしないでください。



***

**ステップ 5: Envoy の構成を確認する**

```bash
# Check Envoy cluster configuration (service discovery)
istioctl proxy-config clusters <pod-name> -n <namespace>

# Check Envoy listener configuration (inbound/outbound)
istioctl proxy-config listeners <pod-name> -n <namespace>

# Check Envoy route configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>
```

**診断:**

* 対象 Service が clusters にない場合、Istiod が Service を認識していません。
* listeners がない場合、ポート構成に誤りがあります。
* endpoints が UNHEALTHY の場合、Pod が Ready ではありません。

***

**ステップ 6: ネットワーク接続をテストする**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Compare Pod-IP routing; this does not bypass the sidecar interception
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
istioctl dashboard envoy <pod-name> -n <namespace>
```

***

**ステップ 7: Istiod のログを確認する**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**ステップ 8: メトリクスとトレースを確認する**

Telemetry アドオンは別途インストールが必要です。ブロッキングするポートフォワードはそれぞれ別のターミナルで実行し、Collector の実際の Service／Namespace に置き換えてください。

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**トラブルシューティングのフローチャート:**

```
1. Pod/Sidecar normal?
   ├─ NO → Check Sidecar injection
   └─ YES → Step 2

2. Service/Endpoint normal?
   ├─ NO → Check Selector
   └─ YES → Step 3

3. Istio configuration normal?
   ├─ NO → Run istioctl analyze
   └─ YES → Step 4

4. mTLS/policies normal?
   ├─ NO → Inspect identity, certificates, and denial logs
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Inspect xDS status and istiod logs
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**参考:**

* [Istio のデバッグガイド](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### 問題 10: Istio のアップグレード戦略

互換性のある EKS クラスターで Istio 1.30.4 から 1.31.0 へ Canary Upgrade を行う方法を説明してください。ワークロードの移行、Gateway の扱い、検証、ロールバック条件を含めてください。

<details>

<summary>回答を表示</summary>

旧 Control Plane は、すべてのワークロードと Gateway の移行が完了し、ロールバック期間が終了するまで稼働させてください。これは istioctl で管理するサイドカー構成の例です。Helm と ambient のインストールにはそれぞれ独自のアップグレード手順があります。以下のリビジョン名は例であり、実際のインストールに合わせてください。

**1. 準備とバックアップ**

Istio/EKS のサポートマトリックスとリリースアップグレードノートを確認します。既存のインストールファイル、該当する場合はチャートのバージョン、メッシュリソース、ベストプラクティス章で説明されている CA/TLS Secret を保全します。対象バージョンの istioctl をダウンロードし、事前チェックを実行します。

```bash
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"
istioctl version
istioctl x precheck
```

**2. Canary Control Plane をインストールする**

既存の構成を基に `canary-install.yaml` を用意し、メッシュ ID、信頼設定、リソース設定を維持します。リビジョンを `1-31-0` にし、Gateway コンポーネントを有効にせず、Control Plane のみの Canary 用に `minimal` を使います。インストール前にレンダリングして内容を確認します。

```bash
istioctl manifest generate -f canary-install.yaml > canary-rendered.yaml
istioctl install -f canary-install.yaml
kubectl rollout status deployment/istiod-1-31-0 -n istio-system
```

`production` プロファイルは存在しません。リビジョンラベルがバイナリのバージョンを選ぶわけではありません。対象バージョンは istioctl と構成で決まります。

**3. テスト Namespace を検証する**

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

続行する前に、実際のプロキシイメージのバージョン、同期状態、mTLS／認可の挙動、エラー、レイテンシーを確認します。

**4. Staging、次に本番の Namespace を一つずつ移行する**

`istio-injection` を削除します。このラベルはリビジョンラベルより優先されるためです。コントローラーを再起動して新しいプロキシを持つ Pod を作成します。該当する場合は StatefulSet、DaemonSet、今後作成する Job も含めます。

```bash
kubectl label namespace staging istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n staging
kubectl rollout status deployment -n staging
istioctl proxy-status
```

アプリケーションのスモークテストが成功し、ワークロードに応じた観察期間を経てから次へ進みます。一定時間 sleep させるだけではヘルスゲートになりません。

**5. 旧 Control Plane の削除前に Gateway を移行する**

Gateway を管理している istioctl／Helm の構成を使ってアップグレードし、プロキシイメージ、リビジョン、外部ロードバランサー設定を含めます。Deployment のラベルだけを変更しても、古いイメージを明示した Gateway には不十分です。ロールアウト、外部リクエスト、proxy-status を確認してください。istioctl の既定プロファイルは共有 Gateway をインプレースで更新する場合があるため、この動作を明示的に計画してください。

**6. 完了またはロールバックする**

Gateway と Deployment 以外のワークロードを含むすべてのプロキシが旧リビジョンから移行したことを確認してから、インストールツールを使って旧リビジョンを削除します。共有の検証 Webhook を手作業で削除しないでください。

```bash
istioctl proxy-status
istioctl uninstall --revision=1-30-4
```

旧リビジョンを削除する前なら、影響を受けた Namespace のラベルを稼働中の旧リビジョンに戻し、ワークロードを再起動し、アップグレード済み Gateway を旧リリース構成で戻して、トラフィックを検証するのがロールバックです。新リビジョンに依存するプロキシがなくなった場合にのみ、新リビジョンを削除してください。旧リビジョンをすでに削除した場合は、ワークロードのラベルを戻す前に旧リビジョンを再インストールして検証してください。

**参考:**

- [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
- [バックアップと運用のガイダンス](../../../service-mesh/istio/best-practices.md)

</details>

***

## スコア計算

* 選択問題 1～5: 各 10 点（合計 50 点）
* 記述問題 6～10: 各 10 点（合計 50 点）
* **合計: 100 点**

**評価基準:**

* 90～100 点: 優秀（Istio の基本概念を十分に理解している）
* 80～89 点: 良好（基本的な運用ができる）
* 70～79 点: 平均（追加学習を推奨）
* 60～69 点: 平均以下（基本概念の復習が必要）
* 0～59 点: 再学習が必要

## 学習リソース

* [Istio インストールガイド](../../../service-mesh/istio/01-installation.md)
* [コア概念](../../../service-mesh/istio/02-basic-concepts.md)
* [コンポーネント](../../../service-mesh/istio/03-architecture.md)
* [Istio 公式ドキュメント](https://istio.io/latest/docs/)

* [インストール構成プロファイル](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Sidecar のインストール](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
* [セキュリティ](https://istio.io/latest/docs/concepts/security/)
* [Internet Engineering Task Force（IETF）、E. Rescorla](https://www.rfc-editor.org/rfc/rfc8446.html)
* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [istioctl](https://istio.io/latest/docs/reference/commands/istioctl/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Istio 1.24.0 の発表](https://istio.io/latest/news/releases/1.24.x/announcing-1.24/)
* [パフォーマンスとスケーラビリティ](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
