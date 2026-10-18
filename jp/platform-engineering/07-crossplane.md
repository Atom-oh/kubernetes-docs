# Crossplane

> **最終更新日**: 2026 年 10 月 16 日 · Crossplane 2.4.2 / AWS provider 2.9.0

## 概念と v2 の変更点

Crossplane は Kubernetes API とコントローラーを通じて、インフラストラクチャとアプリケーションのリソースを調整します。2020 年 6 月 25 日に CNCF に参加し、2021 年 9 月 14 日に Incubating、2025 年 10 月 28 日に Graduated となりました。2023 年／2024 年に Graduated したという相反する記述は訂正済みです。

| コンポーネント | 役割と現在の範囲 |
| --- | --- |
| Provider | パッケージとして CRD／コントローラーをインストールします。AWS のサービスごとに適切なパッケージを選択してください。一つのパッケージがすべての AWS API を網羅するとは限りません。 |
| Managed Resource（MR） | 外部リソースを管理する Provider API です。ここで示す v2 の例は名前空間スコープです。 |
| Composite Resource（XR） | プラットフォーム API のインスタンスです。XRD v2 の既定スコープは Namespaced です。 |
| XRD | XR のスキーマとスコープを定義します。v1 の LegacyCluster と v2 の Namespaced を区別してください。 |
| Composition | Function パイプラインを定義し、XR 入力から必要なリソースと状態を計算します。 |
| Claim | 従来のクラスタースコープ XR に対する名前空間スコープのインターフェイスです。新しい名前空間スコープ XR で必須となる層ではありません。 |

![Crossplane v2 の概念](../.gitbook/assets/en-platform-engineering-07-crossplane-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-07-crossplane-0.html)

既存の v1 XRD は引き続き LegacyCluster Claim を使用でき、従来のクラスタースコープ MR もサポートされています。削除された Resources モードの Composition、ControllerConfig、XR ネイティブの接続情報公開を残したまま、コアのバージョンだけを変更しないでください。公式の v2 移行ガイドでは 1.20 からの準備手順を説明しています。

Terraform も宣言的な望ましい状態を使い、CI で plan/apply を自動化できます。主な違いは、実行ワークフローとコントローラーによる継続的な調整です。Crossplane の動作は managementPolicies、サポート対象フィールド、エラー、クォータにも左右されるため、ドリフトのすべてを直ちに修復するわけではありません。

## Core、Provider、権限

確認対象の Helm chart は 2.4.2 です。このコマンドはオフラインで chart を調査し、クラスターにはインストールしません。

```bash
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update
helm template crossplane crossplane-stable/crossplane   --version 2.4.2 --namespace crossplane-system   --set metrics.enabled=true
```

現在の `provider.defaultActivations` の既定値は `["*"]` です。どの API を有効にするか判断する際は、MRD、ManagedResourceActivationPolicies、インストール済みサービスの範囲を確認してください。Provider のインストール成功だけでは、AWS 認証やリソースの Ready を証明しません。

以下の IAM ロールはプレースホルダーです。信頼ポリシーの対象を正確な EKS issuer、audience、ServiceAccount subject に限定し、サービスアクションとリソースの範囲も絞ってください。`s3:*`／`rds:*`／`ec2:*`／`iam:*` に RequestedRegion 条件を追加しても最小権限にはなりません。RDS と EC2 の Provider には、それぞれ個別に確認したランタイム／ID 設定が必要です。

```yaml
apiVersion: pkg.crossplane.io/v1beta1
kind: DeploymentRuntimeConfig
metadata:
  name: provider-aws-s3-reviewed
spec:
  deploymentTemplate:
    spec:
      selector: {}
      template:
        spec:
          containers:
          - name: package-runtime
            resources:
              requests:
                cpu: 100m
                memory: 256Mi
              limits:
                cpu: 500m
                memory: 512Mi
            ports:
            - name: metrics
              containerPort: 8080
        metadata:
          labels:
            app: provider-aws-s3-reviewed
  serviceAccountTemplate:
    metadata:
      name: provider-aws-s3-reviewed
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReplaceApprovedS3ProviderRole
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws-s3
spec:
  package: xpkg.crossplane.io/crossplane-contrib/provider-aws-s3:v2.9.0
  packagePullPolicy: IfNotPresent
  revisionActivationPolicy: Manual
  revisionHistoryLimit: 2
  runtimeConfigRef:
    name: provider-aws-s3-reviewed
```

