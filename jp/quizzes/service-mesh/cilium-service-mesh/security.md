# Cilium Service Mesh セキュリティクイズ

Cilium 1.20.3 に基づいて確認しています。[セキュリティガイド](../../../service-mesh/cilium-service-mesh/03-security.md)では、アプリケーション接続の外側で行う認証、通信の暗号化、ztunnel beta の違いを、一次資料とともに説明しています。

### 1. Cilium の out-of-band 相互認証で、SPIRE は何を提供しますか？

- **A.** すべての Pod に配置する Istio sidecar
- **B.** agent の認証機構で使う SVID の ID 認証情報
- **C.** それだけでアプリケーション通信をすべて自動的に暗号化する機能
- **D.** Kubernetes API server の代替

<details>
<summary>回答を表示</summary>

**回答: B. agent の認証機構で使う SVID の ID 認証情報**

out-of-band の beta 認証機構では、SPIRE が SVID の ID 認証情報を提供し、Cilium agent 同士がアプリケーション接続とは別に相互認証します。WireGuard/IPsec による暗号化は別の選択です。Cilium 1.20.3 には、独自の CA/bootstrap、登録、ポリシー上の制約を持つ ztunnel mTLS beta もあります。

</details>

### 2. authentication mode を 'required' に設定すると、CiliumNetworkPolicy はどのように動作しますか？

- **A.** 認証なしですべての通信を許可する
- **B.** 相互認証に成功した通信だけを許可する
- **C.** 認証失敗を警告として記録するだけである
- **D.** mTLS を無効にする

<details>
<summary>回答を表示</summary>

**回答: B. 相互認証に成功した通信だけを許可する**

該当する allow ルールは、認証の成功を許可条件とします。これはクラスター全体に適用するスイッチではなく、それだけでアプリケーションのペイロードを TLS 暗号化するものでもありません。ほかの認可要件やアプリケーション側の認証要件は引き続き適用されます。API の形式は authentication: {mode: required} であり、配列ではありません。

</details>

### 3. Cilium WireGuard だけでは、どの通信が暗号化されませんか？

- **A.** サポート対象の異なるノード間 Pod 通信
- **B.** ノード暗号化が有効な場合の、サポート対象のリモートノード通信
- **C.** 同一ノード内の Pod 通信と、外部クライアントからクラスターまでの区間
- **D.** ClusterIP Service を経由する、サポート対象のリモート Pod 通信

<details>
<summary>回答を表示</summary>

**回答: C. 同一ノード内の Pod 通信と、外部クライアントからクラスターまでの区間**

Cilium WireGuard は同一ノード内の Pod 通信を暗号化せず、外部クライアントからクラスターまでの区間も暗号化しません。リモートノード間の通信がどこまで保護されるかは、選択したモードと文書化された例外によって異なります。カーネルの対応が必要であり、Helm chart に userspaceFallback オプションはありません。

</details>

### 4. CiliumNetworkPolicy の L7 HTTP ルールで特定のパスとメソッドを制限するには、どの設定を使いますか？

- **A.** toEndpoints にパスとメソッドを指定する
- **B.** toPorts.rules.http にメソッドとパスを指定する
- **C.** ingress.http に直接指定する
- **D.** spec.http にルールを定義する

<details>
<summary>回答を表示</summary>

**回答: B. toPorts.rules.http にメソッドとパスを指定する**

HTTP ルールは ingress/egress の toPorts.rules.http の下に記述します。サポート対象の method/path/header フィールドを照合できます。ただし、ヘッダーがあることや Bearer token らしい文字列が含まれることだけでは、JWT を検証したり、エンドユーザーを認可したりできません。

</details>

### 5. Cilium の identity ベースポリシーには、どのような利点がありますか？

- **A.** Pod の IP アドレスが変わっても、ポリシーのラベルセレクターを安定して使える
- **B.** ラベルの代わりに MAC アドレスを使う
- **C.** すべての数値 ID が再起動後も永続する
- **D.** アドレスと ID の対応更新が不要になる

<details>
<summary>回答を表示</summary>

**回答: A. Pod の IP アドレスが変わっても、ポリシーのラベルセレクターを安定して使える**

ポリシーは手動管理する Pod IP の一覧ではなく、identity に関係するラベル集合を使います。複数の Pod が同じ identity を共有する場合がありますが、Cilium は引き続きアドレスと identity の対応を更新し、ID をガベージコレクションして再割り当てすることがあります。再起動しても数値 ID が永続する保証はありません。

</details>

### 6. Cilium の DNS L7 ポリシーで外部ドメインへのアクセスを制限するには、どのルールを使いますか？

- **A.** toFQDNs と dns ルールを組み合わせる
- **B.** toEndpoints だけを使う
- **C.** toCIDR だけを使う
- **D.** toEntities だけを使う

<details>
<summary>回答を表示</summary>

**回答: A. toFQDNs と dns ルールを組み合わせる**

DNS ルールは問い合わせ先を選択した resolver に制限します。toFQDNs とポートルールは、学習したアドレスへの接続を別途制御します。実際の UDP/TCP resolver の動作と search-list による名前解決も考慮してください。Service 名には Service と namespace の両方のラベルが含まれ、DNS を許可しても、あらゆる接続が許可されるわけではありません。

