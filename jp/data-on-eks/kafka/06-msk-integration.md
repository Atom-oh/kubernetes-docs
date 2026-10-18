# Part 6: MSK との統合

> **レビュー対象の基準**: MSK Standard/Express Provisioned、MSK Serverless、MSK Connect、Java IAM helper 2.3.9\
> **最終レビュー日**: 2026年10月16日

## 責任範囲と前提条件

Amazon MSK は、AWS が管理するインフラストラクチャ上で EKS クラスターの外部に Kafka ブローカーを実行します。Strimzi は、チームが運用する Kubernetes ワークロードとしてブローカーを実行します。いずれの場合も、アプリケーション、トピック、アクセス制御、保持、復旧についての判断が必要です。マネージドブローカーを使っても、Kafka の動作を理解する必要はなくなりません。

EKS クラスターと互換性のある AWS CLI v2 と kubectl を使ってください。IAM クライアントには、サポート対象の認証ヘルパーと、正常に機能するワークロード認証情報チェーンが必要です。EKS Pod Identity または IRSA で一時認証情報を提供できます。External Secrets Operator は、別のシークレット管理ワークフローで使う任意の構成要素であり、IAM の前提条件ではありません。

## 実際の MSK バリエーションを比較する

| 選択肢 | キャパシティと構成 | 含めるコスト |
| --- | --- | --- |
| MSK Provisioned Standard | ブローカー数とストレージを選択します。必要に応じてストレージの自動スケーリングを設定します。編集できるのはサポート対象のブローカー設定だけです。 | ブローカー稼働時間、プロビジョニング済みストレージ、任意のスループット/階層型ストレージ、ネットワーク |
| MSK Provisioned Express | ブローカーのコンピューティング容量を選択します。ストレージは自動的に拡張され、使用量に応じて課金されます。構成とスループットには強制されるガードレールがあります。 | ブローカー稼働時間、データ取り込み、使用ストレージ、該当するネットワーク料金 |
| MSK Serverless | ブローカー容量は AWS が管理します。利用者はトピック、パーティション、保持、サービスクォータを計画します。 | **クラスター稼働時間**、パーティション稼働時間、データ入出力、使用ストレージ、該当するネットワーク料金 |
| EKS 上の Strimzi | ノード、ディスク、ブローカー/コントローラーのトポロジー、サポート対象 Operator 構成を運用します。 | EKS/EC2/EBS、ネットワーク、予備キャパシティ、可観測性、運用工数 |

Express は **Provisioned のブローカータイプ**であり、Serverless ではありません。現在のドキュメントでは 3 つの AZ が必要とされ、KStreams のサポートが未完了、KIP-932 は非対応など、API/機能上の制約が示されています。すべての Kafka 機能が同じように使えると想定せず、ブローカーとバージョンのサポート組み合わせを確認してください。

Serverless では IAM 認証/認可が必要で、Kafka ACL はサポートされません。設定できるトピック設定は限られています。たとえば保持期間は変更できますが、`cleanup.policy` はトピック作成時にのみ設定できます。既定の保持には 7 日間だけでなく、**パーティションあたり 250 GiB の上限**もあります。時間制限に達する前にデータ量が上限に達する可能性があります。キャパシティの自動スケーリングがあっても、パーティション数やバースト率が無制限になるわけではありません。

これらのサービスには CloudWatch メトリクスがありますが、Serverless の監視機能は Provisioned と同じブローカーレベルの Prometheus/open-monitoring インターフェイスではありません。Serverless のマルチテナンシーでは、トピック/グループの IAM ポリシーも利用者の責任です。Strimzi では、Kubernetes namespace だけで Kafka トピックへのアクセスが認可されるわけではありません。

MSK は API や Infrastructure as Code で管理できます。GitOps は Strimzi 専用ではありません。Strimzi の展開を移植できるかどうかも、ストレージ、ネットワーク、ID、サポート対象 Operator バージョンに依存します。測定した総コストと復旧要件を比較してください。「大規模ならセルフマネージドが常に安い」「急増時は Serverless が最安」という考え方を既定の判断にしないでください。

