# EKS 上の Airflow 詳細ガイド

> **レビュー基準**: Airflow 3.3.1 · 公式 Helm chart 1.22.0
> **確認済みの最新 upstream patch**: Airflow 3.3.2 (September 17, 2026); examples は3.3.1のまま · October 12, 2026

Apache Airflow は、workflow の依存関係を DAG として定義し、task の schedule、実行、監視を行います。EKS では、task ごとの pod の動作は、Helm chart をインストールしただけで決まるのではなく、**executor と operator** に依存します。

Airflow 2 は2026年4月22日に EOL を迎えました。新しい deployment には、保守されている 3.x release を使用してください。Chart 1.22.0 のデフォルトは **Airflow 3.2.2** なので、chart、image、Airflow configuration の各バージョンを個別に確認してください。このシリーズでは 3.3.1 の動作を確認し、そのバージョンを override して chart を render しています。

Upstream 3.3.2 は2026年9月17日に release されました。明示的な Bearer token は session cookie より優先され、有効な cookie が同時に存在していても、無効な Bearer token は request を拒否します。これは、browser cookie と service credential を組み合わせる API client に影響する可能性があります。

このシリーズの example と Helm の確認は3.3.1のままで、3.3.2では再検証していません。

## 主なアーキテクチャ

- Scheduler と executor が task の処理を決定して送信し、metadata の状態を更新します。
- 必須の DAG processor が DAG bundle を parse/serialize します。Worker も、関連する bundle または code distribution 経路を通じて task code を利用できる必要があります。
- API server は UI、REST API、Task Execution API の経路を提供します。Supervisor が管理する Python Task SDK runtime は、この API を使って state と Connection/Variable/XCom にアクセスします。
- Triggerer は、deferrable task が待機している間に **trigger** を実行します。Deferral を使わない最小構成では省略できます。
- Metadata backend には PostgreSQL と MySQL があります。このシリーズでは例として PostgreSQL を使用しますが、唯一の選択肢ではありません。Redis も Celery broker の唯一の選択肢ではありません。

![Airflow の control component、metadata、task execution API、代替 executor 経路。](../../.gitbook/assets/en-data-on-eks-airflow-readme-0.png)

[インタラクティブな図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-readme-0.html)

DAG bundle があらゆる場合に git-sync を置き換えるわけではありません。公式 chart は引き続き git-sync をサポートしているため、コードの配布と bundle のバージョン管理を区別してください。Parser を分離しても、すべての latency、database bottleneck、HA に関する懸念が解消されるわけではありません。

## シリーズ

1. [Kubernetes 上の Airflow アーキテクチャ](01-architecture.md): component、Execution API、database/broker、executor。
2. [Helm deployment と executor の選択](02-helm-deployment.md): 公式 chart、version、connection、worker scaling。
3. [DAG pattern と KubernetesPodOperator](03-dag-patterns.md): pod、code delivery、bundle、Spark/dbt。
4. [Amazon MWAA との統合](04-mwaa-integration.md): マネージド範囲、EKS 統合、version、コスト。
5. [運用とセキュリティ](05-operations.md): HA、migration、secret、log、観測、recovery の確認。


- [Airflow 3.3.1 のアーキテクチャ](https://airflow.apache.org/docs/apache-airflow/3.3.1/core-concepts/overview.html)
- [Airflow 3.3.2 の release note](https://airflow.apache.org/docs/apache-airflow/3.3.2/release_notes.html)
- [サポート対象バージョンと lifecycle](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/supported-versions.html)
- [Airflow の前提条件](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/prerequisites.html)
- [Executor の設定と履歴](https://airflow.apache.org/docs/apache-airflow/3.3.1/core-concepts/executor/index.html)
- [DAG bundle](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/dag-bundles.html)
- [Deferrable operator と trigger](https://airflow.apache.org/docs/apache-airflow/3.3.1/authoring-and-scheduling/deferring.html)

[クイズ](../../quizzes/data-on-eks/airflow/01-architecture-quiz.md)
