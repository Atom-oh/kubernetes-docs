# Linkerd 可観測性クイズ

[可観測性ガイド](../../../service-mesh/linkerd/05-observability.md) に基づいています（2026 年 9 月 11 日確認）。

### 1. Linkerd の主要な HTTP サービスメトリクス 3 種に含まれないものはどれですか？

- A. 成功率
- B. リクエスト率
- C. レイテンシー
- D. CPU 使用率

<details>
<summary>解答を表示</summary>

**解答: D**

**解説:** 3 種のメトリクスは、プロキシが分類する成功率、リクエスト率、レイテンシーです。CPU やキャパシティは追加の運用情報です。これは、プロキシや別の収集機構からプロセス／リソースメトリクスを取得できないという意味ではありません。暗号化された TCP トラフィックから、HTTP サービスメトリクスが自動的に得られるわけでもありません。

</details>

### 2. `linkerd viz stat` の標準テーブル列ではないものはどれですか？

- A. SUCCESS
- B. RPS
- C. LATENCY_P99
- D. ERROR_TYPE

<details>
<summary>解答を表示</summary>

**解答: D**

**解説:** このガイドが対象とするリリースでは、`MESHED`、`SUCCESS`、`RPS`、レイテンシーの各パーセンタイル、`TCP_CONN` が表示されます。wide 出力ではプロキシのバージョン一覧ではなく、トランスポートのバイトレートが追加されます。エラーの調査には、適切なポリシー、Tap、ログ、メトリクスを使ってください。

</details>

### 3. `linkerd viz tap` でできることは何ですか？

- A. ネットワークパケットを完全にキャプチャする
- B. 対応するリクエストをライブストリームで観察する
- C. プロキシのポリシーを自動変更する
- D. 証明書を更新する

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** Tap は対象を限定した、またはサンプリングされたトラフィックの観察機能であり、完全な監査記録ではありません。`max-rps` は Tap で観察するレートの上限で、アプリケーションの全トラフィックを制限するものではありません。現在の Tap には `--from` や `--show-headers` フラグはありません。対応するセレクターを使い、リクエストメタデータへのアクセスを保護してください。

</details>

### 4. 従来の ServiceProfile でルートに名前を付けると、何が可能になりますか？

- A. ディスク I/O の計測
- B. ルート単位のメトリクス収集
- C. 分散トレース全体の自動生成
- D. すべてのメソッドで必須のリトライ

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** ServiceProfile はルート単位のメトリクスと `viz routes` ビューを提供します。これは互換性のために残されているインターフェイスであり、現在の outbound HTTPRoute の信頼性設定より優先されることがあります。可観測性のためにプロファイルを追加しても、安全でないリトライを暗黙に有効化したり、既存ポリシーを上書きしたりしないでください。

</details>

### 5. ガイドでは、既存の既定 Viz Prometheus にローカルからどうアクセスしますか？

- A. 認証なしの NodePort を公開する
- B. パブリック LoadBalancer を作成する
- C. loopback に bind して `kubectl port-forward` を使う
- D. パブリック URL があると仮定する

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** 例では、既存の Prometheus Service を `127.0.0.1` に port-forward します。Prometheus を新規インストールしたり、パブリックアクセス用の認証を構成したりはしません。他のワークロードからアクセスする場合は、該当するネットワーク設定と Linkerd の認可設定も必要です。

</details>

### 6. アプリケーションの例で使う W3C trace context の組み合わせはどれですか？

- A. `x-request-id` と `Authorization`
- B. `x-b3-traceid` と `x-b3-spanid`
- C. `traceparent` と `tracestate`
- D. `x-linkerd-proxy` と `Cookie`

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** Linkerd は W3C と B3 の両方をサポートし、両方が存在する場合は W3C を優先します。`x-request-id` は相関 ID であり、必須のトレース形式ではありません。ヘッダーを伝播させるだけではアプリケーション span は作られず、サンプリングやエクスポートも構成されません。これらの処理には適切なトレーシングライブラリを使ってください。

