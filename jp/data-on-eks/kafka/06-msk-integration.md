# パート 6: MSK Integration

> **対応バージョン**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **最終更新**: July 9, 2026

## ラボ環境のセットアップ

このドキュメントの例を進めるには、以下のツールと環境が必要です。

### 必要なツール

* AWS CLI v2 (MSK cluster と IAM policies の管理用)
* kubectl v1.28 以降、動作する EKS cluster
* `aws-msk-iam-auth` client library (IAM authentication を使用する Kafka clients 用)
* External Secrets Operator または IRSA が設定された EKS cluster (credential injection 用)

前のパートでは、Strimzi を使って EKS 上で Kafka を自分で実行する方法を扱いました。このパートでは、EKS workloads を Amazon MSK — AWS のフルマネージド Kafka service — に接続する方法と、self-managed の Strimzi アプローチとのトレードオフを扱います。また、Kafka と Kinesis Data Streams の関係という、よくある混同点も明確にします。Kinesis Data Streams は完全に別の AWS streaming service です。

## Amazon MSK vs. Self-Managed Strimzi

どちらのアプローチでも EKS workload は Kafka と通信できますが、brokers が実際にどこで動作し、誰が運用するかが異なります。MSK は cluster の外側にある AWS-managed infrastructure 上で brokers を実行します。Strimzi は EKS cluster 内の Pods として brokers を実行します。

| Aspect | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi (self-managed on EKS) |
| --- | --- | --- | --- |
| **Operational burden** | AWS が broker の patching、hardware replacement、storage expansion を処理します | AWS が broker sizing を完全に不要にします (fully auto-scaling) | Operator が rolling upgrades/reconciliation を自動化しますが、upgrade timing、capacity planning、incident response は引き続き自分たちで担います |
| **Cost model** | Per-broker-hour + storage (GB-month) + data transfer | Throughput-based (per partition, per GB in/out) | 直接の EC2/EBS cost — 大規模では通常より安価ですが、運用人員のコストは別途負担します |
| **Autoscaling** | Storage auto-expansion はサポートされています。broker scaling は manual/API-driven です | Fully automatic per-partition scaling。brokers は概念として公開されません | Cruise Control のような tools による半自動化。ただし通常は自分たちで trigger します |
| **Custom configuration** | Broker configuration (`server.properties`) をカスタマイズできます | Custom broker config はありません。一部の APIs/features は制限されます (例: 特定の ACL types、connector types) | ほぼすべてを調整可能です — listeners、interceptors、KRaft controller settings |
| **Version support** | AWS が supported Kafka version list を管理しますが、upstream より遅れる場合があります | Fixed version、version choice なし | Strimzi がサポートする任意の Kafka version を、upstream がリリースしたタイミングで採用できます |
| **Multi-tenancy** | cluster/resource policies による分離。fine-grained customization は限定的です | Tenant isolation は AWS の internal implementation に委ねられます | namespaces、`KafkaUser` ACLs、custom listeners による fine-grained tenancy |
| **Observability/GitOps fit** | CloudWatch/Prometheus exporters 経由で統合します。AWS console が主要な management surface です | 同じ | platform の残りの部分と同じ GitOps/observability pipeline (Argo CD, Prometheus Operator) に自然に適合します |

### MSK を選ぶ理由

* チームに Kafka broker operations の深い専門知識がない、または Kafka operations を core competency にしたくない
* AWS-native operations tooling (console, IAM, CloudWatch) にすでに大きく投資している
* traffic の予測が難しく、MSK Serverless によって broker capacity planning を完全に不要にしたい

### MSK が存在するにもかかわらず、Strimzi で EKS 上に Kafka を自分で実行する理由

