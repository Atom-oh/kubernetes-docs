# MSK Integration Quiz

このクイズでは、Amazon MSK と EKS 上の self-managed Strimzi のトレードオフ、EKS workloads から MSK への接続方法、MSK Connect、および Kafka と Kinesis Data Streams の違いについての理解を確認します。

## Multiple Choice Questions

1. Amazon MSK と EKS 上の self-managed Strimzi の最も根本的な違いは何ですか？
   - A) MSK は Kafka protocol を使用しない
   - B) broker が実際にどこで実行され、誰がそれらの運用責任を負うか
   - C) Strimzi は Kubernetes 上で実行できない
   - D) MSK は partition の概念をサポートしていない

<details>

<summary>解答を表示</summary>

**解答: B) broker が実際にどこで実行され、誰がそれらの運用責任を負うか**

**解説:**
MSK は AWS-managed infrastructure 上で broker を実行し、AWS が patching、hardware replacement、storage expansion を代わりに処理します。Strimzi は EKS cluster 内の Pod として broker を実行します。Operator が rolling upgrade や reconciliation を自動化していても、upgrade のタイミング、capacity planning、incident response などの判断は引き続き利用者の責任です。どちらも同じ Apache Kafka protocol を実装しているため、protocol level の違いはありません。
</details>

2. MSK Serverless を正しく説明している文はどれですか？
   - A) Broker configuration (`server.properties`) は自由にカスタマイズできる
   - B) Broker sizing はユーザーに公開されず、課金は throughput based である
   - C) ZooKeeper-based cluster でのみ動作する
   - D) MSK Provisioned より常に安い

<details>

<summary>解答を表示</summary>

**解答: B) Broker sizing はユーザーに公開されず、課金は throughput based である**

**解説:**
MSK Serverless は partition ごとに auto-scale し、ユーザーが broker count や instance type を意識することはありません。代わりに、partition ごと、入出力 GB ごとの throughput に基づいて課金されます。Custom broker configuration はサポートされておらず、一部の API/feature（特定の ACL type、connector type）は制限されています。Provisioned より安いかどうかは traffic pattern に依存するため、常に安いとは想定できません。
</details>

3. 別個の IAM credentials を配布せずに、EKS pod が MSK broker に認証できる組み合わせはどれですか？
   - A) Secrets Manager を使用した SASL/SCRAM
   - B) `AWS_MSK_IAM` SASL mechanism を使用した IRSA
   - C) AWS Private CA を使用した mTLS
   - D) security group のみを使用した plaintext listener

<details>

<summary>解答を表示</summary>

**解答: B) `AWS_MSK_IAM` SASL mechanism を使用した IRSA**

**解説:**
IRSA (IAM Roles for Service Accounts) は pod に IAM role を付与し、Kafka client で `sasl.mechanism=AWS_MSK_IAM` を設定すると、SigV4-signed request を使用して認証します。主な利点は、password や certificate など、配布または rotate すべき別個の credentials が存在しないことです。SASL/SCRAM と mTLS も有効な authentication method ですが、それぞれ Secrets Manager から credentials を同期する、または certificate を発行して mount する必要があります。
</details>

4. 異なる VPC にある MSK cluster に EKS workload が到達するために必要な network configuration は何ですか？
   - A) MSK は必ず public access に切り替える必要がある
   - B) VPC peering または AWS Transit Gateway で 2 つの VPC を接続する必要がある
   - C) Kafka protocol は自動的に VPC 境界を越える
   - D) NAT gateway だけで十分であり、追加設定は不要である

<details>

<summary>解答を表示</summary>

**解答: B) VPC peering または AWS Transit Gateway で 2 つの VPC を接続する必要がある**

**解説:**
EKS cluster と MSK cluster が異なる VPC にある場合、それらの間の routing を確立するために VPC peering または Transit Gateway が必要です。MSK は public access もサポートしていますが、これは任意の別設定であり、本番環境では一般的に security の理由から private connectivity が好まれます。network path があっても、MSK cluster の security group が EKS node/pod security group からの inbound traffic を許可していなければ、connectivity はブロックされます。
</details>

5. MSK cluster の security group configuration について正しい文はどれですか？
   - A) 同じ VPC 内のすべての traffic は default で許可される
   - B) broker port への inbound traffic は EKS node（または pod）の security group から明示的に許可する必要がある
   - C) IAM authentication を使用する場合、security group は不要である
   - D) security group configuration は MSK Serverless にのみ適用される

<details>

<summary>解答を表示</summary>

**解答: B) broker port への inbound traffic は EKS node（または pod）の security group から明示的に許可する必要がある**

**解説:**
MSK cluster の security group は、default では inbound traffic を許可しません。関連する broker port（plaintext 9092、TLS 9094、SASL/SCRAM 9096、IAM 9098）について、EKS worker node（または per-pod security group を使用している場合は pod）の security group を source として許可する inbound rule を明示的に追加する必要があります。この network layer の security group rule は、使用する authentication mechanism（IAM、SCRAM、mTLS）に関係なく必要です。
</details>

