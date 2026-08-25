# EKS での MLflow デプロイメントクイズ

このクイズでは、EKS 上の MLflow Tracking Server アーキテクチャ（backend store、artifact store、IAM アクセスパターン、Tracking Server をチーム共有サービスとして運用する際の考慮事項）に関する理解を確認します。

## 選択式問題

1. SageMaker の MLflow 互換 Tracking 機能のようなマネージド代替手段ではなく、EKS で MLflow Tracking Server をセルフホストする場合の主なトレードオフは何ですか？
   - A) チームの規模にかかわらず、セルフホストは常により安価である
   - B) すでに EKS を利用しているチームは既存のデプロイメント、observability、IAM パターンを再利用できる一方で、Tracking Server、backend store、artifact store を自ら運用する必要がある
   - C) マネージド代替手段では metrics や parameters をまったくログに記録できない
   - D) トレードオフはない。2 つの選択肢は機能的に同一である

<details>

<summary>回答を表示</summary>

**回答: B) すでに EKS を利用しているチームは既存のデプロイメント、observability、IAM パターンを再利用できる一方で、Tracking Server、backend store、artifact store を自ら運用する必要がある**

**解説:**
セルフホストでは、チームは他の workload にすでに使用している Kubernetes Deployment、observability、IAM（IRSA/Pod Identity）パターンを再利用できます。その代わり、マネージド代替手段に委ねるのではなく、Tracking Server、その backend database、artifact store を直接運用することになります。
</details>

2. MLflow のデフォルト SQLite backend store がチーム共有の Tracking Server に適さないのはなぜですか？
   - A) SQLite では浮動小数点の metric 値を保存できない
   - B) SQLite は、共有 Tracking Server に必要なレベルの同時書き込みをサポートしない
   - C) SQLite には別の EKS node group が必要である
   - D) SQLite の artifacts は 30 日後に期限切れになる

<details>

<summary>回答を表示</summary>

**回答: B) SQLite は、共有 Tracking Server に必要なレベルの同時書き込みをサポートしない**

**解説:**
SQLite は単一の実験担当者には問題なく機能しますが、複数のプロセスが同時に書き込む必要が生じると機能しなくなります。共有 Tracking Server が必要とする同時書き込みの規模をサポートしていません。このため、本番環境では RDS PostgreSQL や Aurora Serverless v2 などの実際の database に置き換えます。
</details>

3. artifact store と対比して、backend store にはどのようなデータが保持されますか？
   - A) backend store にはシリアライズされた models などの大きなバイナリオブジェクトが保持され、artifact store には構造化 metadata が保持される
   - B) backend store には構造化 metadata（experiments、runs、params、metrics、registered models、versions、aliases）が保持され、artifact store には大きなバイナリオブジェクト（models、plots、datasets）が保持される
   - C) 両方の store は冗長性のためにすべてのデータの同一コピーを保持する
   - D) backend store には usernames と passwords のみが保持される

<details>

<summary>回答を表示</summary>

**回答: B) backend store には構造化 metadata（experiments、runs、params、metrics、registered models、versions、aliases）が保持され、artifact store には大きなバイナリオブジェクト（models、plots、datasets）が保持される**

**解説:**
backend store は、experiments、runs、params、metrics、registered models、versions、aliases といった SQL でクエリ可能なすべてを保持する relational database です。artifact store（AWS では S3）は、ログに記録された models、plots、datasets など、backend store が保持しない大きなバイナリオブジェクトを保持します。
</details>

4. AWS で、本番環境の MLflow backend store における標準的な選択肢となる 2 つのサービスはどれですか？
   - A) DynamoDB と EFS
   - B) PostgreSQL 向け Amazon RDS と Aurora Serverless v2
   - C) ElastiCache と S3
   - D) Redshift と Glacier

<details>

<summary>回答を表示</summary>

**回答: B) PostgreSQL 向け Amazon RDS と Aurora Serverless v2**

**解説:**
どちらも同時書き込みをサポートする実際の relational database です。Aurora Serverless v2 は、database を年間を通じてピーク負荷に合わせてサイジングするのではなく、突発的な tracking 負荷に応じてスケーリングできるため、特に検討する価値があります。
</details>

5. Kubernetes への MLflow デプロイメントで言及されている community Helm chart は何で、その repository はどのように追加しますか？
   - A) `bitnami/mlflow`、`helm repo add bitnami https://charts.bitnami.com/bitnami` で追加する
   - B) `community-charts/mlflow`、`helm repo add community-charts https://community-charts.github.io/helm-charts` で追加する
   - C) MLflow 用にメンテナンスされている community chart はない
   - D) `mlflow/mlflow-operator`、`kubectl apply -f` でのみインストールする

<details>

<summary>回答を表示</summary>

**回答: B) `community-charts/mlflow`、`helm repo add community-charts https://community-charts.github.io/helm-charts` で追加する**

**解説:**
`community-charts/helm-charts` は、設定可能な backend database と object storage の設定をサポートする MLflow chart をメンテナンスしており、独自の Deployment/Service/Ingress manifests を手作業で記述する実用的な代替手段となります。
</details>

