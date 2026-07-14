# 基本クイズ

> **対応バージョン**: Istio 1.28.0 **EKS バージョン**: 1.34 (Kubernetes 1.28+) **最終更新**: February 23, 2026

このクイズでは、Istio の基本概念とアーキテクチャに関する理解度を確認します。

## 選択問題（1～5）

### 問題 1: Service Mesh の定義

Service Mesh について、**正しくない**記述はどれですか？

A. マイクロサービス間の通信を処理するインフラストラクチャ層である B. アプリケーションコードを変更してのみ使用できる C. サービス間のトラフィック制御と可観測性を提供する D. ネットワークレベルでセキュリティとポリシーを適用する

<details>

<summary>回答を表示</summary>

**回答: B**

Service Mesh の主要な利点の一つは、**アプリケーションコードを変更せずに**サービス間の通信を制御および監視できることです。

**解説:**

* A (O): Service Mesh は、マイクロサービスアーキテクチャにおけるサービス間通信を担う専用のインフラストラクチャ層です
* B (X): アプリケーションコードを変更せず、sidecar proxy または Ambient Mode を通じて透過的に適用されます
* C (O): VirtualService、DestinationRule などでトラフィックを制御し、metrics/logs/traces を自動収集します
* D (O): mTLS、Authorization Policy などにより、ネットワークレベルでセキュリティポリシーを適用します

**参照:**

