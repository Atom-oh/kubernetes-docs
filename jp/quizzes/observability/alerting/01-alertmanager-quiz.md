# Prometheus Alertmanager クイズ

> **最終更新**: September 13, 2026

---

1. Prometheus のアラートルールに正の `for` 期間がある場合、Firing の前にどの状態になりますか？
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>回答を表示</summary>

**回答: B) Pending**

Pending は Alertmanager の評価段階ではなく、Prometheus ルール評価に属します。設定された期間にわたり、連続する評価で条件が成立し続ける必要があります。`for` がない場合（またはゼロの場合）は、最初に一致した評価で Firing になります。通知のグループ化には別途遅延があり、式が一致しなくなった後も `keep_firing_for` により Firing を維持できます。

</details>

---

2. グループ化タイマーに関する正しい説明はどれですか？
   - A) `group_wait` は新しいグループの最初の通知を遅延させる。
   - B) `group_interval` は変更のないアラートに対する繰り返し間隔のみである。
   - C) `repeat_interval` は新たに追加されたアラートの最初の遅延である。
   - D) 3 つのタイマーはすべて同一である。

<details>
<summary>回答を表示</summary>

**回答: A) `group_wait` は新しいグループの最初の通知を遅延させる。**

`group_interval` は、変更および解決済みアラートを含む、後続のグループチェックをスケジュールします。`repeat_interval` は、変更のない Firing アラートに対する繰り返し通知を制御し、グループ間隔ごとに確認されます。`group_interval` の倍数を使用してください。通知ログの保持設定により、繰り返し通知が早まる場合があります。これらのタイマーは Prometheus ルールの `for` とは独立しています。

</details>

---

3. inhibition は何を行いますか？
   - A) 時間枠の間、すべてのアラートを無視する。
   - B) 一致する source アラートがアクティブな間、一致する target 通知を抑制する。
   - C) アラートの severity を自動的に変更する。
   - D) Prometheus から重複アラートを削除する。

<details>
<summary>回答を表示</summary>

**回答: B) 一致する source アラートがアクティブな間、一致する target 通知を抑制する。**

inhibition は、基になるアラート条件ではなく、通知の適格性を変更します。source/target matcher と等価ラベルは、意図した依存関係を表す必要があります。存在しない等価ラベルは空の値と同様に比較されるため、無関係なアラートを抑制しないよう `cluster` や `node` などの空でない相関ラベルを必須にしてください。ルールリストの順序は優先順位の仕組みではありません。

</details>

---

4. このルールの `for` は何を意味しますか？

   ```yaml
   - alert: HighCPU
     expr: 100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU が 80% を超えると直ちに通知する。
   - B) 複数回の評価にわたり条件が 5 分間継続した後に Firing になる。
   - C) CPU を 5 分ごとに 1 回だけ評価する。
   - D) 物理 CPU の上昇から正確に 5 分後の配信を保証する。

<details>
<summary>回答を表示</summary>

**回答: B) 複数回の評価にわたり条件が 5 分間継続した後に Firing になる。**

これは node-exporter の CPU カウンターがスクレイプされ、適切な評価間隔が設定されていることを前提としています。`for` はスクレイプ/評価間隔を設定せず、配信期限も保証しません。ラベルセットが変わると別のアラートとして識別されます。別の Firing 保持動作が適用されない限り、復旧すると Pending はリセットされます。CrashLoop の例では、最初に 5 分間の観測ウィンドウを使用し、その後 `for: 10m` を使用します。これにより再試行の間隔をつなぎ、一度限りの待機を除外しますが、lookback に関連したクリア遅延があります。

</details>

---

5. `send_resolved: true` は何を有効にしますか？
   - A) その integration の解決通知。
   - B) 自動修復手順。
   - C) アラート条件を正常に変更すること。
   - D) receiver が cluster を修復するための権限。

<details>
<summary>回答を表示</summary>

**回答: A) その integration の解決通知。**

これは選択した integration の解決通知を制御します。デフォルトは receiver により異なります。Resolved はアラートライフサイクルの状態であり、Service が復旧したことを独立して証明するものではありません。式の変更、データ欠損、またはクライアントの更新/期限切れ動作もその状態に影響する可能性があります。

</details>

---

6. Alertmanager cluster 状態の同期にはどのプロトコルが使用されますか？
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>回答を表示</summary>

**回答: C) Gossip**

Gossip は、結果整合性を伴って silence と通知ログの状態を共有します。同じアラートをすべての replica に送信してください。Gossip レイヤーはその fan-out を置き換えるものではありません。重複排除はベストエフォートであり、ネットワークパーティションでは重複が発生する可能性があります。これは exactly-once 配信でも、すべての通知喪失を防ぐ保証でもありません。

</details>

---

7. `severity=critical, team=infra` の場合、以下ではどの route が選択されますか？

   ```yaml
   route:
     receiver: default
     routes:
       - matchers: ['severity="critical"']
         receiver: critical-receiver
       - matchers: ['team="infra"']
         receiver: infra-team
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) 両方の child route