6. 新しいデプロイメントで、Tracking Server の ServiceAccount に IAM role をバインドするための、よりモダンなデフォルトの選択肢として示されている EKS のメカニズムはどれですか？
   - A) ConfigMap に保存された静的 IAM access keys
   - B) EKS Pod Identity。ただし、すでに IRSA を標準化している cluster では IRSA も有効である
   - C) worker node の EC2 instances に直接アタッチされた instance profiles
   - D) container image に組み込まれた共有 root AWS account credential

<details>

<summary>回答を表示</summary>

**回答: B) EKS Pod Identity。ただし、すでに IRSA を標準化している cluster では IRSA も有効である**

**解説:**
EKS Pod Identity は IAM roles を Pods にバインドするための新しいメカニズムであり、一般に EKS での新しい IAM-to-pod バインディングにおける推奨デフォルトとして採用が進んでいます。IRSA も、特にすでにそれを標準化しているチームや clusters では有効な選択肢です。
</details>

7. Postgres をバックエンドにした MLflow Tracking Server は複数 replicas で安全に実行できる一方、SQLite をバックエンドにしたデフォルトはまったくスケールアウトできないのはなぜですか？
   - A) Postgres replicas は Pods 間の in-memory state を自動的に同期する
   - B) すべての共有 state は Pod の外部にあるため、Postgres と S3 をバックエンドにした Tracking Server は stateless である。一方、SQLite は同時書き込みに耐えられない
   - C) SQLite は Postgres より多くの CPU を必要とするため、スケールアウトは無駄である
   - D) Kubernetes では database を使用する Deployment を複数 replicas で実行することは禁止されている

<details>

<summary>回答を表示</summary>

**回答: B) すべての共有 state は Pod の外部にあるため、Postgres と S3 をバックエンドにした Tracking Server は stateless である。一方、SQLite は同時書き込みに耐えられない**

**解説:**
すべての永続 state は Pod 内ではなく backend store と artifact store にあるため、Postgres をバックエンドにした Tracking Server は stateless であり、安全に水平スケーリングできます。SQLite は同時書き込みをサポートしないため、単一プロセスのデフォルトをまったく安全にスケールアウトできません。
</details>

8. model に registered version または alias が付与された後の自然な次のステップとして説明されているものは何ですか？また、それがこのシリーズの対象外である理由は何ですか？
   - A) training job を再実行する。このシリーズの対象外なのは、training が Part 1 ですでに扱われたためである
   - B) その model version を serving system（KServe、custom wrapper、SageMaker など）にロードする。serving infrastructure はそれ自体が広範なトピックであるため、このシリーズの対象外である
   - C) model version を削除する。MLflow では削除がサポートされていないため、このシリーズの対象外である
   - D) backend store を DynamoDB に移行する。DynamoDB がサポートされていないため、このシリーズの対象外である

<details>

<summary>回答を表示</summary>

**回答: B) その model version を serving system（KServe、custom wrapper、SageMaker など）にロードする。serving infrastructure はそれ自体が広範なトピックであるため、このシリーズの対象外である**

**解説:**
model に registered version または alias が付与されると、多くのチームは KServe、custom FastAPI/Flask wrapper、SageMaker などの serving system にそれをロードする段階へ進みます。この serving layer はそれ自体が広範なトピックであり、この 3 部構成のシリーズでは明示的に対象外とされています。
</details>

## 記述式問題

9. MLflow を EKS 上でチーム共有サービスとして実行するためにデプロイする必要がある 3 つのコアアーキテクチャ要素を挙げ、それぞれが保存または実行する内容を簡潔に説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
- MLflow Tracking Server: `mlflow server` を実行し、REST API と UI を公開する stateless container。
- backend store: 構造化 metadata（experiments、runs、params、metrics、registered models、versions、aliases）を保持する relational database（例: RDS PostgreSQL または Aurora Serverless v2）。
- artifact store: ログに記録された models、plots、datasets などの大きなバイナリオブジェクトを保持する object storage（AWS では S3）。

**解説:**
複数の人が Tracking Server を共有するようになれば、この 3 つはどれも任意ではありません。Tracking Server は構造化 metadata と大きな artifacts の両方を書き込むための永続的な保存先を必要とし、どちらも Tracking Server Pod 自体に置くべきではありません。
</details>

10. Tracking Server Deployment において readiness probes と liveness probes が重要な理由と、このドキュメントが正確な health-check endpoint path を指定していない理由を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
readiness probes と liveness probes により、Service は実際に requests を処理できる Pods にのみトラフィックをルーティングでき、応答しなくなった Pod は Kubernetes が自動的に再起動できます。これは長時間稼働するあらゆる Kubernetes service の標準的なプラクティスです。このドキュメントが正確な health-check path を指定していないのは、MLflow version によって異なる可能性があるためであり、想定するのではなく、デプロイする特定の version に対して確認すべきです。

**解説:**
実在しない、または version が一致しない endpoint path に対して probe を実行すると、正常な Pods が unready と判定されたり、実際に停止した Pod の検出に失敗したりします。そのため、使用する MLflow version の実際の path を確認するほうが安全です。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/03-eks-deployment.md)
