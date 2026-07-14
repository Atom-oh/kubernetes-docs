# Prometheus Alertmanager クイズ

Prometheus Alertmanager についての理解を確認するためのクイズです。

---

1. Alertmanager でアラートが Firing になる前に経る中間状態は何ですか？
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>回答を表示</summary>

**回答: B) Pending**

**解説:**
Prometheus アラートには Inactive、Pending、Firing の3つの状態があります。アラートルールの条件（expr）が満たされると、まず Pending 状態に遷移し、`for` 句で指定された期間にわたって条件が継続すると、Firing 状態に遷移して Alertmanager に送信されます。この仕組みにより、一時的なスパイクによる不要なアラートを防止できます。

</details>

---

2. Alertmanager のルーティング設定における `group_wait`、`group_interval`、`repeat_interval` の役割を正しく説明しているものはどれですか？
   - A) group_wait: アラートグループの最初の通知を送信する前の待機時間
   - B) group_interval: 同一アラートを再送信する間隔
   - C) repeat_interval: 新しいアラートがグループに追加された際の待機時間
   - D) すべて同じ機能を実行する

<details>
<summary>回答を表示</summary>

**回答: A) group_wait: アラートグループの最初の通知を送信する前の待機時間**

**解説:**
- `group_wait`: 新しいアラートグループが作成されてから最初の通知を送信するまでの待機時間です。この期間中に同じグループに属する他のアラートを収集し、まとめて送信します。
- `group_interval`: 同じグループに新しいアラートが追加されたとき、次の通知を送信するまでの待機時間です。
- `repeat_interval`: まだ解決されていない同じアラートを再送信する間隔です。

</details>

---

3. Alertmanager の Inhibition 機能を正しく説明しているものはどれですか？
   - A) 特定の期間、すべてのアラートを無視する機能
   - B) 特定のアラートが Firing したときに、関連するアラートを抑制する機能
   - C) アラートの重大度を自動的に下げる機能
   - D) 重複するアラートを統合する機能

<details>
<summary>回答を表示</summary>

**回答: B) 特定のアラートが Firing したときに、関連するアラートを抑制する機能**

**解説:**
Inhibition は、特定の条件のアラート（source）が Firing したときに、関連するアラート（target）を抑制する機能です。たとえば、Node がダウンした場合、その Node に関連するすべての Pod アラートを抑制して、アラートストームを防ぐことができます。Silencing は、特定の期間アラートを無視する別の機能です。

</details>

---

4. PrometheusRule CRD の次のアラートルールは何を意味しますか？
   ```yaml
   - alert: HighCPU
     expr: node_cpu_usage > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU 使用率が 80% を超えると、アラートが直ちに Firing する
   - B) CPU 使用率が 80% を5分間継続して超えると、アラートが Firing する
   - C) CPU 使用率が5分ごとに確認され、80% を超えていればアラートが Firing する
   - D) CPU 使用率が 80% を超えてから5分後に、アラート通知が送信される

<details>
<summary>回答を表示</summary>

**回答: B) CPU 使用率が 80% を5分間継続して超えると、アラートが Firing する**

**解説:**
`for: 5m` 設定は、Firing 状態に遷移する前にアラート条件（expr）が5分間継続して満たされなければならないことを意味します。条件が最初に満たされると状態は Pending になり、5分間満たされ続けると Firing に遷移して Alertmanager に送信されます。これにより、一時的なスパイクによる不要なアラートを防止できます。

</details>

---

5. Alertmanager の receiver 設定における `send_resolved: true` は何を意味しますか？
   - A) 解決済みのアラートも receiver に送信する
   - B) アラートメッセージに解決方法を含める
   - C) アラートを自動的に解決済み状態に変更する
   - D) receiver にアラートを解決する権限を付与する

<details>
<summary>回答を表示</summary>

**回答: A) 解決済みのアラートも receiver に送信する**

**解説:**
`send_resolved: true` 設定は、アラートが解決されたとき（条件が満たされなくなったとき）に、receiver に解決通知を送信します。これにより、対応者は問題が解決されたことを把握できます。デフォルト値は receiver の種類によって異なりますが、一般的には有効にすることが推奨されます。

</details>

---

6. Alertmanager の高可用性設定で、クラスターのメンバー間の状態を同期するために使用されるプロトコルは何ですか？
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>回答を表示</summary>

**回答: C) Gossip**

**解説:**
Alertmanager クラスターは、メンバー間の状態を同期するために Gossip プロトコルを使用します。これにより、Silence 情報と通知ログ（nflog）をすべてのインスタンス間で共有でき、重複したアラート通知を防止します。クラスターを設定する際は、`--cluster.peer` フラグを使用して他のメンバーを指定します。

</details>

---

7. 次の Alertmanager ルーティング設定で、`severity=critical` と `team=infra` を持つアラートはどの receiver に送信されますか？
   ```yaml
   route:
     receiver: 'default'
     routes:
       - match:
           severity: critical
         receiver: 'critical-receiver'
       - match:
           team: infra
         receiver: 'infra-team'
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) critical-receiver と infra-team の両方

