# オブザーバビリティ ラボシリーズ

<span id="architecture-diagram"></span>
<span id="cost-estimate"></span>
<span id="lab-sequence"></span>
<span id="lab-series-introduction"></span>
<span id="learning-outcomes"></span>
<span id="msa-application-overview"></span>
<span id="observability-tool-coverage"></span>
<span id="overview"></span>
<span id="references"></span>
<span id="required-iam-permissions"></span>
<span id="service-call-flow"></span>

> **難易度**: 上級
> **最終更新**: September 13, 2026
実行可能な合成注文アプリケーションと、そのメトリクス/ログ/トレースを、2 つの EKS クラスターにまたがって接続します。ベースラインでは Prometheus、Loki、Tempo、Grafana と、AWS SNS/SQS、Aurora、CloudWatch を使用します。ラボ構成は、本番環境の HA/キャパシティ検証とは別のものです。

![管理/サービスの責任範囲と認証境界](../../.gitbook/assets/en-labs-observability-overview-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-overview-0.html)

## 前提条件 {#prerequisites}

承認済みの一時 AWS ロール、レビュー済みのプライベート VPC/サブネット/ルート/DNS/SG、EBS CSI/gp3、NetworkPolicy 対応 CNI、および AWS Load Balancer Controller を使用してください。包括的なサービス FullAccess や長期間有効なアクセスキーは不要です。各ステージでバージョン、権限、クォータを再確認してください。

| ツール | レビュー済みベースライン |
|---|---|
| EKS / kubectl | 1.36 / 1.36.2 |
| eksctl / Helm | 0.229.0 / 3.21.3 |
| Python / AWS CLI | 3.12 / v2 |
| k6 / Locust | 2.2.0 / 2.46.5 |
| アプリケーション / コントローラー | 例内の固定された要件、イメージダイジェスト、チャートバージョン |

## 実行可能なコードと手順 {#sequence}

このリポジトリの [アプリケーション](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application)、[スタック](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/stack)、[負荷テスト](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/load-test)、および [aiops](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/aiops) の例を使用してください。レビュー済みのコミット/タグを固定し、プライベートな LAB_STATE を保持してください。古く存在しないサンプルリポジトリをクローンしないでください。

![インフラストラクチャからトレース分析までの 6 ステージ](../../.gitbook/assets/en-labs-observability-overview-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-overview-2.html)

| パート | ステージ | 成果 |
|---|---|---|
| 1 | [インフラストラクチャ](01-infrastructure-setup-lab.md) | EKS、プライベート DB、SNS ファンアウト、スコープを限定したロール |
| 2 | [オブザーバビリティスタック](02-observability-stack-lab.md) | mTLS collectors/remote-write、Loki/Tempo/Grafana |
| 3 | [MSA/canary](03-msa-deployment-lab.md) | 実行可能な 5 つのロール、outbox、リビジョンのみの分析 |
| 4 | [負荷/スケーリング](04-load-testing-scaling-lab.md) | 測定済みリクエストと consumer/node の観測 |
| 5 | [アラート/AIOps](05-alerting-aiops-lab.md) | トピックを分離した診断レポーター、人によるレビュー |
| 6 | [分散トレーシング](06-distributed-tracing-lab.md) | 実際の metric/exemplar/trace/log 相関、クリーンアップ |

## アプリケーションとデータフロー {#application}

1 つの Python イメージを、個別の api-gateway、order-service、payment-service、notification、analytics ロールとして実行します。決済/通知は合成であり、実際の請求/メール/SMS は行いません。注文と outbox はトランザクションを共有し、独立したキューとイベント ID の重複排除が notification/analytics を処理します。Gateway 認証、一般的なレート制限、実際の決済ゲートウェイは実装も主張もされていません。

![HTTP、トランザクション outbox、個別の consumer キュー](../../.gitbook/assets/en-labs-observability-overview-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-overview-3.html)

## ベースラインとオプションの拡張機能 {#coverage}


![ベースラインパスと、個別の検証が必要な拡張機能](../../.gitbook/assets/en-labs-observability-overview-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-overview-1.html)

| ベースライン | オプションの個別統合 |
|---|---|
| Prometheus / CloudWatch メトリクス | VictoriaMetrics、Mimir、AMP |
| Loki / CloudWatch Logs | ClickHouse、OpenSearch |
| OTel / Tempo | X-Ray、Dynatrace |
| Grafana | Amazon Managed Grafana、商用ツール |
| Alertmanager / SNS / 診断 Lambda | 既存のオンコールプラットフォーム、CloudWatch Investigations グループ |
| 合成イベント consumer | MWAA スケジューリング/バッチ分析、本番トランザクションシステム |

インストールは、検証済みの取り込み、クエリ、権限、コストとは異なります。拡張機能については、[metrics](../../observability/metrics/README.md)、[logging](../../observability/logging/README.md)、[tracing](../../observability/tracing/README.md)、[Grafana](../../observability/grafana/README.md) のガイドを参照してください。Part5 には OnCall OSS のアーカイブなどの変更が組み込まれています。

## コスト、検証、クリーンアップ {#cost-and-cleanup}

実際の使用量に基づいて、リージョン固有のノード、NAT、EBS、Aurora ACU/ストレージ/I/O、ログ取り込み/保持、メッセージ、KMS、LB、転送、モデル呼び出しを見積もってください。月額のユーザー単位料金と、時間単位のインフラストラクチャ料金を固定された合計額に混在させないでください。単一 writer/backend のラボは本番グレードの HA ではありません。レプリカ上限は絶対的な支出上限ではありません。

ローカルの native/SDK/schema/browser 検証と、実際の AWS 結果を区別してください。リソース、IAM アタッチメント、スナップショット、DNS、LB/PVC をインベントリ化し、Part6 の依存関係順にクリーンアップしてください。すべての失敗を抑制したり、管理対象の依存リソースより先にクラスターを削除したりしないでください。