* [Istio コアコンセプト](../../../service-mesh/istio/02-basic-concepts.md)
* [Service Mesh とは？](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#introduction)

</details>

***

### 問題 2: Istio アーキテクチャコンポーネント

Istio の Control Plane において、サービスディスカバリ、設定管理、証明書管理を担う**集中型コンポーネント**はどれですか？

A. Envoy B. Istiod C. Pilot D. Citadel

<details>

<summary>回答を表示</summary>

**回答: B**

**Istiod** は、従来の Pilot、Citadel、Galley コンポーネントを統合した、Istio 1.5 で導入された単一バイナリです。

**解説:**

* A (X): Envoy は各 Pod で sidecar として実行される Data Plane proxy です
* B (O): Istiod は Control Plane の中核であり、以下を処理します:
  * Service Discovery
  * Configuration Management
  * Certificate Management
* C (X): Pilot は 1.5 より前の Istio バージョンのコンポーネントであり、現在は Istiod に統合されています
* D (X): Citadel も 1.5 より前の Istio バージョンのコンポーネントであり、現在は Istiod に統合されています

**Istiod の主な役割:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**参照:**

* [Istio コンポーネント](../../../service-mesh/istio/03-architecture.md)
* [アーキテクチャの概要](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#architecture-overview)

</details>

***

### 問題 3: Envoy Proxy の役割

Data Plane の Envoy proxy が実行するタスクでは**ない**ものはどれですか？

A. トラフィックルーティングとロードバランシング B. mTLS 暗号化と認証 C. Kubernetes CRD の検証と保存 D. metrics、logs、traces の収集

<details>

<summary>回答を表示</summary>

**回答: C**

Kubernetes CRD の検証と保存は、Control Plane（Istiod）の役割です。

**解説:**

* A (O): Envoy は VirtualService ルールに従ってトラフィックをルーティングし、ロードバランシングします
* B (O): Envoy は mTLS によりサービス間通信を自動的に暗号化し、証明書を検証します
* C (X): CRD の検証と保存は Kubernetes API Server および Istiod の役割です
* D (O): Envoy はすべてのリクエストについて metrics（Prometheus）、logs（Access Log）、traces（Jaeger）を収集します

**参照:**

* [Data Plane 構造](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### 問題 4: Istio インストールプロファイル

Amazon EKS の本番環境で Istio をインストールする際に**推奨される**プロファイルはどれですか？

A. default B. demo C. minimal D. production

<details>

<summary>回答を表示</summary>

**回答: D**

本番環境では、**production** プロファイルを使用する必要があります。

**解説:**

**Istio インストールプロファイル比較:**

| プロファイル        | 目的             | 特徴                           |
| -------------- | ------------------- | ----------------------------------------- |
| **default**    | 開発/テスト | デフォルト設定、中程度のリソース   |
| **demo**       | デモ/学習       | すべての機能が有効、高いリソース使用量 |
| **minimal**    | 最小構成       | Control Plane のみ                        |
| **production** | 本番環境          | HA 設定、高可用性       |

**Production プロファイルの特徴:**

```bash
# Production profile installation
istioctl install --set profile=production -y

# Key characteristics:
# - Istiod replica: 3 (HA)
# - PodDisruptionBudget configured
# - Resource limits properly set
# - Ingress/Egress Gateway included
```

**本番環境チェックリスト:**

* ✅ Control Plane HA（replica ≥ 3）
* ✅ mTLS STRICT mode
* ✅ PodDisruptionBudget を設定済み
* ✅ Resource limits と HPA を設定済み
* ✅ Monitoring stack の準備完了

**参照:**

* [インストールガイド](../../../service-mesh/istio/01-installation.md)
* [ベストプラクティス](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### 問題 5: Istio CRD（Custom Resource Definition）

次のうち、Istio の**トラフィック管理**用 CRD **ではない**ものはどれですか？

A. VirtualService B. DestinationRule C. PeerAuthentication D. Gateway

<details>

<summary>回答を表示</summary>

**回答: C**

**PeerAuthentication** はセキュリティ関連の CRD です。

**解説:**

**Istio CRD の分類:**

**1. トラフィック管理:**

* VirtualService: ルーティングルールの定義
* DestinationRule: ロードバランシング、subset の定義
* Gateway: 外部トラフィックのエントリポイント
* ServiceEntry: 外部サービスの定義
* Sidecar: Envoy 設定スコープの制限

**2. セキュリティ:**

* PeerAuthentication: サービス間認証（mTLS）
* RequestAuthentication: エンドユーザー認証（JWT）
* AuthorizationPolicy: アクセス制御

**3. 可観測性:**

* Telemetry: metrics、logs、traces の設定

**例:**

```yaml
# Traffic Management
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
# Security
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**参照:**

* [トラフィック管理](../../../service-mesh/istio/traffic-management/)
* [セキュリティ](../../../service-mesh/istio/security/)

</details>

***

## 記述問題（6～10）

### 問題 6: Sidecar Injection の仕組み

Istio で Envoy Sidecar を Pod に自動 inject する 2 つの方法を説明し、それぞれの長所と短所を比較してください。

<details>

<summary>回答を表示</summary>

**回答:**

Istio は次の 2 つの方法で Sidecar を自動 inject します:

**1. Namespace レベルの自動 injection:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**長所:**

* Namespace 全体に一度に適用できる
* 管理が容易
* 設定漏れが発生しにくい

**短所:**

* Namespace 内のすべての Pod に適用される（選択的な除外が必要）
* 既存の Pod は再起動が必要

**2. Pod レベルの選択的 injection:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**長所:**

* 特定の Pod のみに選択的に inject できる
* きめ細かな制御が可能
* Namespace label は不要

**短所:**

* 各 Deployment に設定が必要
* 管理対象が増える
* 設定漏れが発生する可能性がある

**比較表:**

| 項目                  | Namespace レベル         | Pod レベル          |
| --------------------- | ----------------------- | ------------------ |
| 範囲                 | Namespace 全体        | 個別の Pod     |
| 管理の複雑さ | 低                     | 高               |
| 選択性           | 低（除外が必要）  | 高               |
| 推奨用途       | 本番環境 | 混在環境 |

**本番環境での推奨事項:**

* デフォルトでは Namespace レベルを使用する
* 除外が必要な Pod にのみ `sidecar.istio.io/inject: "false"` を設定する

**参照:**

* [Sidecar Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### 問題 7: Istio リソース使用量の最適化

1000 Pod を持つ大規模 Kubernetes cluster で Istio を使用する場合の、Sidecar Mode と Ambient Mode における**想定リソース使用量**を計算して比較してください。（ztunnel は 10 node に配置され、waypoint は 1 つと仮定します）

<details>

<summary>回答を表示</summary>

**回答:**

**前提条件:**

* Pod 数: 1000
* Node 数: 10
* Sidecar Memory: 50MB/Pod
* ztunnel Memory: 50MB/Node
* waypoint Memory: 200MB

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

**3. 比較と削減効果:**

| 項目       | Sidecar Mode | Ambient Mode | 削減量   | 削減率 |
| ---------- | ------------ | ------------ | --------- | ------------ |
| **Memory** | 50GB         | 0.7GB        | 49.3GB    | **98.6%**    |
| **CPU**    | 100 vCPU     | 1.5 vCPU     | 98.5 vCPU | **98.5%**    |

**コスト計算（AWS EKS ベース）:**

```
# r5.xlarge: 4 vCPU, 32GB RAM, $0.252/hour

Sidecar Mode:
- CPU: 100 vCPU → 25 instances needed
- Memory: 50GB → 2 instances needed
- Required instances: max(25, 2) = 25
- Monthly cost: 25 × $0.252 × 24 × 30 = $4,536

Ambient Mode:
- CPU: 1.5 vCPU → 1 instance sufficient
- Memory: 0.7GB → 1 instance sufficient
- Required instances: 1
- Monthly cost: 1 × $0.252 × 24 × 30 = $181

Monthly cost savings: $4,536 - $181 = $4,355 (96%)
```

**結論:**

* Ambient Mode は大規模 cluster で**96% 以上のコスト削減**を実現します
* 1000 Pod 規模では、月額で約 **$4,300 の削減**となります
* リソース使用量を **98% 以上**削減できます

**注意事項:**

* L7 機能が必要な場合は追加の waypoint が必要です
* Ambient Mode は Istio 1.28+ では beta 機能です

**参照:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [コスト最適化](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### 問題 8: mTLS の動作メカニズム

Istio で 2 つのサービス（service-a と service-b）が通信する際の mTLS の動作を、段階的に説明してください。Istiod、Envoy、Certificate の役割を含めてください。

<details>

<summary>回答を表示</summary>

**回答:**

**mTLS（Mutual TLS）動作プロセス:**

**ステップ 1: Certificate の発行（Bootstrap）**

* Pod の起動時、Envoy は Service Account を使用して Istiod に Certificate（CSR）をリクエストします
* Istiod は Service Account を検証し、X.509 Certificate を発行します
* Certificate には Service Account ID（例: `cluster.local/ns/default/sa/service-a`）が含まれます
* Certificate の有効期間: デフォルトで 24 時間（自動更新）

**ステップ 2: サービス間通信（mTLS Handshake）**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**詳細なプロセス:**

```yaml
# Service A calls Service B
1. Service A → Envoy A (localhost:outbound)
   - Application sends plaintext HTTP request

2. Envoy A: Outbound Processing
   - Check configuration received from Istiod
   - Check PeerAuthentication policy (STRICT mTLS)
   - Start connection to Service B's Envoy B

3. TLS Handshake (Envoy A ↔ Envoy B)
   a. Envoy A → Envoy B: ClientHello
      - Present own certificate
      - Present supported encryption algorithms

   b. Envoy B → Envoy A: ServerHello
      - Present own certificate
      - Selected encryption algorithm

   c. Mutual Certificate Validation
      - Envoy A: Validate Service B's certificate
      - Envoy B: Validate Service A's certificate
      - Verify signature with Istiod's Root CA

   d. Generate Encrypted Session Key
      - Create TLS 1.3 encrypted channel

4. Envoy B → Service B (localhost:inbound)
   - Deliver decrypted plaintext HTTP request

5. Service B → Envoy B → [mTLS] → Envoy A → Service A
   - Response uses same encrypted channel
```

**各コンポーネントの役割:**

**Istiod:**

* Root CA として機能します（Certificate signing）
* Service Account に基づいて Certificate を発行します
* Certificate を自動更新します（24 時間ごと）
* PeerAuthentication policy を配布します

**Envoy Sidecar:**

* Certificate をリクエストおよび更新します
* TLS Handshake を実行します
* トラフィックを暗号化/復号します
* Certificate を検証します

**Certificate:**

* X.509 Certificate 形式
* Subject Alternative Name（SAN）: Service Account URI
* 有効期間: 24 時間（デフォルト）
* 自動更新

**設定例:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**Certificate の検証:**

```bash
# Check Pod's certificate
istioctl proxy-config secret <pod-name> -o json

# Example output:
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

**セキュリティ上の利点:**

1. **機密性**: すべての通信を暗号化
2. **完全性**: データ改ざんの防止
3. **認証**: 双方向の ID 検証
4. **自動化**: コード変更なしで適用

**参照:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Certificate 管理](../../../service-mesh/istio/03-architecture.md#certificate-management)

</details>

***

### 問題 9: Istio のデバッグ

新たにデプロイしたサービスが Istio mesh 内で通信できない場合の、問題を診断するための段階的なデバッグ方法を記述してください。（少なくとも 5 ステップ）

<details>

<summary>回答を表示</summary>

**回答:**

**Istio サービス通信のデバッグチェックリスト:**

**ステップ 1: Pod と Sidecar のステータス確認**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**診断:**

* container が 1 つのみの場合 → Sidecar が inject されていません
* Pod が CrashLoopBackOff の場合 → Application または Sidecar の初期化に失敗しています

**解決方法:**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**ステップ 2: Service と Endpoint の確認**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpoints <service-name> -n <namespace>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**診断:**

* Endpoint が空の場合 → Service Selector と Pod Label が不一致です
* Service port と Pod port が不一致です

**解決方法:**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**ステップ 3: Istio 設定の確認**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateway -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**診断:**

* `istioctl analyze` のエラーメッセージを確認します
* VirtualService host が Service 名と一致しているか確認します
* DestinationRule subset label が Pod label と一致しているか確認します

**解決方法:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced host not found: reviews
```

***

**ステップ 4: mTLS とセキュリティポリシーの確認**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl authn tls-check <pod-name>.<namespace> <service-name>.<namespace>.svc.cluster.local

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**診断:**

* mTLS mode の不一致（STRICT と PERMISSIVE）
* AuthorizationPolicy がトラフィックをブロックしている

**解決方法:**

```bash
# Temporarily change to PERMISSIVE mode (for debugging)
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

# Temporarily delete AuthorizationPolicy
kubectl delete authorizationpolicy <policy-name> -n <namespace>
```

***

**ステップ 5: Envoy 設定の確認**

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

* target Service が clusters にない場合 → Istiod が Service を認識していません
* listeners がない場合 → port 設定エラーです
* endpoints が UNHEALTHY の場合 → Pod の準備ができていません

***

**ステップ 6: ネットワーク接続テスト**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Test directly without going through Envoy (by Pod IP)
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- curl localhost:15000/stats | grep <service-name>
```

***

**ステップ 7: Istiod logs の確認**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**ステップ 8: Metrics と Tracing の確認**

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**トラブルシューティングフローチャート:**

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
   ├─ NO → Test PERMISSIVE mode
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Restart Istiod
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**参照:**

* [Istio デバッグガイド](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### 問題 10: Istio アップグレード戦略

本番環境で Istio を 1.27.0 から 1.28.0 にアップグレードするための **Canary Upgrade** 戦略を説明してください。段階的なコマンドと検証方法を含めてください。

<details>

<summary>回答を表示</summary>

**回答:**

**Istio Canary Upgrade 戦略:**

Canary Upgrade は、旧バージョンと新バージョンの Control Plane を同時に実行し、workload を段階的に移行する安全なアップグレード手法です。

***

**準備:**

```bash
# 1. Check current version
istioctl version

# 2. Create backup
kubectl get istiooperator -A -o yaml > istio-1.27-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 3. Download new version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 4. Check compatibility
istioctl x precheck
```

***

**ステップ 1: 新しい Control Plane をインストール（revision を使用）**

```bash
# Install new version Control Plane using Revision
istioctl install --set revision=1-28-0 --set profile=production -y

# Verify installation
kubectl get pods -n istio-system -l app=istiod
# Example output:
# istiod-1-27-0-xxxx  (old version)
# istiod-1-28-0-xxxx  (new version)

# Check Revision
kubectl get mutatingwebhookconfigurations | grep istio
# Output:
# istio-sidecar-injector-1-27-0
# istio-sidecar-injector-1-28-0
```

**重要:** この時点では、**2 つの Control Plane** が同時に実行されています。

***

**ステップ 2: テスト Namespace で Canary 検証**

```bash
# Create test namespace
kubectl create namespace istio-upgrade-test

# Label for new version
kubectl label namespace istio-upgrade-test istio.io/rev=1-28-0

# Deploy test application
kubectl apply -n istio-upgrade-test -f samples/sleep/sleep.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml

# Check Sidecar version (should be 1.28.0)
kubectl get pods -n istio-upgrade-test -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'

# Test communication
kubectl exec -n istio-upgrade-test deploy/sleep -- curl http://httpbin:8000/headers

# Check Envoy configuration
istioctl proxy-config clusters deploy/sleep.istio-upgrade-test
```

**検証チェックリスト:**

* ✅ Sidecar はバージョン 1.28.0 で inject されていますか？
* ✅ サービス間通信は正常ですか？
* ✅ mTLS は正しく動作していますか？
* ✅ metrics は収集されていますか？

***

**ステップ 3: Staging Namespace を移行**

```bash
# Switch staging namespace to new version
kubectl label namespace staging istio.io/rev=1-28-0 --overwrite

# Remove existing label (if present)
kubectl label namespace staging istio-injection-

# Restart Pods (inject new version Sidecar)
kubectl rollout restart deployment -n staging

# Monitor restart status
kubectl rollout status deployment -n staging

# Verify version
kubectl get pods -n staging -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

**検証:**

```bash
# Check metrics
kubectl exec -n staging <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_build

# Test communication
kubectl exec -n staging <pod-name> -- curl http://<service-name>

# Visual confirmation with Kiali
istioctl dashboard kiali
```

**24～48 時間監視します:**

* Prometheus metrics を確認する
* エラー率とレイテンシを比較する
* Istiod のリソース使用量を確認する

***

**ステップ 4: 本番 Namespace を段階的に移行**

```bash
# List of production Namespaces
PROD_NAMESPACES="prod-api prod-web prod-worker"

# Migrate one at a time gradually
for ns in $PROD_NAMESPACES; do
  echo "Upgrading namespace: $ns"

  # Update label
  kubectl label namespace $ns istio.io/rev=1-28-0 --overwrite

  # Restart Pods
  kubectl rollout restart deployment -n $ns

  # Wait for completion
  kubectl rollout status deployment -n $ns

  # Verify
  echo "Verifying namespace: $ns"
  kubectl exec -n $ns <pod-name> -- curl http://<service-name>

  # Wait before next Namespace migration (observation)
  echo "Waiting 1 hour before next namespace..."
  sleep 3600
done
```

**段階的な検証:**

```bash
# After each Namespace migration
# 1. Golden Signals
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query in Prometheus:
# - istio_requests_total
# - istio_request_duration_milliseconds
# - istio_request_bytes

# 2. Control Plane status
istioctl proxy-status | grep $ns

# 3. Error logs
kubectl logs -n istio-system -l app=istiod,istio.io/rev=1-28-0 --tail=100
```

***

**ステップ 5: 旧バージョンを削除**

```bash
# Verify all Namespaces have migrated to new version
kubectl get namespace -L istio.io/rev

# Verify no Pods using old version
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}' | grep 1.27

# Remove old version Control Plane
istioctl uninstall --revision=1-27-0 -y

# Verify removal
kubectl get pods -n istio-system -l app=istiod

# Cleanup
kubectl delete mutatingwebhookconfigurations istio-sidecar-injector-1-27-0
kubectl delete validatingwebhookconfigurations istio-validator-1-27-0-istio-system
```

***

**ステップ 6: Gateway のアップグレード（任意）**

```bash
# Upgrade Gateway separately
kubectl patch deployment istio-ingressgateway -n istio-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"istio.io/rev":"1-28-0"}}}}}'