6. MSK Connect について正しい文はどれですか？
   - A) MSK cluster にのみ接続でき、他の Kafka cluster には接続できない
   - B) bootstrap broker への network reachability があれば、EKS 上の Strimzi cluster に対して connector を実行することもできる
   - C) ユーザーは Connect worker の scaling と patching を自分で管理する必要がある
   - D) Connector plugin は container image としてのみ登録できる

<details>

<summary>解答を表示</summary>

**解答: B) bootstrap broker への network reachability があれば、EKS 上の Strimzi cluster に対して connector を実行することもできる**

**解説:**
MSK Connect は MSK cluster に限定されていません。connector が network 経由で bootstrap broker に到達できる限り、EKS 上の self-managed Strimzi cluster を含む任意の Kafka cluster を接続先にできます。AWS は Connect worker infrastructure の provisioning、scaling、patching を管理するため、ユーザーがそれを自分で管理する必要はありません。Custom connector plugin は、JAR の ZIP を S3 に upload して登録します。
</details>

7. Kafka と Kinesis Data Streams の関係を正しく説明している文はどれですか？
   - A) MSK は「Kafka-compatible」なので、Kinesis client は MSK に直接接続できる
   - B) Kafka と Kinesis は異なる protocol を使用する別個の service であり、直接互換性はない
   - C) Kinesis は内部で Kafka protocol をそのまま実装している
   - D) Kafka client は configuration を変更するだけで Kinesis stream に直接接続できる

<details>

<summary>解答を表示</summary>

**解答: B) Kafka と Kinesis は異なる protocol を使用する別個の service であり、直接互換性はない**

**解説:**
Kinesis Data Streams は独自の AWS proprietary API/SDK を持つ完全に別の service であり、Kafka producer/consumer protocol を理解しません。MSK が「Kafka-compatible」と説明される場合、それは Apache Kafka protocol を実装していることだけを意味し、Kinesis との interoperability を意味するものではありません。両者を bridge するには、Kafka Connect（または MSK Connect）上で動作する Kinesis sink/source connector などの別 layer が必要です。
</details>

8. Kafka と Kinesis Data Streams を実際に bridge する正しい方法は何ですか？
   - A) Kafka client の `bootstrap.servers` を Kinesis endpoint に向ける
   - B) Kafka Connect または MSK Connect 上で Kinesis sink/source connector を使用する
   - C) MSK cluster を「Kinesis mode」に切り替える configuration flag を使用する
   - D) 同じ partition model を共有しているため、互いを直接参照できる

<details>

<summary>解答を表示</summary>

**解答: B) Kafka Connect または MSK Connect 上で Kinesis sink/source connector を使用する**

**解説:**
Kafka と Kinesis は protocol 非互換であるため、それらを bridge するには translation を行う connector が必要です。Kinesis sink connector は Kafka topic から message を読み取り、Kinesis stream に書き込みます。Kinesis source connector は Kinesis stream から record を読み取り、Kafka topic に書き込みます。これらの connector は MSK Connect に deploy することも、Strimzi の `KafkaConnect`/`KafkaConnector` CR を介して EKS 上で直接実行することもできます。
</details>

9. MSK が存在するにもかかわらず、Strimzi を使用して EKS 上で Kafka を自分で運用し続ける正当な理由ではないものはどれですか？
   - A) Kafka を platform の他の部分と同じ GitOps/observability pipeline に統合したい
   - B) on-prem または multi-cloud environment への portability が必要である
   - C) MSK がまだサポートしていない新しい Kafka feature が必要である
   - D) broker operations staff をまったく持ちたくない

<details>

<summary>解答を表示</summary>

**解答: D) broker operations staff をまったく持ちたくない**

**解説:**
Self-managed Strimzi は Operator によって多くを自動化しますが、upgrade のタイミング、capacity planning、incident response などの判断は利用者の責任として残ります。broker operations の負担を完全になくしたい場合は、MSK、特に MSK Serverless の方が実際には適しています。GitOps integration、portability、最新の Kafka feature への access は、EKS 上で Strimzi を実行する正当な理由です。
</details>

10. MSK Provisioned と self-managed Strimzi の cost model の違いを最も正確に説明している文はどれですか？
    - A) MSK は常に Strimzi より安い
    - B) MSK は broker-hour と storage に基づいて課金される一方、Strimzi は直接的な EC2/EBS cost に加えて別途 operational staffing cost が発生する
    - C) Strimzi には billing model がなく、完全に無料である
    - D) 2 つの cost model は同一である

<details>

<summary>解答を表示</summary>

**解答: B) MSK は broker-hour と storage に基づいて課金される一方、Strimzi は直接的な EC2/EBS cost に加えて別途 operational staffing cost が発生する**