</details>

### 7. `linkerd viz top` は何を集計しますか？

- A. CPU 使用率順に並べた Pod
- B. Tap で観察したライブのリクエスト経路／ルート
- C. 過去のすべてのエラーメッセージ
- D. 最新のコンテナログ

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** `top` は、サンプリング／レート制限と対応フィルターの範囲内でライブトラフィックを集計します。`hide-sources` は送信元の列を隠す設定であり、ヘッダーを制御するものではありません。ここでの観察結果は、保持された Prometheus メトリクスや完全なリクエスト監査の代わりにはなりません。

</details>

### 8. プロキシの診断ログレベルを変更するアノテーションはどれですか？

- A. `config.linkerd.io/log-level`
- B. `config.linkerd.io/proxy-log-level`
- C. `linkerd.io/proxy-log`
- D. `proxy.linkerd.io/log-level`

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** `proxy-log-level` は診断ログのフィルターを制御し、`proxy-log-format` は診断ログの形式を制御します。HTTP アクセスログは `config.linkerd.io/access-log:json` または `apache` で別途有効にします。Pod template の一部だけを示したものはパッチ／断片であり、完全な Deployment ではありません。

</details>

### 9. 期間を区切った成功率は、どのように計算すべきですか？

- A. 累積成功カウンターと累積総数を rate なしで割る
- B. 存在しない `success_total` カウンターを使う
- C. 同じ対象範囲で成功レスポンス率を総レスポンス率で割り、成功系列の欠落と総数が正である場合を適切に扱う
- D. 存在しない `success_rate` メトリクスの平均を取る

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** 対象とする通信方向と、ワークロード／クラスターの範囲を揃えてください。成功がない期間でも、成功系列が存在しない場合の成功率は 0 になる必要があります。データが欠落している、またはアイドル状態であることを 100% の成功として扱ってはいけません。プロキシの HTTP 分類では 400 が成功に数えられる場合があるため、ビジネス上の SLI と照らして意図的に選んでください。

</details>

### 10. 現在のトレーシング構成で Jaeger はどのような役割を担えますか？

- A. Kubernetes メトリクスの検出を置き換える
- B. アプリケーションのアクセスログだけを集約する
- C. 別途運用するバックエンドとして分散トレースを収集、保存、検索する
- D. トラフィックを自動的に分割する

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** Linkerd-Jaeger 拡張機能は 2.19 で削除されました。現在の Linkerd では OpenTelemetry 対応コレクターを構成し、ここで示す Helm chart の手順ではメッシュ ID も設定します。バックエンドの UI が表示できるだけでは、アプリケーション／プロキシの span が届いていることや、トレースが完全であることの証明にはなりません。

</details>

### 11. Viz がコンテナログビューアーだと仮定せず、`kubectl logs` またはログシステムから確認すべきものは何ですか？

- A. ワークロードのトポロジー
- B. Deployment のメトリクス
- C. Pod のコンテナログ
- D. ServiceProfile のルートメトリクス

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** Viz はワークロードやトラフィックのビュー、トポロジー、Tap を提供します。診断ログとアクセスログは別のデータです。これらのビューを調べる手順だけでは、原因特定、修正、検証までは完了しません。インシデントが自動解決されるわけではありません。

</details>

### 12. Viz をブラウザーからアクセスできる既存の外部 Grafana に接続する設定はどれですか？

- A. `grafana.external:true`
- B. `grafana.externalUrl:https://grafana.example.com/`
- C. `grafana.enabled:false`
- D. `monitoring:external`

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** 現在の Viz は Grafana をインストールしません。外部リンクには `externalUrl` を指定します。`grafana.url` はクラスター内の reverse proxy を使う設定で、root／subpath の追加構成が必要です。どちらの設定も Grafana の作成、データソースの構成、Prometheus へのアクセス許可は行いません。

</details>
