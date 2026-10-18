# データとセキュリティの境界

> **最終更新日**: 2026年9月13日

## 1. データ所有権の選択肢

| 選択肢 | 構成 |
|---|---|
| データベース運用を一元化するアカウント | プラットフォームチームが1つのアカウント内のすべてのデータベースを所有し、運用する |
| ワークロード所有のデータ | 各ワークロードチームが、自らのデータベースを所有し運用する |
| **ハイブリッド** | 運用データベースはワークロードごとに選び、データレイク／ウェアハウス／ストリーミング基盤などの共有資産は別のデータプラットフォームが所有する |

多くの組織にとって、ハイブリッドは現実的な出発点です。ただし、この選択よりも重要なのは、**アカウントをまたいだバックアップ／リストアの技術的な制約**であり、次のセクションで説明します。

<span id="_2-cross-account-data-recovery-constraints-—-the-conditions-that-actually-change-your-decision"></span>

## 2. リソースとボールトの種類ごとにクロスアカウント復旧を検証する

データの所有者と復旧先は、合わせて選択してください。あるスナップショット API に制限があっても、あらゆる復旧経路が不可能になるわけではありません。

<span id="rds-snapshots"></span>

### RDS スナップショットの共有

- RDS DB インスタンスでは、自動スナップショットを共有する前に手動スナップショットへコピーします。RDS の共有手順では AWS Backup が生成したスナップショットにも言及しますが、AWS Backup のあらゆるリストア手順を定義しているわけではありません。
- 受信側は、暗号化された共有 DB インスタンススナップショットをリストアする前にコピーします。デフォルトの AWS 管理 KMS キーで暗号化されたスナップショットは、そのまま共有できません。承認済みのカスタマーマネージドキーで暗号化したコピーを検討してください。
- 手動スナップショットは最大20アカウントと共有できます。Oracle／SQL Server の permanent／persistent オプションには追加の制約があります。
- **Multi-AZ DB クラスターのスナップショットは、この RDS スナップショット共有経路を利用できません。** これは、論理バックアップや検証済みのレプリケーション／復旧経路をすべて否定するものではなく、データベースをワークロード所有にすることを必須とするものでもありません。エンジン、スナップショットの種類、リージョンのサポート状況、代替の復旧 RTO／RPO を確認してください。

<span id="aws-backup-cross-account-copy"></span>

### 標準 AWS Backup ボールト: コピー後にリストアする

- コピー元とコピー先は、管理アカウントでクロスアカウントバックアップが有効になっている同一 Organization に属している必要があります。
- コピー元ロールには `backup:CopyFromBackupVault` と `backup:CopyIntoBackupVault` が必要です。コピー先ボールトには、後者を許可するリソースポリシーが必要です。サービス固有のバックアップ／コピー権限と KMS 権限も適用されます。
- 暗号化要件はリソースの種類によって異なります。AWS Backup が完全に管理するリソースでは、コピー先に `aws/backup` またはカスタマーマネージドキーを利用できます。それ以外のリソースの種類ではカスタマーマネージドキーが必要です。公式のコピー手順では、デフォルトボールトを使わないようにも注意しています。そのため、このガイドでは**キー／ポリシーを明示的に設定した専用のコピー先ボールト**を使います。ボールト名だけでは、暗号化やコピーへの適性を確認できません。
- 標準ボールトによるクロスアカウント復旧では、最初にコピーし、その後コピー先でリストアします。対象リソースのサービスリンクロール、リストアロール、サブネット、SG を準備してください。
- コールド階層からのクロスアカウントコピーはサポートされていません。リソースとリージョンの機能マトリクスを確認してください。

### 論理的にエアギャップされたボールト: 共有アカウントから直接リストアする

論理的にエアギャップされたボールトは AWS RAM を通じて、別の Organization に属するアカウントを含む個々のアカウントと共有できます。受信側は、サポート対象の復旧ポイントを受信側ボールトへコピーする前に、直接リストアできます。したがって、「AWS Backup はクロスアカウントの直接リストアを一切サポートしない」という説明は正確ではありません。

標準ボールトのコピー権限と、エアギャップされたボールトの RAM 共有を区別してください。リソース／リージョンのサポート、リストア IAM、暗号化キーの種類、共有認可、コピー元アカウントにアクセスできない場合の復旧を検証します。あらゆるデータベースの種類がサポートされると想定しないでください。

