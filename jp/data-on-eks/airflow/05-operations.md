# パート5: 運用とセキュリティ

> レビュー済み: Airflow 3.3.1、Helm chart 1.22.0、Amazon provider 9.34.0 / Kubernetes provider 10.21.0。
> 最新の上流パッチ確認済み: 3.3.2。運用例は3.3.1のまま · 2026年10月12日。

この章では、パート2のセルフマネージド EKS デプロイにおける HA、アップグレード、シークレット、ログ、可観測性、復旧を扱います。運用上の基準は、設定が存在するだけでなく、障害後に**実行、データ、ログを復旧できること**です。MWAA ではパート4のマネージド環境／CloudWatch 手順を使ってください。

## 1. データベースとあわせてスケジューラーの HA を検証する

Airflow 2 は、スケジューラーの HA とスタンドアロン DAG プロセッサーをすでにサポートしていました。Airflow 3 で必須となったプロセッサーの分離により、リソースと責任の境界が明確になりましたが、データベースの競合がなくなるわけでも、線形スケーリングが保証されるわけでもありません。スケジューラーは、シリアライズされた DAG とデータベースの行ロックを使って、スケジューリングのクリティカルセクションを調整します。別個のスケジューラーリーダー選出サービスは必要ありません。

```yaml
scheduler:
  replicas: 2
```

この設定で変更されるのはレプリカ数だけです。ノード／AZ 配置、データベースのフェイルオーバーと接続数の上限、API／プロセッサーの可用性、プローブ／PDB、Executor／ブローカーの状態も検証してください。ノード／AZ 障害とデータベースのフェイルオーバー中に、スケジューリングの遅延、再試行、重複した外部書き込みを測定します。スケジューラーページに記載された SQL 機能の注意点は、サポート対象データベースの全マトリクスではありません。パート1のバージョンガイダンスを使ってください。トリガーを使う場合、遅延可能タスクを含め、Triggerer が必要です。

## 2. バックアップ、リストア、移行

メタデータデータベースには、実行状態と Airflow 設定の多くが保存されます。外部シークレットやオブジェクトストレージの XCom バックエンドを使う場合、すべての値がこのデータベースにあるわけではありません。データベースだけでなく、Fernet キー、DAG／バンドルの履歴、イメージ／プロバイダー、外部データ、ログ、シークレットも保護してください。復号キーがなければ、暗号化された行を復元しても不十分です。

環境固有の移行手順書で、次の順序を検証します。

1. サポート対象のアップグレード経路と破壊的変更を確認します。現実的なデータベースのコピーを使ってリハーサルし、所要時間、ロック、ディスク容量、DAG／プロバイダーの互換性を測定します。
2. ホットバックアップにはデータベースの整合性保証を使い、復元をテストします。スナップショット要求が成功しても、処理完了や復旧可能性が証明されるわけではありません。
3. 新しい実行を制御し、既存の処理をドレインするか、意図的に終了させます。ワーカー／タスク、API サーバー、外部自動化など、関係するすべてのデータベース書き込み元を調整してください。スケジューラー、プロセッサー、Triggerer だけを停止しても、すべての書き込みが静止するわけではありません。
4. バックアップ／復旧ポイントを確立し、移行の仕組みを1つだけ使います。Helm の移行 Job／hook と、手動の airflow db migrate コマンドを競合させないでください。
5. トラフィックを再開する前に、データベースの状態、新しい実行、再試行、ログ、シークレットの参照を検証します。移行済みスキーマに古いイメージをデプロイするだけでは、十分なロールバック計画になりません。

### 意図的な履歴保持ポリシーを適用する

アップグレードのたびに、固定日数分のデータを無条件に削除しないでください。まず監査／再実行／depends_on_past の要件と、外部キーのカスケードを確認します。次のコマンドは**削除を行わないプレビュー**です。

```bash
# Preview only: replace the cutoff and table selection with your retention policy.
airflow db clean \
  --clean-before-timestamp '2026-07-01T00:00:00+00:00' \
  --tables dag_run,task_instance \
  --dry-run \
  --error-on-cleanup-failure
```

クリーンアップは、カットオフとテーブル、バックアップを確認した後に別途実行します。デフォルトのアーカイブテーブルは同じデータベース内で容量を消費するため、クリーンアップをしても、すぐにディスクが解放されたり、あらゆる移行が速くなったりするとは限りません。3.3.1 では、一部のクリーンアップ失敗が終了ステータス0の背後に隠れる場合があります。自動化では `--error-on-cleanup-failure` を使い、結果／ログを確認してください。

## 3. Fernet とシークレット解決の経路