複数の Provider に同じ固定 ServiceAccount を所有させないでください。`packagePullPolicy` はパッケージ取得を制御し、`revisionActivationPolicy` は有効化を制御します。`Manual` の場合は ProviderRevision を確認し、必要なバージョンを明示的に有効化してください。

2.9.0 の S3 マニフェストはコミュニティレジストリと Upbound レジストリから取得できましたが、digest は異なっていました。バージョン文字列が同じでも、成果物が同一とは限りません。使用する配布元、レジストリ／digest、サポート条件を固定してください。

この例は IRSA を使う名前空間スコープの ProviderConfig です。2.9.0 のスキーマは Pod Identity にも対応しますが、実際の association／SDK／ランタイム設定が必要です。名前空間ごとに ProviderConfig を分けるだけでは AWS 権限は分離されません。設定の書き込み、参照、ロール引き受けの境界も制約してください。

```yaml
apiVersion: aws.m.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: team-aws
  namespace: team-alpha
spec:
  credentials:
    source: IRSA
```

![Core と Provider コントローラーの役割](../.gitbook/assets/en-platform-engineering-07-crossplane-1.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-07-crossplane-1.html)

## 名前空間スコープの S3 例

この例では `*.aws.m.upbound.io` の名前空間スコープ API を使用します。従来のクラスタースコープ `*.aws.upbound.io` API とは別です。`providerConfigRef` には kind/name を指定します。外部リソースを保持するため、`managementPolicies` から Delete を除外します。これらの名前空間 API には従来の `deletionPolicy` フィールドはありません。

実際に使用する bucket 名、リージョン、ID を先に準備してください。Delete を除外しても更新は許可されます。保持設定はバックアップでもコスト整理の方法でもありません。

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: Bucket
metadata:
  name: app-data
  namespace: team-alpha
  annotations:
    crossplane.io/external-name: replace-with-globally-unique-bucket
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    forceDestroy: false
    tags:
      Environment: Development
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketPublicAccessBlock
metadata:
  name: app-data-public-access
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketVersioning
metadata:
  name: app-data-versioning
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    versioningConfiguration:
      status: Enabled
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketServerSideEncryptionConfiguration
metadata:
  name: app-data-encryption
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    rule:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

Block Public Access の 4 設定はすべて有効です。このバージョンでは `versioningConfiguration` と `applyServerSideEncryptionByDefault` はオブジェクトであり、従来の配列形式ではありません。削除計画では bucket 内のオブジェクト／バージョンと `forceDestroy=false` も考慮してください。

## PostgreSQL プラットフォーム API

この例では承認済み VPC、異なる AZ のプライベートサブネット、クライアント SecurityGroup、パスワード Secret を使用します。ネットワークとデータベースのプロビジョニングは一つのトランザクションではありません。VPC／Subnet MR を別途管理する場合は、CIDR、ルート、egress、DNS、AZ をまとめて検証してください。

新しい XR はその名前空間に直接作成します。誤った Regexp transform で metadata 名のハイフンを取り除こうとせず、`dbName` を個別に検証してください。この例では ProviderConfig 名を `team-aws` に制約します。

```yaml
apiVersion: apiextensions.crossplane.io/v2
kind: CompositeResourceDefinition
metadata:
  name: postgresqldatabases.platform.example.com
spec:
  scope: Namespaced
  group: platform.example.com
  names:
    kind: PostgreSQLDatabase
    plural: postgresqldatabases
  versions:
  - name: v1alpha1
    served: true
    referenceable: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - parameters
            properties:
              parameters:
                type: object
                required:
                - environment
                - dbName
                - vpcID
                - subnetIDs
                - clientSecurityGroupID
                - passwordSecretName
                properties:
                  storageGB:
                    type: integer
                    minimum: 20
                    maximum: 1000
                    default: 50
                  environment:
                    type: string
                    enum:
                    - dev
                    - production
                  dbName:
                    type: string
                    pattern: ^[a-z][a-z0-9]{0,62}$
                  vpcID:
                    type: string
                  subnetIDs:
                    type: array
                    minItems: 2
                    items:
                      type: string
                  clientSecurityGroupID:
                    type: string
                  passwordSecretName:
                    type: string
                  providerConfigName:
                    type: string
                    default: team-aws
                    enum:
                    - team-aws
          status:
            type: object
            properties:
              endpoint:
                type: string
              port:
                type: integer
```