<span id="summary"></span>

### 未承認のコピーと共有を制限する

Organization 外に移動したコピー先に、既存コピーが残る場合があります。コピー元の `backup:CopyTargets`／`backup:CopyTargetOrgPaths` 条件、コピー先ボールトポリシー、KMS、RAM 共有権限、Organization 離脱手順をまとめて評価してください。クロスアカウントバックアップを有効にしても、すべてのユーザーにコピー権限が付与されたり、IAM、ボールト、KMS による拒否が回避されたりするわけではありません。

RTO にはインシデント後に実際に実施するコピー、リストア、アプリケーションの検証が含まれます。事前に作成したコピーは、コピー間隔が RPO に関係するようになります。リソース固有の復旧テストと目標を[判断フレームワーク](./06-decision-framework-and-poc.md)に記録してください。

## 3. PII データ層を分離する

RDS など、VPC 内に直接配置するストレージは、一般的なサービス提供層とは別の VPC に配置する方法が適しています。その目的は、ルーティング、検査、直接アクセス、インシデント封じ込めの範囲を分離することです。**VPC を分けるだけでは不十分です**。IAM、SG、KMS キーポリシー、ログ記録、承認済みアクセス経路を組み合わせる必要があります。

> **共有 VPC の監査アクセス**: 参加者は所有者側の NAT Gateway の構成を記述できませんが、所有者が提供するルート／NAT のインベントリ、Config、Flow Logs、委任された読み取りアクセスから根拠を得られます。専用 VPC は所有関係を簡潔にできる一方、共有 VPC が本質的に監査不能というわけではありません。

S3 は VPC 内に配置するリソースではありません。バケット／アカウントの所有権、VPC エンドポイントとそのポリシー、バケット／アクセスポイントのポリシー、KMS キーポリシー、組織で承認された経路を使って制御します。

### 開発／QA から本番の元の PII データへのアクセスを遮断する

「直接アクセスを遮断する」を具体的な API 経路にすると、次のようなカバレッジマトリクスになります。

| 経路 | 制御メカニズム |
|---|---|
| AWS Backup のクロスアカウントコピー | `backup:CopyTargets`／`CopyTargetOrgPaths` の SCP 条件、コピー先ボールトのアクセス方針 |
| RDS DB インスタンスのスナップショット共有 | `rds:ModifyDBSnapshotAttribute` を承認済み自動化に限定し、`DescribeDBSnapshotAttributes` で共有先を監査する |
| Aurora DB クラスターのスナップショット共有 | `rds:ModifyDBClusterSnapshotAttribute` を承認済み自動化に限定し、`DescribeDBClusterSnapshotAttributes` で共有先を監査する |
| RDS／Aurora のパブリックスナップショット共有 | 両方の共有 API について、受信者の許可リストと `restore=all` の拒否を検証し、KMS、検出、修復の制御を維持する |
| EBS スナップショットの外部共有 | `ec2:ModifySnapshotAttribute` と、受信者の createVolumePermission を制限／監査する |
| EC2 Allowed AMIs（利用側） | アカウント／リージョン設定または宣言的ポリシーで、公開／共有 AMI の検出／利用を制限する。アカウント所有の AMI は対象外 |
| S3 Batch Replication／クロスアカウントレプリケーション | バケットポリシー、レプリケーションロールの制限、RCP |
| DMS／Glue 経由の移動 | そのサービスのネットワーク／IAM 経路 |
| CDC ストリーム（MSK／Kinesis／DMS） | リソースポリシーと、クロスアカウントのコンシューマー制限 |
| クロスアカウントの Athena／Redshift クエリ、Lake Formation | Lake Formation のクロスアカウント許可を監査する |

選択したコピー／リストア経路と組織要件に応じて、KMS キーの種類と復旧権限を選んでください。すべての PII ストレージにカスタマーマネージドキーを一律に要求するわけではありません。コピー先のキー、既存のコピー、許可されたキーポリシー／グラント、コピー元アカウントが使えない場合のエアギャップボールト共有を検証してください。

## 4. Secrets Manager／KMS のクロスアカウントアクセス