Connection と Variable が、デフォルトですべて平文になるわけではありません。Fernet を設定すると、Connection の password／extra フィールドと Variable の値は暗号化されます。ただし、すべてのメタデータフィールドやログが暗号化されるわけではありません。キーを保持／ローテーションし、アクセスを制御してください。AWS Secrets Manager は、サポート対象の外部バックエンドの1つです。

```ini
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

サーバー側での一般的な検索順は、カスタムバックエンド → 環境変数 → メタストアです。外部の値がすべて Airflow UI に表示されるわけではありません。UI で重複するキーを編集しても、優先順位の高い外部の値が引き続き使われることがあります。

Airflow 3 は `[workers]` の `secrets_backend` と `secrets_backend_kwargs` をサポートします。通常の Task SDK タスクコンテキストでも、supervisor と Execution API を通してサーバー側の値を解決できます。そのため、すべてのコンポーネントで同じプレフィックスや直接のデータベースアクセスが必要とは限りません。

想定する経路を文書化し、API 側での検索、ワーカーによる上書き、logging supervisor の解決／キャッシュをそれぞれテストします。レビューしたコードでは、バックエンドの例外は後続経路を試す前にログへ記録されます。すべての失敗が無言で処理されるわけではありません。想定外のフォールバック値と、明示的な検索失敗の両方をテストしてください。シークレットの内容を診断ログに出力しないでください。

## 4. S3 タスクログは、すべてのコンポーネントログを即時にストリーミングするものではない

```ini
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
delete_local_logs = False
```

シークレット名の例: airflow/connections/airflow_remote_logging_conn。値の例:

```json
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

この Connection に静的キーは含まれません。実際の S3 読み取り／書き込み元に合わせて IRSA または Pod Identity と SDK の認証情報選択を設定し、バケットプレフィックス／KMS の権限とネットワークも構成します。API 経由で Connection のメタデータを取得しても、API サーバーの AWS 認証情報が移転するわけではありません。API／UI による読み取りと、タスク／supervisor による書き込みの両方をテストします。

レビューした3.3.1の supervisor は、タスクのサブプロセスが終了してからリモートログをアップロードします。Amazon S3 handler も close／upload の経路で blob を保存します。すべての行が即座に S3 に到達する保証はありません。成功タスク、失敗タスク、ワーカーの強制終了、Pod 削除後の UI での取得をテストしてください。最終アップロード前に SIGKILL やノード障害が起こると、直近のログが失われる可能性があります。

S3 の `remote_logging` が設定するのは**Airflow のタスクログ経路**です。スケジューラー／API／プロセッサーのサービスログも、同じ S3 の場所へ自動的に送るわけではありません。例えば Fluent Bit で標準出力／標準エラーを別途収集すると補完になります。タスクがファイルだけに書き込む場合、コンテナの標準出力を収集しても、そのファイルまで自動的に収集されるわけではありません。PVC や独立したコレクターが Pod 削除後もログを保持する場合があります。実際のストレージ、保持期間、損失の境界を調べてください。

KPO では、呼び出し元の `get_logs` 動作によって、子プロセスの出力が Airflow タスクログに取り込まれます。Airflow を含まない任意の子イメージに airflow.cfg をコピーしても、リモートログ機能は作成されません。

## 5. メトリクスの転送と収集

一致する OTel 依存関係を含むイメージを使い、メトリクスのバックエンドを選択します。次の設定は OTel を選びます。

```ini
[metrics]
statsd_on = False
otel_on = True
```

メトリクスを出力する各プロセスに設定する環境変数の例:

```dotenv
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector.monitoring.svc:4318/v1/metrics
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf
OTEL_METRIC_EXPORT_INTERVAL=30000
OTEL_SERVICE_NAME=airflow
```

3.3.1 では、以前の `otel_host`、`otel_port`、`otel_interval_milliseconds` 設定は非推奨であり、標準の OTel 環境変数に置き換わりました。このエンドポイントは内部向けの OTLP／HTTP の例です。Collector の HTTP receiver、Service ポート、ネットワークポリシー、必要な TLS／認証に合わせてください。

Prometheus が OTLP エンドポイントを単純にスクレイプするわけではありません。例えば Collector の Prometheus exporter をスクレイプするか、認証に対応した適切な remote-write exporter を使って、メトリクスのパイプラインを完成させてください。AMP では、ワークスペースのエンドポイントと AWS 認証を検証します。StatsD を使う場合は、exporter のマッピングと実際の時系列も確認してください。

