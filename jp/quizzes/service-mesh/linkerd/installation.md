# Linkerd インストールクイズ

このクイズでは、Linkerd のインストールとセットアップに関する理解度を確認します。

## クイズ問題

### 1. Linkerd CLI をインストールする正しいコマンドはどれですか？

A. `apt-get install linkerd`
B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`
C. `kubectl install linkerd`
D. `helm install linkerd`

<details>
<summary>回答を表示</summary>

**回答: B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`**

**解説:**
Linkerd CLI は公式インストールスクリプトを通じてインストールされます。このスクリプトはオペレーティングシステムを検出し、適切なバイナリをダウンロードします。Homebrew（`brew install linkerd`）または Chocolatey（`choco install linkerd2`）も使用できますが、公式スクリプトが最も一般的な方法です。

</details>

### 2. Linkerd のインストール前にクラスター要件を検証するコマンドはどれですか？

A. `linkerd check`
B. `linkerd check --pre`
C. `linkerd verify`
D. `linkerd install --dry-run`

<details>
<summary>回答を表示</summary>

**回答: B. `linkerd check --pre`**

**解説:**
`linkerd check --pre` コマンドは、Linkerd のインストール前にクラスターが要件を満たしていることを検証します。Kubernetes API へのアクセス性、バージョン互換性、必要な権限を確認します。インストール後は、完全なステータスを確認するために `linkerd check` を使用します。

</details>

### 3. Helm を使用して Linkerd をインストールする際に必要なものはどれですか？

A. Envoy proxy イメージ
B. Trust Anchor および Identity Issuer 証明書
C. Prometheus 設定ファイル
D. Kubernetes バージョン情報

<details>
<summary>回答を表示</summary>

**回答: B. Trust Anchor および Identity Issuer 証明書**

**解説:**
CLI によるインストールとは異なり、Helm によるインストールでは証明書が自動生成されません。ユーザーは Trust Anchor（Root CA）と Identity Issuer（Intermediate CA）の証明書を自分で作成して提供する必要があります。これにより、本番環境での証明書管理をより適切に制御できます。

</details>

### 4. Linkerd の HA インストールで推奨される Control plane レプリカ数はいくつですか？

A. 1
B. 2
C. 3
D. 5

<details>
<summary>回答を表示</summary>

**回答: C. 3**

**解説:**
HA 構成では、Destination、Identity、Proxy Injector の各コンポーネントに 3 つのレプリカを推奨します。3 つのレプリカがあれば、1 つが障害を起こしてもクォーラムを維持でき、ローリングアップデート中の可用性を確保できます。

</details>

### 5. Viz 拡張機能の主要機能ではないものはどれですか？

A. Web ダッシュボード
B. Prometheus メトリクス収集
C. 自動カナリアデプロイメント
D. リアルタイムトラフィックタップ

<details>
<summary>回答を表示</summary>

**回答: C. 自動カナリアデプロイメント**

**解説:**
Viz 拡張機能は、Web ダッシュボード、Prometheus ベースのメトリクス収集、Grafana ダッシュボード、リアルタイムトラフィックタップ機能を提供します。自動カナリアデプロイメントは、Flagger のような別のツールによって実装されます。

</details>

### 6. EKS の Multicluster gateway に推奨されるロードバランサーのタイプはどれですか？

A. Classic Load Balancer
B. Application Load Balancer (ALB)
C. Network Load Balancer (NLB)
D. Internal Load Balancer

<details>
<summary>回答を表示</summary>

**回答: C. Network Load Balancer (NLB)**

**解説:**
NLB は TCP/TLS トラフィック向けに最適化されているため、Linkerd の mTLS gateway トラフィックに適しています。ALB は HTTP/HTTPS 向けに最適化されており、Linkerd gateway は TCP レベルで動作するため、NLB が推奨されます。

</details>

### 7. Linkerd のアップグレードの正しい順序はどれですか？

A. Data plane → CRD → Control plane
B. CRD → Control plane → Data plane
C. Control plane → CRD → Data plane
D. CRD → Data plane → Control plane

<details>
<summary>回答を表示</summary>

**回答: B. CRD → Control plane → Data plane**

**解説:**
正しいアップグレード順序は、1) CLI のアップグレード、2) CRD のアップグレード、3) Control plane のアップグレード、4) Data plane（proxy）のアップグレードです。新しい API バージョンを使用するためには、CRD を最初にアップグレードする必要があります。

</details>

### 8. `linkerd install --crds` コマンドの目的は何ですか？

A. Linkerd CLI をインストールする
B. Custom Resource Definitions をインストールする
C. 証明書を生成する
D. proxy をインジェクトする

<details>
<summary>回答を表示</summary>

**回答: B. Custom Resource Definitions をインストールする**

**解説:**
`linkerd install --crds` は、Linkerd で使用される CRD（Custom Resource Definitions）のみをインストールします。これには、ServiceProfile、Server、ServerAuthorization などの CRD が含まれます。Control plane は `linkerd install` により別途インストールされます。

</details>

### 9. Jaeger 拡張機能をインストールするコマンドはどれですか？

A. `linkerd install jaeger`
B. `linkerd jaeger install | kubectl apply -f -`
C. `kubectl apply -f jaeger.yaml`
D. `helm install jaeger linkerd/jaeger`

<details>
<summary>回答を表示</summary>

**回答: B. `linkerd jaeger install | kubectl apply -f -`**

**解説:**
Linkerd 拡張機能は、`linkerd <extension> install` 形式でマニフェストを生成し、kubectl で適用します。Jaeger 拡張機能は分散トレーシング機能を提供します。

</details>

### 10. Linkerd を完全に削除する正しい順序はどれですか？

A. Control plane → Extensions → CRD
B. Extensions → Control plane → CRD
C. CRD → Control plane → Extensions
D. すべて同時に削除できる

<details>
<summary>回答を表示</summary>

**回答: B. Extensions → Control plane → CRD**

**解説:**
削除順序はインストールの逆です。1) Viz、Jaeger、Multicluster などの拡張機能を削除する、2) Control plane を削除する、3) CRD を削除する、という順序になります。これは、拡張機能が Control plane に依存し、Control plane が CRD に依存するためです。

</details>

### 11. `linkerd check` コマンドが検証しないものはどれですか？

A. Kubernetes API 接続
B. 証明書の有効性
C. アプリケーションのビジネスロジック
D. Control plane Pod ステータス

<details>
<summary>回答を表示</summary>

**回答: C. アプリケーションのビジネスロジック**

**解説:**
`linkerd check` は、Kubernetes API 接続、証明書の有効性、Control plane Pod ステータス、proxy ステータスなど、Linkerd インフラストラクチャのステータスのみを検証します。アプリケーションのビジネスロジックや機能は検証しません。

</details>

### 12. 自動 proxy インジェクションのために namespace に追加する必要がある annotation はどれですか？

A. `linkerd.io/inject: enabled`
B. `linkerd.io/proxy: true`
C. `sidecar.linkerd.io/inject: true`
D. `linkerd/auto-inject: yes`

<details>
<summary>回答を表示</summary>

**回答: A. `linkerd.io/inject: enabled`**

**解説:**
namespace に `linkerd.io/inject: enabled` annotation を追加すると、その namespace 内のすべての新しい Pod に linkerd-proxy が自動的にインジェクトされます。同じ annotation は個々の Pod にも使用できます。

</details>