* platform の残りの部分 — 他の workloads、GitOps、Prometheus/Grafana — と **同じ tools と同じ deployment pipeline** で Kafka を管理したい。運用対象として 2 つ目の AWS console/IAM surface を追加したくない
* 単一の cloud に縛られない **portability** が必要 (on-prem、multi-cloud migration の可能性)
* 非常に大規模な場合、EC2/EBS を直接管理する方が per-broker-hour pricing より cost-efficient
* MSK がまだ追いついていない最新の Kafka features (new KIPs、custom interceptors、specific KRaft tuning options) が必要

## EKS から MSK への接続

EKS workload が MSK brokers に到達するには、network path と authentication mechanism の両方が必要です。

### Network path

* **Same VPC**: EKS cluster と MSK cluster が同じ VPC 内にある場合、subnet routing だけで connectivity が得られます — 最もシンプルで latency も最小です。
* **Different VPC**: 2 つの VPC を接続するには VPC peering または AWS Transit Gateway が必要です。MSK は public access (public broker endpoints) もサポートしますが、production setups では通常 private connectivity が好まれます。
* **Security groups**: MSK cluster の security group は、関連する broker ports — plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098 — で EKS node (または Pods が独自の security groups を持つ場合は pod) security group からの inbound traffic を明示的に許可する必要があります。default では何も許可されません。

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Authentication mechanisms の比較

| Mechanism | How it works | EKS integration point |
| --- | --- | --- |
| **IAM authentication (`AWS_MSK_IAM`)** | client は `AWS_MSK_IAM` を使用した SigV4-signed request で認証します。これは専用の custom SASL mechanism (OAUTHBEARER extension ではない) です。IAM policies が per-topic permissions を制御します | IRSA 経由で pod に IAM role を付与します — 配布する credentials はまったくありません |
| **SASL/SCRAM** | Username/password based。credentials は AWS Secrets Manager に保存されます | External Secrets Operator 経由で SCRAM credentials を Secrets Manager から Kubernetes Secret に同期します |
| **Mutual TLS (mTLS)** | AWS Private CA が発行した client certificates。identity は certificate によって検証されます | cert-manager または External Secrets Operator 経由で certificates/keys を pods に mount します |

