# Part 3: EKS での MLflow のデプロイ

> **レビュー基準**: MLflow 3.16.0 · community chart 1.11.7 · 2026-09-12

## ラボ環境のセットアップ

サポートされる EKS Kubernetes バージョン、互換性のある kubectl、Helm 3、メタデータデータベース、Artifact ストレージを準備します。`kubectl >=1.34` のような下限指定では、すべての API server との互換性は保証されません。実際の cluster について、client/server のバージョンスキュー・ポリシーを確認してください。

この章は、ダウンロードした chart、ネイティブの Helm rendering、MLflow 3.16.0 server source に基づいています。**AWS のプロビジョニング、RDS 接続、S3 uploads、または EKS deployment の成功を保証するものではありません。** ローカルの SQLite/API チェックについては [Part 1](01-tracking.md)、Registry チェックについては [Part 2](02-model-registry.md) を参照してください。

## MLflow の Tracking Server を EKS で実行する理由

Kubernetes の deployment、observability、IAM のパターンを再利用できますが、server、database、artifact、access control、backup、upgrade に対する責任は負うことになります。SageMaker MLflow Apps やその他の managed registry は代替手段ですが、サポートされる version、authentication、feature、cost が必ずしも同一とは限りません。

チームで共有するために、必ずしも個別の新しい RDS および S3 resource をプロビジョニングする必要はありません。小規模な SQLite/PVC 演習は可能です。本番アーキテクチャは concurrency、durability、recovery の要件に基づいて選択してください。

## アーキテクチャ

| レイヤー | 確認すべき責務と状態 |
|---|---|
| HTTP server | SDK API、UI、artifact proxy、authentication、authorization、host/CORS policy、worker |
| メタデータデータベース | experiment/run/metric/model/registry のメタデータ、pool、migration、backup |
| Artifact store | model/data/plot file、bucket/prefix、IAM、encryption、retention |
| Authentication store | 選択した auth mechanism の user/permission database、session/signing secret、cache |
| オプション機能の状態 | 有効な job、tracing/evaluation、gateway feature で使用される queue、cache、一時 file |

PostgreSQL と S3 を使用しても、すべての feature が stateless になるわけではありません。たとえば、Pod ローカルの basic-auth SQLite database では、replica ごとに異なる user や permission が残る可能性があります。OIDC-plugin cache と job storage は個別に確認してください。

SQLite は relational database であり、serialized write で複数の process をサポートします。2 人目の user が接続しただけで直ちに失敗するわけではありません。ただし、個別の Pod ローカル SQLite file は shared database ではありません。shared file にも writer、filesystem-locking、recovery の制約があります。本番用 PostgreSQL の選択は、これらの要件と関連付けてください。