</details>

### 7. default-deny ポリシーを導入するとき、何を許可すべきですか？

- **A.** すべての外部宛て通信
- **B.** 実際の resolver や必要な probe など、ワークロードが必要とする依存先を明示する
- **C.** 常にホストネットワーク上のすべての通信
- **D.** DNS が過去に返したすべてのアドレス

<details>
<summary>回答を表示</summary>

**回答: B. 実際の resolver や必要な probe など、ワークロードが必要とする依存先を明示する**

ワークロードとネットワーク構成から確認できた依存先だけを許可します。たとえば、実際に使用する DNS resolver への UDP/TCP 53 番ポートや、必要な probe などです。ホストネットワークへの包括的なアクセス許可が常に必要なわけではありません。Cilium policy の方向別ルール配列が空の場合は、enableDefaultDeny を明示的に設定してください。

</details>

### 8. SPIRE における workload attestation の役割は何ですか？

- **A.** 証明書の発行
- **B.** ワークロード ID の検証
- **C.** ネットワークポリシーの適用
- **D.** 通信の暗号化

<details>
<summary>回答を表示</summary>

**回答: B. ワークロード ID の検証**

SPIRE Agent は、設定された attestor/selector を使ってワークロードを検証します。SPIRE Server は Agent を検証し、SVID に署名します。Cilium の out-of-band 統合では、委任された ID の取得と、Cilium のセキュリティ ID に対応するエントリーも使います。これはアプリケーションのペイロードを自動的に暗号化する機能ではありません。

</details>

### 9. audit mode でネットワークポリシーをテストすると、Cilium はどのように動作しますか？

- **A.** すべての通信をブロックする
- **B.** ポリシー違反を記録するが、通信は許可する
- **C.** ポリシーを完全に無効にする
- **D.** アラートだけを送信する

<details>
<summary>回答を表示</summary>

**回答: B. ポリシー違反を記録するが、通信は許可する**

実際に変更可能なエンドポイントオプション PolicyAuditMode は、分離したエンドポイントでのテストにおいて、監査対象 datapath のポリシー適用を切り替えます。cilium.io/audit-mode は、ポリシーごとに指定できるサポート対象の annotation ではありません。テスト後に通常の enforcement に戻し、L7 の動作は別途確認してください。enableDefaultDeny:false も、あらゆる場合に使える audit mode ではありません。

</details>

### 10. 3 層バックエンドの最小権限ポリシーでは、何をモデル化すべきですか？

- **A.** 制限なしのすべての通信
- **B.** 必要なフロントエンドからの ingress、データベースへの egress、DNS などの明示的な依存先
- **C.** フロントエンドからの通信も含め、すべての ingress を許可しない
- **D.** インターネットへの無制限アクセス

<details>
<summary>回答を表示</summary>

**回答: B. 必要なフロントエンドからの ingress、データベースへの egress、DNS などの明示的な依存先**

バックエンドは、必要なフロントエンドの送信元、データベースの宛先、DNS などの明示的な依存先だけを許可します。ガイドのデータベース用ポリシーでは、egress の default-deny を明示的に有効化し、egress の許可ルールを設けていません。ステートフルな応答通信は可能です。ネットワーク分離だけでは、アプリケーション認可やデータ損失防止にはなりません。

</details>

### 11. IPsec の keyRotationDuration: 5m は何を意味しますか？

- **A.** 5 分ごとに新しい鍵を生成する
- **B.** すべてのワークロード証明書を 5 分ごとにローテーションする
- **C.** 鍵の変更後に、切り替えと旧鍵の削除に使う猶予期間を設ける
- **D.** 1 つのグローバル鍵を無期限に再利用する

<details>
<summary>回答を表示</summary>

**回答: C. 鍵の変更後に、切り替えと旧鍵の削除に使う猶予期間を設ける**

IPsec の keyRotationDuration は、鍵素材の変更後に切り替えと旧鍵の削除を行うための猶予期間を制御します。定期的に鍵を生成する設定ではありません。サポートされている協調的な鍵/ID ローテーション手順と、末尾に '+' を付けるトンネル単位の派生鍵形式を使用してください。一方、WireGuard はノードが生成する鍵ペアを管理します。

</details>

### 12. drop の理由を調べる前に、Hubble で drop された flow を選択するコマンドはどれですか？

- **A.** hubble observe --verdict FORWARDED
- **B.** hubble observe --verdict DROPPED
- **C.** hubble policy list
- **D.** hubble status --violations

<details>
<summary>回答を表示</summary>

**回答: B. hubble observe --verdict DROPPED**

DROPPED は、複数の原因で drop された flow を選択します。ポリシー拒否として報告された drop を調べる場合は --drop-reason-desc POLICY_DENIED を追加し、L7 やアプリケーション側の失敗は別途確認してください。AUDIT は別の verdict です。--last で指定する履歴には上限があり、Relay 経由でも Hubble instance ごとに結果が返される場合があります。

</details>