IAM authentication は EKS に最も自然に適合します。IRSA (IAM Roles for Service Accounts) を使うと、pod に scoped IAM role を付与し、topic-level access control を IAM policy だけで表現できます — 配布またはローテーションする passwords や certificates は不要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:AlterCluster",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:cluster/my-msk-cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:us-east-1:111122223333:topic/my-msk-cluster/*/orders"
    }
  ]
}
```

client 側では、`aws-msk-iam-auth` library を classpath (または使用言語の同等 package) に追加し、Kafka client を次のように設定します。

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect は AWS のフルマネージド Kafka Connect offering です。AWS が Connect worker infrastructure の provisioning、scaling、patching を処理します。connector plugins (JAR bundles) は S3 にアップロードして登録します。

重要な点は、MSK Connect は **MSK clusters に限定されない** ということです。bootstrap brokers への network reachability があれば、MSK Connect は Strimzi 経由で EKS 上に実行されている self-managed Kafka cluster に対しても connectors を実行できます。

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| Aspect | MSK Connect | Strimzi `KafkaConnect` (self-operated on EKS) |
| --- | --- | --- |
| **Operational burden** | AWS が worker infrastructure を管理します。自分たちは connector configuration だけを管理します | worker pod scaling、monitoring、resource tuning を自分で管理します |
| **Flexibility** | AWS がサポートする connector framework に限定されます | 任意の connectors、custom SMTs (Single Message Transforms)、sidecars を自由に使用できます |
| **Portability** | AWS-only service で、他の場所へ移すのは困難です | そのまま他の Kubernetes cluster へ portable です |
| **Observability** | CloudWatch Logs/Metrics 経由の connector status | EKS workloads の残りと同じ Prometheus/Grafana pipeline に統合されます |

## Kinesis Data Streams との比較とブリッジ

Kinesis Data Streams と Kafka は同じ文脈で語られることが多いですが、両者は **互換性のある protocols ではありません**。Kinesis は独自の API/SDK を持つ AWS-native streaming service であり、Kafka の producer/consumer protocol を理解しません。MSK が "Kafka-compatible" と説明される事実は、Kinesis と相互運用できることを意味しません — MSK は Apache Kafka protocol の managed implementation であり、Kinesis は完全に別の service です。

| Aspect | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **Protocol** | 幅広い client/tooling ecosystem と互換性のある open-source Kafka protocol | AWS-proprietary API。Kafka clients とは互換性がありません |
| **Scaling unit** | Partitions (topic 作成時に定義され、repartition 可能) | Shards (read/write capacity units。split/merge で調整) |
| **Operational complexity** | brokers/controllers の運用が必要 (MSK はこれを AWS にオフロードします) | フルマネージドで、server concept はまったくありません |
| **AWS service integration** | connectors (Kafka Connect, MSK Connect) 経由の間接的な統合 | Lambda triggers、Firehose、Kinesis Data Analytics との native かつ direct integration |
| **Ecosystem** | 幅広い open-source ecosystem: Kafka Streams、ksqlDB、Flink、Debezium | より小さく、AWS-service-centric な ecosystem。ただし統合はよりシンプル |
| **Retention** | 実質的に unlimited (storage のみ支払い。default 7 days) | Default 24 hours。最大 365 days まで延長可能 (cost は増加) |

### 実際の bridging pattern

Kafka と Kinesis を実際に接続する必要がある場合 — migration のため、または legacy Kinesis consumers とブリッジするため — 実用的な pattern は、built-in protocol compatibility ではなく、**Kafka Connect (または MSK Connect) 上で動作する Kinesis connector** です。

* **Kinesis Sink connector**: Kafka topic から messages を読み取り、Kinesis stream に書き込みます — Kafka-based pipeline の output を Kinesis consumption ecosystem (Lambda, Firehose) に渡すのに便利です
* **Kinesis Source connector**: Kinesis stream から records を読み取り、Kafka topic に書き込みます — consumers を段階的に Kafka へ移行しながら、既存の Kinesis producers を維持するのに便利です

これらの connectors は MSK Connect にデプロイすることも、Strimzi の `KafkaConnect`/`KafkaConnector` CRs 経由で EKS 上に直接実行することもできます — 前のセクションで説明した MSK Connect vs. Strimzi のトレードオフがここにも適用されます。

## 意思決定ガイド

この checklist を使って、self-managed Strimzi、MSK Provisioned、MSK Serverless、Kinesis のどれにするかを絞り込んでください。

* **チームに Kafka operations の専門知識があり、fine-grained tuning/custom configuration が必要ですか?** → Yes: Strimzi (self-managed on EKS) / No: MSK を検討
* **multi-cloud/on-prem portability は必須要件ですか?** → Yes: Strimzi / No: MSK は評価する価値があります
* **traffic が予測不能または spiky で、broker capacity planning を完全に不要にしたいですか?** → Yes: MSK Serverless / No: MSK Provisioned または Strimzi
* **AWS-native event processing (Lambda, Firehose) にすでに深く投資しており、Kafka ecosystem (Kafka Streams, ksqlDB, etc.) は不要ですか?** → Yes: Kinesis Data Streams を評価 / No: Kafka (MSK/Strimzi) を継続
* **AWS console/IAM surface を追加せず、EKS platform の残りと同じ GitOps pipeline で Kafka を管理したいですか?** → Yes: Strimzi / No: MSK

実際には、答えが "both" になることもよくあります — 速度を優先して新しい service を MSK Serverless で開始し、custom tuning が必要になったら Strimzi に移行する、という流れは一般的です。

## 次のステップ

MSK を実行する場合でも Strimzi を実行する場合でも、cluster が健全であることを把握するには、broker metrics と consumer lag の継続的な可視性が必要です。これが [パート 7: Monitoring](./07-monitoring.md) のテーマです。

[メインページに戻る](./)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md) に挑戦してください。