**解説:**
MSK Provisioned は broker-hour pricing、storage（GB-month）、data transfer に基づいて課金されます。Strimzi では EC2/EBS infrastructure の費用を直接支払います。通常、scale が大きい場合は安くなることがありますが、それを運用する staff の cost は別途追加で考慮する必要があります。total cost of ownership でどちらが有利かは、traffic volume、組織の operational capability、labor cost に依存します。
</details>

## Short Answer Questions

11. EKS pod が IAM role を使用して MSK に認証するために使う SASL mechanism の正確な名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `AWS_MSK_IAM`**

**解説:**
`AWS_MSK_IAM` は、client が SigV4-signed credentials（IAM role または user）を使用して認証できるように MSK が提供する SASL mechanism です。client configuration では、`security.protocol=SASL_SSL` と `sasl.mechanism=AWS_MSK_IAM` を設定し、`aws-msk-iam-auth` library の `IAMLoginModule` と `IAMClientCallbackHandler` を JAAS login module および callback handler として登録します。
</details>

12. IAM authentication を使用するために、MSK client が classpath（またはその言語の同等の package manager）に追加する必要がある library の名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `aws-msk-iam-auth`**

**解説:**
`aws-msk-iam-auth` は AWS が提供する client library で、`AWS_MSK_IAM` という専用の custom SASL mechanism（OAUTHBEARER extension ではありません）を実装し、Kafka client が SigV4-signed request を生成して IAM credentials で MSK broker に認証できるようにします。Java client は Maven artifact として配布され、他の言語（Python、Go など）向けには同等の community implementation が存在します。
</details>

13. AWS が connector worker の provisioning と scaling を処理する、AWS の fully managed Kafka Connect service の名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: MSK Connect**

**解説:**
MSK Connect は、AWS が Kafka Connect worker cluster の provisioning、scaling、patching を管理する service です。ユーザーは connector plugin（JAR の ZIP）を S3 に upload し、connector configuration を登録するだけです。MSK cluster だけでなく、EKS 上の Strimzi cluster を含む network reachable な任意の Kafka cluster に接続できます。
</details>

14. Kafka の「partition」に対応する Kinesis Data Streams の scaling unit の名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: Shard**

**解説:**
Kafka は parallelism と scalability のために topic を複数の partition に分割します。partition count は topic 作成時に定義され、後で repartitioning によって調整できます。一方、Kinesis は read/write capacity を shard に分割し、capacity は shard split と merge operation によって調整されます。2 つの概念は似た目的を果たしますが、API と operational mechanics が異なります。
</details>

15. Kafka topic から message を読み取り、Kinesis stream に書き込む Kafka Connect connector の type は何ですか？

<details>

<summary>解答を表示</summary>

**解答: Kinesis Sink connector**

**解説:**
Kinesis Sink connector は Kafka topic を source として扱い、message を読み取って Kinesis stream に書き込みます。逆に、Kinesis Source connector は Kinesis stream から record を読み取り、Kafka topic に書き込みます。Kafka と Kinesis には protocol compatibility がないため、両方の connector はその間で data を実際に bridge する layer として存在します。
</details>

## Hands-on Questions

16. EKS worker node security group (`sg-0efgh5678eksnode`) から MSK cluster security group (`sg-0abcd1234msk`) の IAM authentication port への inbound traffic を許可する AWS CLI command を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

**解説:**
MSK の IAM authentication port は 9098 です。`authorize-security-group-ingress` では、`--group-id` が rule を追加する target security group（MSK security group）を指定し、`--source-group` が許可する traffic source（EKS node security group）を指定します。この rule がない場合、IAM authentication の試行が成功しても、TCP connection の段階でブロックされます。別の auth mechanism を使用する場合は、それに応じて port を調整してください（TLS: 9094、SASL/SCRAM: 9096）。
</details>

17. IAM authentication を使用する Kafka client に、特定の MSK cluster 上の `orders` topic のみに対する read/write access を付与する IAM policy JSON を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
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

**解説:**
最初の statement は、cluster に接続してその state を describe するための最小権限（`Connect`、`DescribeCluster`）を付与します。2 つ目の statement は resource ARN を `topic/my-msk-cluster/*/orders` に scope し、topic-related action、write（`WriteData`）、read（`ReadData`）permission を `orders` topic のみに付与します。resource ARN をここまで厳密に scope することで、client は同じ cluster 上の他の topic に access できません。
</details>

18. `AWS_MSK_IAM` mechanism を使用するように client を構成する Kafka client configuration (properties) file を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

**解説:**
`security.protocol=SASL_SSL` は、SASL authentication と TLS encryption を併用することを指定します。`sasl.mechanism=AWS_MSK_IAM` は IAM-based SASL mechanism を選択します。`sasl.jaas.config` は `aws-msk-iam-auth` library の `IAMLoginModule` を JAAS login module として登録し、`sasl.client.callback.handler.class` は SigV4-signed request を生成する callback handler を指定します。この configuration だけで、client は IRSA 経由で注入された IAM role を含む local credential chain を使用して自動的に認証します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/06-msk-integration.md) | [次のクイズ: Monitoring](./07-monitoring-quiz.md)