スケジューラーのハートビート／スケジューリング遅延、解析エラー／所要時間、キュー内タスクの経過時間、ワーカー／Triggerer のヘルス、データベース接続／ロック、Pending／OOM／ディスク圧迫の状態、ログアップロード失敗を観測します。アラートを作成する前にエクスポートされたメトリクス名／ラベルを確認し、制御された障害を通じて通知の到達をテストしてください。

## 6. オートスケーリングとセキュリティ境界

Celery KEDA のクエリでは、パート2に記載されたとおり、キュー、executor、エイリアスを区別し、同時実行数とレプリカ数の上限を考慮します。永続性の要件に応じて、ワーカーには Deployment または StatefulSet を使用できます。ゼロまでスケールできるかどうかは、最小レプリカ数、トリガー、クールダウンに依存します。すべてのサービスのアイドルコストがなくなるわけではありません。

KubernetesExecutor はタスク Pod を直接作成するため、Celery ワーカープールと同じスケーリングパターンは必要ありません。KEDA が Deployment しかサポートしないという意味ではありません。タスク完了後、ノードオートスケーラーもすべてのノードをただちに削除するわけではありません。キャパシティ、クォータ、PDB、disruption ポリシー、他のワークロードを考慮してください。

| 境界 | 確認する内容 |
| --- | --- |
| AWS ID | 共有 Celery ワーカー上のタスクは、そのワーカーのロールを共有します。分離には、別々のプール／executor／KPO の子プロセスなど、実際の実行境界を使用してください |
| Kubernetes RBAC | KubernetesExecutor または KPO の呼び出し元に、必要な権限を付与します。DAG の解析だけなら Pod 作成権限は必要ありません |
| Namespace／admission | Pod の作成権限があると、別のサービスアカウントを選択したり危険な仕様を指定したりできる場合があります。信頼境界と admission 制御を調べてください |
| NetworkPolicy | CNI による強制適用と、DNS、Execution API、DB／ブローカー、Kubernetes API、認証情報／シークレット／ログの各エンドポイントへの通信を確認します |

NetworkPolicy が制限するのは L3／L4 の接続です。IAM／RBAC／TLS 認証の代わりにはならず、あらゆる横方向移動を確実に防ぐものでもありません。デフォルト拒否を適用する前に実際の依存先を許可し、不要なタスクからデータベースへのアクセスを広げないでください。

## 7. 運用上の受け入れ基準

- [ ] サポート対象のランタイム／プロバイダー、executor の選択、DAG の配信／再実行時のバージョンポリシーを記録する。
- [ ] 適切な本番データベース、バックアップ／リストア、Fernet／外部データの復旧をテストする。RDS は選択肢の1つであり、唯一の選択肢ではない。
- [ ] スケジューラー／API／プロセッサーと、必要な Triggerer の障害／復旧、キャパシティ上限をテストする。
- [ ] 現実的なデータベースコピーを使い、移行、新規実行の受付、ドレイン、ロールバックをリハーサルする。
- [ ] 想定するシークレット解決経路と、IAM／RBAC／admission／ネットワーク境界を検証する。
- [ ] 成功、失敗、強制終了、Pod 削除後のログを調べ、損失の上限を文書化する。
- [ ] メトリクス、サービス／タスクログ、アラートを責任者と手順に関連付ける。
- [ ] 目標負荷と障害条件で、レイテンシ、再試行、重複した外部書き込み、復旧を測定する。

チェックボックスを埋めても信頼性は保証されません。必須 SLO、復旧時間、保持目標に照らした測定結果と未解決の制限を記録してください。

## 検証範囲と参考資料

設定、シークレット解決経路、アップロードのタイミングについて、公式ドキュメントとリリース済みソースを確認しました。S3 アップロード方法の例の構造とローカルファイルの動作を検証しました。実際のデータベース移行、AWS シークレット／S3 呼び出し、Collector への取り込み、障害復旧の演習は行っていません。


- [スケジューラー HA とデータベース調整](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/scheduler.html)
- [データベースのアップグレード](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/upgrading.html)
- [データベースメンテナンス CLI](https://airflow.apache.org/docs/apache-airflow/3.3.1/cli-and-env-variables-ref.html)
- [Fernet 暗号化](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/fernet.html)
- [シークレットバックエンドとワーカー設定](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/secrets-backend/index.html)
- [タスクログ](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/logging-tasks.html)
- [メトリクス設定](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/metrics.html)
- [Amazon provider 9.34.0 の S3 ログ実装](https://github.com/apache/airflow/blob/providers-amazon/9.34.0/providers/amazon/src/airflow/providers/amazon/aws/log/s3_task_handler.py)

[README](README.md)

[クイズ](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)
