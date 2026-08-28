# Part 6: MSK との統合

> **対応バージョン**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **最終更新**: July 9, 2026

## Lab Environment のセットアップ

このドキュメントの例を実行するには、以下のツールと環境が必要です。

### 必要なツール

* AWS CLI v2（MSK cluster と IAM policy の管理用）
* kubectl v1.28 以降、および動作する EKS cluster
* `aws-msk-iam-auth` client library（IAM authentication を使用する Kafka client 用）
* External Secrets Operator または IRSA が設定された EKS cluster（credential injection 用）

前の Part では、Strimzi を使って EKS 上で Kafka を自ら実行する方法を扱いました。この Part では、EKS workload を AWS のフルマネージド Kafka service である Amazon MSK に接続する方法と、セルフマネージドの Strimzi approach とのトレードオフを扱います。また、よくある混同も解消します。Kafka と Kinesis Data Streams はどのような関係にあるのかという点です。Kinesis Data Streams は完全に別の AWS streaming service です。

## Amazon MSK とセルフマネージド Strimzi

どちらの approach でも EKS workload を Kafka と通信させられますが、broker が実際にどこで実行されるか、誰が運用するかが異なります。MSK は cluster 外の AWS 管理 infrastructure 上で broker を実行し、Strimzi は EKS cluster 内の Pod として broker を実行します。

| 観点 | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi（EKS 上のセルフマネージド） |
| --- | --- | --- | --- |
| **運用負荷** | AWS が broker の patching、hardware replacement、storage expansion を処理 | AWS が broker sizing を完全に不要にする（完全 auto-scaling） | Operator が rolling upgrade/reconciliation を自動化するが、upgrade timing、capacity planning、incident response は引き続き担当 |
| **コストモデル** | broker 時間あたり + storage（GB 月あたり）+ data transfer | throughput ベース（partition あたり、GB 入出力あたり） | 直接的な EC2/EBS コスト — 通常は大規模になるほど安価だが、運用人員コストは別途負担 |
| **Autoscaling** | storage の auto-expansion をサポート。broker scaling は manual/API 駆動 | partition ごとに完全自動で scaling。broker は概念として公開されない | Cruise Control などの tool による semi-automated 対応だが、通常は自ら開始する |
| **Custom configuration** | broker configuration（`server.properties`）を customize 可能 | custom broker config なし。一部の API/features は制限される（例: 特定の ACL type、connector type） | listener、interceptor、KRaft controller setting など、ほぼすべてを tuning 可能 |
| **Version support** | AWS が対応する Kafka version list を管理。upstream より遅れる場合がある | fixed version。version choice なし | upstream がリリースし Strimzi が対応すれば、任意の Kafka version を採用可能 |
| **Multi-tenancy** | cluster/resource policy による isolation。fine-grained customization は限定的 | tenant isolation は AWS の内部実装に委任 | namespace、`KafkaUser` ACL、custom listener により fine-grained tenancy を実現 |
| **Observability/GitOps fit** | CloudWatch/Prometheus exporter を通じて統合。AWS console が主な management surface | 同様 | platform の他の部分と同じ GitOps/observability pipeline（Argo CD、Prometheus Operator）に自然に適合 |

### MSK を選ぶ理由

* team に Kafka broker operations の深い専門知識がない、または Kafka operations を中核能力にしたくない
* すでに AWS-native operations tooling（console、IAM、CloudWatch）に大きく投資している
* traffic の予測が難しく、MSK Serverless により broker capacity planning を完全に不要にできる

### MSK があっても EKS 上で Strimzi を使って Kafka を自ら実行する理由

* platform の他の部分と**同じ tool と同じ deployment pipeline**で Kafka を管理したい — 他の workload、GitOps、Prometheus — 運用対象の AWS console/IAM surface を追加せずに済む
* 単一 cloud に縛られない**portability**が必要（on-prem、multi-cloud migration の可能性）
* 非常に大規模な場合、EC2/EBS を直接管理する方が broker 時間あたりの価格設定より cost-efficient
* MSK がまだ追随していない最新の Kafka feature（新しい KIP、custom interceptor、特定の KRaft tuning option）が必要

## EKS から MSK への接続

EKS workload が MSK broker に到達するには、network path と authentication mechanism の両方が必要です。

### ネットワークパス

* **Same VPC**: EKS cluster と MSK cluster が同じ VPC にある場合、subnet routing だけで connectivity を確保できます。最も簡単で低 latency な方法です。
* **Different VPC**: 2 つの VPC を接続するには VPC peering または AWS Transit Gateway が必要です。MSK は public access（public broker endpoint）をサポートしますが、production setup では通常 private connectivity が推奨されます。
* **Security groups**: MSK cluster の security group は、該当する broker port — plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098 — において、EKS node（または Pod 自身の security group を持つ場合は Pod）の security group からの inbound traffic を明示的に許可する必要があります。デフォルトでは何も許可されません。