## EKS からのネットワーク接続

クライアントは、ブートストラップアドレスだけでなく、メタデータで通知された**すべてのブローカーエンドポイント**に到達できる必要があります。DNS、ルート、セキュリティグループ、NACL、Pod/ノードの送信元 ID、egress を検証してください。VPC を共有しているだけでは十分ではありません。

VPC が異なる場合は、ルーティングされた VPC ピアリング/Transit Gateway や、PrivateLink を使うサポート対象 MSK **マルチ VPC プライベート接続**などを選べます。マネージドのマルチ VPC 機能には、同一リージョンであることや、クラスター、認証、AZ サブネットに関する要件があります。パブリックエンドポイントは明示的に選択できるサポート対象クラスターのオプションであり、VPC 間接続の前提条件ではありません。

| 直接接続するエンドポイントの例 | ポート |
| --- | --- |
| プライベート IPv4 TLS | 9094 |
| プライベート IPv4 SASL/SCRAM | 9096 |
| プライベート IPv4 IAM | 9098 |
| パブリック TLS / SCRAM / IAM（サポート対象で有効な場合） | 9194 / 9196 / 9198 |

IPv6 とマネージドマルチ VPC のエンドポイントでは、異なるポートが使われる場合があります。実際のブートストラップ応答を取得し、意図するネットワーク/認証経路に対応するフィールドを選んでください。すべてのエンドポイントを 9098 に書き換えないでください。

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing cluster ARN}"
aws kafka get-bootstrap-brokers \
  --region "$DOCS_AWS_REGION" \
  --cluster-arn "$DOCS_MSK_CLUSTER_ARN"
```

同一 VPC からプライベート IPv4 の IAM エンドポイントに直接接続する場合、ネットワーク管理者は既存ルールを確認したうえで、次のように範囲を限定した例を適用できます。

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_SG_ID:?Set the existing MSK security group ID}"
: "${DOCS_EKS_SOURCE_SG_ID:?Set the actual EKS source security group ID}"
# Example: same-VPC, direct private IPv4 IAM endpoint on port 9098.
aws ec2 authorize-security-group-ingress \
  --region "$DOCS_AWS_REGION" \
  --group-id "$DOCS_MSK_SG_ID" \
  --protocol tcp --port 9098 \
  --source-group "$DOCS_EKS_SOURCE_SG_ID"
```

このコマンドはセキュリティグループを**変更します**。ネットワーク経路に実際に使うノード/Pod の送信元 SG を指定してください。異なる VPC 間の SG 参照には個別のサポート条件があります。既存 SG には自己参照ルールなどがすでに設定されている場合があります。IAM 認証を行う前に、TCP/TLS 接続が確立している必要があります。

## IAM 認証とワークロード ID

| クライアント | サポートされる IAM の仕組み |
| --- | --- |
| Java | `AWS_MSK_IAM`、または AWS Java helper を使った `OAUTHBEARER` |
| Python、JavaScript、Go、.NET | 対応する公式 AWS signer/helper を使った `OAUTHBEARER` |

`AWS_MSK_IAM` は、あらゆる言語の Kafka クライアントが提供する汎用メカニズムではありません。Java 以外の helper も、コミュニティ製の代替品ではなく AWS 公式プロジェクトです。Provisioned クラスターでは SCRAM や相互 TLS も利用できる場合があります。その場合はサポート対象のシークレット/証明書と Kafka ACL の手順を構成してください。これらは Serverless における IAM の代わりにはなりません。

Kafka をテストする前に、ワークロードのロール関連付け/信頼ポリシーと一時認証情報の更新を構成してください。継承されたノードロールが Pod に意図した ID だと想定しないでください。プライベート環境では、選択した認証情報プロバイダーに必要な ID サービスへの接続も必要です。認証情報が更新された後の再認証をテストしてください。Java helper は、Pod Identity を含む一部のプロバイダーでセッション名の一貫性に関する問題を説明しています。その問題が発生した場合は、文書化された回避策を適用してください。

