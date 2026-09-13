# Datadog クイズ

> **最終更新**: September 13, 2026

1. Datadog SaaS でチームに残る責任は何ですか？

   - A) Agent をインストールした後は何もない
   - B) ダッシュボードの色を選ぶことだけ
   - C) Collector、identity、instrumentation、データ処理、monitor、コスト
   - D) Datadog の物理データベースサーバー

<details>
<summary>回答を表示</summary>

**回答: C**

SaaS はバックエンドを管理します。APM、profiling、logs、その他の製品にはそれぞれ異なる権限と課金があり、Agent がすべてを含むわけではありません。

</details>

2. credential/integration に関する正しい記述はどれですか？

   - A) 基本的な Agent ingestion には API key が必要で、application key と AWS account role は追加の特定機能に使用される
   - B) すべての Agent には application key と広範な AWS 読み取り role が必要である
   - C) IRSA を追加すると Datadog SaaS AWS integration が自動的に設定される
   - D) 推測した service-account 名で十分である

<details>
<summary>回答を表示</summary>

**回答: A**

external metrics provider には追加の API permission/key 設定が必要です。SaaS AWS integration では、承認済みの cross-account role/external ID を使用します。実際にレンダリングされた Agent SA を確認してください。

</details>

3. admission.datadoghq.com/enabled=true だけで APM SDK injection が証明されますか？

   - A) はい。すべての language/version を自動的に含みます
   - B) いいえ。SDK annotation または SSI target を設定し、新たに admission された Pod と実際の trace データを検証してください
   - C) はい。Cluster Agent namespace 内でも同様です
   - D) はい。trace socket が存在すれば可能です

<details>
<summary>回答を表示</summary>

**回答: B**

mutation/connection 設定と library injection は別のものです。現在のローカル injection は kube-system と Cluster Agent namespace を除外します。library、runtime、mount、security の互換性も依然として重要です。

</details>

4. application Pod は node DogStatsD Agent にどのように到達すべきですか？

   - A) 常に application の localhost を使用する
   - B) すべての UDP packet に API key を含める
   - C) 無関係な ConfigMap を作成する
   - D) mount された Linux UDS directory など、設定済みで到達可能な endpoint を使用する

<details>
<summary>回答を表示</summary>

**回答: D**

application の localhost は node Agent ではありません。UDS path、permission、SDK argument format は一致している必要があります。datagram は SaaS ingestion を確認応答せず、counter は exactly-once ledger ではありません。

</details>

5. 正しい metric の解釈はどれですか？

   - A) kubernetes.cpu.usage.total は percent である
   - B) 存在しないすべての legacy-catalogue metric は削除された
   - C) kubernetes.cpu.usage.total は nanocore であり、Kubelet restart metric は累積 gauge である
   - D) 繰り返し取得した restart sample を合計すると、新しい restart を数えられる

<details>
<summary>回答を表示</summary>

**回答: C**

system.cpu.idle は percent です。Kubelet と State Core には、有効な metric 名と tag がそれぞれ異なります。restart monitor の例では明示的に total を評価しており、最近の増加には reset を考慮した検証が必要です。

</details>

6. .as_count() の error-ratio path は何を計算しますか？

   - A) 時間集計された error count と total count の比率
   - B) すべての time-bucket ratio の合計
   - C) グローバルな p95
   - D) traffic がゼロの場合の自動的な 100% success

<details>
<summary>回答を表示</summary>

**回答: A**

sum aggregation と一致する group を使用します。helper は good/error count がゼロであることを明示的に出力します。traffic がゼロ、data が欠損、error がない traffic はそれぞれ異なる状態です。

</details>

7. 正しい OpenMetrics/log 設定の記述はどれですか？

   - A) 任意の ConfigMap は自動的に mount される
   - B) 一致する container annotation/current check field を使用する。Logs Grok rule では match_rules/support_rules を使用する
   - C) chart root の prometheus.enabled がすべてを設定する
   - D) Grok の camelCase key と snake_case key は同等である

<details>
<summary>回答を表示</summary>

**回答: B**

現在の OpenMetrics check は openmetrics_endpoint を使用します。datadog.confd は chart 所有の mount を提供し、standalone ConfigMap は自動的にはインストールされません。request-schema validation は live scrape や Grok parse ではありません。

</details>

8. 手動の trace-log correlation で保持すべきものは何ですか？

   - A) dd.trace_id だけを残し、他のすべての MDC field を削除する
   - B) 128-bit ID を任意に numeric cast した値
   - C) ハードコードされた成功した trace ID
   - D) 呼び出し元の既存 MDC context、string ID、実際の instrumentation/data の前提条件

<details>
<summary>回答を表示</summary>

**回答: D**

helper は application code が例外を送出した場合でも context を復元します。これは同期的です。自動 injection/parsing、一貫した service tag、利用可能な trace は別の要件です。

</details>

9. 50 個の service を 50 台の APM host として価格計算することの問題は何ですか？

   - A) APM は常に無料である
   - B) log ingestion が log 請求額のすべてである
   - C) service と請求対象 host は異なる単位であり、製品/contract の allotment と usage を数える必要がある
   - D) すべての cluster には host が 1 台ある

<details>
<summary>回答を表示</summary>

**回答: C**

以前の見積もりは実測された請求額ではありませんでした。indexing/retention、span allotment、custom metric、その他の製品も重要です。nonLocalTraffic は到達可能性であり、cost quota ではありません。

</details>

10. 正しい Watchdog/SLO/diagnostic の実践はどれですか？

   - A) Watchdog insight によって page が配信されたことが証明される
   - B) SLO model と good/total policy を一致させ、routing をテストし、共有前にローカル diagnostic bundle を確認する
   - C) ローカル flare は自動的に upload を許可する
   - D) trace がない場合はすべての DD_ environment value を出力する

<details>
<summary>回答を表示</summary>

**回答: B**

Datadog は metric-、monitor-、time-slice SLO をサポートします。notification と no-data の挙動には検証が必要です。env dump には key が露出する可能性があり、--local は最初の flare collection をローカルに保持します。

</details>

---

[ガイドに戻る](../../../observability/metrics/05-datadog.md)