kubectl rollout restart deployment istio-ingressgateway -n istio-system
kubectl rollout status deployment istio-ingressgateway -n istio-system
```

***

**ロールバック計画:**

```bash
# Immediate rollback if issues occur
# 1. Change Namespace label to old version
kubectl label namespace <namespace> istio.io/rev=1-27-0 --overwrite

# 2. Restart Pods
kubectl rollout restart deployment -n <namespace>

# 3. Remove new version Control Plane
istioctl uninstall --revision=1-28-0 -y
```

***

**ベストプラクティス:**

1. **段階的アプローチ:**
   * テスト → Staging → 本番の段階で進める
   * 一度に 1 つの Namespace を移行する
   * 各段階で十分な観察時間を確保する
2. **モニタリング:**
   * Golden Signals（Latency、Traffic、Errors、Saturation）を監視する
   * Istiod のリソース使用量を確認する
   * 各段階で 24～48 時間観察する
3. **自動化:**
   * CI/CD pipeline に統合する
   * Smoke Tests を自動化する
   * ロールバックスクリプトを準備する
4. **コミュニケーション:**
   * チームとアップグレードスケジュールを共有する
   * release notes を確認する
   * 変更を文書化する

**参照:**

* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [アップグレード戦略](../../../service-mesh/istio/best-practices.md#upgrade-strategy)

</details>

***

## スコア計算

* 選択問題 1～5: 各 10 点（合計 50 点）
* 記述問題 6～10: 各 10 点（合計 50 点）
* **合計: 100 点**

**評価基準:**

* 90～100 点: 優秀（Istio の基本概念を完全に理解）
* 80～89 点: 良好（基本操作が可能）
* 70～79 点: 平均（追加学習を推奨）
* 60～69 点: 平均以下（基本概念の復習が必要）
* 0～59 点: 再学習が必要

## 学習リソース

* [Istio インストールガイド](../../../service-mesh/istio/01-installation.md)
* [コアコンセプト](../../../service-mesh/istio/02-basic-concepts.md)
* [コンポーネント](../../../service-mesh/istio/03-architecture.md)
* [Istio 公式ドキュメント](https://istio.io/latest/docs/)
