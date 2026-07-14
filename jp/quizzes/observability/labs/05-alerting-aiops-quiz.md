# Observability Lab Part 5: Alerting と AIOps クイズ

> **最終更新**: February 22, 2026

Observability End-to-End Lab Part 5 で取り上げた alerting と AIOps の概念に関する理解度を確認しましょう。

---

1. Alertmanager PrometheusRule の `for` フィールドは何を指定しますか？
   - A) アラート評価の間隔
   - B) pending 状態から firing 状態へ移行してアラートが発報するまで、条件が true のまま継続する必要がある期間
   - C) 条件が解消された後もアラートがアクティブな状態を維持する期間
   - D) 自動解決までのアラートの最大有効期間

<details>
<summary>回答を表示</summary>

**回答: B) pending 状態から firing 状態へ移行してアラートが発報するまで、条件が true のまま継続する必要がある期間**

**解説:**
`for` フィールドは、アラート発報のための期間しきい値を設定します。アラート条件が true になると、アラートは「pending」状態になります。条件が `for` で指定した期間全体にわたって true のままである場合にのみ、アラートは「firing」に移行して通知をトリガーします。これにより、短時間の一時的なスパイクに対するアラートを防止できます。たとえば、`for: 5m` は、アラートを発報する前に条件が連続 5 分間 true である必要があることを意味し、瞬間的な変動によるノイズを低減します。

</details>

---

2. Alertmanager のルーティングツリーは、どの receiver がアラートを処理するかをどのように決定しますか？
   - A) アラートは receiver 間にランダムに分配される
   - B) route は上から下へ評価され、アラートは label に基づいて一致し、最初に一致した route の receiver に送信される。より詳細な一致には child route を使用する
   - C) すべての receiver がすべてのアラートを同時に受信する
   - D) route はアラートの severity スコアに基づいて選択される

<details>
<summary>回答を表示</summary>

**回答: B) route は上から下へ評価され、アラートは label に基づいて一致し、最初に一致した route の receiver に送信される。より詳細な一致には child route を使用する**

**解説:**
Alertmanager のルーティングツリーは階層構造です。root route がすべてのアラートを受け取り、その後 child route がアラートの label に対する `match` または `match_re` を使用してフィルタリングします。route には、より詳細な一致のためにネストした child を含めることができます。デフォルトでは、アラートは条件を満たす最初の route に一致しますが、`continue: true` を使用すると複数の route に一致させることができます。これにより、高度なルーティングが可能になります。たとえば、critical アラートは PagerDuty に、warning は Slack に、チーム固有のアラートはそれぞれ異なる channel に送信できます。これらはすべて `severity`、`team`、`service` などの label に基づきます。

</details>

---

3. Grafana OnCall Escalation Chain はどのように機能しますか？
   - A) 通知するチームメンバーをランダムに選択する
   - B) 誰かがアラートを確認応答するまで、待機時間を伴う通知ステップの順序を定義し、異なるユーザーまたはグループへエスカレーションする
   - C) email 通知のみを送信する
   - D) Escalation Chain はカレンダー管理専用である

<details>
<summary>回答を表示</summary>

**回答: B) 誰かがアラートを確認応答するまで、待機時間を伴う通知ステップの順序を定義し、異なるユーザーまたはグループへエスカレーションする**

**解説:**
Grafana OnCall Escalation Chain はインシデント対応ワークフローを定義します。ステップ 1 では on-call engineer に Slack と電話で通知し、5 分待機した後、ステップ 2 で backup engineer にエスカレーションし、10 分待機した後、ステップ 3 で team lead にページングする場合があります。各ステップでは異なる通知 channel（Slack、SMS、電話、email）を使用でき、異なるユーザーまたは schedule を対象にできます。誰かが確認応答すると chain は停止するため、対応範囲を確保しながらアラート疲れを防止できます。

</details>

---

