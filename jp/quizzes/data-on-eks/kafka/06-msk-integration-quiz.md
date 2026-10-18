# MSK統合クイズ

MSKの提供形態、IAMとネットワーク、MSK Connect、Kinesisとの違いを確認します。

## 1. MSKとEKS上のStrimziはどう異なり、どの責任が引き続き必要ですか？

<details>
<summary>解答を表示</summary>

MSKではブローカーがEKS外のAWS管理インフラ上で稼働し、Strimziでは利用者のKubernetes環境内で稼働します。どちらを選んでも、アプリケーション、topicと保持期間、アクセス制御、復旧方法の設計が必要です。

</details>

## 2. throughputだけを見ていると見落としやすい、MSK Serverlessの課金項目は何ですか？

<details>
<summary>解答を表示</summary>

データの入出力や該当するネットワーク料金に加え、cluster hours、partition hours、使用中のstorageも考慮します。自動スケーリングにはservice quotaがあり、常に最も安価とは限りません。

</details>

## 3. EKS PodからMSK IAM accessを利用するには、どのような認証経路が必要ですか？

<details>
<summary>解答を表示</summary>

Pod IdentityやIRSAなどでroleとtrustを設定し、一時認証情報を取得・更新する仕組み、対応するKafka helper、network/TLS接続、data-plane権限を用意します。External Secrets Operatorやnodeから継承したroleだけでは、これらの要件を満たせません。

</details>

## 4. 別のVPCからMSKに接続する方法は、peeringとTransit Gatewayだけですか？

<details>
<summary>解答を表示</summary>

いいえ。サポート対象のMSK multi-VPC private connectivityではPrivateLinkを利用できます。同じRegion内であること、認証方式とAZ/subnetの要件を満たすこと、実際のendpointを確認してください。public accessは必須ではありません。

</details>

## 5. VPCを共有しIAM policyも設定すれば、接続が保証されますか？

<details>
<summary>解答を表示</summary>

いいえ。DNS、route、security group、NACL、egress、実際のsource identity、brokerがadvertiseするすべてのaddressを確認してください。TCP/TLS接続が成立しなければ、IAM認証も成功しません。既存のsecurity group ruleも確認します。

</details>

## 6. ネットワーク経由で到達できるStrimzi listenerなら、MSK Connectですぐに利用できますか？

<details>
<summary>解答を表示</summary>

いいえ。現在のcluster-authentication APIが提供するのはNONE/IAMです。brokerのtrustと認証方式、worker設定を一致させる必要があります。TLS/SCRAM listenerのaddressを指定するだけで利用できるとは限りません。

</details>

## 7. Kafkaのbootstrap.serversをKinesis endpointに変更すれば、clientは互換性を持ちますか？

<details>
<summary>解答を表示</summary>

いいえ。Kinesis Data Streamsは独自のAPIを使用します。key、record、retry、checkpointを橋渡しするには、connectorまたはstream-processing layerが必要です。

</details>

## 8. KafkaをLambdaやFirehoseと統合するには、Connectだけを使いますか？

<details>
<summary>解答を表示</summary>

いいえ。MSKにはLambdaとFirehoseのネイティブ統合機能もあります。KafkaとKinesisの橋渡しは別の作業であり、runtime、format、順序、重複処理を検証する必要があります。

</details>

## 9. GitOpsを使うには、MSKではなくStrimziを選ぶ必要がありますか？

<details>
<summary>解答を表示</summary>

いいえ。MSK APIやIaCもGitOpsに組み込めます。Strimziを選ぶ場合は、必要な構成、portability、運用能力に加えて、storage、network、identityへの依存関係も評価してください。

</details>

## 10. MSK ExpressはServerlessとどう異なりますか？

<details>
<summary>解答を表示</summary>

ExpressはProvisionedのbroker typeで、選択したbroker computeを使います。storageは使用量に応じて課金され、自動的に拡張します。3 AZと各featureの要件を確認し、broker-hour、data-in、storage、その他該当する費用を比較してください。

</details>

## 11. Javaと非Javaのclientでは、どのMSK IAM SASL mechanismを利用できますか？

<details>
<summary>解答を表示</summary>

JavaではAWS_MSK_IAMまたはOAUTHBEARERを使用できます。Python、JavaScript、Go、.NETでは、AWS公式のsigner/helperとともにOAUTHBEARERを使用します。すべての言語でAWS_MSK_IAMを一律に設定しないでください。

</details>

## 12. aws-msk-iam-authを追加するだけで、IAM認証は完了しますか？

<details>
<summary>解答を表示</summary>

いいえ。Java helperは設定したmechanismを実装しますが、利用可能なroleのcredentialと更新の仕組み、trust、data権限、network接続、TLSも必要です。非Java clientでは、該当言語に対応するAWS公式helperを使用します。

</details>

## 13. MSK Connectのruntime versionとplugin更新で重要な点は何ですか？

<details>
<summary>解答を表示</summary>

文書化されている組み合わせはConnect 2.7.1/Java 11と3.7.x/Java 17です。これらはbroker versionとは異なるため、bytecodeだけでなく依存関係とAPIも検証してください。pluginは作成時にS3の内容をコピーするので、objectを上書きしてもpluginは更新されません。

</details>

## 14. Kafkaのpartition数を増やす場合と、Kinesisのcapacity modeを比較してください。

<details>
<summary>解答を表示</summary>

Kafkaのpartition数を増やしても、既存recordは再配置されず、partition数をその場で減らすこともできません。Kinesisはshardを使い、Provisioned、On-demand Standard、On-demand Advantageの各modeを区別します。

</details>

## 15. Serverlessの標準retentionを「7日間」とだけ説明すると不十分なのはなぜですか？

<details>
<summary>解答を表示</summary>

defaultのretention.bytesはpartitionあたり250 GiBのため、保持期間の上限より先にサイズ上限へ達することがあります。保持期間、サイズ、cleanup policy、serviceの制約を合わせて確認してください。Kinesis Data Streamsのdefaultは24時間で、最大365日まで設定できます。

</details>

## 16. 同じVPC内でprivate IPv4のIAM accessを許可するsecurity group commandを書き、その適用範囲を説明してください。

<details>
<summary>解答を表示</summary>

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

実際のnode/pod source security groupを指定し、既存ruleも確認してください。IPv6、public、multi-VPC endpointではportが異なる場合があるため、bootstrap responseを確認します。このcommandはsecurity groupを変更します。

</details>

## 17. orders producerとorders-consumerのpolicyには、どの権限が必要ですか？

<details>
<summary>解答を表示</summary>

policies.pyを使い、正確なcluster ARN/UUIDからpolicyを生成します。producerにはclusterのConnect/WriteDataIdempotentlyと、ordersのDescribeTopic/WriteDataを許可します。consumerにはclusterのConnect、ordersのDescribeTopic/ReadData、そのconsumer groupのDescribeGroup/AlterGroupを許可します。AlterClusterと*Topic*は不要です。transactionには、scopeを絞ったtransactional-ID権限を別途設計してください。

</details>

## 18. Java AWS_MSK_IAM propertiesと、追加で必要なものを書いてください。

<details>
<summary>解答を表示</summary>

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

選択したbootstrap.servers、serializer/deserializer、consumer group.idも設定してください。JVMのCA trust、workload credential、IAM権限、network接続が必要です。hostname verificationは有効のままにしてください。

</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/06-msk-integration.md) | [次のクイズ](./07-monitoring-quiz.md)