### Producer と consumer のポリシーを分ける

次のスクリプトは、既存クラスター ARN から正確なリソース ARN を導出します。`policies.py` として保存してください。ポリシーをローカルに書き出しますが、IAM にはアタッチしません。古い `AlterCluster` と `*Topic*` 管理権限を除外し、consumer-group アクションを含めています。また、冪等書き込みに必要なクラスター範囲の権限と、トピック範囲の書き込み権限を区別します。

```python
import json
import re
import sys
from pathlib import Path

def policies(cluster_arn, topic="orders", group="orders-consumer"):
    match = re.fullmatch(
        r"arn:(aws(?:-[a-z-]+)?):kafka:([a-z0-9-]+):(\d{12}):cluster/([A-Za-z0-9_-]+)/([A-Za-z0-9-]+)",
        cluster_arn,
    )
    if not match:
        raise ValueError("Supply an exact MSK cluster ARN, including its cluster UUID.")
    for name in [topic, group]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", name) or name in [".", ".."]:
            raise ValueError("Use an explicit topic/group name without wildcards.")
    partition, region, account, cluster_name, uuid = match.groups()
    prefix = f"arn:{partition}:kafka:{region}:{account}:"
    identity = f"{cluster_name}/{uuid}"
    topic_arn = prefix + f"topic/{identity}/{topic}"
    group_arn = prefix + f"group/{identity}/{group}"
    def statement(actions, resource):
        return {"Effect": "Allow", "Action": ["kafka-cluster:" + a for a in actions], "Resource": resource}
    return {
        "producer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect", "WriteDataIdempotently"], cluster_arn),
            statement(["DescribeTopic", "WriteData"], topic_arn),
        ]},
        "consumer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect"], cluster_arn),
            statement(["DescribeTopic", "ReadData"], topic_arn),
            statement(["DescribeGroup", "AlterGroup"], group_arn),
        ]},
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 policies.py EXACT_MSK_CLUSTER_ARN")
    for name, policy in policies(sys.argv[1]).items():
        Path(f"msk-{name}-policy.json").write_text(json.dumps(policy, indent=2) + "\n")
```

```bash
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing MSK cluster ARN}"
python3 policies.py "$DOCS_MSK_CLUSTER_ARN"
# Review msk-producer-policy.json and msk-consumer-policy.json,
# then attach each to the appropriate workload role through your IAM workflow.
```

既存のトピック名は `orders`、consumer が使うグループ名は `orders-consumer` です。トピックの作成には、別の管理者 ID を使ってください。producer ポリシーは、文書化された IAM アクションの組み合わせを使った**非トランザクションの冪等書き込み**を対象とします。トランザクション producer には、範囲を限定した transaction-ID アクションと互換性のあるブローカーサポートも必要です。IAM は MSK Kafka 3.8 以降の `WriteTxnMarkers` をサポートします。認可エラーを隠すために、すべての transaction ID を許可したり、冪等性を無効にしたりしないでください。

実効アクセスは、他にアタッチされたポリシー、明示的な拒否、SCP、権限境界、クロスアカウントのリソースポリシーにも依存します。ここにある文書だけで認可境界が完成するわけではありません。`kafka:GetBootstrapBrokers` などの MSK コントロールプレーン操作は、`kafka-cluster:*` データプレーン操作とは別です。これらはデプロイ担当者/Operator の ID に付与できます。

### Java クライアントの構成

`software.amazon.msk:aws-msk-iam-auth:2.3.9` と依存ライブラリを追加するか、検証済みリリースの all-in-one JAR を使ってください。次の内容を `iam.properties` として保存します。

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Java の OAuth メカニズムでは、2 つを組み合わせず、次の設定を代わりに使ってください。

```properties
security.protocol=SASL_SSL
sasl.mechanism=OAUTHBEARER
sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
sasl.login.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
ssl.endpoint.identification.algorithm=https
```