提供される version と参照可能な version を区別してください。複数の version を referenceable にしないでください。実際の CLI `xrd convert` の検証では、Namespaced に対して CRD が 1 つ、LegacyCluster と `claimNames` を使う場合は XR／Claim 用 CRD が 2 つ生成されました。変換はクラスターへのインストールでもデータ移行でもありません。

### Function パイプライン

```yaml
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-patch-and-transform:v0.10.10
---
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-auto-ready
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-auto-ready:v0.7.0
```

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: postgresql-aws-reviewed
spec:
  compositeTypeRef:
    apiVersion: platform.example.com/v1alpha1
    kind: PostgreSQLDatabase
  mode: Pipeline
  pipeline:
  - step: patch-and-transform
    functionRef:
      name: function-patch-and-transform
    input:
      apiVersion: pt.fn.crossplane.io/v1beta1
      kind: Resources
      resources:
      - name: securityGroup
        base:
          apiVersion: ec2.aws.m.upbound.io/v1beta1
          kind: SecurityGroup
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              description: Application database security group
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - &id001
          type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.providerConfigName
          toFieldPath: spec.providerConfigRef.name
          policy:
            fromFieldPath: Required
        - &id002
          type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.tags.Environment
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.vpcID
          toFieldPath: spec.forProvider.vpcId
          policy:
            fromFieldPath: Required
      - name: securityGroupRule
        base:
          apiVersion: ec2.aws.m.upbound.io/v1beta1
          kind: SecurityGroupRule
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              type: ingress
              protocol: tcp
              fromPort: 5432
              toPort: 5432
              securityGroupIdSelector:
                matchControllerRef: true
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.providerConfigName
          toFieldPath: spec.providerConfigRef.name
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.clientSecurityGroupID
          toFieldPath: spec.forProvider.sourceSecurityGroupId
          policy:
            fromFieldPath: Required
      - name: subnetGroup
        base:
          apiVersion: rds.aws.m.upbound.io/v1beta1
          kind: SubnetGroup
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              description: Approved private database subnets
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - *id001
        - *id002
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.subnetIDs
          toFieldPath: spec.forProvider.subnetIds
          policy:
            fromFieldPath: Required
      - name: database
        base:
          apiVersion: rds.aws.m.upbound.io/v1beta1
          kind: Instance
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              engine: postgres
              engineVersion: '17.10'
              username: dbadmin
              storageType: gp3
              storageEncrypted: true
              publiclyAccessible: false
              skipFinalSnapshot: false
              dbSubnetGroupNameSelector:
                matchControllerRef: true
              vpcSecurityGroupIdSelector:
                matchControllerRef: true
              passwordSecretRef:
                name: replace-secret
                key: password
              port: 5432
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - *id001
        - *id002
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.dbName
          toFieldPath: spec.forProvider.dbName
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.storageGB
          toFieldPath: spec.forProvider.allocatedStorage
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.passwordSecretName
          toFieldPath: spec.forProvider.passwordSecretRef.name
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.instanceClass
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: db.t4g.medium
              production: db.r6g.large
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.multiAz
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: false
              production: true
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.deletionProtection
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: false
              production: true
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.backupRetentionPeriod
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: 7
              production: 30
        - type: FromCompositeFieldPath
          fromFieldPath: metadata.name
          toFieldPath: spec.forProvider.finalSnapshotIdentifier
          policy:
            fromFieldPath: Required
          transforms:
          - type: string
            string:
              type: Format
              fmt: '%s-final-review-before-delete'
        - type: FromCompositeFieldPath
          fromFieldPath: metadata.name
          toFieldPath: spec.writeConnectionSecretToRef.name
          policy:
            fromFieldPath: Required
          transforms:
          - type: string
            string:
              type: Format
              fmt: '%s-mr-connection'
        - type: ToCompositeFieldPath
          fromFieldPath: status.atProvider.address
          toFieldPath: status.endpoint
          policy:
            fromFieldPath: Optional
        - type: ToCompositeFieldPath
          fromFieldPath: status.atProvider.port
          toFieldPath: status.port
          policy:
            fromFieldPath: Optional
        connectionDetails:
        - name: endpoint
          type: FromFieldPath
          fromFieldPath: status.atProvider.address
        - name: username
          type: FromFieldPath
          fromFieldPath: spec.forProvider.username
  - step: readiness
    functionRef:
      name: function-auto-ready
