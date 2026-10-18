# Linkerd アーキテクチャクイズ

2026年10月16日に edge-26.10.1 を対象にレビューしました。根拠に基づく構成モデルと制約については、[アーキテクチャガイド](../../../service-mesh/linkerd/02-architecture.md)を参照してください。

### 1. Linkerd のコントロールプレーンのコンポーネントではないものはどれですか？

A. Destination controller

B. Identity controller

C. Proxy Injector

D. Envoy proxy

<details>
<summary>解答と説明</summary>

**解答: D**

Linkerd は Rust 製のデータプレーン proxy を使用します。固定したコントロールプレーンには中核となる Deployment が 3 つあり、policy などの追加の論理 controller はその中で実行されます。Envoy は Istio の sidecar／waypoint で使われますが、Linkerd の controller ではありません。

</details>

### 2. `linkerd2-proxy` はどの言語で書かれていますか？

A. Go

B. C++

C. Rust

D. Java

<details>
<summary>解答と説明</summary>

**解答: C**

Rust で書かれています。言語だけで、どの環境でもメモリ使用量が 10 MB、p99 が 1 ミリ秒未満、または別 proxy より必ず優れているとは結論できません。実際のビルド、ワークロード、設定を使って比較してください。

</details>

### 3. Destination の主な責務ではないものはどれですか？

A. サービスディスカバリー

B. ワークロード証明書の発行

C. サポート対象の ServiceProfile 情報

D. エンドポイントの更新

<details>
<summary>解答と説明</summary>

**解答: B**

Identity は設定済みの issuer credential を使ってワークロード証明書を発行します。Destination はディスカバリーと ServiceProfile の情報を提供します。現在の Gateway API のルーティングと認可には policy controller も関わります。従来の TrafficSplit 拡張だけでは、現在の policy モデル全体を表しません。

</details>

### 4. 既定の証明書階層の最上位で信頼の基点となるものは何ですか？

A. ワークロード証明書

B. Identity issuer

C. Trust anchor

D. 一意な Pod 名

<details>
<summary>解答と説明</summary>

**解答: C**

公開 trust anchor が証明書チェーン検証の基点です。通常はこれが中間 issuer に署名し、その鍵でワークロード証明書に署名します。各ワークロード CSR を処理するたびに、Linkerd がルートの秘密鍵を必要とするわけではありません。

</details>

### 5. ワークロード証明書の既定の有効期間はどのくらいですか？

A. 1 時間

B. 24 時間

C. 7 日

D. 30 日

<details>
<summary>解答と説明</summary>

**解答: B**

既定の設定では発行期間は 24 時間で、有効期限前に更新されます。実際の有効期間と更新時期は設定と証明書の状態によって変わります。証明書の更新だけで、新しい秘密鍵の生成、issuer のローテーション、ルートのローテーションが行われるとは限りません。

</details>

### 6. proxy の自動 injection を行う Kubernetes の仕組みは何ですか？

A. DaemonSet

B. CronJob

C. Mutating admission webhook

D. Application Load Balancer

<details>
<summary>解答と説明</summary>

**解答: C**

この webhook は、新しく作成される対象 Pod を変更します。選択したリリースでは、proxy は通常、ネイティブ sidecar になります。Linkerd CNI を設定すると `linkerd-init` は省略されます。既存 Pod と、対象外または設定で除外された Pod は別途考慮してください。

</details>

### 7. Linkerd CNI を使わない場合、`linkerd-init` は何をしますか？

A. すべてのルーティングポリシーをダウンロードする

B. Pod ネットワークのトラフィック捕捉を設定する

C. ルート CA として動作する

D. Prometheus の時系列を保存する

<details>
<summary>解答と説明</summary>

**解答: B**

Pod のネットワーク namespace 内にトラフィック捕捉ルールを設定します。TCP をリダイレクトする前に、proxy UID と設定済みのバイパスルールを考慮してください。すべてのプロトコルや、バイパスされたすべてのポートが proxy で処理されるわけではありません。

</details>

### 8. inbound proxy の既定ポートはどれですか？

A. 4140

B. 4143

C. 4191

D. 8080

<details>
<summary>解答と説明</summary>

**解答: B**

既定値は inbound が 4143、outbound が 4140、admin／metrics が 4191 です。inbound／outbound は捕捉された TCP を扱います。中身は HTTP／gRPC の場合も不透明な payload の場合もあります。ポートは設定で変更できます。

</details>

### 9. コントロールプレーンの namespace が `linkerd`、trust domain が `cluster.local` のとき、`my-app` の ServiceAccount `web-service` に対する既定の Kubernetes identity はどれですか？

A. spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service

B. web-service.my-app.serviceaccount.identity.linkerd.cluster.local

C. `https://linkerd.io/identity/my-pod`

D. urn:linkerd:my-pod

<details>
<summary>解答と説明</summary>

**解答: B**

Kubernetes TokenReview によって ServiceAccount identity が確認され、DNS 名形式で表されます。同じ ServiceAccount を使う複数の Pod は同じ identity を共有します。SPIFFE／SPIRE の外部ワークロード identity は別の bootstrap 経路を使い、既定の Kubernetes URI 形式ではありません。

</details>

### 10. 対応するベンチマークがない場合、どの比較が妥当ですか？

A. Linkerd は常に正確に 10 MB を使う

B. アーキテクチャとサポート API を比べ、実際のワークロードでリソースとレイテンシーを測定する

C. Istio は常に p99 に 2～5 ミリ秒を加える

D. 設定された memory request が小さければ実行時の使用量も少ないと証明できる

<details>
<summary>解答と説明</summary>

**解答: B**

設定上の予約量、バイナリーサイズ、実際のメモリ使用量、レイテンシーはそれぞれ異なる特性です。同じバージョン／ビルド、アーキテクチャ、トラフィックパターン、policy セットを使って比較してください。拡張性も一般的な製品ランキングから推測せず、選択したモード／API で確認する必要があります。

</details>

### 11. 既定の Kubernetes identity validator は何を検証しますか？

A. Pod IP だけ

B. Kubernetes TokenReview による提示された ServiceAccount token

C. namespace label だけ

D. ConfigMap 名だけ

<details>
<summary>解答と説明</summary>

**解答: B**

リリース済みの validator は token を認証し、Kubernetes の user 情報から DNS 形式の identity を導出します。証明書要求には identity と CSR のデータも含まれます。呼び出し元が提示した SPIFFE URI の見た目が妥当なら受理される、という意味ではありません。

</details>

### 12. ルーティング／policy 設定の動的な更新は、通常どのように proxy に届きますか？

A. Prometheus の metrics endpoint に書き込む

B. ルート証明書の subject を変更する

C. streaming gRPC を含むコントロールプレーン API を通じて配信する

D. node namespace に任意の REDIRECT ルールを適用する

<details>
<summary>解答と説明</summary>

**解答: C**

admin port は health と metrics のインターフェイスを提供しますが、コントロールプレーンの policy API の代わりにはなりません。起動時の環境変数／injection 設定と動的に配信される policy は別々の入力です。動作を診断するときは両方を確認してください。

</details>