4. CloudWatch Alarms の evaluation period と datapoints 設定は何を制御しますか？
   - A) アラーム名と説明を制御する
   - B) evaluation period は metrics のチェック頻度を設定し、datapoints-to-alarm はアラームをトリガーするためにしきい値を超える必要がある期間数を指定する
   - C) dashboard 上のアラームの可視化にのみ影響する
   - D) これらの設定は metric math に置き換えられて非推奨になっている

<details>
<summary>回答を表示</summary>

**回答: B) evaluation period は metrics のチェック頻度を設定し、datapoints-to-alarm はアラームをトリガーするためにしきい値を超える必要がある期間数を指定する**

**解説:**
CloudWatch Alarms では、2 つの主要な設定を使用します。Period（evaluation period）は metrics 集計の時間粒度（例: 1 分、5 分）を定義し、「Datapoints to Alarm」は直近 N 期間のうち、しきい値を超える必要がある期間数を指定します。たとえば、1 分の期間で「5 回中 3 回」と設定した場合、直近 5 分のうち 3 分でしきい値を超えるとアラームがトリガーされます。この組み合わせにより、応答性とノイズ低減のバランスを調整できます。

</details>

---

5. CloudWatch Investigations はどのように AI ベースの根本原因分析を実行しますか？
   - A) 静的な runbook のみを提供する
   - B) ML model を使用して相関関係のある metrics、logs、traces を分析し、異常を特定して、裏付けとなる証拠とともに潜在的な根本原因を提示する
   - C) インシデントごとに手動で調査をトリガーする必要がある
   - D) EC2 instance でのみ動作する

<details>
<summary>回答を表示</summary>

**回答: B) ML model を使用して相関関係のある metrics、logs、traces を分析し、異常を特定して、裏付けとなる証拠とともに潜在的な根本原因を提示する**

**解説:**
CloudWatch Investigations（Amazon CloudWatch Application Signals の一部）は、machine learning を使用して問題を自動調査します。アラームまたは手動でトリガーされると、metrics、logs、traces 全体の telemetry signal を相関付け、インシデントと同時に発生した異常を特定します。関連リソースを分析し、パターンを検出して、confidence score と証拠への link を含む結果を提示します。これにより、手動調査では人間が見落とす可能性のある関連データを明らかにし、平均診断時間を短縮します。

</details>

---

6. Lambda ベースの AIOps Agent は通常、インシデント分析のためにどの順序で telemetry を収集しますか？
   - A) logs、metrics、traces の順に逐次収集する
   - B) 合計収集時間を最小化するため、metrics、logs、traces の telemetry 収集を並列に実行する
   - C) traces のみを収集し、metrics と logs は無視する
   - D) 収集順序はランダムで予測できない

<details>
<summary>回答を表示</summary>

**回答: B) 合計収集時間を最小化するため、metrics、logs、traces の telemetry 収集を並列に実行する**

**解説:**
効果的な AIOps agent は、レイテンシーを最小化するために telemetry を並列収集します。インシデントによって Lambda function がトリガーされると、metrics（error rate、latency）については Prometheus/AMP、関連 logs（error message、stack trace）については Loki/CloudWatch、分散 traces（request flow、bottleneck）については Tempo/X-Ray を同時に query します。並列収集により、agent は包括的な context を迅速に取得でき、AI による分析と対応を高速化できます。これは async/await pattern または並行 API call を使用して実装されます。

</details>

---

7. Bedrock Claude を SRE expert として使用する際、system prompt を設計するための主要な原則は何ですか？
   - A) prompt を可能な限り短くする
   - B) role を明確に定義し、system architecture の context を提供し、output format を指定し、一般的な障害パターンに関する domain 固有の知識を含める
   - C) system prompt には一般的な指示のみを含めるべきである
   - D) prompt 内で特定の technology に言及しない

<details>
<summary>回答を表示</summary>

**回答: B) role を明確に定義し、system architecture の context を提供し、output format を指定し、一般的な障害パターンに関する domain 固有の知識を含める**

