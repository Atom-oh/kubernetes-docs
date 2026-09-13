# ELBv2、Route 53 と Aurora (ACK)

[ACK](../02-ack.md)

これらは ELBv2 1.7.0 / Route 53 1.6.0 / RDS 1.12.0 それぞれのスキーマ例です。Aurora の前段に NLB を配置するものではありません。内部 NLB/DNS はアプリケーションを提供し、Aurora はそれとは別のアプリケーション依存関係です。エンドツーエンドで接続したデプロイはテストしていません。

3 つのコントローラーすべてについて、インフラと認証/権限を準備してください。VPC、private subnet、security group、hosted zone ID は承認済みの値に置き換えてください。NLB とデータベースの security group は、必要な送信元/ポートのみを許可すべきです。内部 NLB は認可やネットワーク制御の代わりにはなりません。

TargetGroup を作成しても target は登録されません。ACK の target は固定 IP を管理できますが、Kubernetes の Pod IP が変化する場合は、適切な AWS Load Balancer Controller のバインディングと所有権の計画が必要です。2 つのコントローラーが同じ AWS オブジェクトを競合して管理する状態は避けてください。

NLB と TargetGroup の ARN は status.ackResourceMetadata.arn にあります。Listener はサポートされている参照を使用します。Route 53 では type ではなく recordType を使用します。alias の DNS と canonicalHostedZoneID は実際の NLB status の値から設定してください。レコードの hosted zone と、NLB alias target の hosted zone ID は別の値です。

Aurora PostgreSQL 17.10 は 2026 年 8 月に発表されました。実際のアカウント/リージョンについて、describe-db-engine-versions と describe-orderable-db-instance-options で engine/クラスの組み合わせとアップグレードパスを確認してください。以前の 15.4 は新しいデフォルトではありません。サポートされている 2 つ以上の AZ にまたがるデータベース用 subnet を準備し、配置と可用性を確認してください。

manageMasterUserPassword=true は、平文パスワードの例を使わずに RDS の Secrets Manager 統合を要求します。必要な KMS/Secrets Manager の権限、コスト、そしてアプリケーションへの承認済みのファイル受け渡し方法を準備してください。deletionProtection と retain は、ライフサイクルの異なる層を保護します。

DBInstance の名前や Role タグによって writer/reader の役割が固定されることはありません。実際のクラスターメンバーシップを確認してください。フェイルオーバーによって writer は変わり得ます。promotionTier は昇格の優先度であり、恒久的な役割の割り当てではありません。カスタム READER エンドポイントは、選択したインスタンスのうち現時点で reader であるものだけを使用します。利用可能なメンバーと、フェイルオーバー後の再接続の挙動を確認してください。AZ を示すように見えるエンドポイント名があっても、AZ フィルタリングが実装されるわけではありません。

## LoadBalancer — loadbalancer-app-nlb

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: LoadBalancer
metadata:
  name: app-nlb
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-nlb
  scheme: internal
  type: network
  subnets:
  - subnet-0123456789abcdef0
  - subnet-0123456789abcdef1
  securityGroups:
  - sg-0123456789abcdef0
```

## TargetGroup — targetgroup-app-tg

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: TargetGroup
metadata:
  name: app-tg
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-tg
  protocol: TCP
  port: 8080
  targetType: ip
  vpcID: vpc-0123456789abcdef0
  healthCheckProtocol: TCP
  healthCheckPort: '8080'
```

## Listener — listener-app-listener

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: Listener
metadata:
  name: app-listener
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  loadBalancerRef:
    from:
      name: app-nlb
  port: 8080
  protocol: TCP
  defaultActions:
  - type: forward
    targetGroupRef:
      from:
        name: app-tg
```

## RecordSet — recordset-app-dns

```yaml
apiVersion: route53.services.k8s.aws/v1alpha1
kind: RecordSet
metadata:
  name: app-dns
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  hostedZoneID: REPLACE_WITH_PRIVATE_ZONE_ID
  name: app.example.com
  recordType: A
  aliasTarget:
    dnsName: REPLACE_WITH_NLB_STATUS_DNS_NAME
    hostedZoneID: REPLACE_WITH_NLB_CANONICAL_HOSTED_ZONE_ID
    evaluateTargetHealth: true
```

## DBSubnetGroup — dbsubnetgroup-app-db-subnets

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBSubnetGroup
metadata:
  name: app-db-subnets
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-db-subnets
  description: Private subnets in distinct supported AZs
  subnetIDs:
  - subnet-0123456789abcdef0
  - subnet-0123456789abcdef1
```

## DBCluster — dbcluster-app-aurora

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBCluster
metadata:
  name: app-aurora
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbClusterIdentifier: app-aurora
  engine: aurora-postgresql
  engineVersion: '17.10'
  masterUsername: dbadmin
  manageMasterUserPassword: true
  dbSubnetGroupRef:
    from:
      name: app-db-subnets
  vpcSecurityGroupIDs:
  - sg-0123456789abcdef1
  storageEncrypted: true
  backupRetentionPeriod: 7
  deletionProtection: true
```

## DBInstance — dbinstance-app-db-1

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-1
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-1
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 0
```

## DBInstance — dbinstance-app-db-2

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-2
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-2
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 1
```

## DBInstance — dbinstance-app-db-3

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-3
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-3
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 2
```

## DBClusterEndpoint — dbclusterendpoint-app-selected-readers

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBClusterEndpoint
metadata:
  name: app-selected-readers
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbClusterEndpointIdentifier: app-selected-readers
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  endpointType: READER
  staticMemberRefs:
  - from:
      name: app-db-2
  - from:
      name: app-db-3
```

## 検証と運用上の前提条件

フィールドは公式のバージョン付き CRD と照合して確認しました。スキーマが正しいことは、IAM 権限、AWS サービスの制約、作成、接続性、復旧を保証するものではありません。適用する前に、retain されるリソースについて所有権、コスト、クリーンアップ、バックアップの責任を割り当ててください。

- [elbv2 v1.7.0 CRDs](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.7.0/config/crd/bases)
- [route53 v1.6.0 CRDs](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.6.0/config/crd/bases)
- [rds v1.12.0 CRDs](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.12.0/config/crd/bases)
- [Aurora PostgreSQL マイナーバージョン](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora カスタムエンドポイント](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
