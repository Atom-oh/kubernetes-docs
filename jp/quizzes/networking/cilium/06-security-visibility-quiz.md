# Cilium セキュリティと可視性クイズ

> **レビュー時の基準**: Cilium 1.20.3、Hubble CLI 1.20.2
> **最終レビュー日**: 2026年10月16日

[ガイドに戻る](../../../networking/cilium/06-security-visibility.md)

## Network Policy の基本

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

1. **CiliumNetworkPolicy は標準の Kubernetes NetworkPolicy をどのように拡張しますか？**

   - A) Pod を選択できない
   - B) サポートされる L7 プロトコルのルールを追加できる
   - C) ノードのみを保護する
   - D) レイテンシの低下を保証する

   <details>
   <summary>解答を表示</summary>

   **解答: B) サポートされる L7 プロトコルのルールを追加できる**

   標準の NetworkPolicy は L3/L4 の接続を制御します。Cilium は HTTP や DNS のポリシーなどの機能を追加しますが、API の選択によって性能が保証されるわけではありません。

   </details>

2. **CiliumNetworkPolicy で使用する API バージョンはどれですか？**

   - A) networking.k8s.io/v1
   - B) cilium.io/v2
   - C) policy.cilium.io/v1
   - D) network.cilium.io/v1

   <details>
   <summary>解答を表示</summary>

   **解答: B) cilium.io/v2**

   API group は cilium.io で、この章では提供されているポリシーバージョン v2 を使用します。

   </details>

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

3. **namespace 内の CiliumNetworkPolicy で `endpointSelector` が選択する対象は何ですか？**

   - A) ポリシーの namespace 内で条件に一致する endpoint
   - B) すべての Kubernetes ノード
   - C) Prometheus サーバー
   - D) LoadBalancer Service のみ

   <details>
   <summary>解答を表示</summary>

   **解答: A) ポリシーの namespace 内で条件に一致する endpoint**

   これはポリシーの適用対象となる endpoint を指定します。ノードポリシーでは、別の仕組みである clusterwide の `nodeSelector` を使用します。

   </details>

4. **`policyTypes: [Ingress]` を指定した標準 NetworkPolicy で、受信を許可するルールが含まれない値はどれですか？**

   - A) `ingress: [{}]`
   - B) `ingress: []`
   - C) `ingress: [{from: [{}]}]`
   - D) すべての送信元アドレスを許可するルール

   <details>
   <summary>解答を表示</summary>

   **解答: B) `ingress: []`**

   空のリストは許可ルールを含みません。空のルールオブジェクトはすべての受信を許可します。ほかに適用される許可ポリシーは引き続き加算的に作用します。

   </details>

5. **選択した Pod に対する egress ポリシーが制御する方向はどれですか？**

   - A) 受信接続のみ
   - B) 送信接続
   - C) プロセス内のトラフィックのみ
   - D) API server の応答のみ

   <details>
   <summary>解答を表示</summary>

   **解答: B) 送信接続**

   Egress は外向きの接続を制御します。隔離された Pod では、実際の DNS resolver など依存先への明示的な許可が必要です。

   </details>

## L7 ポリシー

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

6. **Cilium の HTTP ポリシーで、リクエストの照合に使えないフィールドはどれですか？**

   - A) Path
   - B) Method
   - C) Headers
   - D) Response latency

   <details>
   <summary>解答を表示</summary>

   **解答: D) Response latency**

   HTTP ポリシーは、サポートされるリクエスト属性を照合します。応答時間を観測できても、レイテンシが HTTP 許可ルールのフィールドになるわけではありません。

   </details>

7. **例にある `toFQDNs` ポリシーが DNS 応答を学習するには何が必要ですか？**

   - A) TCP 443 のルールだけ
   - B) 任意の外部 IP だけ
   - C) 到達可能な resolver と、対応する DNS proxy ルール
   - D) Kafka topic のルール

   <details>
   <summary>解答を表示</summary>

   **解答: C) 到達可能な resolver と、対応する DNS proxy ルール**

   DNS の許可/DNS proxy による観測と、その後の宛先 IP の許可は別々です。この例では、検証済みの resolver endpoint への UDP および TCP の DNS 通信を扱います。

   </details>