```

このパイプラインは SecurityGroup、ingress rule、SubnetGroup、RDS Instance を計算します。`matchControllerRef` selector は共通の XR 所有関係を使います。誤った `metadata.uid` ラベルのパッチは使いません。ingress は VPC CIDR 全体ではなく、承認済みクライアント SG から許可します。

Environment map は Boolean／数値の型を保持します。ネイティブ Function の実行では、本番設定として `db.r6g.large`、Multi-AZ／`deletionProtection=true`、30 日間のバックアップ保持が確認されました。実際に使う AWS リージョンで engine 17.10／クラスの提供状況とストレージ上限を検証してください。

`passwordSecretRef` は同じ名前空間に準備した `rds-master-password/password` Secret を参照します。実際のパスワードをドキュメント、CLI 引数、環境変数に記載しないでください。この例では `autoGeneratePassword` と RDS 管理のマスターパスワードを同時に有効化しません。

![テスト済み環境入力を使う同じ Composition](../.gitbook/assets/en-platform-engineering-07-crossplane-2.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-07-crossplane-2.html)

### 開発環境と本番環境の入力

```yaml
apiVersion: platform.example.com/v1alpha1
kind: PostgreSQLDatabase
metadata:
  name: orders-db
  namespace: team-alpha
spec:
  crossplane:
    compositionRef:
      name: postgresql-aws-reviewed
  parameters:
    environment: dev
    dbName: orders
    storageGB: 50
    vpcID: vpc-0123456789abcdef0
    subnetIDs:
    - subnet-0123456789abcdef0
    - subnet-0123456789abcdef1
    clientSecurityGroupID: sg-0123456789abcdef0
    passwordSecretName: rds-master-password
    providerConfigName: team-aws
```

```yaml
apiVersion: platform.example.com/v1alpha1
kind: PostgreSQLDatabase
metadata:
  name: orders-db
  namespace: team-alpha
spec:
  crossplane:
    compositionRef:
      name: postgresql-aws-reviewed
  parameters:
    environment: production
    dbName: orders
    storageGB: 200
    vpcID: vpc-0123456789abcdef0
    subnetIDs:
    - subnet-0123456789abcdef0
    - subnet-0123456789abcdef1
    clientSecurityGroupID: sg-0123456789abcdef0
    passwordSecretName: rds-master-password
    providerConfigName: team-aws
```

これらのファイルは、同じ名前の XR に対する代替入力です。環境を同時に構成する場合は、実際の名前空間、名前、ポリシーをそれぞれ分けてください。`spec.crossplane.compositionRef` は v2 の管理フィールドであり、従来の Claim の `spec.compositionRef` とは異なります。

## 接続 Secret と Ready 状態

コアネイティブの XR 接続情報公開は v2 で削除されました。MR の `writeConnectionSecretToRef` は引き続き使えますが、ここで示す名前空間 MR には name だけを指定します。P&T 0.10.10 は `connectionDetails` を合成 Secret に集約できます。

この例で `orders-db-connection` に公開するのは、観測された RDS address と username のみです。password が自動的に含まれるとはしていません。アプリケーションは endpoint と準備済み password の Secret をファイルとしてマウントし、ローテーション、TLS、再試行を適切に扱ってください。Base64 は暗号化ではありません。

外部 Secrets Manager にデータを送る場合は、適切な PushSecret／Provider 対応を評価してください。ExternalSecret は通常、外部の値を Kubernetes に取り込みます。以前の逆方向の例は誤りでした。

![Composition、観測結果、status、Secret の扱い](../.gitbook/assets/en-platform-engineering-07-crossplane-3.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-07-crossplane-3.html)

新しいリソースの render 結果は `Ready=False` でした。合成した `Ready=True`／address の観測値を与えると、XR の status と合成 Secret が作成されました。出力された日時、名前、状態はシミュレーション結果であり、実際の AWS プロビジョニング記録ではありません。render の成功とサービスの Ready は別です。

## リソースの引き継ぎ、削除、アップグレード

外部名を関連付けた直後に、既存リソースに対する作成／更新／削除をすべて有効にしないでください。まずサポートされる Observe 動作、識別子、リージョン、所有関係を調べ、望ましいフィールドを確認してから管理範囲を広げてください。`initProvider` と調整対象の `forProvider` を区別してください。

これらの名前空間 MR では、リソースを保持するため `managementPolicies` から Delete を除外します。従来の `deletionPolicy: Orphan` とは区別し、ポリシーと Provider の対応状況を確認してください。RDS の `deletionProtection`、最終スナップショット、バックアップはそれぞれ別の保護層です。実際に削除する前に `finalSnapshotIdentifier` の衝突を確認してください。

XR の削除により MR と合成 Secret は削除される一方、Delete を除外したポリシーによって AWS リソースが保持される場合があります。保持するデータベースの認証情報、バックアップ、以降の所有方法を計画してください。古い alpha Usage を既定として使わず、現在の `protection.crossplane.io` Usage／ClusterUsage API とスコープを確認してください。

core、Provider、Function のバージョンは個別に固定し、revision、CRD、IAM の変更を検証してください。稼働中 Composition の API group を単に変更すると、リソースが再作成される可能性があります。新しい Composition を使い、意図的な移行を行ってください。snapshot／restore とデータ検証なしに無停止を約束しないでください。

## 監視と調整

確認対象の AWS Provider の既定値は、poll jitter を含め `--poll=10m` と `--sync=1h` です。`--max-reconcile-rate` はグローバルな rate と同時実行数の両方の設定に使われ、単なる固定同時実行数ではありません。これらはランタイム設定であり、IRSA ProviderConfig の一部ではありません。

この例では、実際の core／Provider Pod label と metrics port を接続します。core chart の `metrics.enabled` を有効にし、Prometheus Operator／scraping は別途準備してください。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: crossplane
  namespace: crossplane-system
spec:
  jobLabel: app
  selector:
    matchLabels:
      app: crossplane
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: provider-aws-s3
  namespace: crossplane-system
spec:
  jobLabel: app
  selector:
    matchLabels:
      app: provider-aws-s3-reviewed
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
```