<details>
<summary>回答を表示</summary>

**回答: B) critical-receiver**

**解説:**
Alertmanager のルーティングはツリー構造で動作し、デフォルトでは最初に一致したルートで処理が終了します。この場合、`severity=critical` 条件が最初に一致するため、アラートは `critical-receiver` に送信されます。複数のルートに送信するには、`continue: true` 設定が必要です。

</details>

---

8. AlertmanagerConfig CRD の主な目的は何ですか？
   - A) Alertmanager のグローバル設定を定義する
   - B) namespace ごとにアラート設定を分離する
   - C) Prometheus アラートルールを定義する
   - D) Alertmanager クラスターを設定する

<details>
<summary>回答を表示</summary>

**回答: B) namespace ごとにアラート設定を分離する**

**解説:**
AlertmanagerConfig CRD は Prometheus Operator が提供するリソースで、Alertmanager の設定（receivers、routes、inhibition rules など）を namespace ごとに個別に管理できます。これにより、各チームはそれぞれの namespace 内でアラート設定を独立して管理できます。

</details>

---

9. Alertmanager で Silence を作成する適切なユースケースではないものはどれですか？
   - A) 計画されたメンテナンス中にアラートを抑制する
   - B) 既知の問題による繰り返しアラートを防止する
   - C) 特定のアラートを恒久的に無効化する
   - D) Deployment 中にアラートを抑制する

<details>
<summary>回答を表示</summary>

**回答: C) 特定のアラートを恒久的に無効化する**

**解説:**
Silence はアラートを一時的に抑制する機能で、必ず終了時刻を指定する必要があります。アラートを恒久的に無効化するには、アラートルール自体を変更または削除する必要があります。Silence の主なユースケースは、メンテナンス、Deployment、既知の問題の調査などの一時的な状況です。

</details>

---

10. 次のうち、Alertmanager テンプレートで使用できる有効な Go template 構文ではないものはどれですか？
    - A) <code v-pre>{{ .Labels.alertname }}</code>
    - B) <code v-pre>{{ if eq .Status "firing" }}Danger{{ end }}</code>
    - C) <code v-pre>{{ range .Alerts }}{{ .Labels.severity }}{{ end }}</code>
    - D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>

<details>
<summary>回答を表示</summary>

**回答: D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>**

**解説:**
Go template は三項演算子（`? :`）をサポートしていません。代わりに <code v-pre>{{ if }}</code> 文を使用する必要があります。正しい構文は次のとおりです。
```
{{ if gt (len .Annotations.description) 100 }}
  {{ slice .Annotations.description 0 100 }}...
{{ else }}
  {{ .Annotations.description }}
{{ end }}
```
Go template はパイプ（`|`）、条件分岐（`if`/`else`）、ループ（`range`）、組み込み関数などをサポートしています。

</details>

---

## 追加学習リソース

- [Prometheus Alerting ドキュメント](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alertmanager 設定](https://prometheus.io/docs/alerting/latest/configuration/)
- [Prometheus Operator - AlertmanagerConfig](https://prometheus-operator.dev/docs/user-guides/alerting/)