8. **DNS の `matchPattern` が提供する機能は何ですか？**

   - A) ポートの割り当て
   - B) ドメイン名のワイルドカード照合
   - C) JWT 署名の検証
   - D) 悪意のあるドメインの自動評価

   <details>
   <summary>解答を表示</summary>

   **解答: B) ドメイン名のワイルドカード照合**

   サポートされるワイルドカード構文を使って、クエリ/ドメイン名を照合します。脅威インテリジェンスのフィードを取得する機能ではありません。

   </details>

9. **ここで扱う HTTP ルールを実装する proxy はどれですか？**

   - A) kube-proxy
   - B) Envoy
   - C) Prometheus
   - D) Hubble Relay

   <details>
   <summary>解答を表示</summary>

   **解答: B) Envoy**

   Cilium は HTTP ポリシーに Envoy を統合します。DNS ポリシーは DNS proxy を使用するため、すべての L7 ルールを Envoy のルールとして説明できるわけではありません。

   </details>

10. **以前の Cilium L7 ポリシー機能のうち、現行 API にないものはどれですか？**

   - A) HTTP method の照合
   - B) HTTP path の照合
   - C) Kafka topic のルール
   - D) DNS 名のルール

   <details>
   <summary>解答を表示</summary>

   **解答: C) Kafka topic のルール**

   Kafka の L7 ポリシーは削除されました。古い Kafka ルールを現行の CiliumNetworkPolicy リソースにコピーしないでください。

   </details>

## 暗号化とセキュリティ

11. **Cilium のノード間トランスポート暗号化モードの組み合わせはどれですか？**

   - A) IPsec と WireGuard
   - B) HTTP と DNS
   - C) Relay と Grafana
   - D) SYN と ACK

   <details>
   <summary>解答を表示</summary>

   **解答: A) IPsec と WireGuard**

   必要なモードとその前提条件を選択してください。SPIRE による相互認証と、beta の ztunnel によるワークロード mTLS は、適用範囲の異なる別機能です。

   </details>

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

12. **この章のデフォルトの WireGuard ノードトンネルプロファイルが対象とする通信はどれですか？**

   - A) 任意の外部トラフィックを含むすべてのパケット
   - B) ノード間を通過する、サポート対象の Cilium 管理下 Pod トラフィック
   - C) トンネルを経由する同一ノード上のすべての Pod トラフィック
   - D) 例外のないすべてのホストトラフィック

   <details>
   <summary>解答を表示</summary>

   **解答: B) ノード間を通過する、サポート対象の Cilium 管理下 Pod トラフィック**

   同一ノード上のトラフィックは、このノードトンネルを使いません。ノード間暗号化は別の beta オプションであり、control plane の通信は対象外です。アプリケーション TLS が引き続き必要な場合もあります。

   </details>

13. **Cilium Host Firewall が保護する対象は何ですか？**

   - A) ブラウザーの JavaScript のみ
   - B) ホストのネットワークトラフィック
   - C) すべてのコンテナ syscall を自動的に
   - D) Grafana のパスワードデータベース

   <details>
   <summary>解答を表示</summary>

   **解答: B) ホストのネットワークトラフィック**

   Host policy はネットワーク制御です。プロセスや syscall の実行時制御には、設定済みの Tetragon policy など別の仕組みを使います。暗号化との互換性も確認してください。

   </details>