アプリケーションに選択した `bootstrap.servers`、key/value の serializer または deserializer、consumer の `group.id` を追加してください。JVM はブローカーの TLS 証明書チェーンを信頼する必要があります。ホスト名検証を有効のままにしてください。これらのプロパティが構成するのは認証メカニズムであり、不足しているワークロード認証情報や IAM 権限を作成するものではありません。

## MSK Connect: デプロイ前に互換性を確認する

MSK Connect はマネージド Kafka Connect worker を実行し、別の場所でホストされた Kafka クラスターを接続先にできます。**ネットワーク到達性だけでは不十分です。** 現在の `KafkaClusterClientAuthentication` API が受け付けるのは `NONE` または `IAM` です。ブローカーの信頼設定、認証、サポート対象 worker 設定が一致する必要があります。Part 2 の TLS/SCRAM Strimzi listener は、ホスト名が解決できても、そのまま接続できるわけではありません。統合のために認証を削除しないでください。

サービスのドキュメントに記載された Connect runtime は **2.7.1 / Java 11** と **3.7.x / Java 17** です。これらは Kafka ブローカーのバージョンや Part 5 で使った Kafka 4.3.1 Connect runtime とは異なります。plugin の bytecode、依存関係、Connect API、ベンダーのサポート表を確認してください。Java 17 でロードできる JAR でも、選択したマネージド runtime で統合テストが必要です。

Part 5 の成果物に Java 17 より上の base class はありませんが、**それだけでは** MSK Connect との互換性は証明されません。次の例は互換性を確認した後、Aiven 3.4.3 ZIP を登録します。対象リージョン内の既存プライベート S3 バケットと、plugin のアップロード/登録権限があることを前提とします。

```bash
: "${DOCS_AWS_REGION:?Set the target region}"
: "${DOCS_PLUGIN_BUCKET:?Set an existing private S3 bucket in that region}"
DOCS_PLUGIN_ZIP="s3-sink-connector-for-apache-kafka-3.4.3.zip"
DOCS_PLUGIN_KEY="plugins/aiven-s3/3.4.3/${DOCS_PLUGIN_ZIP}"
# Download the reviewed release artifact and verify its published digest first.
aws s3 cp "$DOCS_PLUGIN_ZIP" "s3://${DOCS_PLUGIN_BUCKET}/${DOCS_PLUGIN_KEY}" \
  --region "$DOCS_AWS_REGION"
export DOCS_PLUGIN_BUCKET DOCS_PLUGIN_KEY
python3 - <<'PY'
import json
import os
from pathlib import Path
Path("custom-plugin.json").write_text(json.dumps({
    "name": "aiven-s3-3-4-3-reviewed",
    "contentType": "ZIP",
    "location": {"s3Location": {
        "bucketArn": "arn:aws:s3:::" + os.environ["DOCS_PLUGIN_BUCKET"],
        "fileKey": os.environ["DOCS_PLUGIN_KEY"]
    }}
}, indent=2) + "\n")
PY
aws kafkaconnect create-custom-plugin \
  --region "$DOCS_AWS_REGION" \
  --cli-input-json file://custom-plugin.json
```

これは **plugin をアップロードして登録する処理**であり、稼働中の connector を作成するものではありません。connector の作成には、サービス実行ロール、Kafka/ネットワーク設定、ソース/宛先への権限、キャパシティ、converter の構成も必要です。MSK Connect の key/value converter の既定値は StringConverter です。CDC の例で使う JSON schema-envelope 設定は、意図的に構成してください。

MSK Connect は plugin 作成時に S3 オブジェクトをコピーします。S3 オブジェクトを上書きしても plugin は更新されず、custom plugin をその場で編集することもできません。新しいバージョンの plugin リソースと、テスト済みの connector 切替手順を使ってください。稼働中のデータパイプラインを置き換える前に offset を保持して検証してください。自動スケーリングには設定済みの上限があり、単一タスクの source を並列化することもありません。

## Kafka と Kinesis Data Streams

Kinesis Data Streams には独自の API があります。`bootstrap.servers` を Kinesis エンドポイントに置き換えても、Kafka クライアントを変換することはできません。connector または明示的なストリーム処理ブリッジで、レコード、キー、再試行動作、チェックポイントを変換する必要があります。