<details>
<summary>回答を表示</summary>

**回答: B) critical-receiver**

デフォルトの `continue: false` では、最初に一致した sibling により sibling の走査が停止します。後続の sibling も考慮するには、そこに `continue: true` を設定します。これはラベルルーティングのみをテストしています。非アクティブまたはミュートされた route でも走査を停止できるため、時間枠の動作には別途確認が必要です。1 つの receiver 内に複数の integration があっても `continue` は必要ありません。Provider の宛先ルールも適用されます。Slack の incoming-webhook URL は channel に紐づくため、通常用と critical 用の channel には、channel override ではなく別々の webhook ファイル/Secret キーが必要です。

</details>

---

8. namespace が所有する AlertmanagerConfig は何を可能にしますか？
   - A) すべての namespace 制限を自動的に回避する。
   - B) Alertmanager instance によって選択される構造化された route/receiver を管理する。
   - C) PromQL の recording および alert ルールを定義する。
   - D) Gossip peer の設定を置き換える。

<details>
<summary>回答を表示</summary>

**回答: B) Alertmanager instance によって選択される構造化された route/receiver を管理する。**

Operator は object のラベルと namespace を選択する必要があり、参照される Secret は必要な namespace 内に存在する必要があります。その matcher 戦略が namespace の強制方法を制御します。確認済みの Operator 0.93.1 chart は `v1alpha1` を提供しています。必須の API アップグレードを勝手に想定しないでください。グローバル設定の使用は別の選択肢であり、namespace ラベルの一致はアラート送信者の認証ではありません。

</details>

---

9. Silence の適切な用途ではないものはどれですか？
   - A) 計画的なメンテナンス。
   - B) 期間を限定した調査ウィンドウ。
   - C) アラートルールを恒久的に無効化すること。
   - D) レビュー済みの Deployment ウィンドウ。

<details>
<summary>回答を表示</summary>

**回答: C) アラートルールを恒久的に無効化すること。**

silence には有限の終了時刻が必要であり、通知に影響します。期限切れにより抑制は終了します。保存済みの silence 履歴から直ちに削除されるわけではありません。恒久的なルール/ルーティングの変更には別途レビューが必要です。owner、理由、承認済みのスコープを記録してください。期限切れのリマインダーには、明示的に設定されたワークフローが必要です。

</details>

---

10. 無効な Go template 構文である式はどれですか？
   - A) `{{ .CommonLabels.alertname }}`
   - B) `{{ if eq .Status "firing" }}Danger{{ end }}`
   - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
   - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>回答を表示</summary>

**回答: D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

Go template はこの三項式をサポートしていません。root では、Alertmanager は CommonLabels/CommonAnnotations を含む Data を提供します。Labels/Annotations/StartsAt は、`range .Alerts` 内の個々の Alert に属します。以下の例では、Korean テキストを分断しかねない byte slice を避け、各 description を最大 100 rune に整形します。これは出力整形であり、機密データの redaction ではありません。

```text
{{ range .Alerts }}
{{ printf "%.100s" .Annotations.description }}
{{ end }}
```

</details>

---

## 追加の学習リソース

- [Alertmanager 0.34 の設定](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md)
- [通知テンプレートのリファレンス](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/notifications.md)
- [Prometheus Operator のアラート](https://prometheus-operator.dev/docs/developer/alerting/)

[ガイドに戻る](../../../observability/alerting/01-alertmanager.md)