```bash
# Allow the IAM auth port on the MSK security group from the EKS node security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### Authentication mechanism の比較

| Mechanism | 仕組み | EKS integration point |
| --- | --- | --- |
| **IAM authentication (`AWS_MSK_IAM`)** | client は専用 custom SASL mechanism（OAUTHBEARER extension ではない）である `AWS_MSK_IAM` を使用し、SigV4-signed request で authentication を行う。IAM policy が topic ごとの permission を制御 | IRSA により Pod に IAM role を付与 — 配布する credential は一切不要 |
| **SASL/SCRAM** | username/password ベース。credential は AWS Secrets Manager に保存 | External Secrets Operator を通じて Secrets Manager の SCRAM credential を Kubernetes Secret に sync |
| **Mutual TLS (mTLS)** | AWS Private CA が発行した client certificate。certificate により identity を検証 | cert-manager または External Secrets Operator を通じて certificate/key を Pod に mount |

IAM authentication は EKS に最も自然に適合します。IRSA（IAM Roles for Service Accounts）では、scoped IAM role を Pod に付与し、topic-level access control を IAM policy のみで表現できます。配布または rotation が必要な password や certificate はありません。

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

client 側では、`aws-msk-iam-auth` library を classpath（または使用言語向けの同等 package）に追加し、Kafka client を以下のように設定します。

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect は AWS のフルマネージド Kafka Connect offering です。AWS が Connect worker infrastructure の provisioning、scaling、patching を処理します。connector plugin（JAR bundle）は S3 に upload して登録します。

重要な点として、MSK Connect は**MSK cluster に限定されません**。bootstrap broker への network reachability があれば、MSK Connect は Strimzi を通じて EKS 上で実行されるセルフマネージド Kafka cluster に対しても connector を実行できます。

```bash
# Upload a custom connector plugin to S3 and register it as an MSK Connect custom plugin
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| 観点 | MSK Connect | Strimzi `KafkaConnect`（EKS 上で自己運用） |
| --- | --- | --- |
| **運用負荷** | AWS が worker infrastructure を管理。connector configuration のみを管理 | worker Pod の scaling、monitoring、resource tuning を自ら管理 |
| **柔軟性** | AWS がサポートする connector framework に限定 | 任意の connector、custom SMT（Single Message Transform）、sidecar を自由に使用可能 |
| **Portability** | AWS 専用 service。他環境への移行は困難 | 任意の Kubernetes cluster にそのまま portable |
| **Observability** | CloudWatch Logs/Metrics を通じた connector status | 他の EKS workload と同じ Prometheus/Grafana pipeline に統合 |

## Kinesis Data Streams との比較とブリッジ

Kinesis Data Streams と Kafka は同列に語られることが多いですが、**互換 protocol ではありません**。Kinesis は独自の API/SDK を持つ AWS-native streaming service であり、Kafka の producer/consumer protocol を理解しません。MSK が「Kafka-compatible」と説明されることは、Kinesis と interoperable であることを意味しません。MSK は Apache Kafka protocol の managed implementation であり、Kinesis は完全に別の service です。

| 観点 | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **Protocol** | open-source Kafka protocol。幅広い client/tooling ecosystem と互換 | AWS proprietary API。Kafka client とは互換性なし |
| **Scaling unit** | partition（topic 作成時に定義。repartition 可能） | shard（read/write capacity unit。split/merge により調整） |
| **Operational complexity** | broker/controller の運用が必要（MSK では AWS に offload） | 完全マネージド。server という概念がない |
| **AWS service integration** | connector（Kafka Connect、MSK Connect）経由の間接統合 | Lambda trigger、Firehose、Kinesis Data Analytics と native かつ直接統合 |
| **Ecosystem** | 幅広い open-source ecosystem: Kafka Streams、ksqlDB、Flink、Debezium | より小規模で AWS service 中心の ecosystem だが、統合はより簡単 |
| **Retention** | 実質無制限（storage にのみ課金。default は 7 日間） | default は 24 時間。最大 365 日まで延長可能（コストは増加） |

### 実際のブリッジパターン

migration のため、または legacy Kinesis consumer との bridge のために Kafka と Kinesis を実際に接続する必要がある場合、実用的な pattern は built-in protocol compatibility ではなく、**Kafka Connect（または MSK Connect）で実行する Kinesis connector**です。

* **Kinesis Sink connector**: Kafka topic から message を読み、Kinesis stream に書き込みます — Kafka-based pipeline の output を Kinesis consumption ecosystem（Lambda、Firehose）に投入する場合に有用です。
* **Kinesis Source connector**: Kinesis stream から record を読み、Kafka topic に書き込みます — 既存の Kinesis producer を維持しつつ、consumer を段階的に Kafka へ migration する場合に有用です。

これらの connector は MSK Connect に deploy するか、Strimzi の `KafkaConnect`/`KafkaConnector` CR を通じて EKS 上で直接実行できます。前の section の MSK Connect vs. Strimzi のトレードオフがここでも同様に適用されます。

## 判断ガイド

この checklist を使って、セルフマネージド Strimzi、MSK Provisioned、MSK Serverless、Kinesis の選択肢を絞り込みます。

* **team に Kafka operations の専門知識があり、fine-grained tuning/custom configuration が必要ですか？** → Yes: Strimzi（EKS 上のセルフマネージド） / No: MSK を検討
* **multi-cloud/on-prem portability は必須要件ですか？** → Yes: Strimzi / No: MSK を評価する価値あり
* **traffic は予測不能または急増し、broker capacity planning を完全に不要にしたいですか？** → Yes: MSK Serverless / No: MSK Provisioned または Strimzi
* **すでに AWS-native event processing（Lambda、Firehose）に深く投資しており、Kafka ecosystem（Kafka Streams、ksqlDB など）は不要ですか？** → Yes: Kinesis Data Streams を評価 / No: Kafka（MSK/Strimzi）を継続
* **AWS console/IAM surface を追加せず、EKS platform の他の部分と同じ GitOps pipeline で Kafka を管理したいですか？** → Yes: Strimzi / No: MSK

実際には、答えはしばしば「両方」です。新しい service はスピード重視で MSK Serverless から始め、custom tuning が必要になったら Strimzi に migration することは、よくある進め方です。

## 次のステップ

MSK と Strimzi のどちらを実行する場合でも、cluster が健全であることを把握するには broker metric と consumer lag を継続的に可視化する必要があります。これは [Part 7: モニタリング](./07-monitoring.md) のテーマです。

[メインページに戻る](./README.md)

## クイズ

この chapter で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md) に挑戦してください。