シークレットのリソースポリシーと呼び出し元の ID ポリシーの両方が必要です。クロスアカウントのシークレットにはカスタマーマネージド KMS キーが必要で、そのキーには所有者のキーポリシーと呼び出し元の IAM ポリシーの両方が必要です。つまり、一元化したシークレット／キー管理では、ポリシーとローテーションだけでは足りません。**両方のアカウントにまたがる権限と復旧責任を共同で管理する必要があります。**

## 5. AWS ネイティブのセキュリティテレメトリと既存 CNAPP

すでに CNAPP（クラウドネイティブアプリケーション保護プラットフォーム）を利用していて、AWS ネイティブ機能も採用する場合、安全な進め方は「製品を置き換える」ことではありません。**セキュリティ目的ごとに、現在のカバレッジと AWS ネイティブ機能を比較し、確認できた不足だけを補います。** 目的は次のように分類できます。

- 組織全体の予防的な制御
- 構成ポスチャ
- データセキュリティポスチャ
- ワークロード実行時の保護
- 脅威検出
- 検出結果のワークフロー
- ワークロードコンテキストに基づく検出

確認済みの事実:

- Security Hub CSPM の標準、コントロール、ASFF 検出結果を、Security Hub の他の機能と区別してください。名称が同じでも、機能範囲や Config への依存が同一とは限りません。
- Security Hub CSPM のコントロールの多くでは、AWS Config の記録が必要です。これを Control Tower 4.0 のマネージドベースラインの依存関係と合わせて確認してください。ただし、IAM Identity Center サービス自体の前提条件として Config を必須にする説明に変えないでください。
- **Security Hub CSPM は有効化前に生成された検出結果を遡って収集せず、有効化されたリージョンでのみ検出結果を処理します。** 文書化されている CIS AWS Foundations Benchmark のセキュリティチェックを網羅するには、サポート対象のすべてのリージョンで有効化する必要があります。GuardDuty もリージョンごとに有効化します。
- GuardDuty と Security Hub はどちらもソウルリージョンで利用できますが、検出結果の種類／コントロールのカバレッジはリージョンによって異なります。比較には、ソウルリージョンの実際のカバレッジを使ってください。

## 6. 共有サブネットでリソースを作成できることを確認済みのサービス

この表は、公式の共有 VPC サポートリストを要約したものです。このリストでは明示的にサービスが省略される場合があります。リストにないサービスはサービス固有のドキュメントを確認し、サポートされないと明記されている場合と、単にリストにない場合を区別してください。

| サポート対象のサービス | 注記 |
|---|---|
| Amazon RDS、Aurora | 主な対象 |
| ElastiCache（Redis OSS） | |
| Redshift、EMR、Glue | データプラットフォームの一般的な対象 |
| OpenSearch Service、MSK | |
| EC2、ECS、EKS、Lambda、EFS | |
| ALB／NLB／GWLB | |
| PrivateLink（インターフェイスエンドポイント） | |
| VPC Lattice、TGW、VPC Peering、Traffic Mirroring | |
| Route 53（クロスアカウントの PHZ 関連付け） | |
| DMS、Verified Access、SageMaker Unified Studio | |
| **Amazon MQ** | **ActiveMQ のみ。RabbitMQ はサポート対象外** |

Amazon MQ RabbitMQ など、公式リストで明示的に除外されているエンジンについては、別の配置を検討してください。共有 VPC から CUJ 全体を除外する前に、その依存先だけを別の VPC や API 経路で接続できないか検討します。

## 次のステップ

境界、アカウント、IAM、ネットワーク、データに関するすべての判断を再現可能にする方法 → [判断フレームワークと PoC 設計](./06-decision-framework-and-poc.md)

## 参考資料

- [RDS スナップショットの共有](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)
- [RDS の暗号化されたスナップショットの共有](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/share-encrypted-snapshot.html)
- [AWS Backup のクロスアカウントコピー](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- [Secrets Manager のクロスアカウントアクセス](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)
- [KMS の外部アカウント向けキーポリシー](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)
- [Security Hub CSPM の概要](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [リージョン別 Security Hub CSPM コントロール](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html)
- [リージョン別 GuardDuty の相違点](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html)
- [AWS SRA セキュリティツール](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html)
- [共有サブネットでサポートされるサービス](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [論理的にエアギャップされたボールトの共有とリストア](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)

- [Aurora スナップショット共有 API](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBClusterSnapshotAttribute.html)
- [EC2 Allowed AMIs の適用範囲](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-allowed-amis.html)