変わり続ける ProviderRevision 名の label を selector に固定しないでください。`kube_customresource_status_condition` は Crossplane が自動で提供するメトリクスではなく、kube-state-metrics の custom resource metrics などの設定が必要です。rate／increase をカウンターに使う前に実際の名前／label を検証し、histogram quantile は適切にグループ化してください。

## ACK、Backstage、GitOps

ACK リソースも名前空間スコープであり、kro などのツールと組み合わせて Composition に含められます。ACK がクラスタースコープ CR のみを提供する、または CNCF プロジェクトであるという主張は誤りです。Crossplane の名前空間分離は IAM や ProviderConfig／Composition の作成権限の代わりにはなりません。ACK、Terraform、Crossplane の間で、各外部リソースを変更する所有者を一つにしてください。

準備済み Backstage skeleton／action を使い、XR YAML、レビュー済み GitOps PR、ArgoCD による調整を作成します。PR を開いただけではデータベースは作成されません。main ブランチに未マージの catalog file はまだ登録できません。Git history と cloud API audit log は別々です。外部リソースの削除／保持ポリシーに照らして、ArgoCD の prune を確認してください。

![レビュー済み GitOps 変更から XR の調整まで](../.gitbook/assets/en-platform-engineering-07-crossplane-4.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-07-crossplane-4.html)

## 検証範囲

元の韓国語ガイド 1,958 行と英語ガイド 1,827 行、143 行のクイズ 2 件、固有の fenced code block 83 個、および追加の indented code block を読みました。公式 CLI／core 2.4.0 バイナリと P&T 0.10.10／auto-ready 0.7.0 のソースを確認しました。

実際の localhost Function と core render engine で開発、本番、観測状態の各ケースを処理しました。CLI の API-server validation library で MR、XR、DRC、Provider を検証し、core Secret は Kubernetes の公式 OpenAPI と照合しました。不正なデータベース名、Provider の選択、ストレージ入力は拒否されることを確認しました。その後 Function プロセスを停止しました。

AWS／Kubernetes リソース、実際の RDS／ネットワーク／IAM 認証、backup／restore、HA、負荷、Prometheus scrape は実行していません。ローカル出力を本番デプロイ成功として示すものではありません。

- [Crossplane 2.4](https://docs.crossplane.io/v2.4/)
- [v2 へのアップグレード](https://docs.crossplane.io/latest/guides/upgrade-to-crossplane-v2/)
- [接続情報](https://docs.crossplane.io/v2.4/guides/connection-details-composition/)
- [AWS Provider 2.9.0](https://github.com/crossplane-contrib/provider-upjet-aws/tree/v2.9.0)
- [Patch and Transform 0.10.10](https://github.com/crossplane-contrib/function-patch-and-transform/tree/v0.10.10)
- [CNCF](https://www.cncf.io/projects/crossplane/)

[Crossplane クイズ](../quizzes/platform-engineering/07-crossplane-quiz.md)