14. **Authorization ヘッダーに一致するだけで、その bearer token を認証できますか？**

   - A) はい。ヘッダーがあれば JWT の検証も完了する
   - B) はい。正規表現のような値で署名が検証される
   - C) いいえ。ヘッダーの照合では token は検証されない
   - D) はい。HTTP がポート 8443 を使う場合

   <details>
   <summary>解答を表示</summary>

   **解答: C) いいえ。ヘッダーの照合では token は検証されない**

   実際の認証/認可のロジックを使用してください。値を持つ `headers` 文字列はリテラル照合を行います。また、TLS のポート番号だけでは payload は復号されません。

   </details>

15. **Cilium のセキュリティ identity を主に決めるものは何ですか？**

   - A) 常に一意で変わらないことが保証された Pod IP
   - B) セキュリティ上重要なラベルの集合
   - C) ユーザーのブラウザー cookie
   - D) 最後に観測された HTTP 応答

   <details>
   <summary>解答を表示</summary>

   **解答: B) セキュリティ上重要なラベルの集合**

   セキュリティ上重要なラベルが同じ endpoint は、同じ identity を共有できます。identity ベースのポリシーだけでは、エンドユーザー認証や通信の暗号化は提供されません。

   </details>

## 可視性とモニタリング

16. **Hubble の主な役割は何ですか？**

   - A) ネットワークフローの可観測性
   - B) コンテナイメージのデプロイ
   - C) ルールのない完全な WAF
   - D) 疑わしい Pod をすべて自動隔離すること

   <details>
   <summary>解答を表示</summary>

   **解答: A) ネットワークフローの可観測性**

   Hubble はフローのメタデータ、判定結果、サポートされるプロトコルの観測情報を提供します。検出ルールと応答連携には別途構成が必要です。

   </details>

17. **Hubble UI が提供する機能はどれですか？**

   - A) アプリケーション認証情報のローテーション
   - B) サービス依存関係マップとフローの探索
   - C) Slack へのインシデント自動通知
   - D) 実行時 syscall policy のインストール

   <details>
   <summary>解答を表示</summary>

   **解答: B) サービス依存関係マップとフローの探索**

   UI は Relay を通じてネットワーク観測情報を可視化します。通知、デプロイ、実行時ポリシーを管理する controller ではありません。

   </details>

18. **frontend Pod に一致するどちらかの endpoint のフローイベントを追跡するコマンドはどれですか？**

   - A) `hubble observe --pod cilium-security-demo/frontend --follow`
   - B) `hubble watch --pod frontend`
   - C) `cilium hubble status`
   - D) `hubble observe --pod app=frontend`

   <details>
   <summary>解答を表示</summary>

   **解答: A) `hubble observe --pod cilium-security-demo/frontend --follow`**

   namespace を含む Pod 名を指定し、ストリームを追跡するには `--follow` を使います。Pod 名は label selector ではありません。方向と label の絞り込みには別のフラグを使用します。

   </details>

19. **図示されている Hubble metric plugin が提供しないものはどれですか？**

   - A) HTTP 応答ステータスの件数
   - B) TCP flag の件数
   - C) 観測された drop の件数
   - D) コンテナの CPU 使用率

   <details>
   <summary>解答を表示</summary>

   **解答: D) コンテナの CPU 使用率**

   これらの plugin が観測するのはネットワーク/プロキシイベントです。TCP plugin は一般的な同時接続数や RTT の metric を提供しません。また、観測の欠落や喪失も考慮してください。

   </details>

20. **Prometheus Operator がインストール済みの場合、ServiceMonitor 経由で Hubble を scrape するには何が必要ですか？**

   - A) Grafana dashboard を import するだけ
   - B) 静的な public `hubble-metrics.cilium.io:9091` target
   - C) metrics を有効にし、Prometheus が選択する ServiceMonitor を用意する
   - D) 無関係な ConfigMap を作成するだけ

   <details>
   <summary>解答を表示</summary>

   **解答: C) metrics を有効にし、Prometheus が選択する ServiceMonitor を用意する**

   chart の headless Service は、通常 9965 の名前付き `hubble-metrics` port を公開します。Prometheus の namespace/label selector と endpoint への到達性を一致させる必要があります。

   </details>
