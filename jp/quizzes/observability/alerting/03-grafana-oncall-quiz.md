# Grafana OnCall クイズ

Grafana OnCall の理解度を確認するクイズです。

---

1. Grafana OnCall の主要機能ではないものはどれですか？
   - A) オンコールスケジュール管理
   - B) エスカレーションチェーンの設定
   - C) メトリクスの収集と保存
   - D) ChatOps 統合 (Slack, Teams)

<details>
<summary>回答を表示</summary>

**回答: C) メトリクスの収集と保存**

**解説:**
Grafana OnCall は、次の機能を提供するオンコール管理およびインシデント対応ツールです。
- オンコールスケジュール管理（ローテーション、オーバーライド）
- エスカレーションチェーンの設定
- アラートのグループ化とルーティング
- ChatOps 統合 (Slack, MS Teams, Telegram)
- モバイルアプリ通知

メトリクスの収集と保存は、Prometheus や Grafana Mimir などの別のツールの役割です。OnCall は、これらのツールから生成されたアラートを受信して処理します。

</details>

---

2. Grafana OnCall のエスカレーションポリシーにおける `wait` タイプの役割は何ですか？
   - A) アラート送信前にデータ収集を待機する
   - B) 次のエスカレーションステップに進む前に待機する
   - C) ユーザーの応答を待ってから自動解決する
   - D) アラートのグループ化を待機する

<details>
<summary>回答を表示</summary>

**回答: B) 次のエスカレーションステップに進む前に待機する**

**解説:**
エスカレーションチェーンでは、`wait` タイプは現在のステップと次のステップの間の待機時間を設定します。例:
1. ステップ 1: 現在のオンコール対応者に通知する
2. ステップ 2: 900 秒（15 分）待機する
3. ステップ 3: 応答がない場合、二次対応者に通知する

これにより、一次対応者に応答する時間を与え、応答がない場合にのみエスカレーションが進みます。

</details>

---

3. Grafana OnCall のオンコールスケジュールにおける「Override」とは何ですか？
   - A) スケジュールを完全に削除して再作成すること
   - B) 既存のスケジュール内の特定期間について対応者を一時的に変更すること
   - C) スケジュールのタイムゾーンを変更すること
   - D) ローテーションサイクルを変更すること

<details>
<summary>回答を表示</summary>

**回答: B) 既存のスケジュール内の特定期間について対応者を一時的に変更すること**

**解説:**
Override は、通常のオンコールスケジュールにおいて特定期間の対応者を一時的に変更する機能です。主なユースケース:
- 休暇による対応者の交代
- 緊急事態による一時的な変更
- トレーニングや会議による一時的な交代

Override は、既存のスケジュールを維持したまま、特定期間に別の対応者を指定します。

</details>

---

4. Grafana OnCall を Alertmanager と統合する際に使用される方法は何ですか？
   - A) Alertmanager が OnCall のメトリクスを直接収集する
   - B) Alertmanager の webhook_configs を介して OnCall にアラートを送信する
   - C) OnCall が Alertmanager の API を定期的にポーリングする
   - D) 両方のシステムがデータベースを共有する

<details>
<summary>回答を表示</summary>

**回答: B) Alertmanager の webhook_configs を介して OnCall にアラートを送信する**

**解説:**
Alertmanager と Grafana OnCall の統合は Webhook を通じて行われます:
```yaml
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
```

Alertmanager がアラートを発報すると、設定された Webhook URL に HTTP POST リクエストを送信し、OnCall がそれを受信して処理します。

</details>

---

5. Grafana OnCall におけるアラートのグループ化の主な目的は何ですか？
   - A) アラートを時刻順に並べ替える
   - B) 関連するアラートを 1 つにまとめてアラート疲れを軽減する
   - C) アラートを重要度別に分類する
   - D) 重複したアラートを自動的に削除する

<details>
<summary>回答を表示</summary>

**回答: B) 関連するアラートを 1 つにまとめてアラート疲れを軽減する**

**解説:**
アラートのグループ化では、同じ問題によって発生した複数のアラートを 1 つのグループとして管理します。たとえば、node 障害によって複数の Pod アラートが発生した場合、それらをまとめることで、対応者は数十件の個別アラートではなく 1 件のグループ化されたアラートを受け取ります。グループ化キー（例: alertname + namespace）を定義して、どのアラートをまとめるかを決定します。

</details>

---

6. Grafana OnCall のエスカレーションポリシーで `notify_on_call_from_schedule` の `important` フラグが true の場合、何が起こりますか？
   - A) アラートが最優先としてマークされる
   - B) 設定済みのすべてのチャネル（電話、SMS、push など）でアラートが送信される
   - C) エスカレーションチェーンがスキップされ、アラートが直ちに管理者へ送信される
   - D) アラートが永続的に保存される