![保護されたアクセスは、メタデータ/authentication database と S3 artifact を使用する MLflow server につながります。S3 IAM permission と PostgreSQL login permission は別個のものであり、replica をスケールする前に shared state を外部化します。](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## インストール方法と Version Pin

| 方法 | 検証した内容 |
|---|---|
| Community chart | `community-charts/mlflow` 1.11.7 をダウンロード/render したもの。appVersion 3.16.0、default image は `burakince/mlflow` |
| MLflow repository chart | `v3.16.0/charts` には appVersion 3.15.2 の chart 0.1.1 が含まれる。source tag、chart version、image version は異なる |
| Direct manifest | file ベースの credential delivery、networking、authentication、migration policy で直接制御が必要な場合の選択肢 |

upstream repository 内の source は、同一 version の OCI package が公開済みであることを証明しません。レビュー時に official OCI chart 0.1.1 の pull は `not found` を返したため、検証済みのインストール command としてここでは提示しません。

以下の command は、discovery、download、rendering により chart default を確認します。本番用 value は、以下のチェックを使用して別途準備してください。

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

適用前に、render された image/digest、ServiceAccount、credential delivery、CLI argument、probe、Service、Ingress を確認してください。この chart の default は upstream MLflow image ではなく community image です。その database driver、AWS SDK、authentication plugin も確認してください。

### 重要な Chart 1.11.7 の Default

- Default には `replicaCount: 1`、`auth.enabled: false`、`ingress.enabled: false` が含まれます。
- `backendStore.defaultSqlitePath: ":memory:"` は in-memory metadata を設定します。**これは upstream CLI の新しい SQLite-file default とは異なります。** default の chart installation は durable な本番 service ではありません。
- 外部 PostgreSQL は `backendStore.postgres.*` を使用し、credential reference は `backendStore.existingDatabaseSecret.*` を使用します。
- `artifactRoot.s3.*` を `artifactRoot.proxiedArtifactStorage: true` と合わせて確認してください。native rendering は `--artifacts-destination=s3://...` と `--serve-artifacts` を生成しました。
- Basic-auth database setting は `auth.postgres.*` の下で個別に設定します。tracking database を変更しても、authentication state が自動的に共有されるわけではありません。
- `backendStore.databaseMigration: true` は Pod init-container path を追加します。複数の replica が同時に migration を実行できるようにする前に、backup、1 回の調整された migration phase、compatibility check を計画してください。

実際の value や Secret なしで名前を埋めても、本番セットアップは完了しません。この chart の一部の database/authentication reference は、**container environment variable** を通じて渡されます。SecretKeyRef は Git 内の plaintext value を避けますが、process environment への露出を排除するものではありません。policy により environment 内の secret value が禁止される場合は、Secrets Manager/SSM または同等の store から提供される credential file と、それらの file を消費する deployment を準備してください。static AWS key を Helm value や image に配置しないでください。

## IAM と Database Authentication

S3 permission は対象の bucket/prefix に限定してください。実際の operation に応じて、`GetObject`、`PutObject`、listing、multipart、KMS permission を確認してください。proxy mode では server の AWS permission を使用し、direct artifact mode では client permission を使用します。既存の experiment URI は、server flag を変更しただけでは書き換えられません。

EKS Pod Identity には Agent、association、サポートされる SDK が必要であり、Linux EC2 worker が対象です。Fargate や Windows Pod では常に利用可能とは限りません。IRSA も、サポート対象の configuration 内では別の選択肢です。ServiceAccount 名または annotation を 1 つ指定しただけでは、IAM trust、association、SDK setup は完了しません。

S3 用 IAM role が PostgreSQL login を自動的に認可するわけではありません。database network access、TLS validation、user/credential、または別途設定した IAM database authentication を確認してください。意図しない node-role credential fallback を防ぐため、IMDS と SDK configuration をレビューしてください。

## Server Access と Health Check

ClusterIP、private ALB、TLS は networking または transport control を提供しますが、user ごとの MLflow permission に代わるものではありません。直接的な public ALB exposure を前提とせず、組織で保護された ingress architecture を使用してください。

実際の caller に対して MLflow 3.16.0 の `allowed_hosts` と CORS origin を設定してください。この community chart では、対応する CLI argument を `extraArgs.allowedHosts` と `extraArgs.corsAllowedOrigins` で設定できます。Host/CORS restriction は login や authorization に代わるものではありません。basic-auth は 3.16.0 で default により fail-closed authorization へ変更されたため、既存の auth plugin と endpoint compatibility を検証してください。

検証済みの health endpoint は **`/health`** であり、`"OK", 200` を返す実装です。これは HTTP process の応答性を確認するものであり、継続的な RDS/S3 connectivity や user authorization を確認するものではありません。この release では health endpoint を host validation の対象外とします。`static-prefix`、ingress rewrite、plugin を使用する場合は、実際の service path を確認してください。

## 運用上の注意点

replica をスケールする前に、metadata/auth database、session secret、有効な queue/cache を共有または外部化し、failover をテストしてください。その後、topology spread、PDB、readiness、resource limit を適用してください。2 つの Pod だけでは high availability は保証されません。

1 回の API call が常に 1 回の SQL write とは限りません。batch logging、transaction、trace payload、metric history、worker ごとの connection pool をまとめて測定してください。replica/worker 全体の pool は合算されます。1 つの pool の configuration だけでは、database connection の総需要は把握できません。

Aurora Serverless v2 は設定された capacity range と connection、I/O、transaction の制約内で動作します。無制限の burst を吸収したり、より低い cost を保証したりするものではありません。測定した load と recovery requirement に対して provisioned RDS/Aurora と比較してください。

metadata/auth database と artifact を一緒に backup し、restore をテストしてください。`mlflow gc` などの permanent deletion tool は、routine cleanup に追加するのではなく retention policy に照らしてレビューしてください。model alias の変更と serving の再デプロイも別個の operation です。

## 主要な情報源

- [MLflow 3.16.0 release](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracking server architecture](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Community chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [MLflow repository chart](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Server health implementation](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [EKS Pod Identity の制限](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SQLite のユースケースと concurrency](https://www.sqlite.org/whentouse.html)
- [Aurora Serverless v2 の capacity configuration](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[メインページ](README.md) · [クイズ](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