**解説:**
効果的な SRE system prompt には、明確な role 定義（「あなたは Kubernetes インシデントを分析する SRE expert です」）、system context（architecture、tech stack、典型的な問題）、構造化された output format（仮説、証拠、推奨アクション、runbook link）、domain knowledge（一般的な障害パターン、エスカレーション基準、service dependency）が含まれます。過去のインシデントと解決策の例を含めると、応答品質が向上します。prompt は、model が一般的な助言ではなく、実行可能で具体的な推奨事項を提供するよう導く必要があります。

</details>

---

8. 自動化されたインシデント対応において、Alertmanager webhook はどのように API Gateway と Lambda に接続しますか？
   - A) Lambda は SDK を介して Alertmanager のアラートを直接受信する
   - B) Alertmanager は API Gateway の HTTP endpoint に POST request を送信し、endpoint がアラート payload を含む Lambda function をトリガーして処理する
   - C) API Gateway が Alertmanager をポーリングして新しいアラートを取得する
   - D) 接続には proxy 用の専用 EC2 instance が必要である

<details>
<summary>回答を表示</summary>

**回答: B) Alertmanager は API Gateway の HTTP endpoint に POST request を送信し、endpoint がアラート payload を含む Lambda function をトリガーして処理する**

**解説:**
統合フローは次のとおりです。Alertmanager の webhook receiver は API Gateway endpoint URL を使用して設定されます。アラートが発報すると、Alertmanager はアラート詳細（labels、annotations、status、timestamps）を含む JSON payload をこの endpoint に POST します。API Gateway は request を受信し、アラート payload を event として渡して統合された Lambda function をトリガーします。Lambda function はアラートを処理します。たとえば、context による拡充、AI 分析の実行、remediation のトリガー、または incident management system への転送を行います。

</details>

---

9. アラートパイプラインをテストするために、Fault Injection を使用して HighLatency アラートをトリガーするにはどうしますか？
   - A) Alertmanager でアラート status を手動編集する
   - B) Chaos Mesh、Litmus、または application-level fault injection などの tool を使用して service response に人工的な latency を注入し、latency metrics がアラートしきい値を超えるようにする
   - C) Prometheus metric 値を直接変更する
   - D) fault injection では Prometheus アラートをトリガーできない

<details>
<summary>回答を表示</summary>

**回答: B) Chaos Mesh、Litmus、または application-level fault injection などの tool を使用して service response に人工的な latency を注入し、latency metrics がアラートしきい値を超えるようにする**

**解説:**
Fault injection は、alerting pipeline をエンドツーエンドで検証します。Chaos Mesh や Litmus などの tool は、Pod または Service レベルで network latency を注入できます。application-level injection では、handler に sleep delay を追加する場合があります。注入した latency によって metrics（例: `histogram_quantile(0.99, http_request_duration_seconds_bucket)`）が PrometheusRules で定義したしきい値を超えると、アラートは pipeline を通じて自然に発報します。これにより、metrics 収集、alert rule、Alertmanager routing、notification delivery のすべてが正しく機能することをテストできます。

</details>

---

10. AIOps の A2A（Agent-to-Agent）pattern において、Collaborator Agent はどのような役割を果たしますか？
    - A) 人間の operator を完全に置き換える
    - B) primary agent が、特定の data source への query、remediation action の実行、domain expertise の提供などの subtask を委任できる specialized agent として機能する
    - C) logging と monitoring のみを処理する
    - D) Collaborator Agent は primary agent の同一コピーである

<details>
<summary>回答を表示</summary>

**回答: B) primary agent が、特定の data source への query、remediation action の実行、domain expertise の提供などの subtask を委任できる specialized agent として機能する**

**解説:**
A2A pattern では、primary agent（orchestrator）が specialized collaborator agent と連携して調整します。AIOps では、Metrics Agent は Prometheus/CloudWatch を query し、Logs Agent は log data を検索・分析し、Traces Agent は分散 traces を調査し、Remediation Agent は安全な recovery action を実行し、Knowledge Agent は runbook と過去のインシデント data を取得します。primary agent は collaborator の output を統合して、一貫したインシデント分析を作成します。この分担により、specialized prompt、並列実行、関心の分離が可能になり、システム全体の能力が向上します。

</details>