<details>
<summary>回答を表示</summary>

**回答: B) 設定済みのすべてのチャネル（電話、SMS、push など）でアラートが送信される**

**解説:**
`important` フラグの意味:
- `important: true`: ユーザーが設定したすべての通知チャネル（電話、SMS、モバイル push、Slack など）でアラートを送信する
- `important: false`: デフォルトのチャネルのみ（例: Slack）でアラートを送信する

これにより、重要度に応じてアラートの強度を調整できます。Critical アラートは電話/SMS を含めるために important=true に設定でき、Warning は Slack のみを使用するために important=false に設定できます。

</details>

---

7. Grafana OnCall と Slack の統合で使用できないコマンドはどれですか？
   - A) /oncall ack (アラートを確認する)
   - B) /oncall resolve (アラートを解決する)
   - C) /oncall deploy (Deployment を実行する)
   - D) /oncall silence 2h (2 時間サイレンスする)

<details>
<summary>回答を表示</summary>

**回答: C) /oncall deploy (Deployment を実行する)**

**解説:**
Grafana OnCall の Slack コマンド:
- `/oncall` - 現在のオンコール対応者を確認する
- `/oncall schedule` - スケジュールを表示する
- `/oncall ack` - アラートを確認する
- `/oncall resolve` - アラートを解決する
- `/oncall silence 2h` - 2 時間サイレンスする
- `/oncall unsilence` - サイレンスを解除する
- `/oncall escalate` - アラートをエスカレーションする

Deployment の実行は OnCall の機能ではありません。OnCall はアラート管理とオンコール管理に重点を置いています。

</details>

---

8. PagerDuty/OpsGenie と比較した Grafana OnCall の利点ではないものはどれですか？
   - A) オープンソースでセルフホスト可能
   - B) Grafana stack とのネイティブ統合
   - C) 700+ の統合をサポート
   - D) 無料で利用可能（OSS バージョン）

<details>
<summary>回答を表示</summary>

**回答: C) 700+ の統合をサポート**

**解説:**
700+ の統合は PagerDuty の利点です。比較:
- **Grafana OnCall**: 30+ の統合、オープンソース、セルフホスト可能、Grafana ネイティブ統合、無料（OSS）
- **PagerDuty**: 700+ の統合、SaaS のみ、高度な分析/レポート、AIOps 機能
- **OpsGenie**: 200+ の統合、SaaS のみ、Atlassian ecosystem 統合

OnCall は Grafana stack を使用する環境にとってコスト効率の高い選択肢ですが、多様な外部システム統合が必要な場合は PagerDuty の方が適している可能性があります。

</details>

---

9. Grafana OnCall の本番 Deployment における高可用性の推奨構成は何ですか？
   - A) 単一インスタンスで十分
   - B) API server と Celery worker のレプリカ数を増やし、外部 PostgreSQL/Redis を使用する
   - C) 複数の cluster に分散 Deployment する
   - D) 読み取り専用レプリカのみを追加する

<details>
<summary>回答を表示</summary>

**回答: B) API server と Celery worker のレプリカ数を増やし、外部 PostgreSQL/Redis を使用する**

**解説:**
Grafana OnCall の本番 HA 構成:
- **API server**: 3+ レプリカ、Pod Anti-Affinity 設定
- **Celery workers**: 3+ レプリカ、Pod Anti-Affinity 設定
- **PostgreSQL**: 外部マネージド DB（AWS RDS など）を使用
- **Redis**: 外部マネージド Redis（AWS ElastiCache など）を使用

この構成により単一障害点を排除し、個々のコンポーネントに障害が発生してもサービスを継続して運用できます。

</details>

---

10. Grafana OnCall で Route を設定する主な目的は何ですか？
    - A) ネットワークトラフィックの分散
    - B) アラート条件に基づいて異なるエスカレーションチェーンを適用する
    - C) データベースクエリの最適化
    - D) ユーザー認証パスの設定

<details>
<summary>回答を表示</summary>

**回答: B) アラート条件に基づいて異なるエスカレーションチェーンを適用する**

**解説:**
Route は、受信アラートの属性（label、severity、team など）に基づいて、適切なエスカレーションチェーンに接続します:
- `severity=critical` -> Critical エスカレーションチェーン（電話/SMS を含む）
- `team=infra` -> Infrastructure team のエスカレーションチェーン
- `namespace=production` -> Production オンコールスケジュール

ルーティングルールは正規表現を使用して定義され、アラート payload の内容に基づいてマッチします。これにより、異なるアラートタイプに対して適切な対応者とエスカレーションポリシーを適用できます。

</details>

---

## 追加学習リソース

- [Grafana OnCall ドキュメント](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)