| 観点 | Kafka / MSK / Strimzi | Kinesis Data Streams |
| --- | --- | --- |
| 並列度 | トピックパーティション。数を増やしても既存レコードは再分散されず、その場で減らすこともできません。 | シャード。Provisioned では手動でサイズを決め、on-demand モードではサービスが容量を管理します。 |
| キャパシティの選択肢 | Standard、Express、Serverless、セルフマネージドの展開方式によって異なります。 | Provisioned、On-demand Standard、On-demand Advantage。 |
| 保持 | トピック/サービス設定、ストレージ、cleanup policy によります。時間とサイズの両方の上限が重要です。 | 既定は 24 時間。最大 365 日まで設定できます。 |
| AWS 連携 | MSK とのネイティブな Lambda/Firehose 連携や connector を含みます。 | Lambda、Firehose、Managed Service for Apache Flink とネイティブに連携します。 |

「Kafka は Connect 経由でしか AWS と連携できない」という説明は正しくありません。また、Kinesis Data Analytics ではなく、現在のサービス名 **Amazon Managed Service for Apache Flink** を使ってください。ブリッジでは Kinesis sink が Kafka のレコードを Kinesis に書き込み、source は逆方向にデータを流します。選択した runtime と互換性のある、メンテナンスされている plugin を選び、順序、パーティションキーの動作、レコードサイズ上限、重複処理をテストしてください。プロトコルが異なるからといって、全用途に共通するブリッジ製品が決まるわけではありません。

## 選択肢を決める

必要な Kafka API、データレートと偏り、パーティション/保持の上限、レイテンシー、復旧目標、コンプライアンス、チームの運用能力、総コストから検討してください。リージョンとブローカーバージョンの現行サポートを確認してください。MSK と Strimzi のどちらにも IaC/GitOps を使えます。後からサービスを変更する場合は、データ、スキーマ、ID、consumer offset の明示的な移行が必要です。自動的に簡単で一般的な次の手順になるわけではありません。

## 参考資料と検証範囲

ポリシー生成、Java class/JAAS 構成、plugin bytecode、CLI リクエストの形はローカルで確認できます。こうした確認だけでは、実効 IAM 認可、ワークロード認証情報の更新、ブローカーアクセス、マネージド connector のデプロイやデータ配信は証明できません。

- [MSK Express ブローカー](https://docs.aws.amazon.com/msk/latest/developerguide/msk-broker-types-express.html)
- [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Serverless の構成](https://docs.aws.amazon.com/msk/latest/developerguide/serverless-config.html)
- [MSK の料金項目](https://aws.amazon.com/msk/pricing/)
- [MSK のマルチ VPC プライベート接続](https://docs.aws.amazon.com/msk/latest/developerguide/aws-access-mult-vpc.html)
- [MSK のポート情報](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [IAM クライアントの仕組みと公式言語別 helper](https://docs.aws.amazon.com/msk/latest/developerguide/configure-clients-for-iam-access-control.html)
- [MSK IAM アクションとリソースの依存関係](https://docs.aws.amazon.com/msk/latest/developerguide/kafka-actions.html)
- [IAM の利用例](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html)
- [aws-msk-iam-auth 2.3.9](https://github.com/aws/aws-msk-iam-auth/tree/v2.3.9)
- [MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html)
- [MSK Connect の plugin パッケージと Java バージョン](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-plugins.html)
- [MSK Connect クライアント認証 API](https://docs.aws.amazon.com/MSKC/latest/mskc/API_KafkaClusterClientAuthentication.html)
- [MSK と Lambda の統合](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)
- [MSK と Firehose の統合](https://docs.aws.amazon.com/msk/latest/developerguide/integrations-kinesis-data-firehose.html)
- [Kinesis のキャパシティモード](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Kinesis のデータ保持](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)

## 次のステップ

[Part 7: モニタリング](./07-monitoring.md)

[メインページに戻る](./README.md)

## クイズ

[トピッククイズ](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
